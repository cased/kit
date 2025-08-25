import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


HS_SAMPLE = """
module M where

add x y = x + y

newtype Age = Age Int

data Person = Person String Int

class Show a where
  show :: a -> String

foo :: Int -> Int
foo x = x
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

