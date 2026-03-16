import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

YAML_SAMPLE = """\
name: my-app
version: 1.0.0
database:
  host: localhost
  port: 5432
logging:
  level: info
  format: json
"""

YAML_QUOTED_SAMPLE = """\
"foo.bar": 1
'quoted': 2
"""


def test_yaml_parser_and_query_available():
    parser = TreeSitterSymbolExtractor.get_parser(".yaml")
    query = TreeSitterSymbolExtractor.get_query(".yaml")
    if not parser or not query:
        pytest.skip("YAML parser or query not available in this environment")

    tree = parser.parse(YAML_SAMPLE.encode("utf-8"))
    assert tree.root_node is not None


def test_yaml_top_level_keys_only():
    parser = TreeSitterSymbolExtractor.get_parser(".yaml")
    query = TreeSitterSymbolExtractor.get_query(".yaml")
    if not parser or not query:
        pytest.skip("YAML parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".yaml", YAML_SAMPLE)
    names = {s["name"] for s in symbols}

    assert "name" in names
    assert "version" in names
    assert "database" in names
    assert "logging" in names

    assert "host" not in names
    assert "port" not in names
    assert "level" not in names
    assert "format" not in names


def test_yaml_symbol_code_uses_full_mapping_pair():
    parser = TreeSitterSymbolExtractor.get_parser(".yaml")
    query = TreeSitterSymbolExtractor.get_query(".yaml")
    if not parser or not query:
        pytest.skip("YAML parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".yaml", YAML_SAMPLE)
    database_symbol = next(s for s in symbols if s["name"] == "database")

    assert database_symbol["code"].startswith("database:")
    assert "host: localhost" in database_symbol["code"]
    assert database_symbol["end_line"] > database_symbol["start_line"]


def test_yaml_quoted_keys_and_yml_extension():
    parser = TreeSitterSymbolExtractor.get_parser(".yml")
    query = TreeSitterSymbolExtractor.get_query(".yml")
    if not parser or not query:
        pytest.skip("YAML parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".yml", YAML_QUOTED_SAMPLE)
    names = {s["name"] for s in symbols}

    assert "foo.bar" in names
    assert "quoted" in names


def test_yaml_extensions():
    supported = TreeSitterSymbolExtractor.list_supported_languages()
    assert "yaml" in supported
    assert ".yaml" in supported["yaml"]
    assert ".yml" in supported["yaml"]
