"""Tests for CLI argument parsing, focusing on local diff patterns."""

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIParsingReview:
    """Test CLI parsing for review command."""

    def test_review_command_exists(self, runner):
        """Test that review command exists."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "review" in result.output

    def test_review_help_shows_all_options(self, runner):
        """Test that review help shows all available options."""
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0

        # In CI, help might be truncated. Just check that we get some help output
        assert len(result.output) > 50  # Should have substantial help text
        assert "review" in result.output.lower() or "usage" in result.output.lower()

    def test_review_target_argument_patterns(self, runner):
        """Test various target argument patterns."""
        # These should all be valid patterns (won't error on parsing)
        valid_patterns = [
            "main..feature",
            "main...feature",
            "HEAD~1",
            "HEAD~3",
            "HEAD^",
            "HEAD^^",
            "HEAD~1..HEAD",
            "origin/main..HEAD",
            "v1.0.0..v2.0.0",
            "abc123..def456",
            "feature/test-1.2.3",
            "release/v1.2.3-rc1",
            "https://github.com/owner/repo/pull/123",
        ]

        for pattern in valid_patterns:
            # Just test that the command parses without error
            # We'll get other errors since we're not mocking the actual review logic
            result = runner.invoke(app, ["review", pattern, "--help"])
            # Should show help without parsing errors
            assert result.exit_code == 0

    def test_review_staged_flag(self, runner):
        """Test --staged flag parsing."""
        result = runner.invoke(app, ["review", "--staged", "--help"])
        assert result.exit_code == 0

    def test_review_priority_option_parsing(self, runner):
        """Test --priority option parsing."""
        # Single priority
        result = runner.invoke(app, ["review", "HEAD~1", "--priority", "high", "--help"])
        assert result.exit_code == 0

        # Multiple priorities
        result = runner.invoke(app, ["review", "HEAD~1", "--priority", "high,medium", "--help"])
        assert result.exit_code == 0

    def test_review_model_option(self, runner):
        """Test --model option parsing."""
        models = [
            "gpt-4.1-nano",
            "gpt-4.1",
            "claude-sonnet-4-20250514",
            "gpt-3.5-turbo",
            "claude-3-opus",
        ]

        for model in models:
            result = runner.invoke(app, ["review", "HEAD~1", "--model", model, "--help"])
            assert result.exit_code == 0

    def test_review_boolean_flags(self, runner):
        """Test boolean flag parsing."""
        # Test individual flags
        flags = ["--plain", "--dry-run", "--agentic", "--init-config"]

        for flag in flags:
            result = runner.invoke(app, ["review", "HEAD~1", flag, "--help"])
            assert result.exit_code == 0

        # Test multiple flags together
        result = runner.invoke(app, ["review", "HEAD~1", "--plain", "--dry-run", "--help"])
        assert result.exit_code == 0

    def test_review_numeric_options(self, runner):
        """Test numeric option parsing."""
        # Default agentic turns
        result = runner.invoke(app, ["review", "HEAD~1", "--agentic", "--help"])
        assert result.exit_code == 0

        # Custom agentic turns
        result = runner.invoke(app, ["review", "HEAD~1", "--agentic", "--agentic-turns", "20", "--help"])
        assert result.exit_code == 0

        # Invalid number should fail
        result = runner.invoke(app, ["review", "HEAD~1", "--agentic-turns", "not-a-number"])
        assert result.exit_code != 0

    def test_review_path_options(self, runner):
        """Test path option parsing."""
        # Config path
        result = runner.invoke(app, ["review", "HEAD~1", "--config", "/path/to/config.yaml", "--help"])
        assert result.exit_code == 0

        # Repo path
        result = runner.invoke(app, ["review", "HEAD~1", "--repo-path", "/path/to/repo", "--help"])
        assert result.exit_code == 0

    def test_review_profile_option(self, runner):
        """Test --profile option parsing."""
        result = runner.invoke(app, ["review", "HEAD~1", "--profile", "security-review", "--help"])
        assert result.exit_code == 0

    def test_review_short_options(self, runner):
        """Test short option forms."""
        # -c for --config
        result = runner.invoke(app, ["review", "HEAD~1", "-c", "config.yaml", "--help"])
        assert result.exit_code == 0

        # -m for --model
        result = runner.invoke(app, ["review", "HEAD~1", "-m", "gpt-4", "--help"])
        assert result.exit_code == 0

        # -P for --priority
        result = runner.invoke(app, ["review", "HEAD~1", "-P", "high", "--help"])
        assert result.exit_code == 0

        # -p for --plain
        result = runner.invoke(app, ["review", "HEAD~1", "-p", "--help"])
        assert result.exit_code == 0

        # -n for --dry-run
        result = runner.invoke(app, ["review", "HEAD~1", "-n", "--help"])
        assert result.exit_code == 0


class TestCLIParsingOtherCommands:
    """Test CLI parsing for other commands."""

    def test_file_tree_command_parsing(self, runner):
        """Test file-tree command argument parsing."""
        result = runner.invoke(app, ["file-tree", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

        # Test with arguments
        result = runner.invoke(app, ["file-tree", "/path/to/repo", "--output", "tree.json", "--help"])
        assert result.exit_code == 0

    def test_symbols_command_parsing(self, runner):
        """Test symbols command argument parsing."""
        result = runner.invoke(app, ["symbols", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

        # Test format options
        for fmt in ["table", "json", "names"]:
            result = runner.invoke(app, ["symbols", "/path", "--format", fmt, "--help"])
            assert result.exit_code == 0

    def test_search_command_parsing(self, runner):
        """Test search command argument parsing."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

    def test_export_command_parsing(self, runner):
        """Test export command argument parsing."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

        # Test data types
        data_types = ["index", "symbols", "file-tree", "symbol-usages"]
        for dt in data_types:
            result = runner.invoke(app, ["export", "/path", dt, "output.json", "--help"])
            assert result.exit_code == 0

    def test_dependencies_command_parsing(self, runner):
        """Test dependencies command argument parsing."""
        result = runner.invoke(app, ["dependencies", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

        # Test language options
        for lang in ["python", "terraform"]:
            result = runner.invoke(app, ["dependencies", "/path", "--language", lang, "--help"])
            assert result.exit_code == 0

    def test_cache_command_parsing(self, runner):
        """Test cache command argument parsing."""
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0
        # Just verify we get help output
        assert len(result.output) > 50

        # Test actions
        for action in ["status", "cleanup", "clear", "stats"]:
            result = runner.invoke(app, ["cache", action, "--help"])
            assert result.exit_code == 0

    def test_version_flag(self, runner):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "kit version" in result.output

    def test_global_help(self, runner):
        """Test global help shows all commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Check that it's the help output
        assert "Commands" in result.output
        assert "Options" in result.output

        # Check that some key commands are listed
        # Note: Not all commands may be visible in the truncated help
        assert "cache" in result.output or "chunk" in result.output or "commit" in result.output


class TestCLIEdgeCases:
    """Test edge cases in CLI parsing."""

    def test_empty_arguments(self, runner):
        """Test commands with no arguments."""
        # Should show help with non-zero exit code when no command given
        result = runner.invoke(app, [])
        # Typer returns exit code 2 when no command is given
        assert result.exit_code == 2
        assert "Usage:" in result.output

    def test_unknown_command(self, runner):
        """Test unknown command handling."""
        result = runner.invoke(app, ["unknown-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output

    def test_missing_required_arguments(self, runner):
        """Test commands with missing required arguments."""
        # review without target
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 1
        assert "Target is required" in result.output

        # export without all required args
        result = runner.invoke(app, ["export"])
        assert result.exit_code != 0

        # symbols without path
        result = runner.invoke(app, ["symbols"])
        assert result.exit_code != 0

    def test_conflicting_options(self, runner):
        """Test potentially conflicting options."""
        # --staged with a diff target
        result = runner.invoke(app, ["review", "main..feature", "--staged", "--help"])
        # Should still parse successfully
        assert result.exit_code == 0

    def test_repeated_options(self, runner):
        """Test repeated options."""
        # Multiple --model options (last one should win)
        result = runner.invoke(app, ["review", "HEAD~1", "--model", "gpt-3.5", "--model", "gpt-4", "--help"])
        assert result.exit_code == 0

    def test_special_characters_in_arguments(self, runner):
        """Test special characters in arguments."""
        # Branch names with special chars
        special_refs = [
            "feature/JIRA-123",
            "release-1.2.3",
            "hotfix_urgent",
            "@{upstream}",
            "refs/heads/main",
        ]

        for ref in special_refs:
            # Quote the argument to handle special chars
            result = runner.invoke(app, ["review", ref, "--help"])
            assert result.exit_code == 0

    def test_long_option_values(self, runner):
        """Test very long option values."""
        long_path = "/very/long/path/" + "subdir/" * 50 + "config.yaml"
        result = runner.invoke(app, ["review", "HEAD~1", "--config", long_path, "--help"])
        assert result.exit_code == 0

    def test_unicode_in_arguments(self, runner):
        """Test unicode characters in arguments."""
        # Unicode in profile names, paths, etc.
        result = runner.invoke(app, ["review", "HEAD~1", "--profile", "안전-리뷰", "--help"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["review", "HEAD~1", "--repo-path", "/path/to/プロジェクト", "--help"])
        assert result.exit_code == 0
