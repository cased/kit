import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

SAMPLES = {
    ".py": "def foo():\n    pass\n\nclass Bar:\n    pass\n",
    ".js": "function foo() {}\nclass Bar {}\n",
    ".go": "package main\n\nfunc foo() {}\n\ntype Bar struct{}\n",
    ".java": "class Bar { void foo() {} }\n",
    ".rs": "fn foo() {}\nstruct Bar;\n",
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
