import os
import tempfile
from pathlib import Path

import chromadb.api.shared_system_client as _ssc
import pytest

from kit import Repository
from kit.vector_searcher import VectorSearcher


# Auto-reset Chroma global System registry between tests to avoid
# "An instance of Chroma already exists for ephemeral with different settings" errors.
@pytest.fixture(autouse=True)
def _reset_chroma_system():
    yield
    _ssc.SharedSystemClient._identifier_to_system.clear()


def dummy_embed(text):
    # Simple deterministic embedding for testing (sum of char codes)
    return [sum(ord(c) for c in text) % 1000]


def test_vector_searcher_build_and_query():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple file
        fpath = os.path.join(tmpdir, "a.py")
        with open(fpath, "w") as f:
            f.write("""
def foo(): pass
class Bar: pass
""")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index(chunk_by="symbols")
        results = vs.search("foo", top_k=2)
        assert isinstance(results, list)
        assert any("foo" in (r.get("name") or "") for r in results)
        # Test search_semantic via Repository
        results2 = repository.search_semantic("Bar", embed_fn=dummy_embed)
        assert any("Bar" in (r.get("name") or "") for r in results2)


def test_vector_searcher_multiple_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = [
            ("a.py", "def foo(): pass\nclass Bar: pass\n"),
            ("b.py", "def baz(): pass\n# just a comment\n"),
            ("empty.py", "\n"),
            ("unicode.py", "def ünicode(): pass\n"),
        ]
        for fname, content in files:
            with open(os.path.join(tmpdir, fname), "w", encoding="utf-8") as f:
                f.write(content)
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index(chunk_by="symbols")
        # Should find foo, Bar, baz, ünicode
        results = vs.search("foo", top_k=10)
        assert any("foo" in (r.get("name") or "") for r in results)
        results = vs.search("baz", top_k=10)
        assert any("baz" in (r.get("name") or "") for r in results)
        results = vs.search("Bar", top_k=10)
        assert any("Bar" in (r.get("name") or "") for r in results)
        results = vs.search("ünicode", top_k=10)
        assert any("ünicode" in (r.get("name") or "") for r in results)


def test_vector_searcher_empty_and_comment_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "c.py"), "w") as f:
            f.write("# just a comment\n\n")
        with open(os.path.join(tmpdir, "d.py"), "w") as f:
            f.write("")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index(chunk_by="symbols")
        # Should not crash or index anything meaningful
        results = vs.search("anything", top_k=5)
        assert isinstance(results, list)


def test_vector_searcher_chunk_by_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "e.py"), "w") as f:
            f.write("\n".join([f"def f{i}(): pass" for i in range(100)]))
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index(chunk_by="lines")
        results = vs.search("f42", top_k=10)
        assert isinstance(results, list)


def test_vector_searcher_search_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "f.py"), "w") as f:
            f.write("def hello(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("nonexistent", top_k=5)
        assert isinstance(results, list)
        assert all("nonexistent" not in (r.get("name") or "") for r in results)


def test_vector_searcher_top_k_bounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "g.py"), "w") as f:
            f.write("def a(): pass\ndef b(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("a", top_k=10)
        assert len(results) <= 10
        results_zero = vs.search("a", top_k=0)
        assert results_zero == [] or len(results_zero) == 0


def test_vector_searcher_edge_case_queries():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "h.py"), "w") as f:
            f.write("def edgecase(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        assert vs.search("", top_k=5) == [] or isinstance(vs.search("", top_k=5), list)
        assert isinstance(vs.search("$%^&*", top_k=5), list)


def test_vector_searcher_identical_embeddings():
    def constant_embed(text):
        return [42]

    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            with open(os.path.join(tmpdir, f"i{i}.py"), "w") as f:
                f.write(f"def func{i}(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=constant_embed)
        vs.build_index()
        results = vs.search("anything", top_k=5)
        assert len(results) == 3


def test_vector_searcher_missing_embed_fn():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "j.py"), "w") as f:
            f.write("def missing(): pass\n")
        repository = Repository(tmpdir)
        with pytest.raises(ValueError):
            repository.get_vector_searcher()


def test_vector_searcher_persistency():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "k.py")
        with open(fpath, "w") as f:
            f.write("def persist(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        # Simulate restart by creating new VectorSearcher with same persist_dir and backend
        new_vs = VectorSearcher(repository, embed_fn=dummy_embed, persist_dir=vs.persist_dir, backend=vs.backend)
        results = new_vs.search("persist", top_k=2)
        assert any("persist" in (r.get("name") or "") for r in results)


def test_vector_searcher_overwrite_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "l.py")
        with open(fpath, "w") as f:
            f.write("def first(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        with open(fpath, "a") as f:
            f.write("def second(): pass\n")
        vs.build_index()
        results = vs.search("second", top_k=2)
        assert any("second" in (r.get("name") or "") for r in results)


def test_vector_searcher_similar_queries():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "m.py"), "w") as f:
            f.write("def hello(): pass\ndef hell(): pass\n")
        repository = Repository(tmpdir)
        vs = VectorSearcher(repository, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("hell", top_k=2)
        assert any("hell" in (r.get("name") or "") for r in results)
        assert any("hello" in (r.get("name") or "") for r in results)


# --- New test using actual sentence-transformers ---

MODEL_NAME = "all-MiniLM-L6-v2"


def _sentence_transformers_unavailable():
    """Return True if SentenceTransformer or model cannot be imported/loaded."""
    try:
        # Actually try to import SentenceTransformer class to catch import chain issues
        # This will trigger all the dependent imports (transformers, etc.)
        from sentence_transformers import SentenceTransformer

        # Try to initialize a model name to further validate the import chain
        if not hasattr(SentenceTransformer, "__init__"):
            print("DEBUG: SentenceTransformer class doesn't have expected attributes")
            return True

        print("DEBUG: sentence_transformers and SentenceTransformer class imported OK")
        return False
    except (ImportError, ModuleNotFoundError) as err:
        print(f"DEBUG: SentenceTransformer ImportError → skipping test: {err}")
        return True
    except ValueError as err:
        # Catch specific ValueError from importlib.util about openai.__spec__ is None
        print(f"DEBUG: ValueError during SentenceTransformer import → skipping test: {err}")
        return True
    except Exception as err:  # pragma: no cover - other unexpected issues
        print(f"DEBUG: Unexpected error during SentenceTransformer check → skipping: {err}")
        return True


_REASON_ST = "sentence_transformers not installed (see DEBUG output)"


@pytest.mark.skipif(_sentence_transformers_unavailable(), reason=_REASON_ST)
def test_vector_searcher_with_sentence_transformer():
    """End-to-end semantic search using a real embedding model (if available)."""
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        pytest.skip(f"Failed to import SentenceTransformer: {e}")

    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        pytest.skip(f"Failed to load model {MODEL_NAME}: {e}")

    def st_embed_fn(text: str) -> list[float]:
        return model.encode([text])[0].tolist()

    with tempfile.TemporaryDirectory() as tmpdir_st:
        repo_path = Path(tmpdir_st)
        file1_content = """
        def calculate_area_of_circle(radius):
            pi = 3.14159
            return pi * (radius ** 2)
        """
        file2_content = """
        class UserLogin:
            def __init__(self, username, password):
                self.username = username
                self.password = password

            def authenticate(self):
                # Complex authentication logic here
                print(f"Authenticating {self.username}")
                return True
        """
        (repo_path / "geometry.py").write_text(file1_content)
        (repo_path / "auth.py").write_text(file2_content)

        repository = Repository(str(repo_path))
        # Use a unique persist_dir for this test to avoid conflicts
        persist_path = repo_path / ".kit_test_st_index"
        vs = VectorSearcher(repository, embed_fn=st_embed_fn, persist_dir=str(persist_path))
        vs.build_index(chunk_by="symbols")  # Chunking by symbols is often good for semantic code search

        # Query for something related to "circle area calculation"
        query1 = "mathematical function for disk size"
        results1 = vs.search(query1, top_k=1)

        assert len(results1) >= 1, "Should find at least one result for query 1"
        # Check if the top result's metadata (which includes the code) contains relevant terms
        # The 'text' field in metadata should be the chunk of code
        top_result1_text = results1[0].get("code", "")
        assert "calculate_area_of_circle" in top_result1_text or "radius" in top_result1_text, (
            f"Top result for '{query1}' did not contain expected geometry code. Got: {top_result1_text}"
        )

        # Query for something related to "user sign-in"
        query2 = "process for verifying user credentials"
        results2 = vs.search(query2, top_k=1)

        assert len(results2) >= 1, "Should find at least one result for query 2"
        top_result2_text = results2[0].get("code", "")
        assert "UserLogin" in top_result2_text or "authenticate" in top_result2_text, (
            f"Top result for '{query2}' did not contain expected auth code. Got: {top_result2_text}"
        )

        # Test persistence: create a new searcher instance pointing to the same directory
        vs_persistent = VectorSearcher(repository, embed_fn=st_embed_fn, persist_dir=str(persist_path))
        results_persistent = vs_persistent.search(
            query1, top_k=1
        )  # embed_fn might be needed if query embedding is not part of backend state
        assert len(results_persistent) >= 1
        top_result_persistent_text = results_persistent[0].get("code", "")
        assert "calculate_area_of_circle" in top_result_persistent_text or "radius" in top_result_persistent_text
