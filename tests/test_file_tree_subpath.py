import tempfile
from pathlib import Path

import pytest

from kit import Repository


def test_file_tree_subpath():
    """Test file tree with subpath parameter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create test directory structure
        (repo_path / "src").mkdir()
        (repo_path / "src" / "components").mkdir()
        (repo_path / "src" / "utils").mkdir()
        (repo_path / "tests").mkdir()

        # Create test files
        (repo_path / "README.md").write_text("# Test repo")
        (repo_path / "src" / "main.py").write_text("print('hello')")
        (repo_path / "src" / "components" / "button.py").write_text("class Button: pass")
        (repo_path / "src" / "utils" / "helper.py").write_text("def help(): pass")
        (repo_path / "tests" / "test_main.py").write_text("def test(): pass")

        repo = Repository(str(repo_path))

        # Test full tree (no subpath)
        full_tree = repo.get_file_tree()
        full_paths = {item["path"] for item in full_tree if not item["is_dir"]}
        assert "README.md" in full_paths
        assert "src/main.py" in full_paths
        assert "src/components/button.py" in full_paths
        assert "tests/test_main.py" in full_paths

        # Test src subpath
        src_tree = repo.get_file_tree(subpath="src")
        src_paths = {item["path"] for item in src_tree if not item["is_dir"]}
        assert "src/main.py" in src_paths
        assert "src/components/button.py" in src_paths
        assert "src/utils/helper.py" in src_paths
        # Should not contain files outside src/
        assert "README.md" not in src_paths
        assert "tests/test_main.py" not in src_paths

        # Test components subpath
        comp_tree = repo.get_file_tree(subpath="src/components")
        comp_paths = {item["path"] for item in comp_tree if not item["is_dir"]}
        assert "src/components/button.py" in comp_paths
        # Should not contain files outside src/components/
        assert "src/main.py" not in comp_paths
        assert "src/utils/helper.py" not in comp_paths


def test_file_tree_subpath_nonexistent():
    """Test file tree with nonexistent subpath raises error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("print('hello')")

        repo = Repository(str(repo_path))

        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            repo.get_file_tree(subpath="nonexistent")


def test_file_tree_subpath_file_not_dir():
    """Test file tree with file path (not directory) raises error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        (repo_path / "README.md").write_text("# Test")

        repo = Repository(str(repo_path))

        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            repo.get_file_tree(subpath="README.md")
