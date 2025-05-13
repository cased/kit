"""Unit tests for DocstringIndexer and SummarySearcher."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kit import DocstringIndexer, Repository, Summarizer, SummarySearcher
from kit.vector_searcher import VectorDBBackend


class DummyBackend(VectorDBBackend):
    """In-memory VectorDB backend for testing purposes."""

    def __init__(self, persist_dir=None, collection_name=None):
        self.embeddings: list = []
        self.metadatas: list = []
        self.ids: list = []

    # --- VectorDBBackend interface -------------------------------------
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
                # Mark for removal (or update in place if we store indices)
                # For simplicity here, we'll just filter out and re-add
                pass  # Will be replaced by new entry
            new_embeddings.append(embeddings[i])
            new_metadatas.append(metadatas[i])
            new_ids.append(current_id)

        # Filter out old entries that are being updated
        self.embeddings = [
            emb for i, emb in enumerate(self.embeddings) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids
        ]
        self.metadatas = [
            meta for i, meta in enumerate(self.metadatas) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids
        ]
        self.ids = [
            id_val for i, id_val in enumerate(self.ids) if self.ids[i] not in id_to_idx or self.ids[i] not in new_ids
        ]

        self.embeddings.extend(new_embeddings)
        self.metadatas.extend(new_metadatas)
        self.ids.extend(new_ids)

    def query(self, embedding, top_k=5):
        """Return first *top_k* stored metadatas (distance ignored)."""
        return self.metadatas[:top_k]

    def search(self, embedding, top_k=5):
        # Alias query for compatibility with SummarySearcher
        return self.query(embedding, top_k)

    def persist(self):
        # No-op for the in-memory backend
        pass

    def delete(self, ids):
        indices_to_delete = {i for i, doc_id in enumerate(self.ids) if doc_id in ids}
        self.embeddings = [emb for i, emb in enumerate(self.embeddings) if i not in indices_to_delete]
        self.metadatas = [meta for i, meta in enumerate(self.metadatas) if i not in indices_to_delete]
        self.ids = [id_val for i, id_val in enumerate(self.ids) if i not in indices_to_delete]
        return len(indices_to_delete) > 0

    def count(self):  # Add count method
        return len(self.metadatas)


@pytest.fixture(scope="function")
def dummy_repo(tmp_path):
    """Create a temporary repository with a single Python file."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "hello.py").write_text("""def hello():\n    return 'hi'\n""")
    return Repository(str(repo_root))


@pytest.fixture(scope="function")
def repo_with_symbols(tmp_path):
    """Create a temporary repository with a Python file containing symbols."""
    repo_root = tmp_path / "repo_symbols"
    repo_root.mkdir()
    file_content = """
class MyClass:
    def method_one(self):
        return 'method one'

def my_function():
    return 'function one'
"""
    (repo_root / "symbols.py").write_text(file_content)
    return Repository(str(repo_root)), repo_root / "symbols.py"


def test_index_and_search(dummy_repo):
    # --- Arrange --------------------------------------------------------
    # Determine cache path within the temp directory
    _ = Path(dummy_repo.repo_path)
    # Default cache and vector DB paths will be within repo_path/.kit_cache/

    summarizer = MagicMock()
    summarizer.summarize_file.side_effect = lambda p: f"Summary of {p}"
    # Mock summarize_function as it's called by DocstringIndexer for symbol-level indexing
    summarizer.summarize_function.side_effect = (
        lambda path_str, func_name: f"Summary of function {func_name} in {path_str}"
    )
    # Add for completeness, though not strictly needed for the 'hello.py' (function only) test case
    summarizer.summarize_class.side_effect = lambda path_str, class_name: f"Summary of class {class_name} in {path_str}"

    def embed_fn(text):
        return [float(len(text))]  # very simple embedding

    backend = DummyBackend()
    # Default FilesystemCacheBackend will be used internally by DocstringIndexer
    # Its persist_dir will be repo_path/.kit_cache/docstring_cache/
    # The default ChromaDBBackend (mocked by DummyBackend here for test) will use
    # repo_path/.kit_cache/vector_db/

    indexer = DocstringIndexer(
        dummy_repo,
        summarizer,
        embed_fn,
        backend=backend,
        # No explicit cache_backend, so default FilesystemCacheBackend is used
    )

    # --- Act ------------------------------------------------------------
    # Build with default level='symbol'
    indexer.build()

    # --- Assert build() -------------------------------------------------
    # Default level is 'symbol'. 'hello.py' has one function symbol 'hello'.
    assert len(backend.embeddings) == 1
    assert len(backend.metadatas) == 1

    meta = backend.metadatas[0]
    assert meta["file_path"].endswith("hello.py")
    # Symbol level meta:
    assert meta["level"] == "symbol"
    assert meta["symbol_name"] == "hello"
    assert meta["symbol_type"] == "FUNCTION"
    assert meta["summary"].startswith("Summary of function hello")  # Check symbol summary

    # Summarize_function should be called for the 'hello' symbol
    summarizer.summarize_function.assert_called_once_with("hello.py", "hello")
    # Summarize_file should NOT be called when level='symbol'
    summarizer.summarize_file.assert_not_called()

    # --- Act & Assert search() -----------------------------------------
    searcher = SummarySearcher(indexer)
    hits = searcher.search("hello", top_k=5)
    assert hits
    assert hits[0]["file_path"].endswith(
        "hello.py"
    )  # Changed "file" to "file_path", and adjusted for direct metadata access if SummarySearcher returns it directly
    assert "summary" in hits[0]


def test_index_and_search_symbol_level(repo_with_symbols):
    dummy_repo, file_path = repo_with_symbols
    relative_file_path = str(file_path.relative_to(dummy_repo.repo_path))
    # Default cache and vector DB paths will be within dummy_repo.repo_path/.kit_cache/

    # --- Arrange --------------------------------------------------------
    mock_summarizer = MagicMock(spec=Summarizer)
    mock_summarizer.summarize_class.return_value = "Summary of MyClass"

    # Define a side_effect function for summarize_function
    def mock_summarize_func_side_effect(file_path_arg, symbol_name_or_node_path_arg, **kwargs):
        if symbol_name_or_node_path_arg == "MyClass.method_one":
            return "Summary of MyClass.method_one"
        elif symbol_name_or_node_path_arg == "my_function":
            return "Summary of my_function"
        return "Unknown function summary"  # Fallback, should not be hit in this test

    mock_summarizer.summarize_function.side_effect = mock_summarize_func_side_effect

    # Mock Repository's extract_symbols method
    # Ensure dummy_repo itself is not a mock, but its methods can be
    dummy_repo.extract_symbols = MagicMock(
        return_value=[
            {"name": "MyClass", "type": "CLASS", "node_path": "MyClass", "code": "class MyClass: pass"},
            {
                "name": "method_one",
                "type": "METHOD",
                "node_path": "MyClass.method_one",
                "code": "def method_one(self): pass",
            },  # Assuming extract_symbols gives qualified name
            {"name": "my_function", "type": "FUNCTION", "node_path": "my_function", "code": "def my_function(): pass"},
        ]
    )

    def embed_fn(text):
        return [float(len(text))]  # very simple embedding

    backend = DummyBackend()
    # Default FilesystemCacheBackend will be used.

    indexer = DocstringIndexer(
        dummy_repo,
        mock_summarizer,
        embed_fn,
        backend=backend,
    )

    # --- Act ------------------------------------------------------------
    indexer.build(level="symbol", file_extensions=[".py"], force=True)

    # --- Assert build() -------------------------------------------------
    dummy_repo.extract_symbols.assert_called_once_with(relative_file_path)

    # Check calls to summarizer
    # Order of symbol extraction might vary, so check calls without specific order if needed
    # or ensure mock_extract_symbols returns in a fixed order.
    mock_summarizer.summarize_class.assert_called_once_with(relative_file_path, "MyClass")
    assert mock_summarizer.summarize_function.call_count == 2
    mock_summarizer.summarize_function.assert_any_call(relative_file_path, "MyClass.method_one")
    mock_summarizer.summarize_function.assert_any_call(relative_file_path, "my_function")

    assert len(backend.embeddings) == 3
    assert len(backend.metadatas) == 3
    assert len(backend.ids) == 3

    expected_ids = [
        f"{relative_file_path}::MyClass",
        f"{relative_file_path}::MyClass.method_one",
        f"{relative_file_path}::my_function",
    ]
    assert sorted(backend.ids) == sorted(expected_ids)

    for meta in backend.metadatas:
        assert meta["level"] == "symbol"
        assert meta["file_path"] == relative_file_path
        assert "symbol_name" in meta
        assert "symbol_type" in meta
        assert "summary" in meta
        if meta["symbol_name"] == "MyClass":
            assert meta["summary"] == "Summary of MyClass"
            assert meta["symbol_type"] == "CLASS"
        elif meta["symbol_name"] == "MyClass.method_one":
            assert meta["summary"] == "Summary of MyClass.method_one"
            assert meta["symbol_type"] == "METHOD"
        elif meta["symbol_name"] == "my_function":
            assert meta["summary"] == "Summary of my_function"
            assert meta["symbol_type"] == "FUNCTION"

    # --- Act & Assert search() -----------------------------------------
    searcher = SummarySearcher(indexer)
    hits = searcher.search("query for MyClass", top_k=3)
    assert len(hits) == 3  # DummyBackend query returns all in order

    # Assuming 'Summary of MyClass' is most similar due to simple embed_fn
    # or that the query function in DummyBackend just returns metadatas in order
    found_myclass = False
    for hit in hits:
        assert hit["level"] == "symbol"
        if hit["symbol_name"] == "MyClass":
            found_myclass = True
            assert hit["file_path"] == relative_file_path
            assert hit["summary"] == "Summary of MyClass"
    assert found_myclass, "MyClass symbol not found in search results"

    # Test default file extension handling (no specific file_extensions passed to build)
    # This assumes .py is a default handled by the repository/symbol extractor
    indexer_default_ext = DocstringIndexer(dummy_repo, mock_summarizer, embed_fn, backend=DummyBackend())
    indexer_default_ext.build(level="symbol", force=True)  # uses repo_with_symbols dummy repo
    assert len(indexer_default_ext.backend.embeddings) >= 2  # type: ignore
