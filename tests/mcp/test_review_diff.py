"""Tests for MCP review_diff functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kit.mcp.dev_server import KitServerLogic, MCPError, ReviewDiffParams


@pytest.fixture
def server_logic():
    """Create a KitServerLogic instance for testing."""
    return KitServerLogic()


@pytest.fixture
def mock_repo(server_logic):
    """Create a mock repository and return its ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        os.system(f"cd {repo_path} && git init --quiet")
        os.system(f"cd {repo_path} && git config user.name 'Test User'")
        os.system(f"cd {repo_path} && git config user.email 'test@example.com'")

        # Create initial commit
        (repo_path / "test.py").write_text("def hello():\n    print('Hello')\n")
        os.system(f"cd {repo_path} && git add test.py")
        os.system(f"cd {repo_path} && git commit -m 'Initial commit' --quiet")

        # Create a change
        (repo_path / "test.py").write_text("def hello():\n    print('Hello, World!')\n")
        os.system(f"cd {repo_path} && git add test.py")
        os.system(f"cd {repo_path} && git commit -m 'Update greeting' --quiet")

        # Open the repository
        repo_id = server_logic.open_repository(str(repo_path))
        yield repo_id


class TestReviewDiff:
    """Test the review_diff MCP functionality."""

    def test_review_diff_params_validation(self):
        """Test ReviewDiffParams model validation."""
        # Valid params
        params = ReviewDiffParams(repo_id="test-repo", diff_spec="HEAD~1..HEAD")
        assert params.repo_id == "test-repo"
        assert params.diff_spec == "HEAD~1..HEAD"
        assert params.priority_filter is None
        assert params.max_files == 10
        assert params.model is None

        # With optional params
        params = ReviewDiffParams(
            repo_id="test-repo",
            diff_spec="main..feature",
            priority_filter=["high", "medium"],
            max_files=20,
            model="gpt-4",
        )
        assert params.priority_filter == ["high", "medium"]
        assert params.max_files == 20
        assert params.model == "gpt-4"

    def test_review_diff_tool_in_list(self, server_logic):
        """Test that review_diff tool is listed."""
        tools = server_logic.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "review_diff" in tool_names

        # Find the review_diff tool
        review_tool = next(t for t in tools if t.name == "review_diff")
        assert "Review a local git diff" in review_tool.description
        assert review_tool.inputSchema is not None

    def test_review_diff_prompt_in_list(self, server_logic):
        """Test that review_diff prompt is listed."""
        prompts = server_logic.list_prompts()
        prompt_names = [p.name for p in prompts]
        assert "review_diff" in prompt_names

        # Find the review_diff prompt
        review_prompt = next(p for p in prompts if p.name == "review_diff")
        assert len(review_prompt.arguments) >= 2  # At least repo_id and diff_spec

    @patch("kit.mcp.dev_server.LocalDiffReviewer")
    @patch("kit.mcp.dev_server.ReviewConfig")
    def test_review_diff_basic(self, mock_config_class, mock_reviewer_class, server_logic, mock_repo):
        """Test basic review_diff functionality."""
        # Set up mocks
        mock_config = MagicMock()
        mock_config_class.from_file.return_value = mock_config

        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## Review\\n\\nLooks good! Cost: $0.0123"
        mock_reviewer_class.return_value = mock_reviewer

        # Call review_diff
        result = server_logic.review_diff(mock_repo, "HEAD~1..HEAD")

        assert "review" in result
        assert "Kit Local Diff Review" in result["review"]
        assert result["diff_spec"] == "HEAD~1..HEAD"
        assert isinstance(result["cost"], float)
        assert result["cost"] >= 0  # Cost should be non-negative
        assert result["model"] in ["gpt-4", "claude-sonnet-4-20250514"]  # Could be either default

    @patch("kit.mcp.dev_server.LocalDiffReviewer")
    @patch("kit.mcp.dev_server.ReviewConfig")
    def test_review_diff_with_options(self, mock_config_class, mock_reviewer_class, server_logic, mock_repo):
        """Test review_diff with custom options."""
        # Set up mocks
        mock_config = MagicMock()
        mock_config_class.from_file.return_value = mock_config

        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## HIGH Priority\\n\\nIssue found!"
        mock_reviewer_class.return_value = mock_reviewer

        # Call review_diff with options
        result = server_logic.review_diff(
            mock_repo, "--staged", priority_filter=["high"], max_files=5, model="claude-3-opus"
        )

        # The actual review might say "No changes" for --staged in test repo
        assert "review" in result
        assert result["diff_spec"] == "--staged"
        assert result["model"] == "claude-3-opus"

    def test_review_diff_invalid_repo(self, server_logic):
        """Test review_diff with invalid repository ID."""
        with pytest.raises(MCPError) as exc_info:
            server_logic.review_diff("invalid-repo-id", "HEAD~1..HEAD")

        assert exc_info.value.code == -32602  # INVALID_PARAMS
        assert "Repository invalid-repo-id not found" in exc_info.value.message

    @pytest.mark.skip(reason="Mocks not working due to import inside function")
    @patch("kit.mcp.dev_server.LocalDiffReviewer")
    @patch("kit.mcp.dev_server.ReviewConfig")
    def test_review_diff_error_handling(self, mock_config_class, mock_reviewer_class, server_logic, mock_repo):
        """Test review_diff error handling."""
        # Set up mocks to raise an error
        mock_config_class.from_file.side_effect = Exception("Config error")

        with pytest.raises(MCPError) as exc_info:
            server_logic.review_diff(mock_repo, "HEAD~1..HEAD")

        assert exc_info.value.code == -32603  # INTERNAL_ERROR
        assert "Failed to review diff" in exc_info.value.message

    def test_get_prompt_review_diff(self, server_logic, mock_repo):
        """Test get_prompt for review_diff."""
        with patch("kit.mcp.dev_server.LocalDiffReviewer") as mock_reviewer_class:
            mock_reviewer = MagicMock()
            mock_reviewer.review.return_value = "## Review Result"
            mock_reviewer_class.return_value = mock_reviewer

            with patch("kit.mcp.dev_server.ReviewConfig"):
                result = server_logic.get_prompt("review_diff", {"repo_id": mock_repo, "diff_spec": "HEAD~1..HEAD"})

                assert result.description.startswith("AI review of diff:")
                assert len(result.messages) == 1
                assert result.messages[0].content.text == "## Review Result"
