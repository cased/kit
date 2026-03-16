import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

TOML_SAMPLE = """\
[package]
name = "my-app"
version = "1.0.0"

[dependencies]
serde = "1.0"

[build.settings]
opt-level = 2

[[bin]]
name = "main"
path = "src/main.rs"

[[test]]
name = "integration"
"""

TOML_QUOTED_SAMPLE = """\
["foo.bar"]
value = 1

[["bin.name"]]
name = "main"

['lit']
value = 2
"""


def test_toml_parser_and_query_available():
    parser = TreeSitterSymbolExtractor.get_parser(".toml")
    query = TreeSitterSymbolExtractor.get_query(".toml")
    if not parser or not query:
        pytest.skip("TOML parser or query not available in this environment")

    tree = parser.parse(TOML_SAMPLE.encode("utf-8"))
    assert tree.root_node is not None


def test_toml_symbols():
    parser = TreeSitterSymbolExtractor.get_parser(".toml")
    query = TreeSitterSymbolExtractor.get_query(".toml")
    if not parser or not query:
        pytest.skip("TOML parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".toml", TOML_SAMPLE)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}

    assert "package" in names
    assert "dependencies" in names
    assert "build.settings" in names
    assert "bin" in names
    assert "test" in names

    assert "table" in types
    assert "table_array" in types


def test_toml_quoted_table_names_are_normalized():
    parser = TreeSitterSymbolExtractor.get_parser(".toml")
    query = TreeSitterSymbolExtractor.get_query(".toml")
    if not parser or not query:
        pytest.skip("TOML parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".toml", TOML_QUOTED_SAMPLE)
    names = {s["name"] for s in symbols}

    assert "foo.bar" in names
    assert "bin.name" in names
    assert "lit" in names


def test_toml_in_supported_languages():
    supported = TreeSitterSymbolExtractor.list_supported_languages()
    assert "toml" in supported
    assert ".toml" in supported["toml"]
