from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class ContextExtractor:
    """
    Extracts context from source code files for chunking, search, and LLM workflows.
    Supports chunking by lines, symbols, and function/class scope.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path: Path = Path(repo_path)

    def chunk_file_by_lines(self, file_path: str, max_lines: int = 50) -> List[str]:
        """
        Chunk file into blocks of at most max_lines lines.
        """
        chunks: List[str] = []
        with open(self.repo_path / file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines: List[str] = []
            for i, line in enumerate(f, 1):
                lines.append(line)
                if i % max_lines == 0:
                    chunks.append("".join(lines))
                    lines = []
            if lines:
                chunks.append("".join(lines))
        return chunks

    def chunk_file_by_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        ext = Path(file_path).suffix.lower()
        abs_path = self.repo_path / file_path
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception:
            return []
        if ext in TreeSitterSymbolExtractor.LANGUAGES:
            return TreeSitterSymbolExtractor.extract_symbols(ext, code)
        return []

    def extract_context_around_line(self, file_path: str, line: int) -> Optional[Dict[str, Any]]:
        """
        Extracts the function/class (or code block) containing the given line.
        Returns a dict with type, name, and code.
        """
        ext = Path(file_path).suffix.lower()
        abs_path = self.repo_path / file_path
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            code = "".join(all_lines)
        except Exception:
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
