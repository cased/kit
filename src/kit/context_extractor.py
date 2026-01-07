from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class ContextExtractor:
    """
    Extracts context from source code files for chunking, search, and LLM workflows.
    Supports chunking by lines, symbols, and function/class scope.
    """

    # LRU-style cache for file contents: path -> (mtime, content, lines)
    # Avoids re-reading the same file multiple times across method calls
    _file_cache: ClassVar[Dict[str, Tuple[float, str, List[str]]]] = {}
    _cache_max_size: ClassVar[int] = 100  # Max files to cache

    def __init__(self, repo_path: str) -> None:
        self.repo_path: Path = Path(repo_path)

    def _read_file_cached(self, abs_path: Path) -> Tuple[str, List[str]]:
        """Read file content with mtime-based caching.

        Returns (content, lines) tuple. Uses cache if file hasn't changed.
        This avoids redundant disk reads when multiple methods access the same file.
        """
        path_str = str(abs_path)
        try:
            current_mtime = os.path.getmtime(abs_path)
        except OSError:
            # File doesn't exist or can't be accessed
            raise FileNotFoundError(f"Cannot access file: {abs_path}")

        # Check cache
        if path_str in self._file_cache:
            cached_mtime, cached_content, cached_lines = self._file_cache[path_str]
            if cached_mtime == current_mtime:
                return cached_content, cached_lines

        # Read file
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        lines = content.splitlines(keepends=True)

        # Evict oldest entries if cache is full (simple FIFO eviction)
        if len(self._file_cache) >= self._cache_max_size:
            # Remove first 10% of entries
            keys_to_remove = list(self._file_cache.keys())[: self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._file_cache[key]

        # Cache the result
        self._file_cache[path_str] = (current_mtime, content, lines)
        return content, lines

    def invalidate_cache(self, file_path: Optional[str] = None) -> None:
        """Invalidate file cache.

        Args:
            file_path: Specific file to invalidate, or None to clear entire cache.
        """
        if file_path is None:
            self._file_cache.clear()
        elif file_path in self._file_cache:
            del self._file_cache[file_path]

    def chunk_file_by_lines(self, file_path: str, max_lines: int = 50) -> List[str]:
        """
        Chunk file into blocks of at most max_lines lines.
        """
        from .utils import validate_relative_path

        abs_path = validate_relative_path(self.repo_path, file_path)
        try:
            _, all_lines = self._read_file_cached(abs_path)
        except (FileNotFoundError, OSError):
            return []

        chunks: List[str] = []
        for i in range(0, len(all_lines), max_lines):
            chunk_lines = all_lines[i : i + max_lines]
            chunks.append("".join(chunk_lines))
        return chunks

    def chunk_file_by_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        from .utils import validate_relative_path

        ext = Path(file_path).suffix.lower()
        abs_path = validate_relative_path(self.repo_path, file_path)
        try:
            code, _ = self._read_file_cached(abs_path)
        except (FileNotFoundError, OSError):
            return []
        if ext in TreeSitterSymbolExtractor.LANGUAGES:
            return TreeSitterSymbolExtractor.extract_symbols(ext, code)
        return []

    def extract_context_around_line(self, file_path: str, line: int) -> Optional[Dict[str, Any]]:
        """
        Extracts the function/class (or code block) containing the given line.
        Returns a dict with type, name, and code.
        """
        from .utils import validate_relative_path

        ext = Path(file_path).suffix.lower()
        abs_path = validate_relative_path(self.repo_path, file_path)
        try:
            code, all_lines = self._read_file_cached(abs_path)
        except (FileNotFoundError, OSError):
            return None
        if ext == ".py":
            try:
                tree = ast.parse(code, filename=str(abs_path))
                best_node = None
                min_length = float("inf")

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        start_lineno = node.lineno
                        end_lineno = getattr(node, "end_lineno", start_lineno)

                        if start_lineno is not None and end_lineno is not None and start_lineno <= line <= end_lineno:
                            current_length = end_lineno - start_lineno
                            if current_length < min_length:
                                min_length = current_length
                                best_node = node
                            # If lengths are equal, prefer functions/methods over classes if one contains the other
                            elif (
                                current_length == min_length
                                and isinstance(node, ast.FunctionDef)
                                and isinstance(best_node, ast.ClassDef)
                            ):
                                # This heuristic helps if a class and a method start on the same line (unlikely for typical formatting)
                                # A more robust check would be full containment, but this is simpler.
                                best_node = node

                if best_node:
                    start = best_node.lineno
                    end = getattr(best_node, "end_lineno", start)
                    code_block = "".join(all_lines[start - 1 : end])
                    return {
                        "type": "function" if isinstance(best_node, ast.FunctionDef) else "class",
                        "name": best_node.name,
                        "code": code_block,
                    }
            except Exception:  # If AST parsing fails, fall through to generic line-based chunking
                pass

        # For other languages or Python AST failure: fallback to chunk by lines
        context_delta = 10
        # `line` is 1-indexed, list `all_lines` is 0-indexed
        target_line_0_indexed = line - 1

        if not (0 <= target_line_0_indexed < len(all_lines)):
            return None  # Line number out of bounds

        start_chunk_0_indexed = max(0, target_line_0_indexed - context_delta)
        end_chunk_0_indexed = min(len(all_lines), target_line_0_indexed + context_delta + 1)

        code_block_chunk = "".join(all_lines[start_chunk_0_indexed:end_chunk_0_indexed])

        return {
            "type": "code_chunk",
            "name": f"{Path(file_path).name}:{line}",  # Use Path(file_path).name to get filename
            "code": code_block_chunk,
        }
