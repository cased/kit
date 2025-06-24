"""Tests for path validation and traversal protection."""

import tempfile
from pathlib import Path

import pytest

from kit.context_extractor import ContextExtractor
from kit.repo_mapper import RepoMapper
from kit.repository import Repository
from kit.utils import validate_relative_path


class TestValidateRelativePath:
    """Test the core path validation utility function."""

    def test_normal_paths_allowed(self):
        """Test that normal relative paths are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Simple file
            result = validate_relative_path(base, "test.py")
            assert result == base / "test.py"

            # Subdirectory
            result = validate_relative_path(base, "src/main.py")
            assert result == base / "src" / "main.py"

            # Current directory reference
            result = validate_relative_path(base, "./test.py")
            assert result == base / "test.py"

    def test_empty_path_returns_base(self):
        """Test that empty or current directory paths return base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            assert validate_relative_path(base, "") == base
            assert validate_relative_path(base, ".") == base

    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Basic traversal
            with pytest.raises(ValueError, match="outside repository bounds"):
                validate_relative_path(base, "../secret.txt")

            # Multiple levels
            with pytest.raises(ValueError, match="outside repository bounds"):
                validate_relative_path(base, "../../../etc/passwd")

            # Mixed with subdirectories
            with pytest.raises(ValueError, match="outside repository bounds"):
                validate_relative_path(base, "src/../../../secret.txt")

    def test_non_escaping_relative_paths_allowed(self):
        """Test that relative paths that don't escape bounds are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Goes up then back down (path not normalized, but allowed)
            result = validate_relative_path(base, "src/../test.py")
            assert result == base / "src" / ".." / "test.py"

            # Multiple ups and downs that stay within bounds
            result = validate_relative_path(base, "a/b/../c/../../test.py")
            assert result == base / "a" / "b" / ".." / "c" / ".." / ".." / "test.py"

    def test_complex_traversal_patterns(self):
        """Test various complex traversal patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Deep traversal
            with pytest.raises(ValueError, match="outside repository bounds"):
                validate_relative_path(base, "a/b/c/../../../../secret.txt")

            # Sneaky traversal after valid directory
            with pytest.raises(ValueError, match="outside repository bounds"):
                validate_relative_path(base, "src/main.py/../../../secret.txt")


class TestRepositoryPathValidation:
    """Test path validation in Repository methods."""

    def test_get_file_content_path_traversal(self):
        """Test that get_file_content blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_file_content("../secret.txt")

            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_file_content("../../../etc/passwd")

    def test_get_file_content_multiple_files_path_traversal(self):
        """Test that batch file reading blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            # One bad path in a list should fail the whole operation
            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_file_content(["valid.py", "../secret.txt"])

    def test_get_abs_path_validation(self):
        """Test that get_abs_path validates paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            # Normal path should work
            result = repo.get_abs_path("test.py")
            assert "test.py" in result

            # Traversal should fail
            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_abs_path("../secret.txt")

    def test_extract_symbols_incremental_path_validation(self):
        """Test that incremental symbol extraction validates file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            # Create a valid Python file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")

            # Valid path should work
            symbols = repo.extract_symbols_incremental(["test.py"])
            assert isinstance(symbols, list)

            # Invalid path should fail
            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.extract_symbols_incremental(["../secret.py"])


class TestRepoMapperPathValidation:
    """Test path validation in RepoMapper methods."""

    def test_extract_symbols_path_traversal(self):
        """Test that RepoMapper.extract_symbols blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapper = RepoMapper(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                mapper.extract_symbols("../secret.py")

    def test_get_file_tree_subpath_traversal(self):
        """Test that get_file_tree subpath parameter blocks traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mapper = RepoMapper(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                mapper.get_file_tree(subpath="../")

            with pytest.raises(ValueError, match="outside repository bounds"):
                mapper.get_file_tree(subpath="../../etc")


class TestContextExtractorPathValidation:
    """Test path validation in ContextExtractor methods."""

    def test_chunk_file_by_lines_path_traversal(self):
        """Test that chunk_file_by_lines blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ContextExtractor(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                extractor.chunk_file_by_lines("../secret.txt")

    def test_chunk_file_by_symbols_path_traversal(self):
        """Test that chunk_file_by_symbols blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ContextExtractor(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                extractor.chunk_file_by_symbols("../secret.py")

    def test_extract_context_around_line_path_traversal(self):
        """Test that extract_context_around_line blocks path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ContextExtractor(tmpdir)

            with pytest.raises(ValueError, match="outside repository bounds"):
                extractor.extract_context_around_line("../secret.py", 1)


class TestPathValidationIntegration:
    """Integration tests for path validation across components."""

    def test_legitimate_operations_still_work(self):
        """Test that legitimate file operations still work after adding validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    return 'world'\n")

            subdir = Path(tmpdir) / "src"
            subdir.mkdir()
            sub_file = subdir / "main.py"
            sub_file.write_text("from test import hello\nprint(hello())\n")

            # Repository operations should work
            repo = Repository(tmpdir)
            content = repo.get_file_content("test.py")
            assert "def hello" in content

            # Subdirectory files should work
            content = repo.get_file_content("src/main.py")
            assert "from test import hello" in content

            # Multiple files should work
            contents = repo.get_file_content(["test.py", "src/main.py"])
            assert isinstance(contents, dict)
            assert len(contents) == 2

            # File tree with subpath should work
            tree = repo.get_file_tree(subpath="src")
            assert isinstance(tree, list)

            # Symbol extraction should work
            symbols = repo.extract_symbols("test.py")
            assert len(symbols) > 0

    def test_mixed_valid_invalid_paths(self):
        """Test behavior when mixing valid and invalid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            # Should fail fast on first invalid path
            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_file_content(["valid.py", "../invalid.txt", "also_valid.py"])

    def test_symlink_compatibility(self):
        """Test that validation works with symlinked directories (important for macOS)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repository(tmpdir)

            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def test(): pass")

            # Should work even with symlink resolution differences
            content = repo.get_file_content("test.py")
            assert "def test" in content

            # Traversal should still be blocked
            with pytest.raises(ValueError, match="outside repository bounds"):
                repo.get_file_content("../secret.txt")
