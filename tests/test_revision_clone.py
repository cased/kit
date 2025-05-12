import subprocess
import tempfile
import unittest
from pathlib import Path

from kit import Repository


class TestRepositoryRevisions(unittest.TestCase):
    """Tests for the Repository class revision feature."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up temporary directory after tests."""
        self.temp_dir.cleanup()

    def test_clone_specific_revision(self):
        """Test cloning a repository at a specific revision."""
        # Clone a well-known repository with multiple tags/releases
        repo_url = "https://github.com/sferik/t.git"

        # Use a well-known tag that shouldn't change
        revision = "v3.1.0"

        # Initialize repo with revision
        repo = Repository(repo_url, cache_dir=self.temp_path, revision=revision)

        # Verify we have the correct revision checked out
        git_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        git_result = subprocess.run(git_cmd, cwd=repo.repo_path, capture_output=True, text=True, check=True)

        # If HEAD is a tag, it will report in detached HEAD state
        if git_result.stdout.strip() == "HEAD":
            # Check the actual tag name
            describe_cmd = ["git", "describe", "--tags"]
            describe_result = subprocess.run(
                describe_cmd, cwd=repo.repo_path, capture_output=True, text=True, check=True
            )
            # Assert the tag is what we expect
            self.assertEqual(describe_result.stdout.strip(), revision)
        else:
            # If HEAD is a branch, assert it's the correct branch
            self.assertEqual(git_result.stdout.strip(), revision)

    def test_clone_specific_sha(self):
        """Test cloning a repository at a specific SHA commit."""
        # Use a public repo from GitHub
        repo_url = "https://github.com/sferik/t.git"

        # Use a specific commit SHA (first 7 chars are usually enough)
        # This is a real commit from the sferik/t repo
        revision = "@f106e92"  # Using @SHA format

        # Initialize repo with revision
        repo = Repository(repo_url, cache_dir=self.temp_path, revision=revision)

        # Verify we have the correct SHA checked out
        git_cmd = ["git", "rev-parse", "--short", "HEAD"]
        git_result = subprocess.run(git_cmd, cwd=repo.repo_path, capture_output=True, text=True, check=True)

        # Assert the SHA matches (comparing only the part we specified)
        expected_sha = revision.lstrip("@")
        self.assertEqual(git_result.stdout.strip(), expected_sha)


if __name__ == "__main__":
    unittest.main()
