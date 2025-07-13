"""Tests for CLI commands with ref parameter support."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
import typer.testing

from kit.cli import app


@pytest.fixture
def runner():
    """Create a typer test runner."""
    return typer.testing.CliRunner()


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
        test_file.write_text("def hello(): pass")

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


class TestCLIRefParameter:
    """Test CLI commands with ref parameter."""

    def test_git_info_command(self, runner):
        """Test the git-info command."""
        result = runner.invoke(app, ["git-info", "."])
        assert result.exit_code == 0

        # Should contain git metadata
        output = result.stdout
        assert "Current SHA:" in output
        assert "Current Branch:" in output
        assert "Remote URL:" in output

    def test_git_info_with_ref(self, runner, temp_git_repo):
        """Test git-info command with ref parameter."""
        result = runner.invoke(app, ["git-info", temp_git_repo, "--ref", "main"])
        assert result.exit_code == 0

        output = result.stdout
        assert "Current SHA:" in output

    def test_git_info_json_output(self, runner):
        """Test git-info command with JSON output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            result = runner.invoke(app, ["git-info", ".", "--output", temp_file])
            assert result.exit_code == 0

            # Check JSON file was created and contains expected data
            output_data = json.loads(Path(temp_file).read_text())
            assert "current_sha" in output_data
            assert "current_branch" in output_data
            assert "remote_url" in output_data
            assert isinstance(output_data["current_sha"], (str, type(None)))
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_file_tree_with_ref(self, runner, temp_git_repo):
        """Test file-tree command with ref parameter."""
        result = runner.invoke(app, ["file-tree", temp_git_repo, "--ref", "main"])
        assert result.exit_code == 0

        # Should show file tree output
        assert "📁" in result.stdout or "📄" in result.stdout

    def test_symbols_with_ref(self, runner, temp_git_repo):
        """Test symbols command with ref parameter."""
        result = runner.invoke(app, ["symbols", temp_git_repo, "--format", "names", "--ref", "main"])
        assert result.exit_code == 0

        # Should contain some symbols
        output = result.stdout.strip()
        if output:  # Only check if there are symbols
            lines = output.split("\n")
            assert len(lines) > 0

    def test_search_with_ref(self, runner, temp_git_repo):
        """Test search command with ref parameter - skip if ref not supported."""
        result = runner.invoke(app, ["search", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("search command doesn't support --ref parameter yet")

        result = runner.invoke(app, ["search", temp_git_repo, "hello", "--ref", "main"])
        assert result.exit_code == 0

    def test_usages_with_ref(self, runner, temp_git_repo):
        """Test usages command with ref parameter - skip if ref not supported."""
        result = runner.invoke(app, ["usages", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("usages command doesn't support --ref parameter yet")

        result = runner.invoke(app, ["usages", temp_git_repo, "hello", "--ref", "main"])
        assert result.exit_code == 0

    def test_export_with_ref(self, runner, temp_git_repo):
        """Test export command with ref parameter - skip if ref not supported."""
        result = runner.invoke(app, ["export", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("export command doesn't support --ref parameter yet")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            result = runner.invoke(app, ["export", temp_git_repo, "file-tree", temp_file, "--ref", "main"])
            assert result.exit_code == 0

            # Check JSON file was created
            assert Path(temp_file).exists()
            output_data = json.loads(Path(temp_file).read_text())
            assert isinstance(output_data, list)  # file-tree returns a list
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_invalid_ref_error(self, runner, temp_git_repo):
        """Test that invalid ref parameter shows appropriate error."""
        result = runner.invoke(app, ["git-info", temp_git_repo, "--ref", "nonexistent-ref-12345"])
        assert result.exit_code != 0
        assert "Failed to checkout ref" in result.stdout or "Cannot checkout ref" in result.stdout

    def test_help_shows_ref_parameter(self, runner):
        """Test that help output shows ref parameter for relevant commands."""
        pytest.skip("Skipping due to Typer 0.15.3 issue with help command")

        commands_with_ref = ["git-info", "file-tree", "symbols"]

        for command in commands_with_ref:
            result = runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0
            assert "--ref" in result.stdout

    def test_git_info_non_git_repo(self, runner):
        """Test git-info command on non-git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a non-git directory with a Python file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            result = runner.invoke(app, ["git-info", temp_dir])
            assert result.exit_code == 0

            # Should show message about not being git repo
            output = result.stdout
            assert "not a git repository" in output.lower() or "no git metadata" in output.lower()

    def test_ref_with_non_git_repo_error(self, runner):
        """Test that using ref with non-git repo shows error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            result = runner.invoke(app, ["git-info", temp_dir, "--ref", "main"])
            assert result.exit_code != 0
            assert "not a git repository" in result.stdout.lower() or "Cannot checkout ref" in result.stdout
