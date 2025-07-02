"""Tests for local diff review functionality."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app
from kit.pr_review.agentic_reviewer import AgenticPRReviewer
from kit.pr_review.config import (
    GitHubConfig,
    LLMConfig,
    LLMProvider,
    ReviewConfig,
)
from kit.pr_review.reviewer import PRReviewer


class TestLocalDiffCLI:
    """Test CLI integration for local diff functionality."""

    def test_local_diff_argument_parsing(self):
        """Test that --local-diff argument is parsed correctly."""
        runner = CliRunner()

        # Test with init-config to avoid actual review
        result = runner.invoke(app, ["review", "--local-diff", "main..feature", "--init-config"])

        # Should succeed (creates config and exits)
        assert result.exit_code == 0
        assert "Created default config file" in result.output

    def test_local_diff_requires_git_repo(self):
        """Test that local diff requires a git repository."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal config for testing
            config_file = Path(tmpdir) / "config.yaml"
            config_content = """
github:
  token: test_token

llm:
  provider: anthropic
  model: claude-3-5-haiku-20241022
  api_key: test_key
"""
            config_file.write_text(config_content)

            # Mock environment variables
            with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
                # Run in a non-git directory
                result = runner.invoke(
                    app,
                    ["review", "--local-diff", "main..feature", "--config", str(config_file), "--repo-path", tmpdir],
                )

                assert result.exit_code == 1
                assert "Not a git repository" in result.output

    def test_local_diff_mutual_exclusion_with_pr_url(self):
        """Test that --local-diff and PR URL are mutually exclusive."""
        runner = CliRunner()

        result = runner.invoke(
            app, ["review", "https://github.com/owner/repo/pull/123", "--local-diff", "main..feature"]
        )

        assert result.exit_code == 1
        assert "Cannot specify both PR URL and --local-diff" in result.output

    def test_local_diff_requires_either_pr_or_local(self):
        """Test that either PR URL or --local-diff is required."""
        runner = CliRunner()

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 1
        assert "Either PR URL or --local-diff is required" in result.output

    def test_local_diff_help_examples(self):
        """Test that help examples are shown correctly."""
        runner = CliRunner()

        result = runner.invoke(app, ["review"])

        assert "kit review --local-diff main..feature-branch" in result.output
        assert "kit review --local-diff HEAD~1..HEAD" in result.output


class TestLocalDiffReviewer:
    """Test PRReviewer local diff functionality."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-haiku-20241022",
                api_key="test",
            ),
        )
        self.config.post_as_comment = False  # Never post in tests
        self.reviewer = PRReviewer(self.config)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_basic(self, mock_exists, mock_subprocess):
        """Test basic local diff review functionality."""
        # Mock git directory exists
        mock_exists.return_value = True

        # Mock git diff command
        diff_output = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    print("world")
     return "hello"
"""

        # Mock subprocess calls
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:  # git diff main..feature
                return Mock(stdout=diff_output, returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:  # git diff --name-only
                return Mock(stdout="test.py\n", returncode=0)
            elif cmd[1] == "diff" and "--numstat" in cmd:  # git diff --numstat
                return Mock(stdout="1\t0\ttest.py\n", returncode=0)
            elif cmd[1] == "log":  # git log --oneline
                return Mock(stdout="abc1234 Add hello function\n", returncode=0)
            elif cmd[1] == "rev-parse":  # git rev-parse --abbrev-ref HEAD
                return Mock(stdout="feature\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        # Mock Repository and LLM analysis
        with patch("kit.pr_review.reviewer.Repository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.extract_symbols.return_value = []
            mock_repo.find_symbol_usages.return_value = []
            mock_repo.get_dependency_analyzer.side_effect = Exception("No dependency analyzer")
            mock_repo.get_file_tree.return_value = []

            # Mock LLM analysis
            with patch.object(self.reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
                mock_analyze.return_value = "Test analysis result"

                result = self.reviewer.review_local_diff("main..feature", "/fake/repo")

                # Should return a review comment
                assert "Test analysis result" in result
                assert "Local Changes" in result
                assert "main..feature" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_no_changes(self, mock_exists, mock_subprocess):
        """Test local diff review with no changes."""
        mock_exists.return_value = True

        # Mock empty diff
        mock_subprocess.return_value = Mock(stdout="", returncode=0)

        result = self.reviewer.review_local_diff("main..feature", "/fake/repo")

        assert "No changes found" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_git_error(self, mock_exists, mock_subprocess):
        """Test local diff review with git error."""
        mock_exists.return_value = True

        # Mock git diff failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git diff", stderr="fatal: bad revision")

        with pytest.raises(RuntimeError, match="Failed to get git diff"):
            self.reviewer.review_local_diff("invalid..ref", "/fake/repo")

    def test_review_local_diff_not_git_repo(self):
        """Test local diff review in non-git directory."""
        with pytest.raises(RuntimeError, match="Not a git repository"):
            self.reviewer.review_local_diff("main..feature", "/fake/repo")

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_quiet_mode(self, mock_exists, mock_subprocess):
        """Test local diff review in quiet mode."""
        mock_exists.return_value = True
        self.config.quiet = True

        # Mock git commands
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout="diff content", returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        with (
            patch("kit.pr_review.reviewer.Repository"),
            patch.object(self.reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze,
        ):
            mock_analyze.return_value = "Analysis"

            # Should not raise any exceptions in quiet mode
            result = self.reviewer.review_local_diff("main..feature", "/fake/repo")
            assert "Analysis" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_with_priority_filter(self, mock_exists, mock_subprocess):
        """Test local diff review with priority filtering."""
        mock_exists.return_value = True
        self.config.priority_filter = ["high"]

        # Mock git commands
        mock_subprocess.return_value = Mock(stdout="diff content", returncode=0)

        with (
            patch("kit.pr_review.reviewer.Repository"),
            patch.object(self.reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze,
            patch("kit.pr_review.reviewer.filter_review_by_priority") as mock_filter,
        ):
            mock_analyze.return_value = "Full analysis"
            mock_filter.return_value = "Filtered analysis"

            result = self.reviewer.review_local_diff("main..feature", "/fake/repo")

            # Should call priority filter
            mock_filter.assert_called_once()
            assert "Filtered analysis" in result


class TestLocalDiffAgenticReviewer:
    """Test AgenticPRReviewer local diff functionality."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-haiku-20241022",
                api_key="test",
            ),
        )
        self.config.post_as_comment = False
        self.config.agentic_max_turns = 3  # Shorter for tests
        self.reviewer = AgenticPRReviewer(self.config)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_agentic_basic(self, mock_exists, mock_subprocess):
        """Test basic agentic local diff review."""
        mock_exists.return_value = True

        # Mock git commands
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout="diff content", returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        with (
            patch("kit.pr_review.agentic_reviewer.Repository"),
            patch.object(self.reviewer, "_call_llm_agentic") as mock_llm,
        ):
            mock_llm.return_value = "Agentic analysis result"

            result = self.reviewer.review_local_diff_agentic("main..feature", "/fake/repo")

            assert "Agentic analysis result" in result
            assert "Local Changes (Agentic)" in result
            assert "max turns: 3" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_agentic_multi_turn(self, mock_exists, mock_subprocess):
        """Test agentic local diff with multiple turns."""
        mock_exists.return_value = True

        mock_subprocess.return_value = Mock(stdout="diff content", returncode=0)

        with (
            patch("kit.pr_review.agentic_reviewer.Repository"),
            patch.object(self.reviewer, "_call_llm_agentic") as mock_llm,
        ):
            # Mock multiple LLM responses
            mock_llm.side_effect = ["Initial analysis", "Second turn analysis", "Final synthesis"]

            result = self.reviewer.review_local_diff_agentic("main..feature", "/fake/repo")

            # Should call LLM multiple times
            assert mock_llm.call_count >= 3
            assert "Final synthesis" in result


class TestLocalDiffIntegration:
    """Test integration scenarios for local diff functionality."""

    def test_cli_local_diff_with_model_override(self):
        """Test CLI local diff with model override."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            result = runner.invoke(
                app,
                ["review", "--local-diff", "main..feature", "--model", "claude-3-5-haiku-20241022", "--init-config"],
            )

            assert result.exit_code == 0
            assert "Created default config file" in result.output

    def test_cli_local_diff_with_priority_filter(self):
        """Test CLI local diff with priority filtering."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            result = runner.invoke(
                app, ["review", "--local-diff", "main..feature", "--priority", "high,medium", "--init-config"]
            )

            assert result.exit_code == 0

    def test_cli_local_diff_agentic_mode(self):
        """Test CLI local diff with agentic mode."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            result = runner.invoke(
                app, ["review", "--local-diff", "main..feature", "--agentic", "--agentic-turns", "5", "--init-config"]
            )

            assert result.exit_code == 0

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_local_diff_plain_output_default(self, mock_exists, mock_subprocess):
        """Test that local diff defaults to plain output."""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(stdout="diff content", returncode=0)

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with (
            patch("kit.pr_review.reviewer.Repository"),
            patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze,
        ):
            mock_analyze.return_value = "Analysis"

            result = reviewer.review_local_diff("main..feature", "/fake/repo")

            # Should include plain analysis without extra formatting
            assert "Analysis" in result
            assert "Local Changes" in result

    def test_local_diff_various_git_specs(self):
        """Test local diff with various git diff specifications."""
        specs = ["main..feature-branch", "HEAD~1..HEAD", "HEAD~3..HEAD", "v1.0..v2.0", "origin/main..HEAD"]

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        for spec in specs:
            with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):
                mock_subprocess.return_value = Mock(stdout="", returncode=0)

                result = reviewer.review_local_diff(spec, "/fake/repo")
                assert "No changes found" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_local_diff_error_handling(self, mock_exists, mock_subprocess):
        """Test error handling in local diff analysis."""
        mock_exists.return_value = True

        # Mock git diff success but analysis failure
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout="diff content", returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("kit.pr_review.reviewer.Repository") as mock_repo_class:
            # Mock Repository constructor to raise exception
            mock_repo_class.side_effect = Exception("Analysis failed")

            result = reviewer.review_local_diff("main..feature", "/fake/repo")

            # Should handle error gracefully and provide fallback
            assert "Analysis failed" in result
            assert "Reviewing based on git diff only" in result


class TestLocalDiffEdgeCases:
    """Test edge cases for local diff functionality."""

    def test_empty_diff_spec(self):
        """Test local diff with empty diff specification."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):
            mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git diff", stderr="bad revision")

            with pytest.raises(RuntimeError):
                reviewer.review_local_diff("", "/fake/repo")

    def test_single_commit_diff(self):
        """Test local diff for a single commit."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):
            # Mock single commit diff (HEAD~1..HEAD equivalent)
            def mock_run_side_effect(*args, **kwargs):
                cmd = args[0] if args else kwargs.get("args", [])
                if cmd[1] == "diff":
                    return Mock(stdout="diff content", returncode=0)
                elif cmd[1] == "log":
                    return Mock(stdout="abc1234 Single commit message\n", returncode=0)
                else:
                    return Mock(stdout="main\n", returncode=0)

            mock_subprocess.side_effect = mock_run_side_effect

            with (
                patch("kit.pr_review.reviewer.Repository"),
                patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze,
            ):
                mock_analyze.return_value = "Single commit analysis"

                result = reviewer.review_local_diff("HEAD", "/fake/repo")
                assert "Single commit analysis" in result

    def test_large_diff_handling(self):
        """Test handling of large diffs."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        # Create a large diff
        large_diff = "diff --git a/test.py b/test.py\n" + "+" + "x" * 10000

        with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):

            def mock_run_side_effect(*args, **kwargs):
                cmd = args[0] if args else kwargs.get("args", [])
                if cmd[1] == "diff" and len(cmd) == 3:
                    return Mock(stdout=large_diff, returncode=0)
                elif cmd[1] == "diff" and "--name-only" in cmd:
                    return Mock(stdout="test.py\n", returncode=0)
                else:
                    return Mock(stdout="", returncode=0)

            mock_subprocess.side_effect = mock_run_side_effect

            with (
                patch("kit.pr_review.reviewer.Repository"),
                patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze,
            ):
                mock_analyze.return_value = "Large diff analysis"

                result = reviewer.review_local_diff("main..feature", "/fake/repo")
                assert "Large diff analysis" in result
