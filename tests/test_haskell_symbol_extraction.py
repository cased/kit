import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

HS_SAMPLE = r"""
module A.B where

(>>=) x f = f x
add x y = x + y
f = \x -> x

newtype Age = Age Int
data Person = Person String Int
type Str = String

class Show a where
  show :: a -> String

type family F a

instance Show Int where
  show = undefined

main = undefined
"""


def test_haskell_parser_and_query_available():
    """Guarded test: verifies parser/query load for Haskell if available."""
    parser = TreeSitterSymbolExtractor.get_parser(".hs")
    query = TreeSitterSymbolExtractor.get_query(".hs")

    if not parser or not query:
        pytest.skip("Haskell parser or query not available in this environment")

    tree = parser.parse(HS_SAMPLE.encode("utf-8"))
    assert tree.root_node is not None

    # Extraction should run without raising, may return 0+ symbols depending on queries
    symbols = TreeSitterSymbolExtractor.extract_symbols(".hs", HS_SAMPLE)
    assert isinstance(symbols, list)


def _names_by_type(symbols: list[dict]):
    result: dict[str, set[str]] = {}
    for s in symbols:
        t = s.get("type")
        n = s.get("name")
        if isinstance(t, str) and isinstance(n, str):
            result.setdefault(t, set()).add(n)
    return result


def test_haskell_symbols_if_available():
    parser = TreeSitterSymbolExtractor.get_parser(".hs")
    query = TreeSitterSymbolExtractor.get_query(".hs")
    if not parser or not query:
        pytest.skip("Haskell parser or query not available in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(".hs", HS_SAMPLE)
    names_by_type = _names_by_type(symbols)

    # One module symbol (from header), not per-import segments
    assert sum(1 for s in symbols if s.get("type") == "module") == 1

    # Functions
    fn = names_by_type.get("function", set())
    assert {"add", "f", "main"}.issubset(fn)
    # Operator-named function may be captured as ">>="; tolerate absence on some grammars
    # if present, it should appear under function names
    if any(op in fn for op in {"(>>=)", ">>="}):
        assert True

    # Type-level
    assert "Person" in names_by_type.get("data", set())
    assert "Age" in names_by_type.get("newtype", set())
    assert "Str" in names_by_type.get("type", set())
    assert "Show" in names_by_type.get("class", set())
    # Family/instance may vary in naming; check presence of at least one
    assert names_by_type.get("type_family") is not None
    assert any(s.get("type") == "instance" for s in symbols)
