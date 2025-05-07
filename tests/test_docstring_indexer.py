"""Unit tests for DocstringIndexer and SummarySearcher."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from kit import Repository, DocstringIndexer, SummarySearcher
from kit.vector_searcher import VectorDBBackend


class DummyBackend(VectorDBBackend):
    """In-memory VectorDB backend for testing purposes."""

    def __init__(self):
        self.embeddings = []
        self.metadatas = []

    # --- VectorDBBackend interface -------------------------------------
    def add(self, embeddings, metadatas):
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)

    def query(self, embedding, top_k):  # noqa: D401
        """Return first *top_k* stored metadatas (distance ignored)."""
        return self.metadatas[: top_k]

    def persist(self):
        # No-op for the in-memory backend
        pass


@pytest.fixture(scope="function")
def dummy_repo(tmp_path):
    """Create a temporary repository with a single Python file."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "hello.py").write_text("""def hello():\n    return 'hi'\n""")
    return Repository(str(repo_root))


def test_index_and_search(dummy_repo):
    # --- Arrange --------------------------------------------------------
    summarizer = MagicMock()
    summarizer.summarize_file.side_effect = lambda p: f"Summary of {p}"

    embed_fn = lambda text: [float(len(text))]  # very simple embedding

    backend = DummyBackend()

    indexer = DocstringIndexer(dummy_repo, summarizer, embed_fn, backend=backend)

    # --- Act ------------------------------------------------------------
    indexer.build()

    # --- Assert build() -------------------------------------------------
    # The repo contains exactly one file -> one embedding & metadata
    assert len(backend.embeddings) == 1
    assert len(backend.metadatas) == 1

    meta = backend.metadatas[0]
    assert meta["file"].endswith("hello.py")
    assert meta["summary"].startswith("Summary of")

    summarizer.summarize_file.assert_called_once()  # ensure summarizer used

    # --- Act & Assert search() -----------------------------------------
    searcher = SummarySearcher(indexer)
    hits = searcher.search("hello", top_k=5)
    assert hits
    assert hits[0]["file"].endswith("hello.py")
    assert "summary" in hits[0]
