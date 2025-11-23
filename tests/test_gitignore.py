import pytest
from pathlib import Path
import tempfile
from kit.repo_mapper import RepoMapper


def test_root_gitignore_only():
    """Test basic root .gitignore works as before."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Create root .gitignore
        (repo / ".gitignore").write_text("*.pyc\n__pycache__/\n")

        # Create test files
        (repo / "test.py").touch()
        (repo / "test.pyc").touch()
        (repo / "__pycache__").mkdir()
        (repo / "__pycache__" / "test.pyc").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        # Should only include test.py, not .pyc or __pycache__
        paths = [item["path"] for item in tree]
        assert "test.py" in paths
        assert "test.pyc" not in paths
        assert "__pycache__/test.pyc" not in paths


def test_subdirectory_gitignore():
    """Test subdirectory .gitignore files are respected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Create subdirectory with its own .gitignore
        subdir = repo / "frontend"
        subdir.mkdir()
        (subdir / ".gitignore").write_text("node_modules/\n*.log\n")

        # Create test files
        (subdir / "app.js").touch()
        (subdir / "debug.log").touch()
        node_modules = subdir / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.json").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        # Should include app.js but not debug.log or node_modules
        paths = [item["path"] for item in tree]
        assert "frontend/app.js" in paths
        assert "frontend/debug.log" not in paths
        assert "frontend/node_modules/package.json" not in paths


def test_nested_gitignore_precedence():
    """Test deeper .gitignore files override shallower ones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Root .gitignore ignores *.tmp
        (repo / ".gitignore").write_text("*.tmp\n")

        # Subdirectory .gitignore allows *.tmp (negation)
        subdir = repo / "special"
        subdir.mkdir()
        (subdir / ".gitignore").write_text("!*.tmp\n")

        # Create test files
        (repo / "root.tmp").touch()
        (subdir / "special.tmp").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        # Root .tmp should be ignored, but special/ .tmp should be included
        paths = [item["path"] for item in tree]
        assert "root.tmp" not in paths
        assert "special/special.tmp" in paths  # Negation pattern


def test_multiple_subdirectory_gitignores():
    """Test multiple subdirectories each with .gitignore files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Frontend with node_modules
        frontend = repo / "frontend"
        frontend.mkdir()
        (frontend / ".gitignore").write_text("node_modules/\n")
        (frontend / "app.js").touch()
        fe_nm = frontend / "node_modules"
        fe_nm.mkdir()
        (fe_nm / "react.js").touch()

        # Backend with venv
        backend = repo / "backend"
        backend.mkdir()
        (backend / ".gitignore").write_text("venv/\n__pycache__/\n")
        (backend / "main.py").touch()
        be_venv = backend / "venv"
        be_venv.mkdir()
        (be_venv / "python").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        paths = [item["path"] for item in tree]

        # Should include source files
        assert "frontend/app.js" in paths
        assert "backend/main.py" in paths

        # Should exclude ignored directories
        assert "frontend/node_modules/react.js" not in paths
        assert "backend/venv/python" not in paths


def test_no_gitignore_files():
    """Test repository with no .gitignore files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Create files without .gitignore
        (repo / "test.py").touch()
        subdir = repo / "src"
        subdir.mkdir()
        (subdir / "main.py").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        # All files should be included
        paths = [item["path"] for item in tree]
        assert "test.py" in paths
        assert "src/main.py" in paths
