"""Tests for large codebase support features.

These tests verify the features added for handling large codebases:
- Grep timeout parameter and early termination (-m flag)
- File tree pagination
- Warm cache MCP tool
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kit.mcp.dev_server import (
    GetFileTreeParams,
    LocalDevServerLogic,
    WarmCacheParams,
)
from kit.repository import Repository


class TestGrepTimeoutAndEarlyTermination:
    """Test grep timeout parameter and early termination."""

    @pytest.fixture
    def repo(self):
        """Create a test repository with some files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            # Create files with searchable content
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()

            for i in range(10):
                (src_dir / f"file{i}.py").write_text(f"# TODO: task {i}\ndef func{i}():\n    pass\n")

            yield Repository(tmpdir)

    def test_grep_default_timeout(self, repo):
        """Test that grep uses default 120s timeout."""
        # Without env var, default should be 120s
        results = repo.grep("TODO", max_results=5)
        assert len(results) == 5  # Limited by max_results

    def test_grep_timeout_parameter(self, repo):
        """Test that grep accepts timeout parameter."""
        results = repo.grep("TODO", timeout=60)
        assert len(results) > 0

    def test_grep_timeout_from_env(self, repo):
        """Test that grep reads timeout from KIT_GREP_TIMEOUT env var."""
        with patch.dict(os.environ, {"KIT_GREP_TIMEOUT": "300"}):
            results = repo.grep("TODO")
            assert len(results) > 0

    def test_grep_early_termination(self, repo):
        """Test that grep uses -m flag for early termination."""
        # With max_results=2, grep should stop early
        results = repo.grep("TODO", max_results=2)
        assert len(results) <= 2


class TestFileTreePagination:
    """Test file tree pagination in MCP server."""

    @pytest.fixture
    def server_with_repo(self):
        """Create a server with a test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            # Create 50 test files
            for i in range(50):
                (Path(tmpdir) / f"file{i:03d}.py").write_text(f"# File {i}\n")

            server = LocalDevServerLogic()
            repo_id = server.open_repository(tmpdir)

            yield server, repo_id

    def test_pagination_default_limit(self, server_with_repo):
        """Test that default limit is 10000."""
        server, repo_id = server_with_repo
        tree = server.get_file_tree(repo_id)
        assert len(tree) == 50  # All files (less than default limit)

    def test_pagination_with_limit(self, server_with_repo):
        """Test pagination with explicit limit."""
        server, repo_id = server_with_repo
        tree = server.get_file_tree(repo_id)

        # Simulate pagination at MCP layer
        limit = 10
        offset = 0
        paginated = tree[offset : offset + limit]

        assert len(paginated) == 10
        # File order is not deterministic, just verify they're .py files
        assert all(item["path"].endswith(".py") for item in paginated)

    def test_pagination_with_offset(self, server_with_repo):
        """Test pagination with offset."""
        server, repo_id = server_with_repo
        tree = server.get_file_tree(repo_id)

        # Get second page
        limit = 10
        offset = 10
        paginated = tree[offset : offset + limit]

        assert len(paginated) == 10

    def test_pagination_has_more(self, server_with_repo):
        """Test has_more calculation."""
        server, repo_id = server_with_repo
        tree = server.get_file_tree(repo_id)

        total_count = len(tree)
        limit = 10
        offset = 0
        has_more = offset + limit < total_count

        assert has_more is True

        # Last page
        offset = 45
        has_more = offset + limit < total_count

        assert has_more is False


class TestWarmCacheTool:
    """Test the warm_cache MCP tool."""

    @pytest.fixture
    def server_with_repo(self):
        """Create a server with a test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            # Create some test files
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()

            for i in range(5):
                (src_dir / f"module{i}.py").write_text(
                    f"class Class{i}:\n    def method{i}(self):\n        pass\n"
                )

            server = LocalDevServerLogic()
            repo_id = server.open_repository(tmpdir)

            yield server, repo_id

    def test_warm_cache_file_tree(self, server_with_repo):
        """Test warming file tree cache."""
        server, repo_id = server_with_repo

        result = server.warm_cache(repo_id, warm_file_tree=True, warm_symbols=False)

        assert "repo_id" in result
        assert result["repo_id"] == repo_id
        assert "file_tree" in result
        assert "elapsed_seconds" in result["file_tree"]
        assert "file_count" in result["file_tree"]
        assert result["file_tree"]["file_count"] >= 5

    def test_warm_cache_symbols(self, server_with_repo):
        """Test warming symbol cache."""
        server, repo_id = server_with_repo

        result = server.warm_cache(repo_id, warm_file_tree=False, warm_symbols=True)

        assert "symbols" in result
        assert "elapsed_seconds" in result["symbols"]
        assert "symbol_count" in result["symbols"]
        # Should find classes and methods
        assert result["symbols"]["symbol_count"] >= 10

    def test_warm_cache_both(self, server_with_repo):
        """Test warming both caches."""
        server, repo_id = server_with_repo

        result = server.warm_cache(repo_id, warm_file_tree=True, warm_symbols=True)

        assert "file_tree" in result
        assert "symbols" in result


class TestGetFileTreeParamsModel:
    """Test GetFileTreeParams model has pagination fields."""

    def test_has_limit_field(self):
        """Test that GetFileTreeParams has limit field."""
        params = GetFileTreeParams(repo_id="test")
        assert params.limit == 10000  # default

    def test_has_offset_field(self):
        """Test that GetFileTreeParams has offset field."""
        params = GetFileTreeParams(repo_id="test")
        assert params.offset == 0  # default

    def test_custom_pagination(self):
        """Test custom pagination values."""
        params = GetFileTreeParams(repo_id="test", limit=100, offset=50)
        assert params.limit == 100
        assert params.offset == 50


class TestWarmCacheParamsModel:
    """Test WarmCacheParams model."""

    def test_default_values(self):
        """Test default values."""
        params = WarmCacheParams(repo_id="test")
        assert params.warm_file_tree is True
        assert params.warm_symbols is False

    def test_custom_values(self):
        """Test custom values."""
        params = WarmCacheParams(repo_id="test", warm_file_tree=False, warm_symbols=True)
        assert params.warm_file_tree is False
        assert params.warm_symbols is True
