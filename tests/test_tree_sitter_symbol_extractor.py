from unittest.mock import MagicMock, patch

import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class TestSymbolTypeProcessing:
    """Tests for symbol type processing to ensure correct prefix removal."""

    def test_symbol_type_from_fallback_label_function(self):
        """Test that @function correctly becomes 'function' and not 'unction'."""
        # Mock the necessary components
        mock_query = MagicMock()
        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_node = MagicMock()

        # Set up the mock node
        mock_node.text = b"testFunction"
        mock_node.start_point = (10, 0)
        mock_node.end_point = (15, 0)
        mock_node.start_byte = 100
        mock_node.end_byte = 200

        # Set up the captures that would trigger the fallback path
        captures = {"@function": mock_node}
        matches = [(0, captures)]

        mock_query.matches.return_value = matches
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        source_code = "def testFunction():\n    pass"

        # Use patch to avoid global mocking pollution
        with (
            patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query),
            patch.object(TreeSitterSymbolExtractor, "get_parser", return_value=mock_parser),
        ):
            # Call the method
            symbols = TreeSitterSymbolExtractor.extract_symbols(".py", source_code)

            # Verify the result
            assert len(symbols) == 1
            assert symbols[0]["type"] == "function"  # Should be "function", not "unction"
            assert symbols[0]["name"] == "testFunction"

    def test_symbol_type_from_fallback_label_class(self):
        """Test that @class correctly becomes 'class'."""
        # Mock similar to above but with @class
        mock_query = MagicMock()
        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_node = MagicMock()

        mock_node.text = b"TestClass"
        mock_node.start_point = (5, 0)
        mock_node.end_point = (10, 0)
        mock_node.start_byte = 50
        mock_node.end_byte = 150

        captures = {"@class": mock_node}
        matches = [(0, captures)]

        mock_query.matches.return_value = matches
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        source_code = "class TestClass:\n    pass"

        with (
            patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query),
            patch.object(TreeSitterSymbolExtractor, "get_parser", return_value=mock_parser),
        ):
            symbols = TreeSitterSymbolExtractor.extract_symbols(".py", source_code)

            assert len(symbols) == 1
            assert symbols[0]["type"] == "class"
            assert symbols[0]["name"] == "TestClass"

    def test_symbol_type_from_definition_capture(self):
        """Test that definition.function correctly becomes 'function'."""
        mock_query = MagicMock()
        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_name_node = MagicMock()
        mock_def_node = MagicMock()

        mock_name_node.text = b"myFunction"
        mock_name_node.start_point = (3, 0)
        mock_name_node.end_point = (3, 10)

        mock_def_node.text = b"def myFunction():\n    return 42"
        mock_def_node.start_point = (3, 0)
        mock_def_node.end_point = (4, 14)
        mock_def_node.start_byte = 30
        mock_def_node.end_byte = 65

        captures = {"name": mock_name_node, "definition.function": mock_def_node}
        matches = [(0, captures)]

        mock_query.matches.return_value = matches
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        source_code = "def myFunction():\n    return 42"

        with (
            patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query),
            patch.object(TreeSitterSymbolExtractor, "get_parser", return_value=mock_parser),
        ):
            symbols = TreeSitterSymbolExtractor.extract_symbols(".py", source_code)

            assert len(symbols) == 1
            assert symbols[0]["type"] == "function"  # Should correctly extract "function" from "definition.function"
            assert symbols[0]["name"] == "myFunction"

    def test_removeprefix_behavior_verification(self):
        """Test that our fix correctly handles the prefix removal."""
        # Test the specific case that was failing
        test_label = "@function"

        # Old buggy behavior would be:
        # "@function".lstrip("definition.") -> "@unction" (removes 'f')
        # "@unction".lstrip("@") -> "unction"

        # New correct behavior:
        result = test_label.removeprefix("definition.").removeprefix("@")
        assert result == "function"

        # Test with definition.function
        test_label2 = "definition.function"
        result2 = test_label2.removeprefix("definition.").removeprefix("@")
        assert result2 == "function"

        # Test edge case where definition. is not at start
        test_label3 = "not_definition.function"
        result3 = test_label3.removeprefix("definition.").removeprefix("@")
        assert result3 == "not_definition.function"  # Should remain unchanged


class TestDartSupport:
    """Tests for Dart language support."""

    def test_dart_basic_symbols(self):
        """Test that Dart symbols are extracted correctly."""
        dart_code = """
class Calculator {
  int add(int a, int b) {
    return a + b;
  }
}

void main() {
  print('Hello, Dart!');
}

enum Status {
  pending,
  completed
}
"""

        symbols = TreeSitterSymbolExtractor.extract_symbols(".dart", dart_code)

        # Should extract class, function, and enum
        assert len(symbols) >= 3

        symbol_types = {s["type"] for s in symbols}
        symbol_names = {s["name"] for s in symbols}

        assert "class" in symbol_types
        assert "function" in symbol_types
        assert "enum" in symbol_types

        assert "Calculator" in symbol_names
        assert "add" in symbol_names
        assert "main" in symbol_names
        assert "Status" in symbol_names

    def test_dart_in_supported_languages(self):
        """Test that Dart is included in supported languages."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()
        assert "dart" in supported
        assert ".dart" in supported["dart"]


class TestZigSupport:
    """Tests for Zig language support."""

    def test_zig_basic_symbols(self):
        """Test that Zig symbols are extracted correctly."""
        zig_code = """
const std = @import("std");

pub fn add(a: i32, b: i32) i32 {
    return a + b;
}

pub const Point = struct {
    x: i32,
    pub fn length(self: Point) i32 {
        return self.x;
    }
};

pub const Color = enum { Red, Green, Blue };

pub const Value = union(enum) {
    int: i32,
    float: f32,
};
"""

        parser = TreeSitterSymbolExtractor.get_parser(".zig")
        query = TreeSitterSymbolExtractor.get_query(".zig")
        if not parser or not query:
            pytest.skip("Zig tree-sitter grammar not available")

        symbols = TreeSitterSymbolExtractor.extract_symbols(".zig", zig_code)

        assert len(symbols) >= 5

        symbol_types = {s["type"] for s in symbols}
        symbol_names = {s["name"] for s in symbols}

        for expected_type in {"function", "struct", "enum", "union"}:
            assert expected_type in symbol_types

        for expected_name in {"add", "length", "Point", "Color", "Value"}:
            assert expected_name in symbol_names

    def test_zig_in_supported_languages(self):
        """Ensure Zig is listed as a supported language."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()
        assert "zig" in supported
        assert ".zig" in supported["zig"]
