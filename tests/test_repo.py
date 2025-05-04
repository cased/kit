import tempfile
import os
import pytest
from kit import Repository

def test_repo_get_file_tree_and_symbols():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/foo/bar")
        with open(f"{tmpdir}/foo/bar/baz.py", "w") as f:
            f.write("""
class Foo:
    def bar(self): pass

def baz(): pass
""")
        repository = Repository(tmpdir)
        tree = repository.get_file_tree()
        assert any(item["path"].endswith("baz.py") for item in tree)
        assert any(item["is_dir"] and item["path"].endswith("foo/bar") for item in tree)
        symbols = repository.extract_symbols("foo/bar/baz.py")
        names = {s["name"] for s in symbols}
        assert "Foo" in names
        assert "baz" in names
        types = {s["type"] for s in symbols}
        assert "class" in types
        assert "function" in types

@pytest.mark.parametrize("structure", [
    ["a.py", "b.py", "c.txt"],
    ["dir1/x.py", "dir2/y.py"],
])
def test_repo_file_tree_various(structure):
    with tempfile.TemporaryDirectory() as tmpdir:
        for relpath in structure:
            path = os.path.join(tmpdir, relpath)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("pass\n")
        repository = Repository(tmpdir)
        tree = repository.get_file_tree()
        for relpath in structure:
            assert any(item["path"].endswith(relpath) for item in tree)
