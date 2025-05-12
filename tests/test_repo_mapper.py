import tempfile

from kit import RepoMapper


def test_get_file_tree():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files and dirs
        import os

        os.makedirs(f"{tmpdir}/foo/bar")
        with open(f"{tmpdir}/foo/bar/baz.py", "w") as f:
            f.write("def test(): pass\n")
        mapper = RepoMapper(tmpdir)
        tree = mapper.get_file_tree()
        assert any(item["path"].endswith("baz.py") for item in tree)
        assert any(item["is_dir"] and item["path"].endswith("foo/bar") for item in tree)


def test_extract_symbols():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = f"{tmpdir}/a.py"
        with open(pyfile, "w") as f:
            f.write("""
class Foo:
    def bar(self): pass

def baz(): pass
""")
        mapper = RepoMapper(tmpdir)
        symbols = mapper.extract_symbols("a.py")
        names = {s["name"] for s in symbols}
        assert "Foo" in names
        assert "baz" in names
        types = {s["type"] for s in symbols}
        assert "class" in types
        assert "function" in types
