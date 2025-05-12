"""Failing tests specifying desired incremental behaviour for DocstringIndexer."""

import hashlib
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kit import DocstringIndexer, Repository
from kit.vector_searcher import VectorDBBackend

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "realistic_repo"


class DummyBackend(VectorDBBackend):
    """Minimal in-memory backend with delete support for tests."""

    def __init__(self):
        self.embeddings = []
        self.metadatas = []
        self.ids = []

    def add(self, embeddings, metadatas, ids=None):
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids or [str(i) for i in range(len(metadatas))])

    def query(self, embedding, top_k):
        return self.metadatas[:top_k]

    def persist(self):
        pass

    def count(self):
        return len(self.metadatas)

    def delete(self, ids):
        for _id in ids:
            if _id in self.ids:
                idx = self.ids.index(_id)
                self.ids.pop(idx)
                self.embeddings.pop(idx)
                self.metadatas.pop(idx)


@pytest.fixture(scope="function")
def realistic_repo(tmp_path):
    # Copy fixture repo to tmp so we can mutate files safely
    workdir = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, workdir)
    return Repository(str(workdir))


def _hash_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def test_incremental_indexing(realistic_repo):
    """Initial build -> modify one file -> rebuild should only upsert that file's symbols."""

    summarizer = MagicMock()
    summarizer.summarize_function.side_effect = lambda p, s: f"F-{s}"
    summarizer.summarize_class.side_effect = lambda p, s: f"C-{s}"

    def embed_fn(t):
        return [float(len(t))]

    backend = DummyBackend()
    indexer = DocstringIndexer(realistic_repo, summarizer, embed_fn, backend=backend)

    # 1. initial build
    indexer.build(level="symbol", force=True)
    initial_count = backend.count()

    # 2. mutate utils.py (append a comment)
    utils_file = Path(realistic_repo.repo_path) / "utils.py"
    utils_file.write_text(utils_file.read_text() + "\n# change\n")

    indexer.build(level="symbol")  # incremental

    # summarizer should have been called for symbols in utils.py only
    assert summarizer.summarize_function.call_count > 0
    # naive check: count unchanged (upsert not duplicate)
    assert backend.count() == initial_count

    # 3. delete models/user.py -> rebuild
    user_file = Path(realistic_repo.repo_path) / "models" / "user.py"
    user_file.unlink()

    indexer.build(level="symbol")

    # count should now be reduced (symbols from user.py removed)
    assert backend.count() < initial_count
