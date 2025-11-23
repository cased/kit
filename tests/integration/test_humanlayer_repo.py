import pytest
from pathlib import Path
from kit.repo_mapper import RepoMapper
import subprocess


@pytest.mark.integration
@pytest.mark.skipif(
    not Path("/home/selman/dev/humanlayer").exists(),
    reason="Requires humanlayer repository"
)
def test_humanlayer_repo_gitignore():
    """Integration test: Verify fix works on actual humanlayer repo."""

    # Get git's file count
    result = subprocess.run(
        ["git", "ls-files"],
        cwd="/home/selman/dev/humanlayer",
        capture_output=True,
        text=True
    )
    git_files = set(result.stdout.strip().split("\n"))
    git_count = len(git_files)

    # Get kit's file count
    mapper = RepoMapper("/home/selman/dev/humanlayer")
    tree = mapper.get_file_tree()
    kit_count = len(tree)
    kit_paths = {item["path"] for item in tree}

    # Should be approximately equal (within 10% tolerance for build artifacts)
    tolerance = 0.1
    assert abs(kit_count - git_count) / git_count < tolerance, \
        f"Kit returned {kit_count} files, Git tracks {git_count} files"

    # Should be well under token limit (assuming ~100 chars per file path)
    estimated_tokens = kit_count * 100
    assert estimated_tokens < 25000, \
        f"Estimated {estimated_tokens} tokens (exceeds 25k limit)"

    # Verify no node_modules files included
    node_modules_files = [p for p in kit_paths if "node_modules" in p]
    assert len(node_modules_files) == 0, \
        f"Found {len(node_modules_files)} node_modules files (should be 0)"
