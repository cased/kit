"""Tests for JavaScript/TypeScript arrow function symbol extraction.

Verifies that arrow functions are properly detected by the symbol extractor.
See: https://github.com/cased/kit/issues/168
"""

import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class TestJavaScriptArrowFunctions:
    """Tests for JavaScript arrow function detection."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear query cache before each test."""
        TreeSitterSymbolExtractor._queries.clear()
        yield

    def test_const_arrow_function(self):
        """Arrow function assigned to const should be detected."""
        code = "const myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_let_arrow_function(self):
        """Arrow function assigned to let should be detected."""
        code = "let myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_var_arrow_function(self):
        """Arrow function assigned to var should be detected."""
        code = "var myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_async_arrow_function(self):
        """Async arrow function should be detected."""
        code = "const asyncFunc = async () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "asyncFunc" in names

    def test_arrow_function_with_params(self):
        """Arrow function with parameters should be detected."""
        code = "const add = (a, b) => a + b;"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "add" in names

    def test_exported_arrow_function(self):
        """Exported arrow function should be detected."""
        code = "export const myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_function_expression(self):
        """Function expression should be detected."""
        code = "const myFunc = function() {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_traditional_function_still_works(self):
        """Traditional function declaration should still work."""
        code = "function myFunc() {}"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_class_method_still_works(self):
        """Class methods should still be detected."""
        code = """
class MyClass {
  myMethod() {}
}
"""
        symbols = TreeSitterSymbolExtractor.extract_symbols(".js", code)
        names = {s["name"] for s in symbols}
        assert "MyClass" in names
        assert "myMethod" in names


class TestTypeScriptArrowFunctions:
    """Tests for TypeScript arrow function detection."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear query cache before each test."""
        TreeSitterSymbolExtractor._queries.clear()
        yield

    def test_const_arrow_function(self):
        """Arrow function assigned to const should be detected."""
        code = "const myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_typed_arrow_function(self):
        """Arrow function with type annotations should be detected."""
        code = "const add = (a: number, b: number): number => a + b;"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)
        names = {s["name"] for s in symbols}
        assert "add" in names

    def test_exported_arrow_function(self):
        """Exported arrow function should be detected."""
        code = "export const myFunc = () => {};"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)
        names = {s["name"] for s in symbols}
        assert "myFunc" in names

    def test_interface_still_works(self):
        """Interface declarations should still work."""
        code = "interface MyInterface { prop: string; }"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)
        names = {s["name"] for s in symbols}
        assert "MyInterface" in names

    def test_type_alias_still_works(self):
        """Type alias declarations should still work."""
        code = "type MyType = string | number;"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)
        names = {s["name"] for s in symbols}
        assert "MyType" in names


class TestTSXArrowFunctions:
    """Tests for TSX arrow function detection (React components)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear query cache before each test."""
        TreeSitterSymbolExtractor._queries.clear()
        yield

    def test_arrow_component(self):
        """Arrow function React component should be detected."""
        code = "const MyComponent = () => { return <div>Hello</div>; };"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".tsx", code)
        names = {s["name"] for s in symbols}
        assert "MyComponent" in names

    def test_exported_arrow_component(self):
        """Exported arrow function React component should be detected."""
        code = "export const MyComponent = () => <span>Hi</span>;"
        symbols = TreeSitterSymbolExtractor.extract_symbols(".tsx", code)
        names = {s["name"] for s in symbols}
        assert "MyComponent" in names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
