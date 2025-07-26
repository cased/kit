"""Integration tests for CLI local review command."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository with sample content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # Handle case where current directory doesn't exist (e.g., in CI)
            original_cwd = tmpdir

        try:
            os.chdir(repo_path)

            # Initialize git repo
            os.system("git init --quiet")
            os.system('git config user.name "Test User"')
            os.system('git config user.email "test@example.com"')

            # Create initial commit
            (repo_path / "README.md").write_text("# Test Project\n")
            (repo_path / "main.py").write_text("def main():\n    print('Hello')\n")
            os.system("git add .")
            os.system('git commit -m "Initial commit" --quiet')

            # Create a feature branch with changes
            os.system("git checkout -b feature --quiet")
            (repo_path / "feature.py").write_text("def feature():\n    return 'New feature'\n")
            (repo_path / "main.py").write_text("def main():\n    print('Hello, World!')\n")
            os.system("git add .")
            os.system('git commit -m "Add feature" --quiet')

            # Switch back to main
            os.system("git checkout main --quiet")

            yield repo_path
        finally:
            try:
                os.chdir(original_cwd)
            except FileNotFoundError:
                # If original_cwd doesn't exist, just stay in tmpdir
                pass


class TestCLILocalReview:
    """Test CLI local review command."""

    def test_review_help(self, runner):
        """Test review command help text."""
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "GitHub PR URL or local diff" in result.output
        assert "main..feature" in result.output
        # More robust check for staged option
        assert "staged" in result.output.lower() and "review staged changes" in result.output.lower()

    def test_review_missing_target(self, runner):
        """Test review with missing target."""
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 1
        assert "Target is required" in result.output
        assert "GitHub PR:" in result.output
        assert "Local diff:" in result.output

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_review_local_diff(self, mock_reviewer_class, runner, temp_git_repo):
        """Test reviewing local diff between branches."""
        # Mock the reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## Review\nLooks good!"
        mock_reviewer_class.return_value = mock_reviewer

        # Mock config loading
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock(
                post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None, repo_path=None
            )
            # Add llm attribute with model for model validation
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            # Run review
            os.chdir(temp_git_repo)
            result = runner.invoke(app, ["review", "main..feature", "--dry-run"])

            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
                if result.exc_info:
                    import traceback

                    traceback.print_exception(*result.exc_info)
            assert result.exit_code == 0
            assert "REVIEW COMMENT THAT WOULD BE POSTED:" in result.output
            assert "Looks good!" in result.output
            mock_reviewer.review.assert_called_once_with("main..feature")

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_review_staged_changes(self, mock_reviewer_class, runner, temp_git_repo):
        """Test reviewing staged changes."""
        # Mock the reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## Review\nStaged changes look good!"
        mock_reviewer_class.return_value = mock_reviewer

        # Mock config loading
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock(
                post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None, repo_path=None
            )
            # Add llm attribute with model for CostTracker
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            config_obj.llm_model = "gpt-3.5-turbo"  # Ensure the model is valid
            mock_config.return_value = config_obj

            # Stage a change
            os.chdir(temp_git_repo)
            (temp_git_repo / "new_file.py").write_text("print('New file')\n")
            os.system("git add new_file.py")

            # Run review
            result = runner.invoke(app, ["review", "--staged", "--dry-run"])

            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
                if result.exc_info:
                    import traceback

                    traceback.print_exception(*result.exc_info)
            assert result.exit_code == 0
            assert "Staged changes look good!" in result.output
            mock_reviewer.review.assert_called_once_with("--staged")

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_review_commit_range(self, mock_reviewer_class, runner, temp_git_repo):
        """Test reviewing commit range."""
        # Mock the reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## Review\nCommit looks good!"
        mock_reviewer_class.return_value = mock_reviewer

        # Mock config loading
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock(
                post_as_comment=False,
                quiet=True,  # Test plain mode
                llm_model="gpt-3.5-turbo",
                priority_filter=None,
            )
            # Add llm attribute with model for model validation
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            # Run review
            os.chdir(temp_git_repo)
            result = runner.invoke(app, ["review", "HEAD~1..HEAD", "--plain"])

            assert result.exit_code == 0
            # In plain mode, only the review content is shown
            assert "## Review\nCommit looks good!" in result.output
            assert "REVIEW COMMENT" not in result.output

    def test_review_github_pr(self, runner):
        """Test that GitHub PR URLs still work."""
        with patch("kit.pr_review.reviewer.PRReviewer") as mock_pr_reviewer_class:
            mock_reviewer = MagicMock()
            mock_reviewer.review_pr.return_value = "PR review content"
            mock_pr_reviewer_class.return_value = mock_reviewer

            with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
                config_obj = MagicMock(
                    post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None
                )
                config_obj.llm = MagicMock(model="gpt-3.5-turbo")
                mock_config.return_value = config_obj

                result = runner.invoke(app, ["review", "https://github.com/owner/repo/pull/123", "--dry-run"])

                # Should use PRReviewer, not LocalDiffReviewer
                assert mock_pr_reviewer_class.called
                assert "PR review content" in result.output

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_review_with_repo_path(self, mock_reviewer_class, runner, temp_git_repo):
        """Test review with custom repo path."""
        # Mock the reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## Review\nCustom repo!"
        mock_reviewer_class.return_value = mock_reviewer

        # Mock config loading
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock(
                post_as_comment=False,
                quiet=False,
                llm_model="gpt-3.5-turbo",
                priority_filter=None,
                repo_path=str(temp_git_repo),
            )
            # Add llm attribute with model for model validation
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            # Run review from different directory
            result = runner.invoke(app, ["review", "HEAD~1..HEAD", "--dry-run", "--repo-path", str(temp_git_repo)])

            assert result.exit_code == 0
            assert "Using existing repository:" in result.output
            assert str(temp_git_repo) in result.output

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_review_with_priority_filter(self, mock_reviewer_class, runner, temp_git_repo):
        """Test review with priority filtering."""
        # Mock the reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "## HIGH Priority\nCritical issue"
        mock_reviewer_class.return_value = mock_reviewer

        # Mock config loading
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config = MagicMock(post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None)
            config.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config

            # Run review
            os.chdir(temp_git_repo)
            result = runner.invoke(app, ["review", "HEAD~1..HEAD", "--dry-run", "--priority=high"])

            assert result.exit_code == 0
            assert config.priority_filter == ["high"]
            assert "Priority filter: high" in result.output

    def test_review_error_handling(self, runner, temp_git_repo):
        """Test error handling in review command."""
        with patch("kit.pr_review.local_reviewer.LocalDiffReviewer") as mock_reviewer_class:
            mock_reviewer = MagicMock()
            mock_reviewer.review.side_effect = RuntimeError("Test error")
            mock_reviewer_class.return_value = mock_reviewer

            with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
                config_obj = MagicMock(
                    post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None
                )
                config_obj.llm = MagicMock(model="gpt-3.5-turbo")
                mock_config.return_value = config_obj

                os.chdir(temp_git_repo)
                result = runner.invoke(app, ["review", "HEAD~1..HEAD"])

                assert result.exit_code == 1
                assert "Review failed: Test error" in result.output

    def test_review_agentic_mode_not_supported(self, runner, temp_git_repo):
        """Test that agentic mode is not supported for local diffs."""
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock(
                post_as_comment=False, quiet=False, llm_model="gpt-3.5-turbo", priority_filter=None, repo_path=None
            )
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            os.chdir(temp_git_repo)
            result = runner.invoke(app, ["review", "HEAD~1..HEAD", "--agentic"])

            assert result.exit_code == 1
            assert "Agentic mode is not yet supported for local diffs" in result.output
