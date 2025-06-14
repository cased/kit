import json
import uuid
from unittest.mock import patch

import pytest
from mcp.types import TextContent

from kit.mcp.server import INVALID_PARAMS, GetFileTreeParams, KitServerLogic, MCPError
from kit.summaries import LLMError


@pytest.fixture
def logic():
    return KitServerLogic()


class TestMCPGitHubTokenPickup:
    """Test MCP server automatic GitHub token pickup from environment."""

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "test_kit_token", "GITHUB_TOKEN": "test_github_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_picks_up_kit_github_token(self, mock_repo_class):
        """Test that MCP server picks up KIT_GITHUB_TOKEN when no token provided."""
        logic = KitServerLogic()

        repo_id = logic.open_repository("https://github.com/test/repo")

        # Should have called Repository with KIT_GITHUB_TOKEN
        mock_repo_class.assert_called_once_with(
            "https://github.com/test/repo",
            github_token="test_kit_token",  # KIT_GITHUB_TOKEN should be used
            ref=None,
        )
        assert repo_id in logic._repos

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_github_token"}, clear=True)
    @patch("kit.mcp.server.Repository")
    def test_mcp_picks_up_github_token_fallback(self, mock_repo_class):
        """Test that MCP server falls back to GITHUB_TOKEN when KIT_GITHUB_TOKEN not set."""
        logic = KitServerLogic()

        repo_id = logic.open_repository("https://github.com/test/repo")

        # Should have called Repository with GITHUB_TOKEN
        mock_repo_class.assert_called_once_with(
            "https://github.com/test/repo",
            github_token="test_github_token",  # GITHUB_TOKEN should be used as fallback
            ref=None,
        )
        assert repo_id in logic._repos

    @patch.dict("os.environ", {}, clear=True)
    @patch("kit.mcp.server.Repository")
    def test_mcp_no_token_when_env_empty(self, mock_repo_class):
        """Test that MCP server passes None when no environment tokens are set."""
        logic = KitServerLogic()

        repo_id = logic.open_repository("https://github.com/test/repo")

        # Should have called Repository with None
        mock_repo_class.assert_called_once_with(
            "https://github.com/test/repo",
            github_token=None,  # No token should be passed
            ref=None,
        )
        assert repo_id in logic._repos

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "env_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_explicit_token_overrides_env(self, mock_repo_class):
        """Test that explicitly provided token overrides environment variables."""
        logic = KitServerLogic()

        repo_id = logic.open_repository("https://github.com/test/repo", github_token="explicit_token")

        # Should have called Repository with explicit token
        mock_repo_class.assert_called_once_with(
            "https://github.com/test/repo",
            github_token="explicit_token",  # Explicit token should override environment
            ref=None,
        )
        assert repo_id in logic._repos

    @patch.dict("os.environ", {"KIT_GITHUB_TOKEN": "test_token"})
    @patch("kit.mcp.server.Repository")
    def test_mcp_with_ref_passes_token(self, mock_repo_class):
        """Test that MCP server passes environment token even when ref is specified."""
        logic = KitServerLogic()

        repo_id = logic.open_repository("https://github.com/test/repo", ref="main")

        # Should have called Repository with environment token and ref
        mock_repo_class.assert_called_once_with(
            "https://github.com/test/repo",
            github_token="test_token",  # Environment token should be used
            ref="main",
        )
        assert repo_id in logic._repos


class TestMCPMultiFileContent:
    """Test MCP server multi-file get_file_content functionality."""

    def test_get_single_file_content_mcp(self, logic):
        """Test single file content retrieval through MCP server."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = "def hello():\n    print('world')\n"

            result = logic.get_file_content(repo_id, "test.py")

            assert isinstance(result, str)
            assert "def hello()" in result
            mock_content.assert_called_once_with("test.py")

    def test_get_multiple_file_contents_mcp(self, logic):
        """Test multiple file content retrieval through MCP server."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {"file1.py": "# File 1\nprint('hello')", "file2.py": "# File 2\nprint('world')"}

            result = logic.get_file_content(repo_id, ["file1.py", "file2.py"])

            assert isinstance(result, dict)
            assert len(result) == 2
            assert "file1.py" in result
            assert "file2.py" in result
            assert "# File 1" in result["file1.py"]
            assert "# File 2" in result["file2.py"]

    def test_get_multiple_file_contents_dedicated_method(self, logic):
        """Test dedicated get_multiple_file_contents method."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {"src/main.py": "# Main file", "src/utils.py": "# Utils file"}

            result = logic.get_multiple_file_contents(repo_id, ["src/main.py", "src/utils.py"])

            assert isinstance(result, dict)
            assert len(result) == 2
            assert result["src/main.py"] == "# Main file"
            assert result["src/utils.py"] == "# Utils file"

    def test_get_file_content_path_validation_single(self, logic):
        """Test path validation for single file."""
        repo_id = logic.open_repository(".")

        with pytest.raises(MCPError) as exc:
            logic.get_file_content(repo_id, "../secrets.txt")
        assert exc.value.code == INVALID_PARAMS
        assert "Path traversal" in exc.value.message

    def test_get_file_content_path_validation_multiple(self, logic):
        """Test path validation for multiple files."""
        repo_id = logic.open_repository(".")

        with pytest.raises(MCPError) as exc:
            logic.get_file_content(repo_id, ["valid.py", "../secrets.txt"])
        assert exc.value.code == INVALID_PARAMS
        assert "Path traversal" in exc.value.message

    def test_get_multiple_file_contents_error_handling(self, logic):
        """Test error handling in dedicated multiple file method."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.side_effect = FileNotFoundError("Files not found: missing.py")

            with pytest.raises(MCPError) as exc:
                logic.get_multiple_file_contents(repo_id, ["missing.py"])
            assert exc.value.code == INVALID_PARAMS
            assert "Files not found" in exc.value.message

    def test_get_file_content_type_detection(self, logic):
        """Test that method correctly handles both string and list inputs."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            # Test string input
            mock_content.return_value = "string content"
            result1 = logic.get_file_content(repo_id, "single.py")
            assert isinstance(result1, str)

            # Test list input
            mock_content.return_value = {"multi.py": "dict content"}
            result2 = logic.get_file_content(repo_id, ["multi.py"])
            assert isinstance(result2, dict)

    def test_get_file_content_empty_list(self, logic):
        """Test handling of empty file list."""
        repo_id = logic.open_repository(".")

        with patch("kit.repository.Repository.get_file_content") as mock_content:
            mock_content.return_value = {}

            result = logic.get_file_content(repo_id, [])
            assert isinstance(result, dict)
            assert len(result) == 0

    def test_mcp_tools_list_includes_multi_file(self, logic):
        """Test that tools list includes the new multi-file tool."""
        tools = logic.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "get_file_content" in tool_names
        assert "get_multiple_file_contents" in tool_names

    def test_path_mapping_consistency(self, logic):
        """Test that original paths are preserved in results."""
        repo_id = logic.open_repository(".")

        # Mock the path validation to return different relative paths
        with patch.object(logic, "_check_within_repo") as mock_check:

            def mock_path_check(repo, path):
                from pathlib import Path

                # Simulate path validation returning absolute paths
                return Path(repo.repo_path) / path

            mock_check.side_effect = mock_path_check

            with patch("kit.repository.Repository.get_file_content") as mock_content:
                mock_content.return_value = {"nested/file1.py": "content1", "nested/file2.py": "content2"}

                # Request with original paths
                result = logic.get_multiple_file_contents(repo_id, ["nested/file1.py", "nested/file2.py"])

                # Should get back results keyed by original paths
                assert "nested/file1.py" in result
                assert "nested/file2.py" in result
                assert result["nested/file1.py"] == "content1"
                assert result["nested/file2.py"] == "content2"


def test_open_repository(logic):
    repo_id = logic.open_repository(".")
    uuid.UUID(repo_id)
    assert repo_id in logic._repos


def test_get_file_tree(logic):
    repo_id = logic.open_repository(".")
    tree = logic.get_file_tree(repo_id)
    assert isinstance(tree, list)
    assert len(tree) > 0
    first_item = tree[0]
    assert isinstance(first_item, dict)
    assert "path" in first_item
    assert "name" in first_item
    assert "is_dir" in first_item


def test_extract_symbols(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.extract_symbols") as mock_extract:
        mock_extract.return_value = [{"name": "test_func", "type": "function"}]
        symbols = logic.extract_symbols(repo_id, "test_file.py")
        assert isinstance(symbols, list)
        assert len(symbols) == 1
        assert symbols[0]["name"] == "test_func"
        assert symbols[0]["type"] == "function"


def test_find_symbol_usages(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.find_symbol_usages") as mock_find:
        mock_find.return_value = [{"file": "test.py", "line": 1}]
        usages = logic.find_symbol_usages(repo_id, "test_symbol")
        assert isinstance(usages, list)
        assert len(usages) == 1
        assert usages[0]["file"] == "test.py"
        assert usages[0]["line"] == 1


def test_search_code(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.search_text") as mock_search:
        mock_search.return_value = [{"file": "test.py", "line": 1}]
        results = logic.search_code(repo_id, "test_query")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["file"] == "test.py"
        assert results[0]["line"] == 1


def test_get_file_content(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.get_file_content") as mock_content:
        mock_content.return_value = "test content"
        content = logic.get_file_content(repo_id, "test_file.py")
        assert isinstance(content, str)
        assert content == "test content"


def test_get_code_summary_mocked(logic):
    """Test get_code_summary with mocked Summarizer."""
    # First create a real repo
    repo_id = logic.open_repository(".")

    with patch("kit.mcp.server.Summarizer") as mock_summarizer:
        # Setup mock instance
        instance = mock_summarizer.return_value
        instance.summarize_file.return_value = "File summary"
        instance.summarize_function.return_value = "Function summary"
        instance.summarize_class.return_value = "Class summary"

        # Test with just file path
        result = logic.get_code_summary(repo_id, "test.py")
        assert result == {"file": "File summary"}

        # Test with file path and symbol name
        result = logic.get_code_summary(repo_id, "test.py", "test_symbol")
        assert result == {"file": "File summary", "function": "Function summary", "class": "Class summary"}

        # Verify mock calls
        instance.summarize_file.assert_called_with("test.py")
        instance.summarize_function.assert_called_with("test.py", "test_symbol")
        instance.summarize_class.assert_called_with("test.py", "test_symbol")


def test_get_prompt_open_repo(logic):
    result = logic.get_prompt("open_repo", {"path_or_url": "."})
    assert "Repository opened with ID" in result.description


def test_invalid_prompt_name(logic):
    with pytest.raises(MCPError):
        logic.get_prompt("unknown_prompt", {"foo": "bar"})


def test_list_tools(logic):
    tools = logic.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    first_tool = tools[0]
    assert hasattr(first_tool, "name")
    assert hasattr(first_tool, "description")
    assert hasattr(first_tool, "inputSchema")


def test_list_prompts(logic):
    prompts = logic.list_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) > 0
    first_prompt = prompts[0]
    assert hasattr(first_prompt, "name")
    assert hasattr(first_prompt, "description")
    assert hasattr(first_prompt, "arguments")


def test_get_prompt_with_missing_args(logic):
    with pytest.raises(MCPError) as exc_info:
        logic.get_prompt("open_repo", None)
    assert "Arguments are required" in str(exc_info.value)


def test_get_prompt_with_invalid_args(logic):
    with pytest.raises(MCPError) as exc_info:
        logic.get_prompt("open_repo", {"invalid_arg": "value"})
    assert "Missing required argument" in str(exc_info.value)


def test_repository_not_found(logic):
    with pytest.raises(MCPError) as exc_info:
        logic.get_file_tree("nonexistent_repo")
    assert "Repository nonexistent_repo not found" in str(exc_info.value)


def test_open_repository_invalid_path(logic):
    with patch("kit.mcp.server.Repository") as MockRepo:
        MockRepo.side_effect = FileNotFoundError("Repository path not found")
        with pytest.raises(MCPError) as exc_info:
            logic.open_repository("/nonexistent/path")
        assert "Repository path not found" in str(exc_info.value)


def test_get_file_content_nonexistent_file(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.get_file_content") as mock_content:
        mock_content.side_effect = FileNotFoundError("File not found")
        with pytest.raises(MCPError) as exc_info:
            logic.get_file_content(repo_id, "nonexistent_file.py")
        assert "File not found" in str(exc_info.value)


def test_extract_symbols_invalid_file(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.extract_symbols") as mock_extract:
        mock_extract.side_effect = FileNotFoundError("File not found")
        with pytest.raises(MCPError) as exc_info:
            logic.extract_symbols(repo_id, "nonexistent_file.py")
        assert "File not found" in str(exc_info.value)


def test_find_symbol_usages_invalid_symbol(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.find_symbol_usages") as mock_find:
        mock_find.return_value = []
        usages = logic.find_symbol_usages(repo_id, "NonexistentSymbol123")
        assert isinstance(usages, list)
        assert len(usages) == 0


def test_search_code_invalid_pattern(logic):
    repo_id = logic.open_repository(".")
    with patch("kit.repository.Repository.search_text") as mock_search:
        mock_search.side_effect = Exception("Invalid pattern")
        with pytest.raises(MCPError) as exc_info:
            logic.search_code(repo_id, "query", pattern="invalid[pattern")
        assert "Invalid search pattern" in str(exc_info.value)


def test_get_code_summary_invalid_type(logic):
    """Test get_code_summary when symbol is not found."""
    repo_id = logic.open_repository(".")
    with patch("kit.mcp.server.Summarizer") as mock_summarizer:
        instance = mock_summarizer.return_value
        instance.summarize_file.return_value = "File summary"
        instance.summarize_function.side_effect = ValueError("Symbol not found")
        instance.summarize_class.side_effect = ValueError("Symbol not found")

        # Test that we get None for function and class summaries when symbol not found
        result = logic.get_code_summary(repo_id, "test.py", "nonexistent_symbol")
        assert result == {"file": "File summary", "function": None, "class": None}


def test_find_symbol_usages_invalid_repo_id(logic):
    with pytest.raises(MCPError) as exc_info:
        logic.find_symbol_usages("invalid_repo_id", "some_symbol")
    assert "Repository invalid_repo_id not found" in str(exc_info.value)


def test_get_code_summary_invalid_repo_id(logic):
    """Test get_code_summary with invalid repository ID."""
    with pytest.raises(MCPError) as exc_info:
        logic.get_code_summary("invalid_repo", "test.py")
    assert exc_info.value.code == INVALID_PARAMS
    assert "Repository invalid_repo not found" in str(exc_info.value)


def test_get_code_summary_error(logic):
    """Test get_code_summary error handling."""
    repo_id = logic.open_repository(".")
    with patch("kit.mcp.server.Summarizer") as mock_summarizer:
        instance = mock_summarizer.return_value

        # Test FileNotFoundError
        instance.summarize_file.side_effect = FileNotFoundError("File not found")
        with pytest.raises(MCPError) as exc_info:
            logic.get_code_summary(repo_id, "test.py")
        assert exc_info.value.code == INVALID_PARAMS
        assert "File not found" in str(exc_info.value)

        # Reset mock
        instance.summarize_file.side_effect = None
        instance.summarize_file.return_value = "File summary"

        # Test LLMError
        instance.summarize_file.side_effect = LLMError("LLM API error")
        with pytest.raises(MCPError) as exc_info:
            logic.get_code_summary(repo_id, "test.py")
        assert exc_info.value.code == INVALID_PARAMS
        assert "LLM API error" in str(exc_info.value)

        # Reset mock
        instance.summarize_file.side_effect = None
        instance.summarize_file.return_value = "File summary"

        # Test partial failure (function summary fails with ValueError)
        instance.summarize_function.side_effect = ValueError("Not a function")
        instance.summarize_class.return_value = "Class summary"

        result = logic.get_code_summary(repo_id, "test.py", "test_symbol")
        assert result == {
            "file": "File summary",
            "function": None,  # None because ValueError was caught
            "class": "Class summary",
        }

        # Reset mock
        instance.summarize_function.side_effect = None
        instance.summarize_function.return_value = "Function summary"

        # Test both function and class summaries fail with ValueError
        instance.summarize_function.side_effect = ValueError("Not a function")
        instance.summarize_class.side_effect = ValueError("Not a class")

        result = logic.get_code_summary(repo_id, "test.py", "test_symbol")
        assert result == {
            "file": "File summary",
            "function": None,  # None because ValueError was caught
            "class": None,  # None because ValueError was caught
        }


def test_get_file_content_path_traversal(logic):
    """Attempting to read ../ should raise INVALID_PARAMS."""
    repo_id = logic.open_repository(".")
    with pytest.raises(MCPError) as exc:
        logic.get_file_content(repo_id, "../pyproject.toml")
    assert exc.value.code == INVALID_PARAMS
    assert "Path traversal" in exc.value.message


def test_extract_symbols_path_traversal(logic):
    """Path outside repo for extract_symbols should be rejected."""
    repo_id = logic.open_repository(".")
    with pytest.raises(MCPError):
        logic.extract_symbols(repo_id, "../../secrets.txt")


def test_mcp_tool_output_get_file_tree(logic: KitServerLogic):
    """
    Tests that the MCP-like processing for the 'get_file_tree' tool
    correctly formats its output as a JSON string within TextContent.
    This simulates the behavior of the relevant part of the call_tool handler.
    """
    repo_id = logic.open_repository(".")
    assert repo_id is not None

    tool_arguments = {"repo_id": repo_id}
    parsed_args = GetFileTreeParams(**tool_arguments)

    raw_tree_data = logic.get_file_tree(parsed_args.repo_id)
    assert isinstance(raw_tree_data, list), "logic.get_file_tree should return a list"
    assert len(raw_tree_data) > 0, "File tree should not be empty for the current directory"

    mcp_formatted_result_list = [TextContent(type="text", text=json.dumps(raw_tree_data, indent=2))]

    assert isinstance(mcp_formatted_result_list, list)
    assert len(mcp_formatted_result_list) == 1

    result_content_object = mcp_formatted_result_list[0]
    assert isinstance(result_content_object, TextContent)
    assert result_content_object.type == "text"

    try:
        parsed_json_payload = json.loads(result_content_object.text)
    except json.JSONDecodeError:
        pytest.fail(f"The result TextContent.text is not valid JSON. Content: {result_content_object.text[:200]}...")

    assert isinstance(parsed_json_payload, list), "Parsed JSON payload should be a list"
    assert parsed_json_payload == raw_tree_data, "Parsed JSON data does not match raw tree data"

    first_item_in_json_tree = parsed_json_payload[0]
    assert isinstance(first_item_in_json_tree, dict)
    assert "path" in first_item_in_json_tree
    assert "name" in first_item_in_json_tree
    assert "is_dir" in first_item_in_json_tree
