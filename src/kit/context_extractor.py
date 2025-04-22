from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import ast
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
                code = f.read()
        except Exception:
            return None
        if ext == ".py":
            try:
                tree = ast.parse(code, filename=str(abs_path))
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        start = node.lineno
                        end = node.end_lineno if hasattr(node, "end_lineno") else start
                        if start is not None and end is not None and start <= line <= end:
                            code_block = "".join(lines[start-1:end])
                            return {
                                "type": "function" if isinstance(node, ast.FunctionDef) else "class",
                                "name": node.name,
                                "code": code_block
                            }
            except Exception:
                return None
        # For other languages: fallback to chunk by lines
        return None
