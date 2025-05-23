"""Tests for CLI commands with ref parameter support."""

import json
import subprocess
from pathlib import Path

import pytest


def run_kit_command(args: list, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Helper to run kit CLI commands."""
    cmd = ["kit", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)


class TestCLIRefParameter:
    """Test CLI commands with ref parameter."""

    def test_git_info_command(self):
        """Test the git-info command."""
        result = run_kit_command(["git-info", "."])
        assert result.returncode == 0

        # Should contain git metadata
        output = result.stdout
        assert "Current SHA:" in output
        assert "Current Branch:" in output
        assert "Remote URL:" in output

    def test_git_info_with_ref(self):
        """Test git-info command with ref parameter."""
        result = run_kit_command(["git-info", ".", "--ref", "main"])
        assert result.returncode == 0

        output = result.stdout
        assert "Current SHA:" in output

    def test_git_info_json_output(self):
        """Test git-info command with JSON output."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            result = run_kit_command(["git-info", ".", "--output", temp_file])
            assert result.returncode == 0

            # Check JSON file was created and contains expected data
            output_data = json.loads(Path(temp_file).read_text())
            assert "current_sha" in output_data
            assert "current_branch" in output_data
            assert "remote_url" in output_data
            assert isinstance(output_data["current_sha"], (str, type(None)))
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_file_tree_with_ref(self):
        """Test file-tree command with ref parameter."""
        result = run_kit_command(["file-tree", ".", "--ref", "main"])
        assert result.returncode == 0

        # Should show file tree output
        assert "📁" in result.stdout or "📄" in result.stdout

    def test_symbols_with_ref(self):
        """Test symbols command with ref parameter."""
        result = run_kit_command(["symbols", ".", "--format", "names", "--ref", "main"])
        assert result.returncode == 0

        # Should contain some symbols
        output = result.stdout.strip()
        if output:  # Only check if there are symbols
            lines = output.split("\n")
            assert len(lines) > 0

    def test_search_with_ref(self):
        """Test search command with ref parameter - skip if ref not supported."""
        result = run_kit_command(["search", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("search command doesn't support --ref parameter yet")

        result = run_kit_command(["search", ".", "Repository", "--ref", "main"])
        assert result.returncode == 0

    def test_usages_with_ref(self):
        """Test usages command with ref parameter - skip if ref not supported."""
        result = run_kit_command(["usages", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("usages command doesn't support --ref parameter yet")

        result = run_kit_command(["usages", ".", "Repository", "--ref", "main"])
        assert result.returncode == 0

    def test_export_with_ref(self):
        """Test export command with ref parameter - skip if ref not supported."""
        result = run_kit_command(["export", "--help"])
        if "--ref" not in result.stdout:
            pytest.skip("export command doesn't support --ref parameter yet")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            result = run_kit_command(["export", ".", "file-tree", temp_file, "--ref", "main"])
            assert result.returncode == 0

            # Check JSON file was created
            assert Path(temp_file).exists()
            output_data = json.loads(Path(temp_file).read_text())
            assert isinstance(output_data, list)  # file-tree returns a list
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_invalid_ref_error(self):
        """Test that invalid ref parameter shows appropriate error."""
        result = run_kit_command(["git-info", ".", "--ref", "nonexistent-ref-12345"])
        assert result.returncode != 0
        assert "Failed to checkout ref" in result.stdout or "Cannot checkout ref" in result.stdout

    def test_help_shows_ref_parameter(self):
        """Test that help output shows ref parameter for relevant commands."""
        commands_with_ref = ["git-info", "file-tree", "symbols"]

        for command in commands_with_ref:
            result = run_kit_command([command, "--help"])
            assert result.returncode == 0
            assert "--ref" in result.stdout

    def test_git_info_non_git_repo(self):
        """Test git-info command on non-git repository."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a non-git directory with a Python file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            result = run_kit_command(["git-info", temp_dir])
            assert result.returncode == 0

            # Should show message about not being git repo
            output = result.stdout
            assert "not a git repository" in output.lower() or "no git metadata" in output.lower()

    def test_ref_with_non_git_repo_error(self):
        """Test that using ref with non-git repo shows error."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            result = run_kit_command(["git-info", temp_dir, "--ref", "main"])
            assert result.returncode != 0
            assert "not a git repository" in result.stdout.lower() or "Cannot checkout ref" in result.stdout
