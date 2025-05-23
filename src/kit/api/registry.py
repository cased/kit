"""Persistent repository registry used by the FastAPI layer.

* Maps a canonical repo path/URL to a deterministic SHA-1-based ID.
* Persists that map in ``~/.kit/registry.json`` so IDs survive restarts.
* Maintains an LRU in-process cache of ``kit.Repository`` objects for speed.

This keeps the web API stateless across workers and deploys while still
re-using heavy in-memory structures when hot.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit

from ..repository import Repository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGISTRY_DIR = Path.home() / ".kit"
_REGISTRY_FILE = _REGISTRY_DIR / "registry.json"


def _canonical(value: str, ref: str | None = None) -> str:
    """Return a stable representation including an optional *ref*/commit."""
    if "://" in value:  # remote URL
        parts = urlsplit(value)
        base = parts._replace(fragment="").geturl()
        return f"{base}@{ref or 'HEAD'}"

    # Local path
    base = str(Path(value).expanduser().resolve())
    if ref:
        return f"{base}@{ref}"

    # If not provided, attempt to resolve current commit
    try:
        import subprocess

        result = subprocess.run(["git", "-C", base, "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            ref = result.stdout.strip()
    except Exception:
        ref = None
    return f"{base}@{ref or 'WORKTREE'}"


def path_to_id(canonical_path: str) -> str:
    """Deterministically hash *canonical_path* to a short ID string."""
    return hashlib.sha1(canonical_path.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PersistentRepoRegistry:
    """Thread-safe, process-local registry with on-disk persistence."""

    def __init__(self, max_cache_entries: int = 32) -> None:
        self._lock = threading.Lock()
        self._map: Dict[str, Dict[str, str]] = {}  # id -> {'path': str, 'ref': str}
        self._cache: "OrderedDict[str, Repository]" = OrderedDict()
        self._max_cache = max_cache_entries
        self._load()

    # --------------------------- Persistence ---------------------------
    def _load(self) -> None:
        if _REGISTRY_FILE.exists():
            try:
                self._map = json.loads(_REGISTRY_FILE.read_text())
            except Exception:
                # Corrupt file – start fresh but keep a backup
                _REGISTRY_FILE.rename(_REGISTRY_FILE.with_suffix(".bak"))
                self._map = {}
        else:
            _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
            _REGISTRY_FILE.write_text("{}")

    def _save(self) -> None:
        tmp = _REGISTRY_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._map, indent=2))
        tmp.replace(_REGISTRY_FILE)

    # --------------------------- Public API ---------------------------
    def add(self, path_or_url: str, ref: str | None = None) -> str:
        canon = _canonical(path_or_url, ref)
        rid = path_to_id(canon)
        with self._lock:
            if rid not in self._map:
                from pathlib import Path as _P

                real = path_or_url
                if "://" not in path_or_url:
                    real = str(_P(path_or_url).expanduser().resolve())
                self._map[rid] = {
                    "path": real,
                    "ref": ref or "",
                }
                self._save()
        return rid

    def get_repo(self, repo_id: str) -> Repository:
        with self._lock:
            if repo_id in self._cache:
                # Move to front (most-recently used)
                self._cache.move_to_end(repo_id, last=False)
                return self._cache[repo_id]

            rec = self._map.get(repo_id)
            if rec is None:
                raise KeyError(repo_id)

            # Pass ref parameter to Repository if it exists
            ref = rec.get("ref") if rec.get("ref") else None
            repo = Repository(rec["path"], ref=ref)
            self._cache[repo_id] = repo
            self._cache.move_to_end(repo_id, last=False)
            # Evict if over capacity
            if len(self._cache) > self._max_cache:
                _, old_repo = self._cache.popitem(last=True)
                # No explicit close needed; allow GC
            return repo

    def delete(self, repo_id: str) -> None:
        with self._lock:
            removed = self._map.pop(repo_id, None)
            self._cache.pop(repo_id, None)
            if removed is not None:
                self._save()


# Export singleton
registry = PersistentRepoRegistry()
