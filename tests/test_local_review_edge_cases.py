"""Test edge cases and error handling for local review."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kit.pr_review.config import ReviewConfig
from kit.pr_review.local_reviewer import LocalDiffReviewer


@pytest.fixture
def mock_config():
    """Create a mock ReviewConfig."""
    config = MagicMock(spec=ReviewConfig)
    config.max_files = 10
    config.quiet = True
    config.save_reviews = False
    config.priority_filter = None
    config.llm_provider = "anthropic"
    config.llm_model = "test-model"
    config.llm_api_key = "test-key"
    config.llm_api_base_url = None
    config.llm_temperature = 0.1
    config.llm_max_tokens = 1000
    config.custom_pricing = None
    return config


class TestLocalReviewEdgeCases:
    """Test edge cases and error conditions."""

    def test_not_git_repository(self, mock_config):
        """Test error when not in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reviewer = LocalDiffReviewer(mock_config, Path(tmpdir))

            with pytest.raises(RuntimeError, match="Not in a git repository"):
                reviewer.review("HEAD~1..HEAD")

    def test_invalid_git_ref(self, mock_config):
        """Test error with invalid git reference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create initial commit
            (repo_path / "test.txt").write_text("test")
            os.system("git add test.txt")
            os.system('git commit -m "Initial" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            with pytest.raises(ValueError, match="Invalid git ref"):
                reviewer._get_commit_info("nonexistent-branch")

    def test_diff_between_invalid_refs(self, mock_config):
        """Test error when getting diff between invalid refs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            with pytest.raises(ValueError, match="Invalid git ref"):
                reviewer._get_diff("invalid-ref-1", "invalid-ref-2")

    def test_llm_api_error(self, mock_config):
        """Test handling of LLM API errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create commits
            (repo_path / "test.py").write_text("print('test')")
            os.system("git add test.py")
            os.system('git commit -m "Add test" --quiet')

            # Create a second commit so HEAD~1 exists
            (repo_path / "test.py").write_text("print('test modified')")
            os.system("git add test.py")
            os.system('git commit -m "Modify test" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Mock LLM to raise error
            with patch.object(reviewer, "_get_llm_review") as mock_llm:
                mock_llm.side_effect = Exception("API Error")

                with pytest.raises(RuntimeError, match="Failed to review local diff: API Error"):
                    reviewer.review("HEAD~1..HEAD")

    def test_missing_llm_library(self, mock_config):
        """Test error when LLM library is not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            (repo_path / "test.py").write_text("print('test')")
            os.system("git add test.py")
            os.system('git commit -m "Test" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Create a second commit so HEAD~1 exists
            (repo_path / "test2.py").write_text("print('test2')")
            os.system("git add test2.py")
            os.system('git commit -m "Add test2" --quiet')

            # Mock import error by mocking the method that uses anthropic
            with patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_anthropic:
                mock_anthropic.side_effect = ValueError(
                    "Anthropic library not installed. Install with: pip install anthropic"
                )

                with pytest.raises(RuntimeError):
                    reviewer.review("HEAD~1..HEAD")

    def test_empty_repository(self, mock_config):
        """Test reviewing in empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # No commits yet
            with pytest.raises(ValueError):
                reviewer._get_commit_info("HEAD")

    def test_review_with_no_changes(self, mock_config):
        """Test reviewing when there are no changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            (repo_path / "test.txt").write_text("test")
            os.system("git add test.txt")
            os.system('git commit -m "Initial" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Mock empty analysis
            with patch.object(reviewer, "_analyze_with_kit") as mock_analyze:
                mock_analyze.return_value = {"symbols": [], "structure": [], "total_files": 0, "changed_files": 0}

                result = reviewer.review("HEAD..HEAD")
                assert "No changes to review" in result

    def test_malformed_diff(self, mock_config):
        """Test handling of malformed diffs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Mock _get_commit_info to avoid needing a real git repo
            with patch.object(reviewer, "_get_commit_info") as mock_commit_info:
                mock_commit_info.return_value = {
                    "hash": "abc123",
                    "author": "Test",
                    "date": "now",
                    "subject": "Test commit",
                    "body": "",
                }

                # Mock _get_diff to return malformed content
                with patch.object(reviewer, "_get_diff") as mock_diff:
                    mock_diff.return_value = "This is not a valid diff format"

                    with patch.object(reviewer, "_get_changed_files") as mock_files:
                        mock_files.return_value = []

                        # Should handle gracefully
                        change = reviewer._prepare_local_change("HEAD..HEAD")
                        assert change.diff == "This is not a valid diff format"
                        assert change.files == []

    def test_very_long_diff(self, mock_config):
        """Test handling of very long diffs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create initial commit
            (repo_path / "README.md").write_text("Initial")
            os.system("git add README.md")
            os.system('git commit -m "Initial commit" --quiet')

            # Create a large file
            large_content = "\n".join([f"line {i}" for i in range(10000)])
            (repo_path / "large.txt").write_text(large_content)
            os.system("git add large.txt")
            os.system('git commit -m "Add large file" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Should handle large diffs
            diff = reviewer._get_diff("HEAD~1", "HEAD")
            assert len(diff) > 100000  # Very long diff

    def test_special_characters_in_filenames(self, mock_config):
        """Test handling files with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create initial commit
            (repo_path / "README.md").write_text("Initial")
            os.system("git add README.md")
            os.system('git commit -m "Initial commit" --quiet')

            # Create files with special characters
            special_files = [
                "file with spaces.txt",
                "file-with-dashes.py",
                "file_with_underscores.js",
                "file.multiple.dots.tsx",
            ]

            for filename in special_files:
                (repo_path / filename).write_text(f"Content of {filename}")

            os.system("git add .")
            os.system('git commit -m "Add files with special names" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)
            files = reviewer._get_changed_files("HEAD~1", "HEAD")

            filenames = [f["filename"] for f in files]
            for special_file in special_files:
                assert special_file in filenames

    def test_permission_denied_on_save(self, mock_config):
        """Test handling permission errors when saving review."""
        mock_config.save_reviews = True

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create initial commit
            (repo_path / "initial.txt").write_text("initial")
            os.system("git add initial.txt")
            os.system('git commit -m "Initial" --quiet')

            # Create second commit
            (repo_path / "test.txt").write_text("test")
            os.system("git add test.txt")
            os.system('git commit -m "Test" --quiet')

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Mock save to raise permission error
            with patch.object(reviewer, "_save_review") as mock_save:
                mock_save.side_effect = PermissionError("Permission denied")

                # Should continue despite save error
                with patch.object(reviewer, "_get_llm_review") as mock_llm:
                    mock_llm.return_value = ("Test review", {})

                    result = reviewer.review("HEAD~1..HEAD")
                    assert "Test review" in result

    def test_concurrent_git_operations(self, mock_config):
        """Test handling when git operations fail due to locks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Mock git command to simulate lock
            with patch.object(reviewer, "_run_git_command") as mock_git:
                mock_git.return_value = ("", 128)  # Git lock error code

                with pytest.raises(ValueError):
                    reviewer._get_diff("HEAD", "HEAD")

    def test_detached_head_state(self, mock_config):
        """Test reviewing in detached HEAD state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)
            os.system("git init --quiet")
            os.system('git config user.name "Test"')
            os.system('git config user.email "test@test.com"')

            # Create commits
            (repo_path / "test1.txt").write_text("test1")
            os.system("git add test1.txt")
            os.system('git commit -m "Commit 1" --quiet')

            (repo_path / "test2.txt").write_text("test2")
            os.system("git add test2.txt")
            os.system('git commit -m "Commit 2" --quiet')

            # Go to detached HEAD
            os.system("git checkout HEAD~1 --quiet")

            reviewer = LocalDiffReviewer(mock_config, repo_path)

            # Should still work
            files = reviewer._get_changed_files("HEAD", "HEAD@{1}")
            assert any(f["filename"] == "test2.txt" for f in files)
