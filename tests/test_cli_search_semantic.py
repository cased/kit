"""Tests for the search-semantic CLI command."""

import re

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text for easier testing."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestSearchSemanticCommand:
    """Test cases for the search-semantic CLI command."""

    def test_help_message(self, runner):
        """Test that search-semantic shows proper help message."""
        result = runner.invoke(app, ["search-semantic", "--help"])

        assert result.exit_code == 0

        # Strip ANSI codes for easier testing
        clean_output = strip_ansi_codes(result.output).lower()

        assert "semantic search" in clean_output
        assert "vector embeddings" in clean_output or "natural language" in clean_output
        assert "top-k" in clean_output
        assert "embedding-model" in clean_output
        assert "chunk-by" in clean_output

    def test_missing_required_arguments(self, runner):
        """Test error when required arguments are missing."""
        # Missing query
        result = runner.invoke(app, ["search-semantic", "."])
        assert result.exit_code == 2  # Typer error for missing required argument

        # Missing path
        result = runner.invoke(app, ["search-semantic"])
        assert result.exit_code == 2  # Typer error for missing required argument

    def test_invalid_chunk_by_parameter(self, runner):
        """Test error handling for invalid chunk-by parameter."""
        # This test validates input validation before any imports
        result = runner.invoke(app, ["search-semantic", ".", "test", "--chunk-by", "invalid"])

        assert result.exit_code == 1

        # The error might come before chunk validation if sentence-transformers is missing
        # So we check for either the chunk validation error OR the missing dependency error
        if "sentence-transformers" not in result.output:
            assert "Invalid chunk_by value: invalid" in result.output
            assert "Use 'symbols' or 'lines'" in result.output

    def test_sentence_transformers_dependency_handling(self, runner):
        """Test that command handles sentence-transformers dependency gracefully."""
        # This test checks the real behavior without mocking
        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        # Should either work (exit 0) or show helpful error (exit 1)
        assert result.exit_code in [0, 1]

        if result.exit_code == 1:
            # If it fails, should be due to missing sentence-transformers or similar
            expected_errors = [
                "sentence-transformers",
                "Failed to load embedding model",
                "Failed to initialize vector searcher",
                "Error:",
            ]
            assert any(error in result.output for error in expected_errors)
        else:
            # If it succeeds, should show valid JSON output
            import json

            try:
                json.loads(result.output)
                # Successfully parsed JSON output
            except json.JSONDecodeError:
                # Not JSON, check for expected text output
                assert "Loading embedding model" in result.output or "Searching for" in result.output

    def test_nonexistent_path_handling(self, runner):
        """Test handling of nonexistent repository paths."""
        result = runner.invoke(app, ["search-semantic", "/nonexistent/path", "test query"])

        # The command may return empty results for nonexistent paths
        # or fail depending on the implementation
        if result.exit_code == 0:
            # Check for empty results (valid JSON array)
            import json

            try:
                results = json.loads(result.output)
                assert isinstance(results, list)
                # Empty or minimal results for nonexistent path
            except json.JSONDecodeError:
                # Not JSON, might be text output
                pass
        else:
            # Should fail gracefully with error message
            assert "Error:" in result.output or "Failed" in result.output

    def test_command_in_main_help(self, runner):
        """Test that search-semantic command appears in main help."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        clean_output = strip_ansi_codes(result.output).lower()
        assert "search-semantic" in clean_output
