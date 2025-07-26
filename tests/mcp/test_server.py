import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kit.mcp.server import INVALID_PARAMS, GetPromptResult, KitServerLogic, MCPError


@pytest.fixture
def logic():
    """Create a KitServerLogic instance for testing."""
    return KitServerLogic()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
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

        # Make initial commit
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)

        yield temp_dir


class TestMCPGitHubTokenPickup:
    """Test MCP server GitHub token pickup functionality."""

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "test_kit_token", "GITHUB_TOKEN": "test_github_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_picks_up_kit_github_token(self, mock_repo_class):
        """Test that MCP server picks up KIT_GITHUB_TOKEN environment variable."""
        logic = KitServerLogic()
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            repo_id = logic.open_repository(temp_dir)

            mock_repo_class.assert_called_once_with(temp_dir, github_token="test_kit_token", ref=None)
            assert repo_id in logic._repos

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_github_token"}, clear=True)
    @patch("kit.mcp.server.Repository")
    def test_mcp_picks_up_github_token_fallback(self, mock_repo_class):
        """Test that MCP server falls back to GITHUB_TOKEN when KIT_GITHUB_TOKEN is not set."""
        logic = KitServerLogic()
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            repo_id = logic.open_repository(temp_dir)

            mock_repo_class.assert_called_once_with(temp_dir, github_token="test_github_token", ref=None)
            assert repo_id in logic._repos

    @patch.dict("os.environ", {}, clear=True)
    @patch("kit.mcp.server.Repository")
    def test_mcp_no_token_when_env_empty(self, mock_repo_class):
        """Test that MCP server works without GitHub token when environment is empty."""
        logic = KitServerLogic()
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            repo_id = logic.open_repository(temp_dir)

            mock_repo_class.assert_called_once_with(temp_dir, github_token=None, ref=None)
            assert repo_id in logic._repos

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "env_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_explicit_token_overrides_env(self, mock_repo_class):
        """Test that explicitly passed GitHub token overrides environment variable."""
        logic = KitServerLogic()
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            repo_id = logic.open_repository(temp_dir, github_token="explicit_token")

            mock_repo_class.assert_called_once_with(temp_dir, github_token="explicit_token", ref=None)
            assert repo_id in logic._repos

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "test_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_with_ref_passes_token(self, mock_repo_class):
        """Test that MCP server passes GitHub token when ref is specified."""
        logic = KitServerLogic()
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            repo_id = logic.open_repository(temp_dir, ref="main")

            mock_repo_class.assert_called_once_with(temp_dir, github_token="test_token", ref="main")
            assert repo_id in logic._repos


class TestMCPMultiFileContent:
    """Test MCP server multi-file get_file_content functionality."""

    def test_get_single_file_content_mcp(self, logic, temp_git_repo):
        """Test single file content retrieval through MCP server."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = "def hello():\n    print('world')\n"

            result = logic.get_file_content(repo_id, "test.py")

            assert isinstance(result, str)
            assert "def hello()" in result
            mock_content.assert_called_once_with("test.py")

    def test_get_multiple_file_contents_mcp(self, logic, temp_git_repo):
        """Test multiple file content retrieval through MCP server."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {"file1.py": "# File 1\nprint('hello')", "file2.py": "# File 2\nprint('world')"}

            result = logic.get_file_content(repo_id, ["file1.py", "file2.py"])

            assert isinstance(result, dict)
            assert len(result) == 2
            assert "file1.py" in result
            assert "file2.py" in result
            assert "# File 1" in result["file1.py"]
            assert "# File 2" in result["file2.py"]

    def test_get_multiple_file_contents_dedicated_method(self, logic, temp_git_repo):
        """Test dedicated get_multiple_file_contents method."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {"src/main.py": "# Main file", "src/utils.py": "# Utils file"}

            result = logic.get_multiple_file_contents(repo_id, ["src/main.py", "src/utils.py"])

            assert isinstance(result, dict)
            assert len(result) == 2
            assert result["src/main.py"] == "# Main file"
            assert result["src/utils.py"] == "# Utils file"

    def test_get_file_content_path_validation_single(self, logic, temp_git_repo):
        """Test path validation for single file."""
        repo_id = logic.open_repository(temp_git_repo)

        with pytest.raises(MCPError) as exc:
            logic.get_file_content(repo_id, "../secrets.txt")
        assert exc.value.code == INVALID_PARAMS
        assert "Path traversal" in exc.value.message

    def test_get_file_content_path_validation_multiple(self, logic, temp_git_repo):
        """Test path validation for multiple files."""
        repo_id = logic.open_repository(temp_git_repo)

        with pytest.raises(MCPError) as exc:
            logic.get_file_content(repo_id, ["valid.py", "../secrets.txt"])
        assert exc.value.code == INVALID_PARAMS
        assert "Path traversal" in exc.value.message

    def test_get_multiple_file_contents_error_handling(self, logic, temp_git_repo):
        """Test error handling in dedicated multiple file method."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.side_effect = FileNotFoundError("Files not found: missing.py")

            with pytest.raises(MCPError) as exc:
                logic.get_multiple_file_contents(repo_id, ["missing.py"])
            assert exc.value.code == INVALID_PARAMS
            assert "Files not found" in exc.value.message

    def test_get_file_content_type_detection(self, logic, temp_git_repo):
        """Test that method correctly handles both string and list inputs."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            # Test string input
            mock_content.return_value = "string content"
            result1 = logic.get_file_content(repo_id, "single.py")
            assert isinstance(result1, str)

            # Test list input
            mock_content.return_value = {"multi.py": "dict content"}
            result2 = logic.get_file_content(repo_id, ["multi.py"])
            assert isinstance(result2, dict)

    def test_get_file_content_empty_list(self, logic, temp_git_repo):
        """Test handling of empty file list."""
        repo_id = logic.open_repository(temp_git_repo)

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {}

            result = logic.get_file_content(repo_id, [])
            assert isinstance(result, dict)
            assert len(result) == 0

    def test_mcp_tools_list_includes_multi_file(self, logic):
        """Test that tools list includes the multi-file content method."""
        tools = logic.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "get_multiple_file_contents" in tool_names

    def test_path_mapping_consistency(self, logic, temp_git_repo):
        """Test that path mapping is consistent between single and multiple file methods."""
        repo_id = logic.open_repository(temp_git_repo)

        def mock_path_check(path):
            # This would be called by the repository to validate paths
            # When called with a list, return a dictionary
            if isinstance(path, list):
                return {p: f"Content of {p}" for p in path}
            return f"Content of {path}"

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.side_effect = mock_path_check

            # Both methods should use the same path validation
            logic.get_file_content(repo_id, "test.py")
            logic.get_file_content(repo_id, ["test.py"])

            # Verify both calls were made
            assert mock_content.call_count == 2


def test_open_repository(logic, temp_git_repo):
    """Test opening a repository."""
    repo_id = logic.open_repository(temp_git_repo)
    assert isinstance(repo_id, str)
    assert repo_id in logic._repos


def test_get_file_tree(logic, temp_git_repo):
    """Test getting file tree."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.get_file_tree(repo_id)
    assert isinstance(result, list)
    assert len(result) > 0


def test_extract_symbols(logic, temp_git_repo):
    """Test extracting symbols."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.extract_symbols(repo_id, "test.py")
    assert isinstance(result, list)
    assert len(result) > 0


def test_find_symbol_usages(logic, temp_git_repo):
    """Test finding symbol usages."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.find_symbol_usages(repo_id, "hello")
    assert isinstance(result, list)


def test_search_code(logic, temp_git_repo):
    """Test searching code."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.search_code(repo_id, "hello")
    assert isinstance(result, list)


def test_get_file_content(logic, temp_git_repo):
    """Test getting file content."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.get_file_content(repo_id, "test.py")
    assert isinstance(result, str)


def test_get_code_summary_mocked(logic, temp_git_repo):
    """Test getting code summary with mocked repository."""
    repo_id = logic.open_repository(temp_git_repo)

    # Mock the analyzer instead of Repository method
    with patch.object(logic, "get_analyzer") as mock_get_analyzer:
        mock_analyzer = MagicMock()
        mock_analyzer.summarize_file.return_value = {
            "summary": "This is a test file with a hello function and TestClass."
        }
        mock_analyzer.summarize_symbol.return_value = [
            {"name": "hello", "type": "function", "line": 1}
        ]
        mock_get_analyzer.return_value = mock_analyzer

        result = logic.get_code_summary(repo_id, "test.py")

        assert isinstance(result, dict)
        assert "file" in result
        assert "summary" in result["file"]


def test_get_prompt_open_repo(logic, temp_git_repo):
    """Test getting prompt with open repository."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.get_prompt("get_code_summary", {"repo_id": repo_id, "file_path": "test.py"})
    assert isinstance(result, GetPromptResult)
    assert result.messages


def test_invalid_prompt_name(logic, temp_git_repo):
    """Test getting invalid prompt name."""
    repo_id = logic.open_repository(temp_git_repo)
    with pytest.raises(MCPError):
        logic.get_prompt("invalid_prompt", {"repo_id": repo_id})


def test_list_tools(logic):
    """Test listing tools."""
    tools = logic.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_list_prompts(logic):
    """Test listing prompts."""
    prompts = logic.list_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) > 0


def test_get_prompt_with_missing_args(logic, temp_git_repo):
    """Test getting prompt with missing arguments."""
    logic.open_repository(temp_git_repo)
    with pytest.raises(MCPError):
        logic.get_prompt("get_code_summary", None)


def test_get_prompt_with_invalid_args(logic, temp_git_repo):
    """Test getting prompt with invalid arguments."""
    logic.open_repository(temp_git_repo)
    with pytest.raises(MCPError):
        logic.get_prompt("get_code_summary", {"invalid": "args"})


def test_repository_not_found(logic):
    """Test accessing non-existent repository."""
    with pytest.raises(MCPError):
        logic.get_file_tree("nonexistent-repo-id")


def test_open_repository_invalid_path(logic):
    """Test opening repository with invalid path."""
    # Repository accepts non-existent paths, so we test operations on it instead
    repo_id = logic.open_repository("/nonexistent/path")
    # Operations on non-existent repo should fail
    with pytest.raises(MCPError):
        logic.get_file_content(repo_id, "test.py")


def test_get_file_content_nonexistent_file(logic, temp_git_repo):
    """Test getting content of non-existent file."""
    repo_id = logic.open_repository(temp_git_repo)
    with pytest.raises(MCPError):
        logic.get_file_content(repo_id, "nonexistent.py")


def test_extract_symbols_invalid_file(logic, temp_git_repo):
    """Test extracting symbols from invalid file."""
    repo_id = logic.open_repository(temp_git_repo)
    # Repository logs warning and returns empty list for non-existent files
    result = logic.extract_symbols(repo_id, "nonexistent.py")
    assert isinstance(result, list)
    assert len(result) == 0


def test_find_symbol_usages_invalid_symbol(logic, temp_git_repo):
    """Test finding usages of non-existent symbol."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.find_symbol_usages(repo_id, "nonexistent_symbol")
    assert isinstance(result, list)
    assert len(result) == 0


def test_search_code_invalid_pattern(logic, temp_git_repo):
    """Test searching with invalid pattern."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.search_code(repo_id, "nonexistent_pattern")
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_code_summary_invalid_type(logic, temp_git_repo):
    """Test getting code summary with invalid type."""
    repo_id = logic.open_repository(temp_git_repo)
    # get_code_summary doesn't have a symbol_type parameter
    # Test with invalid file path instead
    with pytest.raises(MCPError):
        logic.get_code_summary(repo_id, "../invalid/path.py")


def test_find_symbol_usages_invalid_repo_id(logic):
    """Test finding symbol usages with invalid repo ID."""
    with pytest.raises(MCPError):
        logic.find_symbol_usages("nonexistent-repo-id", "symbol")


def test_get_code_summary_invalid_repo_id(logic):
    """Test getting code summary with invalid repo ID."""
    with pytest.raises(MCPError):
        logic.get_code_summary("nonexistent-repo-id", "test.py")


def test_get_code_summary_error(logic, temp_git_repo):
    """Test getting code summary with error."""
    repo_id = logic.open_repository(temp_git_repo)

    # Mock the analyzer instead of Repository method
    with patch.object(logic, "get_analyzer") as mock_get_analyzer:
        mock_analyzer = MagicMock()
        mock_analyzer.summarize_file.side_effect = Exception("Test error")
        mock_get_analyzer.return_value = mock_analyzer

        with pytest.raises(MCPError):
            logic.get_code_summary(repo_id, "test.py")


def test_get_file_content_path_traversal(logic, temp_git_repo):
    """Test path traversal protection in get_file_content."""
    repo_id = logic.open_repository(temp_git_repo)

    with pytest.raises(MCPError) as exc:
        logic.get_file_content(repo_id, "../../../etc/passwd")
    assert exc.value.code == INVALID_PARAMS
    assert "Path traversal" in exc.value.message


def test_extract_symbols_path_traversal(logic, temp_git_repo):
    """Test path traversal protection in extract_symbols."""
    repo_id = logic.open_repository(temp_git_repo)

    with pytest.raises(MCPError) as exc:
        logic.extract_symbols(repo_id, "../../../etc/passwd")
    assert exc.value.code == INVALID_PARAMS
    assert "Path traversal" in exc.value.message


def test_mcp_tool_output_get_file_tree(logic: KitServerLogic, temp_git_repo):
    """Test MCP tool output for get_file_tree."""
    repo_id = logic.open_repository(temp_git_repo)
    result = logic.get_file_tree(repo_id)
    assert isinstance(result, list)
    assert len(result) > 0
