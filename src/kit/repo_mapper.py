from __future__ import annotations

import logging
import os
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional

import pathspec

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

    def _load_gitignore(self):
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                return pathspec.PathSpec.from_lines("gitwildmatch", f)
        return None

    def _should_ignore(self, file: Path) -> bool:
        rel_path = str(file.relative_to(self.repo_path))
        # Always ignore .git and its contents
        if ".git" in file.parts:
            return True
        # Ignore files matching .gitignore
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

    def get_file_tree(self) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts representing all files in the repo.
        Each dict contains: path, size, mtime, is_file.
        """
        if self._file_tree is not None:
            return self._file_tree
        tree = []
        tracked_tree_paths = set()
        for path in self.repo_path.rglob("*"):
            if path.is_dir() or self._should_ignore(path):
                continue
            file_path = str(path.relative_to(self.repo_path))
            parent_path = str(path.parent.relative_to(self.repo_path))
            for subpath in self._subpaths_for_path(parent_path):
                if subpath not in tracked_tree_paths:
                    tracked_tree_paths.add(subpath)
                    tree.append(
                        {
                            "path": subpath,
                            "is_dir": True,
                            "name": PurePath(subpath).name,
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
        self._file_tree = tree
        return tree

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
        abs_path = self.repo_path / file_path
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
