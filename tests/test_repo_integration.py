import tempfile
from kit import Repo

def test_repo_index_and_chunking():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/a.py", "w") as f:
            f.write("""def foo(): pass\nclass Bar: pass\n""")
        repo = Repo(tmpdir)
        idx = repo.index()
        assert "file_tree" in idx and "symbols" in idx
        assert any("a.py" in f for f in idx["symbols"])
        lines = repo.chunk_file_by_lines("a.py", max_lines=1)
        assert len(lines) > 1
        syms = repo.chunk_file_by_symbols("a.py")
        names = {s["name"] for s in syms}
        assert "foo" in names
        assert "Bar" in names
        ctx = repo.extract_context_around_line("a.py", 1)
        assert ctx is not None
