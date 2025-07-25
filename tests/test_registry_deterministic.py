"""Tests for deterministic ID generation in registry with ref parameters."""

import subprocess
import tempfile
from pathlib import Path

from src.kit.api.registry import PersistentRepoRegistry, _canonical, path_to_id


class TestRegistryDeterministicIDs:
    """Test that registry generates deterministic IDs based on path+ref combinations."""

    def test_same_path_ref_same_id(self):
        """Test that same path+ref combination always returns same ID."""
        registry = PersistentRepoRegistry()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Add same path+ref multiple times
            id1 = registry.add(temp_dir, "main")
            id2 = registry.add(temp_dir, "main")
            id3 = registry.add(temp_dir, "main")

            # All should be the same
            assert id1 == id2 == id3

    def test_different_refs_different_ids(self):
        """Test that different refs for same path return different IDs."""
        registry = PersistentRepoRegistry()

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            # Same path, different refs
            id_main = registry.add(temp_dir, "main")
            id_feature = registry.add(temp_dir, "feature")
            id_develop = registry.add(temp_dir, "develop")

            # All should be different
            assert id_main != id_feature
            assert id_main != id_develop
            assert id_feature != id_develop

    def test_canonical_path_includes_ref(self):
        """Test that _canonical function properly includes ref parameter."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            path = temp_dir

            canon_main = _canonical(path, "main")
            canon_feature = _canonical(path, "feature")

            # Should be different for different refs
            assert canon_main != canon_feature

            # Should include the ref in the canonical form
            assert "main" in canon_main
            assert "feature" in canon_feature

    def test_path_to_id_deterministic(self):
        """Test that path_to_id function is deterministic."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a git repo in the temp directory
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)

            canon1 = _canonical(temp_dir, "main")
            canon2 = _canonical(temp_dir, "main")

            # Should be deterministic
            assert canon1 == canon2

    def test_remote_url_with_ref(self):
        """Test deterministic IDs for remote URLs with refs."""
        registry = PersistentRepoRegistry()

        url = "https://github.com/owner/repo"

        id1 = registry.add(url, "main")
        id2 = registry.add(url, "main")
        id3 = registry.add(url, "v1.0.0")
        id4 = registry.add(url)  # No ref

        # Same URL+ref should be same
        assert id1 == id2
        # Different refs should be different
        assert id1 != id3
        assert id1 != id4
        assert id3 != id4

    def test_canonical_remote_url_format(self):
        """Test canonical format for remote URLs."""
        url = "https://github.com/owner/repo"

        canon_main = _canonical(url, "main")
        canon_none = _canonical(url, None)

        # Should include ref for remote URLs
        assert canon_main.endswith("@main")
        assert canon_none.endswith("@HEAD")  # Default for remote URLs

    def test_local_path_resolution(self):
        """Test that local paths are resolved consistently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            # Test relative vs absolute paths
            canon1 = _canonical(temp_dir, "main")
            canon2 = _canonical(str(Path(temp_dir).resolve()), "main")

            # Should resolve to same canonical representation
            id1 = path_to_id(canon1)
            id2 = path_to_id(canon2)
            assert id1 == id2
