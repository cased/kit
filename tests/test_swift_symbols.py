import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

SWIFT_SAMPLE = """\
class Animal {
    var name: String
    init(name: String) {
        self.name = name
    }
}

struct Point {
    var x: Int
    var y: Int
}

enum Direction {
    case north, south, east, west
}

extension Animal {
    func speak() -> String {
        return name
    }
}

actor Worker {
    func run() {}
}

protocol Drawable {
    func draw()
}

typealias StringMap = [String: String]

func greet(person: String) -> String {
    return "Hello, \\(person)!"
}
"""


def test_swift_parser_and_query_available():
    parser = TreeSitterSymbolExtractor.get_parser(".swift")
    query = TreeSitterSymbolExtractor.get_query(".swift")
    if not parser or not query:
        pytest.skip("Swift parser or query not available in this environment")

    tree = parser.parse(SWIFT_SAMPLE.encode("utf-8"))
    assert tree.root_node is not None


def test_swift_symbols():
    parser = TreeSitterSymbolExtractor.get_parser(".swift")
    query = TreeSitterSymbolExtractor.get_query(".swift")
    if not parser or not query:
        pytest.skip("Swift parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".swift", SWIFT_SAMPLE)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    animal_symbols = [s for s in symbols if s["name"] == "Animal"]

    # All 9 symbol types
    assert "Animal" in names
    assert "Point" in names
    assert "Direction" in names
    assert "Worker" in names
    assert "Drawable" in names
    assert "StringMap" in names
    assert "greet" in names
    assert "init" in names

    assert len(animal_symbols) == 2
    assert {s["type"] for s in animal_symbols} == {"class", "extension"}

    assert "class" in types
    assert "actor" in types
    assert "struct" in types
    assert "enum" in types
    assert "extension" in types
    assert "protocol" in types
    assert "typealias" in types
    assert "function" in types
    assert "initializer" in types


def test_swift_in_supported_languages():
    supported = TreeSitterSymbolExtractor.list_supported_languages()
    assert "swift" in supported
    assert ".swift" in supported["swift"]
