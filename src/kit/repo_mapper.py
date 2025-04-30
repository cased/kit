from __future__ import annotations
import ast
import os
import time
from pathlib import Path
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
        gitignore_path = self.repo_path / '.gitignore'
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                return pathspec.PathSpec.from_lines('gitwildmatch', f)
        return None

    def _should_ignore(self, file: Path) -> bool:
        rel_path = str(file.relative_to(self.repo_path))
        # Always ignore .git and its contents
        if '.git' in file.parts:
            return True
        # Ignore files matching .gitignore
        if self._gitignore_spec and self._gitignore_spec.match_file(rel_path):
            return True
        return False

    def get_file_tree(self) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts representing all files in the repo.
        Each dict contains: path, size, mtime, is_file.
        """
        if self._file_tree is not None:
            return self._file_tree
        tree = []
        for path in self.repo_path.rglob("*"):
            if self._should_ignore(path):
                continue
            tree.append({
                "path": str(path.relative_to(self.repo_path)),
                "is_dir": path.is_dir(),
                "name": path.name,
                "size": path.stat().st_size if path.is_file() else 0
            })
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
            # Optionally log error
            pass

    def _extract_symbols_from_file(self, file: Path) -> List[Dict[str, Any]]:
        ext = file.suffix.lower()
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception:
            return []
        if ext in TreeSitterSymbolExtractor.LANGUAGES:
            try:
                symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
                for s in symbols:
                    s["file"] = str(file)
                return symbols
            except Exception:
                return []
        return []

    def extract_symbols(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        if file_path is not None:
            ext = Path(file_path).suffix.lower()
            abs_path = self.repo_path / file_path
            if self._should_ignore(abs_path):
                return []
            # Use TreeSitterSymbolExtractor for all supported languages, including Python
            if ext in TreeSitterSymbolExtractor.LANGUAGES:
                return TreeSitterSymbolExtractor.extract_symbols(ext, abs_path.read_text(encoding="utf-8", errors="ignore"))
            else:
                return []
        # If no file_path, extract all symbols in repo
        symbols = []
        for file in self.repo_path.rglob("*"):
            if self._should_ignore(file):
                continue
            ext = file.suffix.lower()
            # Use TreeSitterSymbolExtractor for all supported languages, including Python
            if ext in TreeSitterSymbolExtractor.LANGUAGES:
                symbols.extend(TreeSitterSymbolExtractor.extract_symbols(ext, file.read_text(encoding="utf-8", errors="ignore")))
        return symbols

    def get_repo_map(self) -> Dict[str, Any]:
        """
        Returns a dict with file tree and a mapping of files to their symbols.
        """
        self.scan_repo()
        return {
            "file_tree": self.get_file_tree(),
            "symbols": {k: v["symbols"] for k, v in self._symbol_map.items()}
        }

    # --- Helper methods ---
    def _should_ignore(self, path: Path) -> bool:
        if not path.is_file():
            return True
        rel_path = str(path.relative_to(self.repo_path))
        # Always ignore .git and its contents
        if '.git' in path.parts:
            return True
        # Ignore files matching .gitignore
        if self._gitignore_spec and self._gitignore_spec.match_file(rel_path):
            return True
        return False
