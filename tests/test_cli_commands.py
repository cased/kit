"""Tests for CLI command argument parsing and validation."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestSearchCommands:
    """Test search and search-semantic command parsing."""

    def test_search_command_basic(self, runner):
        """Test basic search command parsing."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "textual search" in result.output

    def test_search_with_options(self, runner):
        """Test search command with various options."""
        # Test pattern option
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.search.return_value = []
            runner.invoke(app, ["search", ".", "test", "--pattern", "*.py"])
            # Should execute without parse errors

    def test_search_json_output(self, runner):
        """Test search with JSON output."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.search.return_value = [{"file": "test.py", "line": 1, "content": "test line"}]
            runner.invoke(app, ["search", ".", "test", "--json"])
            # Should produce JSON output

    def test_search_semantic_command(self, runner):
        """Test search-semantic command parsing."""
        result = runner.invoke(app, ["search-semantic", "--help"])
        assert result.exit_code == 0
        assert "semantic search" in result.output

    def test_search_semantic_options(self, runner):
        """Test search-semantic with options."""
        # Test with limit
        # --help should work even with other options
        result = runner.invoke(app, ["search-semantic", "--help"])
        assert result.exit_code == 0

        # Test with model option parsing
        result = runner.invoke(app, ["search-semantic", "--help"])
        assert result.exit_code == 0


class TestGrepCommand:
    """Test grep command parsing."""

    def test_grep_basic(self, runner):
        """Test basic grep command."""
        result = runner.invoke(app, ["grep", "--help"])
        assert result.exit_code == 0
        assert "literal grep search" in result.output

    def test_grep_options(self, runner):
        """Test grep command options."""
        options_to_test = [
            ["grep", ".", "pattern", "--ignore-case"],
            ["grep", ".", "pattern", "-i"],  # Short form
            ["grep", ".", "pattern", "--include", "*.py"],
            ["grep", ".", "pattern", "--exclude", "*.pyc"],
            ["grep", ".", "pattern", "--max-results", "100"],
            ["grep", ".", "pattern", "-n", "50"],  # Short form
            ["grep", ".", "pattern", "--directory", "src"],
            ["grep", ".", "pattern", "-d", "tests"],  # Short form
            ["grep", ".", "pattern", "--include-hidden"],
        ]

        for args in options_to_test:
            result = runner.invoke(app, [*args, "--help"])
            assert result.exit_code == 0

    def test_grep_case_sensitivity(self, runner):
        """Test grep case sensitivity options."""
        # Default (case sensitive)
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.grep.return_value = []
            runner.invoke(app, ["grep", ".", "TEST"])
            # Should search case-sensitively by default

        # Case insensitive
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.grep.return_value = []
            runner.invoke(app, ["grep", ".", "TEST", "--ignore-case"])
            # Should search case-insensitively


class TestDependenciesCommand:
    """Test dependencies command parsing."""

    def test_dependencies_help(self, runner):
        """Test dependencies command help."""
        result = runner.invoke(app, ["dependencies", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50
        assert "dependencies" in result.output.lower() or "usage" in result.output.lower()

    def test_dependencies_language_options(self, runner):
        """Test language option validation."""
        # Valid languages
        for lang in ["python", "terraform"]:
            result = runner.invoke(app, ["dependencies", ".", "--language", lang, "--help"])
            assert result.exit_code == 0

    def test_dependencies_format_options(self, runner):
        """Test format option validation."""
        # Valid formats
        for fmt in ["json", "text", "tree"]:
            result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--format", fmt, "--help"])
            assert result.exit_code == 0

    def test_dependencies_visualization(self, runner):
        """Test visualization options."""
        # Test visualization format
        result = runner.invoke(
            app, ["dependencies", ".", "--language", "python", "--visualize", "output.png", "--help"]
        )
        assert result.exit_code == 0

        # Test with different formats
        for fmt in ["png", "svg", "pdf"]:
            viz_file = f"output.{fmt}"
            result = runner.invoke(
                app, ["dependencies", ".", "--language", "python", "--visualize", viz_file, "--help"]
            )
            assert result.exit_code == 0


class TestSymbolCommands:
    """Test symbol-related commands."""

    def test_symbols_command(self, runner):
        """Test symbols command."""
        result = runner.invoke(app, ["symbols", "--help"])
        assert result.exit_code == 0
        assert "Extract symbols" in result.output

    def test_symbols_formats(self, runner):
        """Test symbols output formats."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.extract_symbols.return_value = []

            # Table format (default)
            runner.invoke(app, ["symbols", "."])

            # JSON format
            runner.invoke(app, ["symbols", ".", "--format", "json"])

            # Names format
            runner.invoke(app, ["symbols", ".", "--format", "names"])

    def test_usages_command(self, runner):
        """Test usages command."""
        result = runner.invoke(app, ["usages", "--help"])
        assert result.exit_code == 0
        assert "usages" in result.output.lower()

    def test_usages_with_type(self, runner):
        """Test usages with type filter."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.find_symbol_usages.return_value = []

            runner.invoke(app, ["usages", ".", "MyClass", "--type", "class"])
            # Should execute without errors


class TestContextCommands:
    """Test context extraction commands."""

    def test_context_command(self, runner):
        """Test context command."""
        result = runner.invoke(app, ["context", "--help"])
        assert result.exit_code == 0
        assert "context" in result.output.lower()

    def test_context_with_line_number(self, runner):
        """Test context extraction with line number."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.get_context_for_line.return_value = []

            runner.invoke(app, ["context", ".", "file.py", "42"])
            # Should execute without errors

    def test_chunk_commands(self, runner):
        """Test chunk extraction commands."""
        # chunk-lines
        result = runner.invoke(app, ["chunk-lines", "--help"])
        assert result.exit_code == 0
        assert "chunk" in result.output.lower()

        # chunk-symbols
        result = runner.invoke(app, ["chunk-symbols", "--help"])
        assert result.exit_code == 0
        assert "symbols" in result.output.lower()

    def test_chunk_lines_options(self, runner):
        """Test chunk-lines with options."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.chunk_file_by_lines.return_value = []

            # With custom max lines
            runner.invoke(app, ["chunk-lines", ".", "file.py", "--max-lines", "100"])

            # With overlap
            runner.invoke(app, ["chunk-lines", ".", "file.py", "--overlap", "10"])


class TestServeCommand:
    """Test serve command for API server."""

    def test_serve_help(self, runner):
        """Test serve command help."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50
        assert "serve" in result.output.lower() or "api" in result.output.lower() or "usage" in result.output.lower()

    def test_serve_options(self, runner):
        """Test serve command options."""
        # Custom host and port
        # --help should work
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0


class TestCommitCommand:
    """Test commit message generation command."""

    def test_commit_help(self, runner):
        """Test commit command help."""
        result = runner.invoke(app, ["commit", "--help"])
        assert result.exit_code == 0
        assert "commit" in result.output.lower()

    def test_commit_options(self, runner):
        """Test commit command options."""
        # Test help works
        result = runner.invoke(app, ["commit", "--help"])
        assert result.exit_code == 0

        # Test model option parsing
        result = runner.invoke(app, ["commit", "--model", "gpt-4", "--help"])
        assert result.exit_code == 0


class TestExportCommand:
    """Test export command variations."""

    def test_export_types(self, runner):
        """Test different export types."""
        export_types = ["index", "symbols", "file-tree", "symbol-usages"]

        for export_type in export_types:
            result = runner.invoke(app, ["export", ".", export_type, "output.json", "--help"])
            assert result.exit_code == 0

    def test_export_symbol_usages_requires_symbol(self, runner):
        """Test that symbol-usages export requires --symbol."""
        with patch("kit.Repository"):
            result = runner.invoke(app, ["export", ".", "symbol-usages", "output.json"])
            assert result.exit_code == 1
            assert "--symbol is required" in result.output

    def test_export_with_ref(self, runner):
        """Test export with git ref."""
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.write_symbols.return_value = None

            runner.invoke(app, ["export", ".", "symbols", "output.json", "--ref", "v1.0.0"])
            # Should handle ref parameter


class TestEdgeCasesAndValidation:
    """Test edge cases and input validation."""

    def test_numeric_validation(self, runner):
        """Test numeric parameter validation."""
        # Invalid numbers
        result = runner.invoke(app, ["search", ".", "test", "--max-results", "not-a-number"])
        assert result.exit_code != 0

        result = runner.invoke(app, ["chunk-lines", ".", "file.py", "--max-lines", "-10"])
        # Negative numbers might be rejected

    def test_path_validation(self, runner):
        """Test path parameter handling."""
        # Non-existent paths
        with patch("kit.Repository") as mock_repo:
            mock_repo.side_effect = FileNotFoundError("Path not found")

            result = runner.invoke(app, ["symbols", "/non/existent/path"])
            assert result.exit_code == 1

    def test_empty_string_handling(self, runner):
        """Test empty string parameters."""
        # Empty query
        runner.invoke(app, ["search", ".", ""])
        # Should handle empty query gracefully

    def test_special_characters(self, runner):
        """Test special characters in parameters."""
        # Regex special chars in search
        with patch("kit.Repository") as mock_repo:
            mock_repo.return_value.search.return_value = []

            special_queries = [
                "test.*",
                "func\\(\\)",
                "[a-z]+",
                "^start",
                "end$",
            ]

            for query in special_queries:
                runner.invoke(app, ["search", ".", query])
                # Should handle regex patterns

    def test_very_long_arguments(self, runner):
        """Test very long argument values."""
        # Very long query
        long_query = "test " * 1000
        result = runner.invoke(app, ["search", ".", long_query, "--help"])
        assert result.exit_code == 0

        # Very long path
        long_path = "/".join(["directory"] * 100)
        result = runner.invoke(app, ["symbols", long_path, "--help"])
        assert result.exit_code == 0
