"""Failing tests specifying desired incremental behaviour for DocstringIndexer."""

import hashlib
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kit import DocstringIndexer, Repository
from kit.cache_backends.filesystem import FilesystemCacheBackend
from kit.vector_searcher import VectorDBBackend

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "realistic_repo"


# A dummy backend that just stores things in memory for testing
# For incremental tests, we want to inspect its state.
class DummyBackend(VectorDBBackend):
    def __init__(self, persist_dir=None, collection_name=None): # Added to match Chroma's signature
        self.embeddings: list = []
        self.metadatas: list = []
        self.ids: list = []

    def add(self, embeddings, metadatas, ids):
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def upsert(self, embeddings, metadatas, ids):
        # Simple upsert: remove old if id exists, then add
        id_to_idx = {old_id: i for i, old_id in enumerate(self.ids)}
        new_embeddings, new_metadatas, new_ids = [], [], []
        for i, current_id in enumerate(ids):
            if current_id in id_to_idx:
                pass # Will be replaced by new entry
            new_embeddings.append(embeddings[i])
            new_metadatas.append(metadatas[i])
            new_ids.append(current_id)
        
        self.embeddings = [emb for i, emb in enumerate(self.embeddings) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids]
        self.metadatas = [meta for i, meta in enumerate(self.metadatas) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids]
        self.ids = [id_val for i, id_val in enumerate(self.ids) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids]
        
        self.embeddings.extend(new_embeddings)
        self.metadatas.extend(new_metadatas)
        self.ids.extend(new_ids)

    def query(self, embedding, top_k=5):
        return self.metadatas[:top_k]

    def search(self, embedding, top_k=5):
        return self.query(embedding, top_k)

    def persist(self):
        pass

    def delete(self, ids):
        indices_to_delete = {i for i, doc_id in enumerate(self.ids) if doc_id in ids}
        self.embeddings = [emb for i, emb in enumerate(self.embeddings) if i not in indices_to_delete]
        self.metadatas = [meta for i, meta in enumerate(self.metadatas) if i not in indices_to_delete]
        self.ids = [id_val for i, id_val in enumerate(self.ids) if i not in indices_to_delete]
        return len(indices_to_delete) > 0

@pytest.fixture
def realistic_repo(tmp_path: Path) -> Repository:
    # Copy fixture to a temporary directory so tests can modify it
    repo_path = tmp_path / "realistic_repo_copy"
    shutil.copytree(FIXTURE_REPO, repo_path)
    return Repository(str(repo_path))


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_incremental_indexing(realistic_repo):
    """Initial build -> modify one file -> rebuild should only upsert that file's symbols."""
    repo_path = Path(realistic_repo.repo_path)
    # Default cache and vector DB paths will be within repo_path/.kit_cache/
    # We'll use an explicit FilesystemCacheBackend to control its path for the test if needed for assertions,
    # but DocstringIndexer will create its own default if cache_backend=None.
    # For this test, we want to ensure the cache mechanism works, so an explicit one is fine.
    cache_base_dir = repo_path / ".test_incremental_cache" # Base for this test's cache data
    fs_cache_dir = cache_base_dir / "docstring_cache"
    fs_cache_dir.mkdir(parents=True, exist_ok=True)

    summarizer = MagicMock()
    summarizer.summarize_function.side_effect = lambda p, s: f"F-{s}"
    summarizer.summarize_class.side_effect = lambda p, s: f"C-{s}"

    def embed_fn(text: str):
        return [float(len(text))]

    backend = DummyBackend()
    cache_backend = FilesystemCacheBackend(persist_dir=str(fs_cache_dir))
    
    # Since persist_dir is removed from DocstringIndexer, we don't pass it here.
    # The dummy backend doesn't persist. The cache_backend does, to fs_cache_dir.
    indexer = DocstringIndexer(
        realistic_repo,
        summarizer,
        embed_fn,
        backend=backend,
        cache_backend=cache_backend,
    )

    # 1. initial build
    indexer.build(level="symbol", force=True)
    assert backend.add.call_count == 0 # Upsert is used
    assert backend.upsert.call_count == 1
    initial_upsert_args = backend.upsert.call_args[0]
    initial_embeddings_count = len(initial_upsert_args[0])
    # Count symbols in fixture (app.py: 2 func, 1 class; utils.py: 1 func)
    assert initial_embeddings_count == 4 

    # Reset mock for next stage
    backend.upsert.reset_mock()

    # 2. modify one file (e.g., add a comment to utils.py)
    utils_py_path = repo_path / "src" / "utils.py"
    with open(utils_py_path, "a") as f:
        f.write("\n# A new comment")

    # 3. rebuild (should be incremental)
    indexer.build(level="symbol", force=False) # Not forcing, so cache should be used
    assert backend.upsert.call_count == 1 # Should only upsert changed symbols
    incremental_upsert_args = backend.upsert.call_args[0]
    # utils.py has one function `get_user_info`. Only this one should be re-indexed.
    assert len(incremental_upsert_args[0]) == 1 
    updated_metadata = incremental_upsert_args[1][0]
    assert updated_metadata["file_path"] == "src/utils.py"
    assert updated_metadata["symbol_name"] == "get_user_info"

    # 4. No changes, rebuild (should do nothing)
    backend.upsert.reset_mock()
    indexer.build(level="symbol", force=False)
    assert backend.upsert.call_count == 0 # No calls if nothing changed
