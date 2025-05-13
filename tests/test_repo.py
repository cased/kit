import os
import tempfile

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


@pytest.mark.parametrize(
    ("structure", "expected_treepaths"),
    [
        (
            {
                "a.py": "pass",
                "b.py": "pass",
                "c.txt": "test",
            },
            [
                "a.py",
                "b.py",
                "c.txt",
            ],
        ),
        (
            {
                "dir1/x.py": "pass",
                "dir2/y.py": "pass",
            },
            [
                "dir1",
                "dir1/x.py",
                "dir2",
                "dir2/y.py",
            ],
        ),
        (
            {
                "dir1/dir2/z.py": "pass",
            },
            [
                "dir1",
                "dir1/dir2",
                "dir1/dir2/z.py",
            ],
        ),
        (
            {
                ".gitignore": "dir1/a.py",
                "dir1/a.py": "pass",
                "dir2/b.py": "pass",
            },
            [
                ".gitignore",
                "dir2",
                "dir2/b.py",
            ],
        ),
    ],
)
def test_repo_file_tree_various(structure, expected_treepaths):
    with tempfile.TemporaryDirectory() as tmpdir:
        for relpath, contents in structure.items():
            path = os.path.join(tmpdir, relpath)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(contents)

        repository = Repository(tmpdir)
        tree = repository.get_file_tree()
        actual_treepaths = [x["path"] for x in tree]
        assert sorted(actual_treepaths) == sorted(expected_treepaths)


def test_repo_get_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup: Create some test files
        content1 = "Hello, world!\nThis is a test file."
        file1_path = "dir1/file1.txt"
        full_file1_path = os.path.join(tmpdir, file1_path)
        os.makedirs(os.path.dirname(full_file1_path), exist_ok=True)
        with open(full_file1_path, "w") as f:
            f.write(content1)

        empty_file_path = "empty.txt"
        full_empty_file_path = os.path.join(tmpdir, empty_file_path)
        with open(full_empty_file_path, "w") as f:
            pass  # Create an empty file

        repository = Repository(tmpdir)

        # Test 1: Read content from an existing file
        retrieved_content1 = repository.get_file_content(file1_path)
        assert retrieved_content1 == content1

        # Test 2: Read content from an empty file
        retrieved_empty_content = repository.get_file_content(empty_file_path)
        assert retrieved_empty_content == ""

        # Test 3: Attempt to read content from a non-existent file
        non_existent_file_path = "non_existent.txt"
        with pytest.raises(FileNotFoundError):
            repository.get_file_content(non_existent_file_path)

        # Test 4: Attempt to read content from a directory (should also fail)
        with pytest.raises(IOError):  # Or perhaps FileNotFoundError or IsADirectoryError, adjust as per actual behavior
            repository.get_file_content("dir1")
