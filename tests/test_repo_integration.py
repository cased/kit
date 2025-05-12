import tempfile

from kit import Repository


def test_repo_index_and_chunking():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/a.py", "w") as f:
            f.write("""def foo(): pass\nclass Bar: pass\n""")
        repository = Repository(tmpdir)
        idx = repository.index()
        assert "file_tree" in idx and "symbols" in idx
        assert any("a.py" in f for f in idx["symbols"])
        lines = repository.chunk_file_by_lines("a.py", max_lines=1)
        assert len(lines) > 1
        syms = repository.chunk_file_by_symbols("a.py")
        names = {s["name"] for s in syms}
        assert "foo" in names
        assert "Bar" in names
        ctx = repository.extract_context_around_line("a.py", 1)
        assert ctx is not None
