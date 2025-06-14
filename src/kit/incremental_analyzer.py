"""Enhanced incremental analysis system for kit repositories.

This module provides sophisticated caching and invalidation strategies that go beyond
simple mtime-based checking to provide maximum performance for large repositories.
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

logger = logging.getLogger(__name__)


class FileAnalysisCache:
    """Manages file-level analysis caching with multiple invalidation strategies."""

    def __init__(self, repo_path: Path, cache_dir: Optional[Path] = None, max_cache_size: int = 10000):
        self.repo_path = repo_path
        self.cache_dir = cache_dir or (repo_path / ".kit" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size

        # Cache file paths
        self.metadata_file = self.cache_dir / "analysis_metadata.json"
        self.symbols_cache_file = self.cache_dir / "symbols_cache.json"

        # In-memory caches with LRU eviction
        self._file_metadata: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._symbols_cache: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()

        # Load existing cache
        self._load_cache()

    def _load_cache(self) -> None:
        """Load existing cache from disk."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    loaded_metadata = json.load(f)
                    self._file_metadata = OrderedDict(loaded_metadata)

            if self.symbols_cache_file.exists():
                with open(self.symbols_cache_file, "r") as f:
                    loaded_symbols = json.load(f)
                    self._symbols_cache = OrderedDict(loaded_symbols)

            logger.debug(f"Loaded cache: {len(self._file_metadata)} files, {len(self._symbols_cache)} symbol sets")
        except (IOError, OSError, PermissionError) as e:
            logger.warning(f"Failed to load cache due to filesystem issue: {e}")
            self._file_metadata = OrderedDict()
            self._symbols_cache = OrderedDict()
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load cache due to corrupted data: {e}")
            self._file_metadata = OrderedDict()
            self._symbols_cache = OrderedDict()
        except Exception as e:
            logger.error(f"Unexpected error loading cache: {e}")
            # Re-raise for serious issues like out of memory
            raise

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache size exceeds limit."""
        while len(self._file_metadata) > self.max_cache_size:
            # Remove oldest entry (FIFO/LRU)
            oldest_key = next(iter(self._file_metadata))
            self._file_metadata.pop(oldest_key, None)
            self._symbols_cache.pop(oldest_key, None)
            logger.debug(f"Evicted cache entry for {oldest_key}")

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self._file_metadata, f, indent=2)

            with open(self.symbols_cache_file, "w") as f:
                json.dump(self._symbols_cache, f, indent=2)

            logger.debug(f"Saved cache: {len(self._file_metadata)} files, {len(self._symbols_cache)} symbol sets")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Get content hash of a file for change detection."""
        try:
            with open(file_path, "rb") as f:
                # Read in chunks for large files
                hasher = hashlib.sha256()
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
                return hasher.hexdigest()
        except (IOError, OSError, PermissionError) as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error hashing file {file_path}: {e}")
            return ""

    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive metadata for a file."""
        try:
            stat = file_path.stat()
            return {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": self._get_file_hash(file_path),
                "last_analyzed": time.time(),
            }
        except Exception as e:
            logger.warning(f"Failed to get metadata for {file_path}: {e}")
            return {}

    def is_file_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since last analysis."""
        rel_path = str(file_path.relative_to(self.repo_path))

        if rel_path not in self._file_metadata:
            return True  # Never analyzed

        cached_metadata = self._file_metadata[rel_path]
        current_metadata = self._get_file_metadata(file_path)

        # Quick mtime check first (fastest)
        if cached_metadata.get("mtime") != current_metadata.get("mtime"):
            return True

        # Size check (very fast)
        if cached_metadata.get("size") != current_metadata.get("size"):
            return True

        # Hash check for definitive answer (slower but accurate)
        if cached_metadata.get("hash") != current_metadata.get("hash"):
            return True

        return False

    def get_cached_symbols(self, file_path: Path) -> Optional[List[Dict[str, Any]]]:
        """Get cached symbols for a file if still valid."""
        rel_path = str(file_path.relative_to(self.repo_path))

        if self.is_file_changed(file_path):
            return None

        # Move to end for LRU behavior
        if rel_path in self._symbols_cache:
            symbols = self._symbols_cache.pop(rel_path)
            self._symbols_cache[rel_path] = symbols
            return symbols

        return None

    def cache_symbols(self, file_path: Path, symbols: List[Dict[str, Any]]) -> None:
        """Cache symbols for a file with current metadata."""
        rel_path = str(file_path.relative_to(self.repo_path))
        metadata = self._get_file_metadata(file_path)

        # Atomic update: prepare data first, then update both caches together
        # This reduces the window for inconsistent state
        self._file_metadata[rel_path] = metadata
        self._symbols_cache[rel_path] = symbols

        # Evict old entries if needed
        self._evict_if_needed()

        # Periodically save to disk
        if len(self._file_metadata) % 50 == 0:  # Save every 50 files
            self._save_cache()

    def invalidate_file(self, file_path: Path) -> None:
        """Invalidate cache for a specific file."""
        rel_path = str(file_path.relative_to(self.repo_path))
        self._file_metadata.pop(rel_path, None)
        self._symbols_cache.pop(rel_path, None)

    def cleanup_stale_entries(self) -> int:
        """Remove cache entries for files that no longer exist."""
        removed_count = 0
        stale_files = []

        for rel_path in list(self._file_metadata.keys()):
            file_path = self.repo_path / rel_path
            if not file_path.exists():
                stale_files.append(rel_path)

        for rel_path in stale_files:
            self._file_metadata.pop(rel_path, None)
            self._symbols_cache.pop(rel_path, None)
            removed_count += 1

        if removed_count > 0:
            self._save_cache()
            logger.info(f"Cleaned up {removed_count} stale cache entries")

        return removed_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        total_files = len(self._file_metadata)
        total_symbols = sum(len(symbols) for symbols in self._symbols_cache.values())

        # Calculate cache size
        cache_size = 0
        if self.metadata_file.exists():
            cache_size += self.metadata_file.stat().st_size
        if self.symbols_cache_file.exists():
            cache_size += self.symbols_cache_file.stat().st_size

        return {
            "cached_files": total_files,
            "total_symbols": total_symbols,
            "cache_size_bytes": cache_size,
            "cache_size_mb": cache_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._file_metadata.clear()
        self._symbols_cache.clear()

        # Remove cache files
        for cache_file in [self.metadata_file, self.symbols_cache_file]:
            if cache_file.exists():
                cache_file.unlink()

        logger.info("Cleared all analysis cache")

    def finalize(self) -> None:
        """Save cache before shutdown."""
        self._save_cache()


class IncrementalAnalyzer:
    """Enhanced incremental analysis engine for repositories."""

    def __init__(self, repo_path: Path, cache_dir: Optional[Path] = None):
        self.repo_path = repo_path
        self.cache = FileAnalysisCache(repo_path, cache_dir)

        # Performance tracking
        self._stats = {"files_analyzed": 0, "files_cached": 0, "cache_hits": 0, "cache_misses": 0, "analysis_time": 0.0}

    def analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single file with caching."""
        start_time = time.time()

        # Try cache first
        cached_symbols = self.cache.get_cached_symbols(file_path)
        if cached_symbols is not None:
            self._stats["cache_hits"] += 1
            logger.debug(f"Cache hit for {file_path}")
            return cached_symbols

        # Cache miss - analyze file
        self._stats["cache_misses"] += 1
        self._stats["files_analyzed"] += 1

        symbols = self._extract_symbols_from_file(file_path)

        # Cache the results
        self.cache.cache_symbols(file_path, symbols)

        analysis_time = time.time() - start_time
        self._stats["analysis_time"] += analysis_time

        logger.debug(f"Analyzed {file_path} in {analysis_time:.3f}s, found {len(symbols)} symbols")
        return symbols

    def _extract_symbols_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract symbols from a file using tree-sitter."""
        ext = file_path.suffix.lower()

        if ext not in TreeSitterSymbolExtractor.LANGUAGES:
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()

            symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)

            # Add file path to each symbol
            for symbol in symbols:
                symbol["file"] = str(file_path.relative_to(self.repo_path))

            return symbols

        except Exception as e:
            logger.warning(f"Failed to extract symbols from {file_path}: {e}")
            return []

    def analyze_changed_files(self, file_paths: List[Path]) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze only files that have changed."""
        results = {}
        changed_files = []

        # Filter to only changed files
        for file_path in file_paths:
            if self.cache.is_file_changed(file_path):
                changed_files.append(file_path)
            else:
                # Use cached results
                cached_symbols = self.cache.get_cached_symbols(file_path)
                if cached_symbols:
                    results[str(file_path.relative_to(self.repo_path))] = cached_symbols
                    self._stats["cache_hits"] += 1

        logger.info(
            f"Analyzing {len(changed_files)} changed files (skipping {len(file_paths) - len(changed_files)} cached)"
        )

        # Analyze changed files
        for file_path in changed_files:
            symbols = self.analyze_file(file_path)
            results[str(file_path.relative_to(self.repo_path))] = symbols

        return results

    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_stats = self.cache.get_cache_stats()

        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = (self._stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self._stats,
            "cache_hit_rate": f"{hit_rate:.1f}%",
            "avg_analysis_time": self._stats["analysis_time"] / max(self._stats["files_analyzed"], 1),
            **cache_stats,
        }

    def cleanup_cache(self) -> None:
        """Clean up stale cache entries."""
        self.cache.cleanup_stale_entries()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear_cache()
        self._stats = {"files_analyzed": 0, "files_cached": 0, "cache_hits": 0, "cache_misses": 0, "analysis_time": 0.0}

    def finalize(self) -> None:
        """Finalize analysis and save cache."""
        self.cache.finalize()

        # Log final stats
        stats = self.get_analysis_stats()
        logger.info(
            f"Analysis complete: {stats['cache_hit_rate']} cache hit rate, "
            f"{stats['files_analyzed']} files analyzed in {stats['analysis_time']:.2f}s"
        )
