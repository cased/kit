"""Tests for deterministic ID generation in registry with ref parameters."""

import tempfile
from pathlib import Path

from src.kit.api.registry import PersistentRepoRegistry, _canonical, path_to_id


class TestRegistryDeterministicIDs:
    """Test that registry generates deterministic IDs based on path+ref combinations."""

    def test_same_path_ref_same_id(self):
        """Test that same path+ref combination always returns same ID."""
        registry = PersistentRepoRegistry()

        # Add same path+ref multiple times
        id1 = registry.add(".", "main")
        id2 = registry.add(".", "main")
        id3 = registry.add(".", "main")

        # Should all be the same
        assert id1 == id2 == id3

    def test_different_refs_different_ids(self):
        """Test that different refs for same path return different IDs."""
        registry = PersistentRepoRegistry()

        # Same path, different refs
        id_main = registry.add(".", "main")
        id_tag = registry.add(".", "v1.0.0")
        id_commit = registry.add(".", "abc123def456")
        id_none = registry.add(".")

        # All should be different
        ids = [id_main, id_tag, id_commit, id_none]
        assert len(set(ids)) == len(ids), f"Expected all different IDs, got: {ids}"

    def test_canonical_path_includes_ref(self):
        """Test that _canonical function properly includes ref parameter."""
        path = "."

        canon_main = _canonical(path, "main")
        canon_tag = _canonical(path, "v1.0.0")
        canon_none = _canonical(path, None)

        # Should include ref in canonical representation
        assert "@main" in canon_main
        assert "@v1.0.0" in canon_tag
        assert canon_main != canon_tag
        assert canon_main != canon_none

    def test_path_to_id_deterministic(self):
        """Test that path_to_id function is deterministic."""
        canon1 = _canonical(".", "main")
        canon2 = _canonical(".", "main")
        canon3 = _canonical(".", "v1.0.0")

        id1 = path_to_id(canon1)
        id2 = path_to_id(canon2)
        id3 = path_to_id(canon3)

        # Same canonical path should give same ID
        assert id1 == id2
        # Different canonical path should give different ID
        assert id1 != id3

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
