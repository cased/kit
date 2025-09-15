"""AST-based code search using tree-sitter."""

import re
from pathlib import Path
from typing import Any, Dict, List, cast

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

from .tree_sitter_symbol_extractor import LANGUAGES


class ASTPattern:
    """Represents an AST search pattern."""

    def __init__(self, pattern: str, mode: str = "simple"):
        self.pattern = pattern
        self.mode = mode
        self._compile()

    def _compile(self):
        """Compile the pattern based on mode."""
        if self.mode == "simple":
            # Convert simple patterns to search criteria
            # e.g., "async def $NAME" -> look for async function_definition nodes
            self.is_async = "async" in self.pattern
            self.is_def = "def" in self.pattern
            self.is_class = "class" in self.pattern
            self.is_try = "try:" in self.pattern

            # Extract wildcards like $NAME, $ARGS, etc.
            self.wildcards = re.findall(r"\$[A-Z_]+", self.pattern)

        elif self.mode == "pattern":
            # Parse pattern-based query
            # {"type": "function_definition", "async": true}
            import json

            try:
                self.criteria = json.loads(self.pattern)
            except (json.JSONDecodeError, ValueError):
                self.criteria = {"text_match": self.pattern}

        elif self.mode == "query":
            # Tree-sitter query language - keep as is
            self.ts_query = self.pattern

    def matches(self, node: Node, source: bytes) -> bool:
        """Check if a node matches this pattern."""
        if self.mode == "simple":
            return self._matches_simple(node, source)
        elif self.mode == "pattern":
            return self._matches_pattern(node, source)
        elif self.mode == "query":
            # Query mode needs special handling with tree-sitter queries
            return False  # TODO: Implement full query support
        return False

    def _matches_simple(self, node: Node, source: bytes) -> bool:
        """Match using simple pattern syntax."""
        node_type = node.type

        # Check node type
        if self.is_def and node_type != "function_definition":
            return False
        if self.is_class and node_type != "class_definition":
            return False
        if self.is_try and node_type != "try_statement":
            return False

        # Check async modifier
        if self.is_async:
            # Look for async keyword in function definitions
            if node_type == "function_definition":
                for child in node.children:
                    if child.type == "async":
                        break
                else:
                    return False  # No async keyword found

        # If we made it here, basic criteria match
        return True

    def _matches_pattern(self, node: Node, source: bytes) -> bool:
        """Match using pattern criteria."""
        if "type" in self.criteria:
            if node.type != self.criteria["type"]:
                return False

        if "async" in self.criteria:
            has_async = any(child.type == "async" for child in node.children)
            if has_async != self.criteria["async"]:
                return False

        if "text_match" in self.criteria:
            node_text = source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
            if self.criteria["text_match"] not in node_text:
                return False

        return True


class ASTSearcher:
    """AST-based code search engine."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._parsers: Dict[str, Any] = {}

    def search_pattern(
        self, pattern: str, file_pattern: str = "*.py", mode: str = "simple", max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for AST patterns in code.

        Args:
            pattern: The pattern to search for
            file_pattern: Glob pattern for files to search
            mode: Search mode - "simple", "pattern", or "query"
            max_results: Maximum number of results to return

        Returns:
            List of matches with file, line, type, and code information
        """
        ast_pattern = ASTPattern(pattern, mode)
        results: List[Dict[str, Any]] = []

        for file_path in self._get_matching_files(file_pattern):
            if len(results) >= max_results:
                break

            try:
                matches = self._search_file(file_path, ast_pattern)
                for match in matches:
                    results.append(match)
                    if len(results) >= max_results:
                        break
            except Exception:
                # Skip files that can't be parsed
                continue

        return results[:max_results]

    def _get_matching_files(self, pattern: str) -> List[Path]:
        """Get all files matching the given pattern."""
        if "**" in pattern:
            return list(self.repo_path.glob(pattern))
        else:
            return list(self.repo_path.rglob(pattern))

    def _search_file(self, file_path: Path, pattern: ASTPattern) -> List[Dict[str, Any]]:
        """Search a single file for pattern matches."""
        # Determine language from extension
        ext = file_path.suffix
        if ext not in LANGUAGES:
            return []

        language_name = LANGUAGES[ext]

        # Get or create parser
        if language_name not in self._parsers:
            try:
                self._parsers[language_name] = get_parser(cast(Any, language_name))
            except Exception:
                return []

        parser = self._parsers[language_name]

        # Read and parse file
        try:
            source = file_path.read_bytes()
            tree = parser.parse(source)
        except Exception:
            return []

        # Search the tree
        matches: List[Dict[str, Any]] = []
        self._search_node(tree.root_node, source, pattern, file_path, matches)

        return matches

    def _search_node(
        self, node: Node, source: bytes, pattern: ASTPattern, file_path: Path, matches: List[Dict[str, Any]]
    ):
        """Recursively search a node and its children."""
        # Check if this node matches
        if pattern.matches(node, source):
            # Extract match information
            start_line = node.start_point[0] + 1  # Convert to 1-based
            start_col = node.start_point[1]

            # Get node text
            node_text = source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

            # Get context (parent node if available)
            context = self._get_context(node, source)

            matches.append(
                {
                    "file": str(file_path.relative_to(self.repo_path)),
                    "line": start_line,
                    "column": start_col,
                    "type": node.type,
                    "text": node_text[:500],  # Limit text size
                    "context": context,
                }
            )

        # Search children
        for child in node.children:
            self._search_node(child, source, pattern, file_path, matches)

    def _get_context(self, node: Node, source: bytes) -> Dict[str, Any]:
        """Get context information for a match."""
        context = {"node_type": node.type}

        # Find parent function or class
        parent = node.parent
        while parent:
            if parent.type in ["function_definition", "class_definition"]:
                # Get the name of the parent
                for child in parent.children:
                    if child.type == "identifier":
                        name = source[child.start_byte : child.end_byte].decode("utf-8", errors="ignore")
                        context[f"parent_{parent.type}"] = name
                        break
                break
            parent = parent.parent

        return context


def find_common_patterns(repo_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Find common code patterns that might need attention.

    Returns a dict of pattern_name -> list of matches
    """
    searcher = ASTSearcher(repo_path)
    patterns = {}

    # Find async functions
    patterns["async_functions"] = searcher.search_pattern(
        "async def", file_pattern="**/*.py", mode="simple", max_results=20
    )

    # Find try blocks without finally
    patterns["try_without_finally"] = [
        match
        for match in searcher.search_pattern(
            '{"type": "try_statement"}', file_pattern="**/*.py", mode="pattern", max_results=50
        )
        if "finally" not in match["text"]
    ]

    # Find TODO comments
    patterns["todos"] = searcher.search_pattern(
        '{"text_match": "TODO"}', file_pattern="**/*.py", mode="pattern", max_results=20
    )

    return patterns
