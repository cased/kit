"""Test tree-sitter API compatibility handling."""

from unittest.mock import Mock, patch

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class TestTreeSitterCompatibility:
    """Test that symbol extraction handles different tree-sitter API versions."""

    def test_matches_api_success(self):
        """Test successful extraction using matches() API."""
        code = "function test() { return 42; }"

        # Mock query with matches() method
        mock_query = Mock()
        mock_query.matches = Mock(
            return_value=[
                (
                    0,
                    {
                        "name": [Mock(text=b"test", start_point=(0, 9), end_point=(0, 13), start_byte=9, end_byte=13)],
                        "definition.function": [
                            Mock(
                                text=b"function test() { return 42; }",
                                start_point=(0, 0),
                                end_point=(0, 30),
                                start_byte=0,
                                end_byte=30,
                            )
                        ],
                    },
                )
            ]
        )

        with patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query):
            with patch.object(TreeSitterSymbolExtractor, "get_parser") as mock_parser:
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.return_value.parse.return_value = mock_tree

                symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)

                assert len(symbols) == 1
                assert symbols[0]["name"] == "test"
                assert symbols[0]["type"] == "function"
                mock_query.matches.assert_called_once()

    def test_captures_api_fallback(self):
        """Test fallback to captures() API when matches() doesn't exist."""
        code = "interface User { id: number; }"

        # Mock query without matches() but with captures()
        mock_query = Mock(spec=["captures", "capture_count"])
        mock_query.captures = Mock(
            return_value=[
                ("name", Mock(text=b"User", start_point=(0, 10), end_point=(0, 14), start_byte=10, end_byte=14)),
                (
                    "definition.interface",
                    Mock(
                        text=b"interface User { id: number; }",
                        start_point=(0, 0),
                        end_point=(0, 30),
                        start_byte=0,
                        end_byte=30,
                    ),
                ),
            ]
        )

        with patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query):
            with patch.object(TreeSitterSymbolExtractor, "get_parser") as mock_parser:
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.return_value.parse.return_value = mock_tree

                symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)

                assert len(symbols) == 1
                assert symbols[0]["name"] == "User"
                assert symbols[0]["type"] == "interface"
                mock_query.captures.assert_called_once()

    def test_matches_api_attribute_error(self):
        """Test handling when matches() exists but throws AttributeError."""
        code = "class Test {}"

        # Mock query where matches() exists but fails
        mock_query = Mock()
        mock_query.matches = Mock(side_effect=AttributeError("'Query' object has no attribute 'matches'"))
        mock_query.captures = Mock(
            return_value=[
                ("name", Mock(text=b"Test", start_point=(0, 6), end_point=(0, 10), start_byte=6, end_byte=10)),
                (
                    "definition.class",
                    Mock(text=b"class Test {}", start_point=(0, 0), end_point=(0, 13), start_byte=0, end_byte=13),
                ),
            ]
        )

        with patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query):
            with patch.object(TreeSitterSymbolExtractor, "get_parser") as mock_parser:
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.return_value.parse.return_value = mock_tree

                symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)

                assert len(symbols) == 1
                assert symbols[0]["name"] == "Test"
                assert symbols[0]["type"] == "class"
                mock_query.matches.assert_called_once()
                mock_query.captures.assert_called_once()

    def test_no_compatible_api(self):
        """Test handling when neither matches() nor captures() work."""
        code = "const x = 42;"

        # Mock query where both APIs fail
        mock_query = Mock()
        mock_query.matches = Mock(side_effect=AttributeError("No matches"))
        mock_query.captures = Mock(side_effect=AttributeError("No captures"))

        with patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query):
            with patch.object(TreeSitterSymbolExtractor, "get_parser") as mock_parser:
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.return_value.parse.return_value = mock_tree

                symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)

                assert symbols == []
                mock_query.matches.assert_called_once()
                mock_query.captures.assert_called_once()

    def test_query_object_without_methods(self):
        """Test handling when query object exists but has no methods."""
        code = "function test() {}"

        # Mock query with no matches or captures methods
        mock_query = Mock(spec=[])  # Empty spec means no methods

        with patch.object(TreeSitterSymbolExtractor, "get_query", return_value=mock_query):
            with patch.object(TreeSitterSymbolExtractor, "get_parser") as mock_parser:
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.return_value.parse.return_value = mock_tree

                symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)

                assert symbols == []

    def test_real_typescript_extraction(self):
        """Test with real TypeScript code to ensure compatibility."""
        typescript_code = """
interface User {
    id: number;
    name: string;
}

class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    getUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
}

export function greetUser(name: string): string {
    return `Hello, ${name}!`;
}
"""

        # This should work with the actual implementation
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", typescript_code)

        # Verify we got the expected symbols
        symbol_names = [s["name"] for s in symbols]
        assert "User" in symbol_names
        assert "UserService" in symbol_names
        assert "addUser" in symbol_names
        assert "getUser" in symbol_names
        assert "greetUser" in symbol_names

        # Verify types are correct
        symbol_map = {s["name"]: s["type"] for s in symbols}
        assert symbol_map.get("User") == "interface"
        assert symbol_map.get("UserService") == "class"
        assert symbol_map.get("greetUser") == "function"
