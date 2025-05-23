"""Tests for MCP server with ref parameter and git metadata support."""

from unittest.mock import patch

import pytest

from kit.mcp.server import KitServerLogic


class TestMCPRefParameter:
    """Test MCP server with ref parameter support."""

    def test_open_repository_with_ref(self):
        """Test opening repository with ref parameter via MCP."""
        logic = KitServerLogic()

        # Test opening repository with ref
        repo_id = logic.open_repository(".", ref="main")
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

        # Test opening repository without ref
        repo_id = logic.open_repository(".")
        assert isinstance(repo_id, str)

        # Verify repository is stored
        assert repo_id in logic._repos

        # Check that the repository has no ref
        repo = logic._repos[repo_id]
        assert repo.ref is None

    def test_get_git_info(self):
        """Test getting git info via MCP."""
        logic = KitServerLogic()

        # Open repository
        repo_id = logic.open_repository(".")

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

    def test_get_git_info_with_ref(self):
        """Test getting git info for repository opened with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(".", ref="main")

        # Get git info
        git_info = logic.get_git_info(repo_id)

        assert git_info["current_sha"] is not None

    def test_get_git_info_nonexistent_repo(self):
        """Test getting git info for nonexistent repository."""
        logic = KitServerLogic()

        with pytest.raises(Exception):  # Should raise some kind of error
            logic.get_git_info("nonexistent-repo-id")

    def test_file_tree_with_ref(self):
        """Test getting file tree for repository with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(".", ref="main")

        # Get file tree
        file_tree = logic.get_file_tree(repo_id)

        assert isinstance(file_tree, list)
        assert len(file_tree) > 0

    def test_extract_symbols_with_ref(self):
        """Test extracting symbols for repository with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(".", ref="main")

        # Extract symbols
        symbols = logic.extract_symbols(repo_id, "src/kit/repository.py")

        assert isinstance(symbols, list)

    def test_search_code_with_ref(self):
        """Test searching code for repository with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(".", ref="main")

        # Search code
        results = logic.search_code(repo_id, "Repository")

        assert isinstance(results, list)

    def test_find_symbol_usages_with_ref(self):
        """Test finding symbol usages for repository with ref."""
        logic = KitServerLogic()

        # Open repository with ref
        repo_id = logic.open_repository(".", ref="main")

        # Find symbol usages
        usages = logic.find_symbol_usages(repo_id, "Repository")

        assert isinstance(usages, list)

    def test_tools_list_includes_git_info(self):
        """Test that tools list includes get_git_info tool."""
        logic = KitServerLogic()

        tools = logic.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "get_git_info" in tool_names

    def test_open_repository_params_includes_ref(self):
        """Test that OpenRepoParams includes ref parameter."""
        from kit.mcp.server import OpenRepoParams

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
        from kit.mcp.server import GitInfoParams

        params = GitInfoParams(repo_id="test-repo-id")
        assert params.repo_id == "test-repo-id"

    @patch("tempfile.TemporaryDirectory")
    def test_open_repository_invalid_ref_error(self, mock_temp_dir):
        """Test that opening repository with invalid ref raises appropriate error."""
        from kit.mcp.server import INVALID_PARAMS, MCPError

        logic = KitServerLogic()

        with pytest.raises(MCPError) as exc_info:
            logic.open_repository(".", ref="nonexistent-ref-12345")

        assert exc_info.value.code == INVALID_PARAMS

    def test_multiple_repositories_with_different_refs(self):
        """Test opening multiple repositories with different refs."""
        logic = KitServerLogic()

        # Open repository without ref
        repo_id1 = logic.open_repository(".")

        # Open repository with ref
        repo_id2 = logic.open_repository(".", ref="main")

        # Should be different repository instances
        assert repo_id1 != repo_id2
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

        # Should not error when github_token is provided
        repo_id = logic.open_repository(".", github_token="fake-token")
        assert isinstance(repo_id, str)

    def test_call_tool_git_info_integration(self):
        """Test calling git_info tool through the tool interface."""
        from kit.mcp.server import GitInfoParams

        logic = KitServerLogic()

        # Open repository
        repo_id = logic.open_repository(".")

        # Simulate calling the tool
        git_args = GitInfoParams(repo_id=repo_id)
        git_info = logic.get_git_info(git_args.repo_id)

        assert isinstance(git_info, dict)
        assert "current_sha" in git_info
