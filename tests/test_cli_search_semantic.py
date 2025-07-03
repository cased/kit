"""Tests for the search-semantic CLI command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestSearchSemanticCommand:
    """Test cases for the search-semantic CLI command."""

    def test_help_message(self, runner):
        """Test that search-semantic shows proper help message."""
        result = runner.invoke(app, ["search-semantic", "--help"])
        
        assert result.exit_code == 0
        assert "Perform semantic search using vector embeddings" in result.output
        assert "natural language queries" in result.output
        assert "--top-k" in result.output
        assert "--embedding-model" in result.output
        assert "--chunk-by" in result.output

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
        # This test just validates input without importing sentence_transformers
        result = runner.invoke(app, ["search-semantic", ".", "test", "--chunk-by", "invalid"])
        
        assert result.exit_code == 1
        assert "Invalid chunk_by value: invalid" in result.output
        assert "Use 'symbols' or 'lines'" in result.output

    def test_sentence_transformers_not_installed_error(self, runner):
        """Test that command fails gracefully when sentence-transformers is not available."""
        # This test will naturally fail if sentence-transformers is not installed
        # We expect either success (if installed) or a helpful error message
        result = runner.invoke(app, ["search-semantic", ".", "test query"])
        
        # Should either work (exit 0) or show helpful error (exit 1)
        assert result.exit_code in [0, 1]
        
        if result.exit_code == 1:
            # If it fails, should be due to missing sentence-transformers or similar
            expected_errors = [
                "sentence-transformers",
                "Failed to load embedding model",
                "Failed to initialize vector searcher"
            ]
            assert any(error in result.output for error in expected_errors) 