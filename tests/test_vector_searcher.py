import tempfile
import os
import pytest
from kit.repo import Repo
from kit.vector_searcher import VectorSearcher, ChromaDBBackend

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
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index(chunk_by="symbols")
        results = vs.search("foo", top_k=2)
        assert isinstance(results, list)
        assert any("foo" in (r.get("name") or "") for r in results)
        # Test search_semantic via Repo
        results2 = repo.search_semantic("Bar", embed_fn=dummy_embed)
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
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
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
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index(chunk_by="symbols")
        # Should not crash or index anything meaningful
        results = vs.search("anything", top_k=5)
        assert isinstance(results, list)

def test_vector_searcher_chunk_by_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "e.py"), "w") as f:
            f.write("\n".join([f"def f{i}(): pass" for i in range(100)]))
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index(chunk_by="lines")
        results = vs.search("f42", top_k=10)
        assert isinstance(results, list)

def test_vector_searcher_search_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "f.py"), "w") as f:
            f.write("def hello(): pass\n")
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("nonexistent", top_k=5)
        assert isinstance(results, list)
        assert all("nonexistent" not in (r.get("name") or "") for r in results)

def test_vector_searcher_top_k_bounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "g.py"), "w") as f:
            f.write("def a(): pass\ndef b(): pass\n")
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("a", top_k=10)
        assert len(results) <= 10
        results_zero = vs.search("a", top_k=0)
        assert results_zero == [] or len(results_zero) == 0

def test_vector_searcher_edge_case_queries():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "h.py"), "w") as f:
            f.write("def edgecase(): pass\n")
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
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
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=constant_embed)
        vs.build_index()
        results = vs.search("anything", top_k=5)
        assert len(results) == 3

def test_vector_searcher_missing_embed_fn():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "j.py"), "w") as f:
            f.write("def missing(): pass\n")
        repo = Repo(tmpdir)
        with pytest.raises(ValueError):
            repo.get_vector_searcher()

def test_vector_searcher_persistency():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "k.py")
        with open(fpath, "w") as f:
            f.write("def persist(): pass\n")
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index()
        # Simulate restart by creating new VectorSearcher with same persist_dir and backend
        new_vs = VectorSearcher(repo, embed_fn=dummy_embed, persist_dir=vs.persist_dir, backend=vs.backend)
        results = new_vs.search("persist", top_k=2)
        assert any("persist" in (r.get("name") or "") for r in results)

def test_vector_searcher_overwrite_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "l.py")
        with open(fpath, "w") as f:
            f.write("def first(): pass\n")
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
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
        repo = Repo(tmpdir)
        vs = VectorSearcher(repo, embed_fn=dummy_embed)
        vs.build_index()
        results = vs.search("hell", top_k=2)
        assert any("hell" in (r.get("name") or "") for r in results)
        assert any("hello" in (r.get("name") or "") for r in results)
