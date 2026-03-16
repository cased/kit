import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

BASH_SAMPLE = """\
function greet() {
    echo "Hello, $1!"
}

say_hi() {
    echo "Hi there"
}
"""


def test_bash_parser_and_query_available():
    parser = TreeSitterSymbolExtractor.get_parser(".sh")
    query = TreeSitterSymbolExtractor.get_query(".sh")
    if not parser or not query:
        pytest.skip("Bash parser or query not available in this environment")

    tree = parser.parse(BASH_SAMPLE.encode("utf-8"))
    assert tree.root_node is not None


def test_bash_symbols():
    parser = TreeSitterSymbolExtractor.get_parser(".sh")
    query = TreeSitterSymbolExtractor.get_query(".sh")
    if not parser or not query:
        pytest.skip("Bash parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".sh", BASH_SAMPLE)
    names = {s["name"] for s in symbols}

    assert "greet" in names
    assert "say_hi" in names
    assert all(s["type"] == "function" for s in symbols)


def test_bash_extensions():
    supported = TreeSitterSymbolExtractor.list_supported_languages()
    assert "bash" in supported
    assert ".sh" in supported["bash"]
    assert ".bash" in supported["bash"]


def test_bash_extension_extracts_symbols():
    parser = TreeSitterSymbolExtractor.get_parser(".bash")
    query = TreeSitterSymbolExtractor.get_query(".bash")
    if not parser or not query:
        pytest.skip("Bash parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".bash", BASH_SAMPLE)
    names = {s["name"] for s in symbols}

    assert "greet" in names
    assert "say_hi" in names
