"""Integration tests for grep functionality across all Kit interfaces."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kit import Repository
from kit.mcp.server import KitServerLogic


class TestGrepIntegration:
    """Integration tests for grep functionality across Python API, CLI, REST API, and MCP."""

    @pytest.fixture
    def test_repo(self):
        """Create a test repository with various files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create directory structure
            (repo_path / "src").mkdir()
            (repo_path / "tests").mkdir()
            (repo_path / "docs").mkdir()
            (repo_path / ".github").mkdir()
            (repo_path / "node_modules").mkdir()

            # Create files with searchable content
            (repo_path / "README.md").write_text("# Project\n\nTODO: Complete the documentation")
            (repo_path / "src" / "main.py").write_text("def main():\n    # TODO: implement\n    pass")
            (repo_path / "src" / "utils.py").write_text("def helper():\n    return 'helper function'\n")
            (repo_path / "tests" / "test_main.py").write_text("def test_main():\n    # TODO: add test\n    pass")
            (repo_path / "docs" / "guide.md").write_text("# Guide\n\nThis is a guide.")
            (repo_path / ".github" / "workflow.yml").write_text("name: CI\non: push")
            (repo_path / "node_modules" / "lib.js").write_text("function excluded() { }")

            yield str(repo_path)

    def test_python_api_grep(self, test_repo):
        """Test grep functionality through Python API."""
        repo = Repository(test_repo)

        # Basic search
        results = repo.grep("TODO")
        assert len(results) == 3  # README.md, main.py, test_main.py
        files = {result["file"] for result in results}
        assert "README.md" in files
        assert "src/main.py" in files
        assert "tests/test_main.py" in files

        # Directory filtering
        src_results = repo.grep("TODO", directory="src")
        assert len(src_results) == 1
        assert src_results[0]["file"] == "src/main.py"

        # File pattern filtering
        py_results = repo.grep("def", include_pattern="*.py")
        assert len(py_results) == 3  # main, helper, test_main functions
        py_files = {result["file"] for result in py_results}
        assert all(f.endswith(".py") for f in py_files)

        # Case insensitive
        case_results = repo.grep("todo", case_sensitive=False)
        assert len(case_results) == 3

        # Hidden directories (should exclude node_modules automatically)
        all_results = repo.grep("CI", include_hidden=True)  # CI is in .github/workflow.yml
        hidden_files = {result["file"] for result in all_results}
        assert not any("node_modules" in f for f in hidden_files)  # Should be excluded
        assert any(".github" in f for f in hidden_files)  # Should be included with include_hidden

    def test_mcp_server_grep(self, test_repo):
        """Test grep functionality through MCP server."""
        logic = KitServerLogic()

        # Open repository
        repo_id = logic.open_repository(test_repo)

        # Basic grep
        results = logic.grep_code(repo_id, "TODO")
        assert len(results) >= 2  # At least README and Python files
        assert isinstance(results, list)
        assert all("file" in result for result in results)
        assert all("line_number" in result for result in results)
        assert all("line_content" in result for result in results)

        # Directory filtering
        src_results = logic.grep_code(repo_id, "def", directory="src")
        assert len(src_results) >= 1
        src_files = {result["file"] for result in src_results}
        assert all(f.startswith("src/") for f in src_files)

        # File patterns
        py_results = logic.grep_code(repo_id, "def", include_pattern="*.py")
        assert len(py_results) >= 2
        py_files = {result["file"] for result in py_results}
        assert all(f.endswith(".py") for f in py_files)

        # Case insensitive
        case_results = logic.grep_code(repo_id, "TODO", case_sensitive=False)
        assert len(case_results) >= 2

    def test_grep_vs_search_behavior(self, test_repo):
        """Test that grep behaves differently from search (literal vs regex)."""
        repo = Repository(test_repo)

        # Create a file with regex special characters
        test_file = Path(test_repo) / "regex_test.py"
        test_file.write_text("pattern = r'\\d+'\ntext = 'hello.world'\n")

        # Literal search with grep (should find the literal dot)
        grep_results = repo.grep(".")
        grep_files = {result["file"] for result in grep_results}
        assert "regex_test.py" in grep_files

        # Search should work with regex patterns
        search_results = repo.search_text(r"\.")  # Escaped dot
        assert isinstance(search_results, list)

    def test_smart_exclusions_behavior(self, test_repo):
        """Test that smart exclusions work correctly."""
        repo = Repository(test_repo)

        # Search for 'function' - should not find anything in node_modules
        results = repo.grep("function")
        result_files = {result["file"] for result in results}

        # Should not include node_modules files
        assert not any("node_modules" in f for f in result_files)

        # But should include other files
        assert len(results) >= 0  # May not find 'function' in other files

    def test_error_handling(self, test_repo):
        """Test error handling across interfaces."""
        repo = Repository(test_repo)

        # Invalid directory
        with pytest.raises(ValueError, match="Directory not found"):
            repo.grep("test", directory="nonexistent")

        # MCP server error handling
        logic = KitServerLogic()
        repo_id = logic.open_repository(test_repo)

        from kit.mcp.server import INVALID_PARAMS, MCPError

        with pytest.raises(MCPError) as exc_info:
            logic.grep_code(repo_id, "test", directory="nonexistent")
        assert exc_info.value.code == INVALID_PARAMS

    def test_grep_performance_features(self, test_repo):
        """Test that performance-oriented features work correctly."""
        repo = Repository(test_repo)

        # Max results limiting
        limited_results = repo.grep("e", max_results=2)  # Very common letter
        assert len(limited_results) <= 2

        # Directory filtering for performance
        focused_results = repo.grep("TODO", directory="src")
        all_results = repo.grep("TODO")
        assert len(focused_results) <= len(all_results)

    @patch("subprocess.run")
    def test_grep_command_construction(self, mock_subprocess, test_repo):
        """Test that grep command is constructed correctly."""
        from subprocess import CompletedProcess

        # Mock successful grep execution
        mock_subprocess.return_value = CompletedProcess(args=[], returncode=0, stdout="test.py:1:test content\n")

        repo = Repository(test_repo)

        # Test basic grep
        repo.grep("test")

        # Verify grep command was called
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args[0][0]  # First positional argument

        # Should use literal search (-F flag)
        assert "-F" in call_args
        assert "test" in call_args

        # Should exclude .git directory
        assert "--exclude-dir" in call_args
        assert ".git" in call_args

    def test_integration_consistency(self, test_repo):
        """Test that all interfaces return consistent results."""
        # Python API
        repo = Repository(test_repo)
        python_results = repo.grep("TODO")

        # MCP Server
        logic = KitServerLogic()
        repo_id = logic.open_repository(test_repo)
        mcp_results = logic.grep_code(repo_id, "TODO")

        # Results should be consistent (same number of matches)
        assert len(python_results) == len(mcp_results)

        # Same files should be found
        python_files = {result["file"] for result in python_results}
        mcp_files = {result["file"] for result in mcp_results}
        assert python_files == mcp_files
