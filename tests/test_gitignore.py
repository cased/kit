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


def test_code_searcher_respects_subdirectory_gitignore():
    """Test CodeSearcher also respects subdirectory .gitignore files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        from kit.code_searcher import CodeSearcher

        # Create subdirectory with its own .gitignore
        subdir = repo / "src"
        subdir.mkdir()
        (subdir / ".gitignore").write_text("*.log\n")

        # Create test files with searchable content
        (repo / "root.py").write_text("search_pattern")
        (subdir / "code.py").write_text("search_pattern")
        (subdir / "debug.log").write_text("search_pattern")

        searcher = CodeSearcher(str(repo))
        results = searcher.search_text("search_pattern")

        # Should find matches in .py but not .log
        files = [r["file"] for r in results]
        assert "root.py" in files
        assert "src/code.py" in files
        assert "src/debug.log" not in files


def test_absolute_patterns_in_subdirectory():
    """Test absolute patterns (starting with /) in subdirectory .gitignore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Subdirectory with absolute pattern
        subdir = repo / "frontend"
        subdir.mkdir()
        (subdir / ".gitignore").write_text("/build/\n")

        # Create test files
        (subdir / "src").mkdir()
        (subdir / "src" / "app.js").touch()
        (subdir / "build").mkdir()
        (subdir / "build" / "bundle.js").touch()
        (subdir / "src" / "build").mkdir()
        (subdir / "src" / "build" / "config.js").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        paths = [item["path"] for item in tree]
        # /build/ should only ignore frontend/build/, not frontend/src/build/
        assert "frontend/src/app.js" in paths
        assert "frontend/build/bundle.js" not in paths
        assert "frontend/src/build/config.js" in paths


def test_complex_negation_patterns():
    """Test complex negation scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Root ignores all .env files
        (repo / ".gitignore").write_text("*.env\n")

        # Config directory allows .env.example
        config = repo / "config"
        config.mkdir()
        (config / ".gitignore").write_text("!*.env.example\n")

        # Create test files
        (repo / "root.env").touch()
        (repo / "README.md").touch()
        (config / "app.env").touch()
        (config / "template.env.example").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        paths = [item["path"] for item in tree]
        assert "README.md" in paths
        assert "root.env" not in paths
        assert "config/app.env" not in paths
        assert "config/template.env.example" in paths  # Negation allows it


def test_patterns_without_wildcards_match_at_any_depth():
    """Test that patterns without wildcards (like 'node_modules') match at any depth."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Frontend with .gitignore containing plain 'node_modules' (no wildcards)
        frontend = repo / "frontend"
        frontend.mkdir()
        (frontend / ".gitignore").write_text("node_modules\n")

        # Create node_modules at multiple depths
        (frontend / "package.json").touch()

        # Direct child
        nm1 = frontend / "node_modules"
        nm1.mkdir()
        (nm1 / "pkg1.json").touch()

        # Nested in src
        src = frontend / "src"
        src.mkdir()
        nm2 = src / "node_modules"
        nm2.mkdir()
        (nm2 / "pkg2.json").touch()

        # Deeply nested
        deep = src / "components" / "ui"
        deep.mkdir(parents=True)
        nm3 = deep / "node_modules"
        nm3.mkdir()
        (nm3 / "pkg3.json").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        paths = [item["path"] for item in tree]

        # package.json should be included
        assert "frontend/package.json" in paths

        # All node_modules at any depth should be ignored
        assert "frontend/node_modules/pkg1.json" not in paths
        assert "frontend/src/node_modules/pkg2.json" not in paths
        assert "frontend/src/components/ui/node_modules/pkg3.json" not in paths


def test_deeply_nested_gitignores():
    """Test .gitignore files at multiple depth levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Root .gitignore
        (repo / ".gitignore").write_text("*.tmp\n")

        # Level 1
        l1 = repo / "level1"
        l1.mkdir()
        (l1 / ".gitignore").write_text("*.cache\n")
        (l1 / "file.txt").touch()
        (l1 / "file.tmp").touch()
        (l1 / "file.cache").touch()

        # Level 2
        l2 = l1 / "level2"
        l2.mkdir()
        (l2 / ".gitignore").write_text("!*.tmp\n")  # Re-allow .tmp here
        (l2 / "deep.txt").touch()
        (l2 / "deep.tmp").touch()
        (l2 / "deep.cache").touch()

        mapper = RepoMapper(str(repo))
        tree = mapper.get_file_tree()

        paths = [item["path"] for item in tree]
        assert "level1/file.txt" in paths
        assert "level1/file.tmp" not in paths  # Ignored by root
        assert "level1/file.cache" not in paths  # Ignored by level1
        assert "level1/level2/deep.txt" in paths
        assert "level1/level2/deep.tmp" in paths  # Negation allows it
        assert "level1/level2/deep.cache" not in paths  # Still ignored by level1
