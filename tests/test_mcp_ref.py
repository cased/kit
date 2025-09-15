"""Tests for MCP server with ref parameter and git metadata support."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kit.mcp.dev_server import KitServerLogic


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

        # Create some files
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("def hello(): pass\nclass TestClass: pass")

        # Make initial commit
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)

        # Get the current branch name (could be master or main)
        result = subprocess.run(
            ["git", "branch", "--show-current"], cwd=temp_dir, check=True, capture_output=True, text=True
        )
        default_branch = result.stdout.strip()

        # Create main branch if it doesn't exist
        if default_branch != "main":
            subprocess.run(["git", "checkout", "-b", "main"], cwd=temp_dir, check=True, capture_output=True)

        # Create a test branch
        subprocess.run(["git", "branch", "test-branch"], cwd=temp_dir, check=True, capture_output=True)

        yield temp_dir


class TestMCPRefParameter:
    """Test MCP server with ref parameter support."""

    def test_open_repository_with_ref(self, temp_git_repo):
        """Test opening repository with ref parameter via MCP."""
        logic = KitServerLogic()

        # Test opening repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")
        assert isinstance(repo_id, str)
        assert len(repo_id) > 0

        # Verify repository is stored
        assert repo_id in logic._repos

        # Check that the repository has the ref
        repo = logic._repos[repo_id]
        assert repo.ref == "main"

    def test_open_repository_without_ref(self):
        """Test opening repository without ref parameter via MCP."""
        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Test opening repository without ref
            repo_id = logic.open_repository(temp_dir)
            assert isinstance(repo_id, str)

            # Verify repository is stored
            assert repo_id in logic._repos

            # Check that the repository has no ref
            repo = logic._repos[repo_id]
            assert repo.ref is None

    def test_get_git_info(self):
        """Test getting git info via MCP."""
        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Create a test file and commit it
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass\nclass TestClass: pass")
            subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)

            # Open repository
            repo_id = logic.open_repository(temp_dir)

            # Get git info
            git_info = logic.get_git_info(repo_id)

            assert isinstance(git_info, dict)
            assert "current_sha" in git_info
            assert "current_sha_short" in git_info
            assert "current_branch" in git_info
            assert "remote_url" in git_info

            # Should have actual git data
            assert git_info["current_sha"] is not None
            assert len(git_info["current_sha"]) == 40  # Full SHA
            assert git_info["current_sha_short"] is not None
            assert len(git_info["current_sha_short"]) == 7  # Short SHA

    def test_get_git_info_with_ref(self, temp_git_repo):
        """Test getting git info for repository opened with ref via MCP."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")

        # Get git info
        result = logic.get_git_info(repo_id)
        assert result["current_sha"] is not None
        assert result["current_branch"] == "main"

    def test_get_git_info_nonexistent_repo(self):
        """Test getting git info for nonexistent repository."""
        logic = KitServerLogic()

        with pytest.raises(Exception):  # Should raise some kind of error
            logic.get_git_info("nonexistent-repo-id")

    def test_file_tree_with_ref(self, temp_git_repo):
        """Test getting file tree for repository opened with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")

        # Get file tree
        result = logic.get_file_tree(repo_id)
        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain test.py
        assert any(item["name"] == "test.py" for item in result)

    def test_extract_symbols_with_ref(self, temp_git_repo):
        """Test extracting symbols from repository opened with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")

        # Extract symbols
        result = logic.extract_symbols(repo_id, "test.py")
        assert isinstance(result, list)
        # Should find at least the hello function
        assert any(s["name"] == "hello" for s in result)

    def test_search_code_with_ref(self, temp_git_repo):
        """Test searching code in repository opened with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")

        # Search for code
        result = logic.search_code(repo_id, "hello")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_find_symbol_usages_with_ref(self, temp_git_repo):
        """Test finding symbol usages in repository opened with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(temp_git_repo, ref="main")

        # Find usages
        result = logic.find_symbol_usages(repo_id, "hello")
        assert isinstance(result, list)

    def test_tools_list_includes_review_diff(self):
        """Test that tools list includes review_diff tool."""
        logic = KitServerLogic()

        tools = logic.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "review_diff" in tool_names

    def test_open_repository_params_includes_ref(self):
        """Test that OpenRepoParams includes ref parameter."""
        from kit.mcp.dev_server import OpenRepoParams

        # Test creating params with ref
        params = OpenRepoParams(path_or_url=".", ref="main")
        assert params.path_or_url == "."
        assert params.ref == "main"

        # Test creating params without ref
        params = OpenRepoParams(path_or_url=".")
        assert params.path_or_url == "."
        assert params.ref is None

    def test_git_info_params(self):
        """Test GitInfoParams model."""
        from kit.mcp.dev_server import GitInfoParams

        params = GitInfoParams(repo_id="test-repo-id")
        assert params.repo_id == "test-repo-id"

    @patch("tempfile.TemporaryDirectory")
    def test_open_repository_invalid_ref_error(self, mock_temp_dir):
        """Test that opening repository with invalid ref raises appropriate error."""
        from kit.mcp.dev_server import INVALID_PARAMS, MCPError

        logic = KitServerLogic()

        with pytest.raises(MCPError) as exc_info:
            logic.open_repository(".", ref="nonexistent-ref-12345")

        assert exc_info.value.code == INVALID_PARAMS

    def test_multiple_repositories_with_different_refs(self, temp_git_repo):
        """Test opening multiple repositories with different refs."""
        logic = KitServerLogic()

        # Open repository without ref
        repo_id1 = logic.open_repository(temp_git_repo)

        # Open repository with ref
        repo_id2 = logic.open_repository(temp_git_repo, ref="main")

        # Verify different IDs
        assert repo_id1 != repo_id2

        # Verify different refs
        assert logic._repos[repo_id1].ref is None
        assert logic._repos[repo_id2].ref == "main"

        # Both should be able to provide git info
        git_info1 = logic.get_git_info(repo_id1)
        git_info2 = logic.get_git_info(repo_id2)

        assert isinstance(git_info1, dict)
        assert isinstance(git_info2, dict)

    def test_github_token_parameter(self):
        """Test that github_token parameter is properly handled."""
        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Should not error when github_token is provided
            repo_id = logic.open_repository(temp_dir, github_token="fake-token")
            assert isinstance(repo_id, str)

    def test_call_tool_git_info_integration(self):
        """Test calling git_info tool through the tool interface."""
        from kit.mcp.dev_server import GitInfoParams

        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Open repository
            repo_id = logic.open_repository(temp_dir)

            # Call git_info tool
            GitInfoParams(repo_id=repo_id)
            result = logic.get_git_info(repo_id)

            assert isinstance(result, dict)
            assert "current_sha" in result

    def test_grep_code_tool(self):
        """Test grep_code tool via MCP."""
        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Create a test file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass\nclass TestClass: pass")

            # Open repository
            repo_id = logic.open_repository(temp_dir)

            # Test grep_code tool
            from kit.mcp.dev_server import GrepParams

            GrepParams(repo_id=repo_id, pattern="hello")
            result = logic.grep_code(repo_id, "hello")

            assert isinstance(result, list)
            assert len(result) > 0

    def test_grep_code_with_parameters(self):
        """Test grep_code tool with various parameters."""
        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Create test files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass\nclass TestClass: pass")
            other_file = Path(temp_dir) / "other.py"
            other_file.write_text("def goodbye(): pass")

            # Open repository
            repo_id = logic.open_repository(temp_dir)

            # Test with include pattern
            result = logic.grep_code(repo_id, "hello", include_pattern="*.py")
            assert isinstance(result, list)
            assert len(result) > 0

            # Test with case insensitive
            result = logic.grep_code(repo_id, "HELLO", case_sensitive=False)
            assert isinstance(result, list)
            assert len(result) > 0

    def test_grep_code_invalid_directory(self):
        """Test grep_code with invalid directory."""
        from kit.mcp.dev_server import INVALID_PARAMS, MCPError

        logic = KitServerLogic()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Open repository
            repo_id = logic.open_repository(temp_dir)

            # Test with invalid directory - should raise MCPError
            with pytest.raises(MCPError) as exc_info:
                logic.grep_code(repo_id, "hello", directory="/nonexistent")
            assert exc_info.value.code == INVALID_PARAMS
            assert "Directory not found" in exc_info.value.message

    def test_grep_params_model(self):
        """Test GrepParams model."""
        from kit.mcp.dev_server import GrepParams

        # Test basic params
        params = GrepParams(repo_id="test-repo", pattern="TODO")
        assert params.repo_id == "test-repo"
        assert params.pattern == "TODO"
        assert params.case_sensitive is True  # Default
        assert params.include_hidden is False  # Default

        # Test with all parameters
        params = GrepParams(
            repo_id="test-repo",
            pattern="function",
            case_sensitive=False,
            include_pattern="*.py",
            exclude_pattern="*test*",
            max_results=50,
            directory="src",
            include_hidden=True,
        )
        assert params.case_sensitive is False
        assert params.include_pattern == "*.py"
        assert params.exclude_pattern == "*test*"
        assert params.max_results == 50
        assert params.directory == "src"
        assert params.include_hidden is True

    def test_tools_list_includes_grep(self):
        """Test that tools list includes grep_code tool."""
        logic = KitServerLogic()

        tools = logic.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "grep_code" in tool_names

        # Find the grep tool and check its description
        grep_tool = next(tool for tool in tools if tool.name == "grep_code")
        assert "literal string search" in grep_tool.description.lower()
