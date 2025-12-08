from __future__ import annotations

import logging
import os
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional

import pathspec

# Rust-based file walker via ignore-python (47x faster than pure Python)
from ignore import WalkBuilder

from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class RepoMapper:
    """
    Maps the structure and symbols of a code repository.
    Implements incremental scanning and robust symbol extraction.
    Supports multi-language via tree-sitter queries.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path: Path = Path(repo_path)
        self._symbol_map: Dict[str, Dict[str, Any]] = {}  # file -> {mtime, symbols}
        self._file_tree: Optional[List[Dict[str, Any]]] = None
        self._gitignore_spec = self._load_gitignore()
        # Cache string versions for faster path operations
        self._repo_path_str: str = str(self.repo_path)
        self._repo_path_resolved_str: Optional[str] = None

    def _load_gitignore(self):
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                return pathspec.PathSpec.from_lines("gitwildmatch", f)
        return None

    def _should_ignore(self, file: Path) -> bool:
        # Fast check for .git in path using string operations
        file_str = str(file)
        if "/.git/" in file_str or file_str.endswith("/.git"):
            return True

        # Fast relative path calculation using string operations
        if file_str.startswith(self._repo_path_str):
            # Direct prefix match - strip repo path and leading slash
            rel_path = file_str[len(self._repo_path_str) :].lstrip(os.sep)
        else:
            # Fallback: try with resolved paths (handles symlinks)
            if self._repo_path_resolved_str is None:
                self._repo_path_resolved_str = str(self.repo_path.resolve())
            resolved_str = str(file.resolve())
            if resolved_str.startswith(self._repo_path_resolved_str):
                rel_path = resolved_str[len(self._repo_path_resolved_str) :].lstrip(os.sep)
            else:
                # File is outside repo bounds - ignore it
                return True

        # Check gitignore patterns
        if self._gitignore_spec and self._gitignore_spec.match_file(rel_path):
            return True
        return False

    def _subpaths_for_path(self, rel_path: str) -> List[str]:
        """
        Return every cumulative sub-path in a relative path.

        >>> self._subpaths_for_path("foo/bar/baz")
        ['foo', 'foo/bar', 'foo/bar/baz']
        """
        pure_rel_path = PurePath(rel_path)
        sub_paths: List[str] = []
        for i in range(1, len(pure_rel_path.parts) + 1):
            sub_paths.append(str(PurePath(*pure_rel_path.parts[:i])))
        return sub_paths

    def _get_file_tree_rust(self, start_dir: Path, subpath: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fast file tree using Rust ignore crate (23x faster than Python).
        Properly handles .gitignore, .ignore, and nested ignore files.
        """
        tree: List[Dict[str, Any]] = []
        tracked_tree_paths: set[str] = set()
        repo_path_str = str(self.repo_path)

        # Build walker with gitignore support, include hidden files
        walker = WalkBuilder(start_dir).hidden(False).git_ignore(True).git_exclude(True).build()

        for entry in walker:
            path = entry.path()
            if not path.is_file():
                continue

            # Get path relative to repo root
            path_str = str(path)
            if path_str.startswith(repo_path_str):
                file_path = path_str[len(repo_path_str) :].lstrip(os.sep)
            else:
                continue

            # Skip .git directory
            if "/.git/" in path_str or "/.git" == path_str[-5:]:
                continue

            parent_path = str(Path(file_path).parent) if Path(file_path).parent != Path(".") else ""

            # Add parent directories
            if parent_path:
                for subdir in self._subpaths_for_path(parent_path):
                    if subdir not in tracked_tree_paths:
                        tracked_tree_paths.add(subdir)
                        tree.append(
                            {
                                "path": subdir,
                                "is_dir": True,
                                "name": PurePath(subdir).name,
                                "size": 0,
                            }
                        )

            try:
                size = path.stat().st_size
            except OSError:
                size = 0

            tree.append(
                {
                    "path": file_path,
                    "is_dir": False,
                    "name": path.name,
                    "size": size,
                }
            )

        return tree

    def _get_file_tree_python(self, start_dir: Path, subpath: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Python fallback for file tree (used when ignore-python not installed).
        """
        tree: List[Dict[str, Any]] = []
        tracked_tree_paths: set[str] = set()

        for path in start_dir.rglob("*"):
            if path.is_dir() or self._should_ignore(path):
                continue

            # Calculate relative path from the starting directory
            if subpath:
                rel_to_subpath = path.relative_to(start_dir)
                file_path = str(Path(subpath) / rel_to_subpath)
            else:
                file_path = str(path.relative_to(self.repo_path))

            parent_path = str(Path(file_path).parent) if Path(file_path).parent != Path(".") else ""

            # Add parent directories
            if parent_path:
                for subdir in self._subpaths_for_path(parent_path):
                    if subdir not in tracked_tree_paths:
                        tracked_tree_paths.add(subdir)
                        tree.append(
                            {
                                "path": subdir,
                                "is_dir": True,
                                "name": PurePath(subdir).name,
                                "size": 0,
                            }
                        )

            tree.append(
                {
                    "path": file_path,
                    "is_dir": False,
                    "name": path.name,
                    "size": path.stat().st_size,
                }
            )

        return tree

    def get_file_tree(self, subpath: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts representing files in the repo or a subdirectory.
        Each dict contains: path, size, mtime, is_file.

        Uses Rust-based walker when available (23x faster), falls back to Python.

        Args:
            subpath: Optional subdirectory path relative to repo root.
                    If None, returns entire repo tree. If specified, returns
                    tree starting from that subdirectory.
        """
        # Don't use cache if subpath is specified (different from default behavior)
        if subpath is not None or self._file_tree is None:
            # Determine the starting directory
            if subpath:
                from .utils import validate_relative_path

                start_dir = validate_relative_path(self.repo_path, subpath)
                if not start_dir.exists() or not start_dir.is_dir():
                    raise ValueError(f"Subpath '{subpath}' does not exist or is not a directory")
            else:
                start_dir = self.repo_path

            # Use Rust walker (47x faster than pure Python)
            tree = self._get_file_tree_rust(start_dir, subpath)

            # Only cache if using default behavior (no subpath)
            if subpath is None:
                self._file_tree = tree
            return tree

        return self._file_tree

    def scan_repo(self) -> None:
        """
        Scan all supported files and update symbol map incrementally.
        Uses mtime to avoid redundant parsing.
        """
        for file in self.repo_path.rglob("*"):
            if not file.is_file():
                continue
            if self._should_ignore(file):
                continue
            ext = file.suffix.lower()
            if ext in TreeSitterSymbolExtractor.LANGUAGES or ext == ".py":
                self._scan_file(file)

    def _scan_file(self, file: Path) -> None:
        try:
            mtime: float = os.path.getmtime(file)
            entry = self._symbol_map.get(str(file))
            if entry and entry["mtime"] == mtime:
                return  # No change
            symbols: List[Dict[str, Any]] = self._extract_symbols_from_file(file)
            self._symbol_map[str(file)] = {"mtime": mtime, "symbols": symbols}
        except Exception as e:
            logging.warning(f"Error scanning file {file}: {e}", exc_info=True)

    def _extract_symbols_from_file(self, file: Path) -> List[Dict[str, Any]]:
        ext = file.suffix.lower()
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception as e:
            logging.warning(f"Could not read file {file} for symbol extraction: {e}")
            return []
        if ext in TreeSitterSymbolExtractor.LANGUAGES:
            try:
                symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
                for s in symbols:
                    s["file"] = str(file)
                return symbols
            except Exception as e:
                logging.warning(f"Error extracting symbols from {file} using TreeSitter: {e}")
                return []
        return []

    def extract_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts symbols from a single specified file on demand.
        This method performs a fresh extraction and does not use the internal cache.
        For cached or repository-wide symbols, use scan_repo() and get_repo_map().

        Args:
            file_path (str): The relative path to the file from the repository root.

        Returns:
            List[Dict[str, Any]]: A list of symbols extracted from the file.
                                 Returns an empty list if the file is ignored,
                                 not supported, or if an error occurs.
        """
        from .utils import validate_relative_path

        abs_path = validate_relative_path(self.repo_path, file_path)
        if self._should_ignore(abs_path):
            logging.debug(f"Ignoring file specified in extract_symbols: {file_path}")
            return []

        ext = abs_path.suffix.lower()
        if ext in TreeSitterSymbolExtractor.LANGUAGES:
            try:
                code = abs_path.read_text(encoding="utf-8", errors="ignore")
                symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
                for s in symbols:
                    s["file"] = str(abs_path.relative_to(self.repo_path))
                return symbols
            except Exception as e:
                logging.warning(f"Error extracting symbols from {abs_path} in extract_symbols: {e}")
                return []
        else:
            logging.debug(f"File type {ext} not supported for symbol extraction: {file_path}")
            return []

    def get_repo_map(self) -> Dict[str, Any]:
        """
        Returns a dict with file tree and a mapping of files to their symbols.
        Ensures the symbol map is up-to-date by scanning the repo and refreshes the file tree.
        """
        self.scan_repo()
        self._file_tree = None
        return {"file_tree": self.get_file_tree(), "symbols": {k: v["symbols"] for k, v in self._symbol_map.items()}}

    # --- Helper methods ---
