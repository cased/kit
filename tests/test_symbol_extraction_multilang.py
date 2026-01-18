import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

SAMPLES = {
    ".py": "def foo():\n    pass\n\nclass Bar:\n    pass\n",
    ".js": "function foo() {}\nclass Bar {}\n",
    ".go": "package main\n\nfunc foo() {}\n\ntype Bar struct{}\n",
    ".java": "class Bar { void foo() {} }\n",
    ".rs": "fn foo() {}\nstruct Bar;\n",
    ".zig": "pub fn foo() void {}\npub const Bar = struct {};\n",
}


@pytest.mark.parametrize("ext,code", list(SAMPLES.items()))
def test_symbol_extraction(ext: str, code: str):
    # Ensure tree-sitter has a parser+query for this extension
    parser = TreeSitterSymbolExtractor.get_parser(ext)
    query = TreeSitterSymbolExtractor.get_query(ext)
    if not parser or not query:
        pytest.skip(f"Language for {ext} not supported in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
    assert symbols, f"No symbols extracted for {ext}"

    # Simple sanity: expect 'foo' OR 'Bar' present
    names = {s.get("name") for s in symbols}
    assert any(name in names for name in {"foo", "Bar", "main"}), f"Expected symbols missing for {ext}: {names}"


# Test for issue #187: get_symbol_code returns symbol name instead of actual source code
# https://github.com/cased/kit/issues/187
MULTILINE_SAMPLES = {
    ".ts": """
function myFunction(x: number, y: number): number {
    const result = x + y;
    return result;
}
""",
    ".js": """
function myFunction(x, y) {
    const result = x + y;
    return result;
}
""",
    ".rs": """
fn my_function(x: i32, y: i32) -> i32 {
    let result = x + y;
    result
}
""",
    ".py": """
def my_function(x, y):
    result = x + y
    return result
""",
    ".go": """
package main

func myFunction(x int, y int) int {
    result := x + y
    return result
}
""",
}


@pytest.mark.parametrize("ext,code", list(MULTILINE_SAMPLES.items()))
def test_symbol_code_contains_full_body(ext: str, code: str):
    """Test that extract_symbols returns full function body in 'code' field, not just the name.

    This is a regression test for issue #187 where the code field only contained
    the symbol name (e.g., 'myFunction') instead of the actual source code.
    """
    parser = TreeSitterSymbolExtractor.get_parser(ext)
    query = TreeSitterSymbolExtractor.get_query(ext)
    if not parser or not query:
        pytest.skip(f"Language for {ext} not supported in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
    assert symbols, f"No symbols extracted for {ext}"

    # Find a function symbol
    func_symbols = [s for s in symbols if s.get("type") in ("function", "method")]
    assert func_symbols, f"No function symbols found for {ext}"

    func = func_symbols[0]
    func_name = func.get("name")
    func_code = func.get("code", "")

    # The code field should contain more than just the function name
    assert len(func_code) > len(func_name), (
        f"Code field for {ext} only contains name '{func_name}', expected full function body. "
        f"Got: '{func_code}'"
    )

    # The code should contain the function keyword or definition
    assert func_name in func_code, f"Function name '{func_name}' not found in code for {ext}"

    # For multi-line functions, end_line should be greater than start_line
    start_line = func.get("start_line", 0)
    end_line = func.get("end_line", 0)
    assert end_line > start_line, (
        f"For multi-line function in {ext}, expected end_line > start_line. "
        f"Got start_line={start_line}, end_line={end_line}"
    )
