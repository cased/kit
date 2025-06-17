import logging
import os
import time
from pathlib import Path

import pytest

from kit.repository import Repository


def _make_repo_dir(root: Path, name: str, mtime_offset_hours: float = 0.0) -> Path:
    """Helper to create a dummy repo directory with an adjusted *mtime*."""
    repo_dir = root / name
    repo_dir.mkdir(parents=True, exist_ok=True)
    if mtime_offset_hours:
        ts = time.time() - mtime_offset_hours * 3600
        os.utime(repo_dir, (ts, ts))
    return repo_dir


def test_performs_cache_cleanup(tmp_path: Path):
    """Repositories older than *ttl* hours should be removed."""
    cache_root = tmp_path / "kit-repo-cache"
    cache_root.mkdir()

    # Create one old repo (>2h) and one fresh repo (now)
    old_repo = _make_repo_dir(cache_root, "old-repo", mtime_offset_hours=3)
    fresh_repo = _make_repo_dir(cache_root, "fresh-repo")

    # Reset the lru_cache to ensure the helper executes for this test
    Repository._perform_cache_cleanup.cache_clear()

    Repository._perform_cache_cleanup(str(cache_root), ttl_hours=2)

    assert not old_repo.exists(), "Old repo should have been cleaned up"
    assert fresh_repo.exists(), "Fresh repo should remain"


def test_env_var_ttl_parsing(monkeypatch, tmp_path: Path):
    """Environment variable should set default TTL when not explicitly provided."""
    monkeypatch.setenv("KIT_TMP_REPO_TTL_HOURS", "1.5")

    repo_dir = tmp_path / "dummy"
    repo_dir.mkdir()

    repo = Repository(str(repo_dir))  # Local path – no clone
    assert repo.cache_ttl_hours == 1.5


@pytest.mark.parametrize("val", ["", "not-a-number"])
def test_env_var_ttl_invalid(monkeypatch, tmp_path: Path, val, caplog):
    """Invalid env values should be ignored and logged at DEBUG level."""
    monkeypatch.setenv("KIT_TMP_REPO_TTL_HOURS", val)
    caplog.set_level(logging.DEBUG)

    repo_dir = tmp_path / "dummy2"
    repo_dir.mkdir()
    repo = Repository(str(repo_dir))

    assert repo.cache_ttl_hours is None
    # Confirm a debug log entry was produced (optional but helpful)
    assert any("Invalid value for KIT_TMP_REPO_TTL_HOURS" in rec.getMessage() for rec in caplog.records)
