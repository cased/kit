"""Tests for local diff review functionality."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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

    def test_local_diff_mutual_exclusion(self):
        """Test that PR URL and --local-diff are mutually exclusive."""
        runner = CliRunner()

        result = runner.invoke(
            app, ["review", "https://github.com/owner/repo/pull/123", "--local-diff", "main..feature"]
        )

        assert result.exit_code == 1
        assert "Cannot specify both PR URL and --local-diff" in result.output

    def test_local_diff_required_input(self):
        """Test that either PR URL or --local-diff is required."""
        runner = CliRunner()

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 1
        assert "Either PR URL or --local-diff is required" in result.output

    def test_local_diff_with_config_file(self):
        """Test local diff with custom config file."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as config_file:
            config_file.write("""
github:
  token: test_token
llm:
  provider: anthropic
  model: claude-3-5-haiku-20241022
  api_key: test_key
""")
            config_file.flush()

            try:
                # Mock subprocess to avoid actual git commands
                with patch("subprocess.run") as mock_subprocess:
                    mock_subprocess.return_value = Mock(stdout="", returncode=0)

                    # Mock the entire review process
                    with patch("kit.pr_review.reviewer.PRReviewer.review_local_diff") as mock_review:
                        mock_review.return_value = "Mock review result"

                        with patch("pathlib.Path.exists", return_value=True):
                            tmpdir = Path("/tmp/test_repo")

                            result = runner.invoke(
                                app,
                                ["review", "--local-diff", "main..feature", "--config", str(config_file.name), "--repo-path", str(tmpdir)],
                            )

                            assert result.exit_code == 0
            finally:
                os.unlink(config_file.name)


class TestLocalDiffReviewer:
    """Test PRReviewer local diff functionality."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-3-5-haiku-20241022", api_key="test"),
        )
        # Ensure analysis is enabled
        self.config.clone_for_analysis = True
        self.reviewer = PRReviewer(self.config)

    def _mock_repository(self):
        """Create a properly mocked Repository instance."""
        mock_repo = MagicMock()
        mock_repo.extract_symbols.return_value = []
        mock_repo.find_symbol_usages.return_value = []
        mock_repo.get_dependency_analyzer.side_effect = Exception("No dependency analyzer")
        mock_repo.get_file_tree.return_value = []
        return mock_repo

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_basic(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test basic local diff review functionality."""
        # Mock git directory exists
        mock_exists.return_value = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

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
    def test_review_local_diff_not_git_repo(self, mock_exists, mock_subprocess):
        """Test local diff review in non-git repository."""
        mock_exists.return_value = False

        with pytest.raises(RuntimeError, match="Not a git repository"):
            self.reviewer.review_local_diff("main..feature", "/fake/repo")

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_quiet_mode(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test local diff review in quiet mode."""
        mock_exists.return_value = True
        self.config.quiet = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

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

        with patch.object(self.reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
            mock_analyze.return_value = "Analysis"

            # Should not raise any exceptions in quiet mode
            result = self.reviewer.review_local_diff("main..feature", "/fake/repo")
            assert "Analysis" in result

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_with_priority_filter(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test local diff review with priority filtering."""
        mock_exists.return_value = True
        self.config.priority_filter = ["high"]

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

        # Mock git commands with more complete responses
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout="diff --git a/test.py b/test.py\n+added line", returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            elif cmd[1] == "diff" and "--numstat" in cmd:
                return Mock(stdout="1\t0\ttest.py\n", returncode=0)
            elif cmd[1] == "log":
                return Mock(stdout="abc1234 Test commit\n", returncode=0)
            elif cmd[1] == "rev-parse":
                return Mock(stdout="feature\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        # Mock the entire analysis method and filter directly
        async def mock_analysis_with_filter(*args, **kwargs):
            # Simulate the analysis calling the filter
            from kit.pr_review.priority_filter import filter_review_by_priority
            analysis = "Full analysis with high priority issues"
            return filter_review_by_priority(analysis, ["high"], self.config.max_review_size_mb)

        with patch.object(self.reviewer, "analyze_local_diff_with_kit", side_effect=mock_analysis_with_filter):
            result = self.reviewer.review_local_diff("main..feature", "/fake/repo")

            # Should include the analysis
            assert "analysis" in result.lower()


class TestLocalDiffAgenticReviewer:
    """Test AgenticPRReviewer local diff functionality."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-3-5-haiku-20241022", api_key="test"),
        )
        # Ensure analysis is enabled
        self.config.clone_for_analysis = True
        self.reviewer = AgenticPRReviewer(self.config)

    def _mock_repository(self):
        """Create a properly mocked Repository instance."""
        mock_repo = MagicMock()
        mock_repo.extract_symbols.return_value = []
        mock_repo.find_symbol_usages.return_value = []
        mock_repo.get_dependency_analyzer.side_effect = Exception("No dependency analyzer")
        mock_repo.get_file_tree.return_value = []
        return mock_repo

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_agentic_basic(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test basic agentic local diff review."""
        mock_exists.return_value = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

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

        with patch.object(self.reviewer, "_call_llm_agentic") as mock_llm:
            mock_llm.return_value = "Agentic analysis result"

            result = self.reviewer.review_local_diff_agentic("main..feature", "/fake/repo")

            assert "Agentic analysis result" in result
            assert mock_llm.called

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_review_local_diff_agentic_multi_turn(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test agentic local diff with multiple turns."""
        mock_exists.return_value = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

        # Mock git commands with complete responses
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout="diff --git a/test.py b/test.py\n+added line", returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            elif cmd[1] == "diff" and "--numstat" in cmd:
                return Mock(stdout="1\t0\ttest.py\n", returncode=0)
            elif cmd[1] == "log":
                return Mock(stdout="abc1234 Test commit\n", returncode=0)
            elif cmd[1] == "rev-parse":
                return Mock(stdout="feature\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        # Create async mock for LLM calls
        call_count = 0
        async def mock_llm_agentic(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            responses = ["Initial analysis", "Second turn analysis", "Final synthesis"]
            return responses[min(call_count - 1, len(responses) - 1)]

        with patch.object(self.reviewer, "_call_llm_agentic", side_effect=mock_llm_agentic) as mock_llm:
            result = self.reviewer.review_local_diff_agentic("main..feature", "/fake/repo")

            # Should have multiple calls for turns
            assert call_count >= 2
            assert "Final synthesis" in result


class TestLocalDiffIntegration:
    """Test integration scenarios for local diff functionality."""

    def test_local_diff_model_override(self):
        """Test local diff with model override."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = Mock(stdout="", returncode=0)

                with patch("kit.pr_review.reviewer.PRReviewer.review_local_diff") as mock_review:
                    mock_review.return_value = "Mock review result"

                    with patch("pathlib.Path.exists", return_value=True):
                        result = runner.invoke(
                            app,
                            ["review", "--local-diff", "main..feature", "--model", "claude-3-5-haiku-20241022", "--init-config"],
                        )

                        assert result.exit_code == 0

    def _mock_repository(self):
        """Create a properly mocked Repository instance."""
        mock_repo = MagicMock()
        mock_repo.extract_symbols.return_value = []
        mock_repo.find_symbol_usages.return_value = []
        mock_repo.get_dependency_analyzer.side_effect = Exception("No dependency analyzer")
        mock_repo.get_file_tree.return_value = []
        return mock_repo

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_local_diff_plain_output_default(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test that local diff defaults to plain output."""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(stdout="diff content", returncode=0)

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
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

        with patch("kit.Repository") as mock_repo_class:
            # Mock Repository constructor to raise exception
            mock_repo_class.side_effect = Exception("Analysis failed")

            result = reviewer.review_local_diff("main..feature", "/fake/repo")

            # Should handle error gracefully and provide fallback
            assert "Analysis failed" in result
            assert "Reviewing based on git diff only" in result


class TestLocalDiffEdgeCases:
    """Test edge cases for local diff functionality."""

    def _mock_repository(self):
        """Create a properly mocked Repository instance."""
        mock_repo = MagicMock()
        mock_repo.extract_symbols.return_value = []
        mock_repo.find_symbol_usages.return_value = []
        mock_repo.get_dependency_analyzer.side_effect = Exception("No dependency analyzer")
        mock_repo.get_file_tree.return_value = []
        return mock_repo

    def test_empty_diff_spec(self):
        """Test local diff with empty diff specification."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):
            mock_subprocess.return_value = Mock(stdout="", returncode=0)

            result = reviewer.review_local_diff("", "/fake/repo")
            assert "No changes found" in result

    def test_priority_filtering_integration(self):
        """Test priority filtering integration with CLI."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            result = runner.invoke(
                app, ["review", "--local-diff", "main..feature", "--priority", "high,medium", "--init-config"]
            )

            assert result.exit_code == 0

    def test_agentic_mode_integration(self):
        """Test agentic mode integration with CLI."""
        runner = CliRunner()

        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "test", "KIT_ANTHROPIC_TOKEN": "test"}):
            result = runner.invoke(
                app, ["review", "--local-diff", "main..feature", "--agentic", "--agentic-turns", "5", "--init-config"]
            )

            assert result.exit_code == 0

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_single_commit_diff(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test local diff for a single commit."""
        mock_exists.return_value = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

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

        with patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
            mock_analyze.return_value = "Single commit analysis"

            result = reviewer.review_local_diff("HEAD", "/fake/repo")
            assert "Single commit analysis" in result

    @patch("kit.Repository")  # Mock at the kit module level
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")  
    def test_large_diff_handling(self, mock_exists, mock_subprocess, mock_repo_class):
        """Test handling of large diffs."""
        mock_exists.return_value = True

        # Set up Repository mock
        mock_repo = self._mock_repository()
        mock_repo_class.return_value = mock_repo

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        # Create a large diff
        large_diff = "diff --git a/test.py b/test.py\n" + "+" + "x" * 10000

        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd[1] == "diff" and len(cmd) == 3:
                return Mock(stdout=large_diff, returncode=0)
            elif cmd[1] == "diff" and "--name-only" in cmd:
                return Mock(stdout="test.py\n", returncode=0)
            else:
                return Mock(stdout="", returncode=0)

        mock_subprocess.side_effect = mock_run_side_effect

        with patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
            mock_analyze.return_value = "Large diff analysis"

            result = reviewer.review_local_diff("main..feature", "/fake/repo")
            assert "Large diff analysis" in result

    def test_git_command_failure(self):
        """Test handling of git command failures."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("subprocess.run") as mock_subprocess, patch("pathlib.Path.exists", return_value=True):
            mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git diff", stderr="bad revision")

            with pytest.raises(RuntimeError, match="Failed to get git diff"):
                reviewer.review_local_diff("main..feature", "/fake/repo")

    def test_non_git_repository_error(self):
        """Test error handling for non-git repositories."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="test", api_key="test"),
        )
        reviewer = PRReviewer(config)

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(RuntimeError, match="Not a git repository"):
                reviewer.review_local_diff("main..feature", "/fake/repo")
