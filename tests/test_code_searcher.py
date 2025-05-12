import os
import tempfile

from kit import CodeSearcher


def test_search_text_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "foo.py")
        with open(pyfile, "w") as f:
            f.write("""
def foo(): pass

def bar(): pass
""")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("def foo")
        assert any("foo" in m["line"] for m in matches)
        matches_bar = searcher.search_text("bar")
        assert any("bar" in m["line"] for m in matches_bar)


def test_search_text_multiple_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = ["a.py", "b.py", "c.txt"]
        for fname in files:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(f"def {fname[:-3]}(): pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("def ", file_pattern="*.py")
        assert len(matches) == 2
        assert all(m["file"].endswith(".py") for m in matches)


def test_search_text_regex():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "foo.py")
        with open(pyfile, "w") as f:
            f.write("def foo(): pass\ndef bar(): pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text(r"def [fb]oo")
        assert any("foo" in m["line"] for m in matches)
        assert not any("bar" in m["line"] for m in matches)
