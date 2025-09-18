"""Tests for the local development MCP server."""

import tempfile
from pathlib import Path

import pytest

from kit.mcp.dev_server import (
    DeepResearchParams,
    LocalDevServerLogic,
)


class TestLocalDevServerLogic:
    """Test the LocalDevServerLogic class."""

    @pytest.fixture
    def server(self):
        """Create a server instance."""
        return LocalDevServerLogic()

    def test_init(self, server):
        """Test server initialization."""
        assert server._repos == {}
        assert server._test_results == {}
        assert server._context_cache == {}

    def test_open_repository(self, server):
        """Test opening a repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            repo_id = server.open_repository(tmpdir)

            assert repo_id == "repo_0"
            assert repo_id in server._repos
            assert server._repos[repo_id].repo_path == tmpdir

    def test_get_repo(self, server):
        """Test getting a repository by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            repo_id = server.open_repository(tmpdir)
            repo = server.get_repo(repo_id)

            assert repo is not None
            assert repo.repo_path == tmpdir

    def test_get_repo_not_found(self, server):
        """Test getting a non-existent repository."""
        from kit.mcp.dev_server import MCPError

        with pytest.raises(MCPError, match="Repository invalid_id not found"):
            server.get_repo("invalid_id")

    def test_deep_research_package(self, server):
        """Test deep research package functionality."""
        result = server.deep_research_package("fastapi", query="What are the main features?")

        assert result["package"] == "fastapi"
        assert "status" in result
        assert "source" in result
        assert "providers" in result  # Changed from provider to providers
        assert isinstance(result["providers"], list)  # Providers is now a list
        assert "version" in result
        # Documentation is now a dict from Context7 or None if not found
        if result["status"] == "success":
            assert "documentation" in result
            assert isinstance(result["documentation"], dict)
        else:
            # If not found, should have guidance
            assert "available_libraries" in result or "documentation" in result

    def test_list_tools(self, server):
        """Test listing available tools."""
        tools = server.list_tools()

        assert isinstance(tools, list)
        assert len(tools) >= 8  # Should have at least 8 core tools

        tool_names = {tool.name for tool in tools}

        # Check for our key tools that actually exist
        assert "open_repository" in tool_names
        assert "deep_research_package" in tool_names
        assert "grep_ast" in tool_names  # Replaced semantic_search with grep_ast
        assert "review_diff" in tool_names
        assert "extract_symbols" in tool_names


class TestMCPServerIntegration:
    """Test the MCP server integration."""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test that the server can be initialized."""
        from kit.mcp.dev_server import serve

        # We can't fully test the server without mocking stdio
        # but we can check it's importable
        assert serve is not None
        assert callable(serve)

    def test_parameter_models(self):
        """Test that all parameter models are valid."""
        # Test instantiation of parameter models
        params = DeepResearchParams(package_name="fastapi")
        assert params.package_name == "fastapi"
