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
