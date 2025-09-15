"""Tests for tree-sitter API compatibility (0.25.1+ with QueryCursor)."""

import pytest
import tree_sitter
from tree_sitter_language_pack import get_language, get_parser

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


def test_tree_sitter_version():
    """Verify we're using tree-sitter >= 0.25.1."""
    # tree-sitter 0.25.1 should have QueryCursor that requires query parameter
    with pytest.raises(TypeError, match="missing required argument"):
        tree_sitter.QueryCursor()


def test_query_cursor_api():
    """Test that the new QueryCursor API works correctly."""
    parser = get_parser("python")
    language = get_language("python")

    code = """
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
"""

    tree = parser.parse(bytes(code, "utf8"))
    root = tree.root_node

    # Create a simple query
    query_text = "(function_definition name: (identifier) @name)"
    query = tree_sitter.Query(language, query_text)

    # Test that QueryCursor with query works
    cursor = tree_sitter.QueryCursor(query)
    assert cursor is not None

    # Test that matches() works
    matches = cursor.matches(root)
    assert isinstance(matches, list)
    assert len(matches) == 2  # hello and method

    # Verify match structure
    for match_idx, match in enumerate(matches):
        pattern_idx, captures = match
        assert isinstance(pattern_idx, int)
        assert isinstance(captures, dict)
        assert "name" in captures
        assert isinstance(captures["name"], list)
        assert len(captures["name"]) > 0


def test_extract_symbols_with_new_api():
    """Test that TreeSitterSymbolExtractor works with the new API."""
    python_code = """
def foo():
    pass

class Bar:
    def baz(self):
        return 42
"""

    symbols = TreeSitterSymbolExtractor.extract_symbols(".py", python_code)

    assert len(symbols) == 3
    symbol_names = {s["name"] for s in symbols}
    assert symbol_names == {"foo", "Bar", "baz"}

    symbol_types = {s["type"] for s in symbols}
    assert "function" in symbol_types
    assert "class" in symbol_types
    assert "method" in symbol_types


def test_extract_symbols_typescript():
    """Test TypeScript symbol extraction with new API."""
    ts_code = """
interface User {
    id: number;
    name: string;
}

class UserService {
    getUser(id: number): User {
        return { id, name: "Test" };
    }
}

export function processUser(user: User): void {
    console.log(user.name);
}
"""

    symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", ts_code)

    assert len(symbols) == 4
    symbol_names = {s["name"] for s in symbols}
    assert symbol_names == {"User", "UserService", "getUser", "processUser"}

    # Verify types
    for symbol in symbols:
        if symbol["name"] == "User":
            assert symbol["type"] == "interface"
        elif symbol["name"] == "UserService":
            assert symbol["type"] == "class"
        elif symbol["name"] == "getUser":
            assert symbol["type"] == "method"
        elif symbol["name"] == "processUser":
            assert symbol["type"] == "function"


def test_multiple_languages():
    """Test that multiple languages work with the new API."""
    test_cases = [
        (".go", 'func main() { fmt.Println("Hello") }', 1, {"main"}),
        (".rs", "fn calculate(x: i32) -> i32 { x * 2 }", 1, {"calculate"}),
        (".java", "public class Test { public void run() {} }", 2, {"Test", "run"}),
        (".rb", 'def greeting\n  puts "hello"\nend', 1, {"greeting"}),
    ]

    for ext, code, expected_count, expected_names in test_cases:
        symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
        assert len(symbols) == expected_count, f"Failed for {ext}"
        symbol_names = {s["name"] for s in symbols}
        assert symbol_names == expected_names, f"Failed for {ext}"
