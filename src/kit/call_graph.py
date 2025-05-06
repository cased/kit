"""Basic static call-graph builder for Python code in a repo.

This is intentionally minimal: we look at AST `Call` nodes and map them to
symbol names that appear *anywhere* in the repo.  It does **not** attempt to
resolve imports or fully-qualified names – but is good enough to catch most
in-repo function calls for context-building purposes.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

from .repo_mapper import RepoMapper


class CallGraphBuilder:
    """Generate a file-level call graph (who *calls* which files)."""

    def __init__(self, repo_path: str, repo_map: Dict):
        self.repo_path = Path(repo_path)
        self.repo_map = repo_map
        # Map symbol name -> set(files defining it)
        self._symbol_index: Dict[str, Set[str]] = {}
        self._build_symbol_index()

    def _build_symbol_index(self) -> None:
        for file, symbols in self.repo_map.get("symbols", {}).items():
            for sym in symbols:
                name = sym.get("name")
                if not name:
                    continue
                self._symbol_index.setdefault(name, set()).add(file)

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    def build_call_graph(self) -> Dict[str, Set[str]]:
        """Return mapping *caller_file* -> set[*callee_file*]."""
        graph: Dict[str, Set[str]] = {}
        for file in self.repo_map.get("symbols", {}).keys():
            abs_path = self.repo_path / file
            deps = self._extract_called_files(abs_path)
            graph[file] = deps
        return graph

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_called_files(self, abs_path: Path) -> Set[str]:
        if not abs_path.exists() or abs_path.suffix != ".py":
            return set()
        try:
            tree = ast.parse(abs_path.read_text(encoding="utf-8"))
        except Exception:
            return set()

        called_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name: str | None = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name:
                    called_names.add(name)

        deps: Set[str] = set()
        for cname in called_names:
            deps.update(self._symbol_index.get(cname, set()))
        # Exclude self-file to avoid self loops
        rel_path = str(abs_path.relative_to(self.repo_path))
        deps.discard(rel_path)
        return deps
