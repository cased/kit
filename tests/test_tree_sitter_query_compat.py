import types

import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class _DummyNode:
    def __init__(self, text="dummy"):
        # tree-sitter Node objects expose a ``text`` bytes property
        self.text = text.encode()
        # Some grammar queries access ``type`` – keep minimal attr
        self.type = "identifier"
        # Minimal positional info expected by extractor
        self.start_point = (0, 0)
        self.end_point = (0, len(text))
        self.start_byte = 0
        self.end_byte = len(text)


class _DummyParser:
    """Bare-minimum parser that returns an object with ``root_node`` attr."""

    class _DummyTree:
        def __init__(self):
            self.root_node = None  # We never inspect it in the stub

    def parse(self, _bytes: bytes):  # noqa: D401 – simple stub
        return self._DummyTree()


class _FakeQueryCapturesOnly:
    """Simulates tree_sitter.Query when the legacy ``matches`` API is missing."""

    def captures(self, _root):
        # Return a minimal sequence of (capture_name, node) tuples
        return [("name", _DummyNode())]


@pytest.fixture(autouse=True)
def _patch_tree_sitter(monkeypatch):
    """Monkey-patch the extractor to return our dummy query / parser."""

    monkeypatch.setattr(
        TreeSitterSymbolExtractor,
        "get_query",
        lambda _ext: _FakeQueryCapturesOnly(),
    )
    monkeypatch.setattr(
        TreeSitterSymbolExtractor,
        "get_parser",
        lambda _ext: _DummyParser(),
    )


def test_extract_symbols_fallback_to_captures():
    """`extract_symbols` should work when `Query.matches` is unavailable (>=0.23)."""

    symbols = TreeSitterSymbolExtractor.extract_symbols(".py", "print('hi')\n")

    assert symbols, "Expected at least one symbol when using captures-only Query"
    assert symbols[0]["name"] == "dummy" 