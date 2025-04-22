import tempfile
from kit import ContextExtractor

def test_chunk_file_by_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = f"{tmpdir}/test.py"
        with open(fpath, "w") as f:
            f.write(("def foo():\n    pass\ndef bar():\n    pass\n") * 10)
        extractor = ContextExtractor(tmpdir)
        chunks = extractor.chunk_file_by_lines("test.py", max_lines=3)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

def test_chunk_file_by_symbols():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = f"{tmpdir}/test.py"
        with open(fpath, "w") as f:
            f.write("""class Foo:\n    def bar(self): pass\ndef baz(): pass\n""")
        extractor = ContextExtractor(tmpdir)
        chunks = extractor.chunk_file_by_symbols("test.py")
        names = {c["name"] for c in chunks}
        assert "Foo" in names
        assert "baz" in names
        types = {c["type"] for c in chunks}
        assert "class" in types
        assert "function" in types

def test_extract_context_around_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = f"{tmpdir}/test.py"
        with open(fpath, "w") as f:
            f.write("""def foo():\n    x = 1\n    y = 2\n    return x + y\n""")
        extractor = ContextExtractor(tmpdir)
        ctx = extractor.extract_context_around_line("test.py", 2)
        assert ctx is not None
        assert ctx["name"] == "foo"
