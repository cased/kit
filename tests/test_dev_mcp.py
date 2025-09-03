"""Tests for the local development MCP server."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kit.mcp.dev_server import (
    BuildContextParams,
    DeepResearchParams,
    FileChange,
    FileWatcher,
    LocalDevServerLogic,
    SemanticSearchParams,
    WatchFilesParams,
)


class TestFileWatcher:
    """Test the FileWatcher class."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.repo_path = "/test/repo"
        repo.get_file_tree.return_value = [
            {"path": "test.py", "is_dir": False},
            {"path": "src/main.py", "is_dir": False},
            {"path": ".git/config", "is_dir": False},
            {"path": "node_modules/lib.js", "is_dir": False},
        ]
        return repo

    def test_file_watcher_init(self, mock_repo):
        """Test FileWatcher initialization."""
        watcher = FileWatcher(mock_repo)

        assert watcher.repo == mock_repo
        assert watcher.watched_files == {}
        assert watcher.changes == []
        assert watcher.running is False

    @pytest.mark.asyncio
    async def test_start_watching(self, mock_repo):
        """Test starting file watching."""
        watcher = FileWatcher(mock_repo)

        # Start watching in background
        task = asyncio.create_task(watcher.start_watching(["*.py"], [".git", "node_modules"]))

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop watching
        watcher.stop_watching()

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert watcher.running is False

    def test_get_recent_changes(self, mock_repo):
        """Test getting recent file changes."""
        watcher = FileWatcher(mock_repo)

        # Add some mock changes
        watcher.changes = [
            FileChange("file1.py", "created", 1000),
            FileChange("file2.py", "modified", 1001),
            FileChange("file3.py", "modified", 1002),
        ]

        recent = watcher.get_recent_changes(limit=2)

        assert len(recent) == 2
        assert recent[0].path == "file2.py"
        assert recent[1].path == "file3.py"


class TestLocalDevServerLogic:
    """Test the LocalDevServerLogic class."""

    @pytest.fixture
    def server(self):
        """Create a server instance."""
        return LocalDevServerLogic()

    def test_init(self, server):
        """Test server initialization."""
        assert server._repos == {}
        assert server._watchers == {}
        assert server._test_results == {}
        assert server._context_cache == {}
        assert server._indexers == {}

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

    @pytest.mark.asyncio
    async def test_watch_files(self, server):
        """Test starting file watching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            repo_id = server.open_repository(tmpdir)

            result = await server.watch_files(repo_id, patterns=["*.py"], exclude_dirs=[".git"])

            assert result["status"] == "watching"
            assert result["patterns"] == ["*.py"]
            assert result["exclude_dirs"] == [".git"]
            assert repo_id in server._watchers

    def test_get_file_changes(self, server):
        """Test getting file changes."""
        # No watcher exists
        changes = server.get_file_changes("invalid_repo")
        assert changes == []

        # With watcher
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            repo_id = server.open_repository(tmpdir)
            server._watchers[repo_id] = MagicMock()
            server._watchers[repo_id].get_recent_changes.return_value = [FileChange("test.py", "modified", 1000)]

            changes = server.get_file_changes(repo_id)

            assert len(changes) == 1
            assert changes[0]["path"] == "test.py"
            assert changes[0]["type"] == "modified"

    def test_deep_research_package(self, server):
        """Test deep research package functionality."""
        result = server.deep_research_package("fastapi", query="What are the main features?")

        assert result["package"] == "fastapi"
        assert "model" in result
        assert "execution_time" in result
        assert "documentation" in result
        assert isinstance(result["documentation"], str)

    def test_build_smart_context(self, server):
        """Test building smart context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            # Create some test files
            (Path(tmpdir) / "auth.py").write_text("def authenticate(): pass")
            (Path(tmpdir) / "test_auth.py").write_text("def test_auth(): pass")
            (Path(tmpdir) / "requirements.txt").write_text("fastapi==0.1.0\n")

            repo_id = server.open_repository(tmpdir)

            context = server.build_smart_context(
                repo_id,
                task_description="add authentication",
                include_tests=True,
                include_docs=False,
                include_dependencies=True,
                max_files=10,
            )

            assert context["task"] == "add authentication"
            assert context["repository"]["path"] == tmpdir
            assert isinstance(context["relevant_files"], list)
            assert isinstance(context["tests"], list)
            assert isinstance(context["dependencies"], list)

    def test_list_tools(self, server):
        """Test listing available tools."""
        tools = server.list_tools()

        assert isinstance(tools, list)
        assert len(tools) == 16  # Should have exactly 16 tools

        tool_names = {tool.name for tool in tools}

        # Check for our key tools that actually exist
        assert "open_repository" in tool_names
        assert "watch_files" in tool_names
        assert "deep_research_package" in tool_names
        assert "build_smart_context" in tool_names
        assert "semantic_search" in tool_names
        assert "review_diff" in tool_names
        assert "get_file_content" in tool_names
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
        params = WatchFilesParams(repo_id="test", patterns=["*.py"], exclude_dirs=[".git"])
        assert params.repo_id == "test"

        params = DeepResearchParams(package_name="fastapi", use_context7=True, max_sources=5)
        assert params.package_name == "fastapi"

        params = BuildContextParams(
            repo_id="test",
            task_description="Add auth",
            include_tests=True,
            include_docs=True,
            include_dependencies=True,
            max_files=20,
        )
        assert params.task_description == "Add auth"

        params = SemanticSearchParams(repo_id="test", query="authentication", max_results=10)
        assert params.query == "authentication"
