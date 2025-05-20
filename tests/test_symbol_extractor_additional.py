import os
import tempfile
from pathlib import Path

import pytest

from kit import Repository, TreeSitterSymbolExtractor

# ------------------ Helpers ------------------


def _write_tmp_and_extract(tmpdir: str, filename: str, content: str):
    """Utility that writes *content* to *filename* inside *tmpdir* and extracts symbols."""
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    repo = Repository(tmpdir)
    return repo.extract_symbols(filename)


# ------------------ Language Smoke-Tests ------------------


@pytest.mark.parametrize(
    "fname,source,expected_names",
    [
        pytest.param(
            "sample.js",
            """function foo() { return 1; }\nclass Bar {\n  baz() {}\n}\n""",
            {"foo", "Bar"},
        ),
        pytest.param(
            "sample.tsx",
            """import React from 'react';\nfunction MyComponent() { return <div/>; }\nexport class Helper {}\n""",
            {"MyComponent", "Helper"},
        ),
        pytest.param(
            "sample.rs",
            """fn foo() {}\nstruct Bar { x: i32 }\nenum Baz { A, B }\n""",
            {"foo", "Bar", "Baz"},
        ),
        pytest.param(
            "sample.c",
            """int add(int a, int b) { return a + b; }\nstruct Point { int x; int y; };\nenum Color { RED, GREEN, BLUE };\n""",
            {"add", "Point", "Color"},
        ),
        pytest.param(
            "sample.rb",
            """class Foo\n  def bar; end\nend\nmodule Baz; end\ndef top_level; end\n""",
            {"Foo", "Baz", "bar"},
        ),
        pytest.param(
            "Sample.java",
            """public class MyClass {\n  public void foo() {}\n}\ninterface MyInterface {}\nenum MyEnum { A, B; }\n""",
            {"MyClass", "MyInterface", "MyEnum"},
        ),
    ],
)
def test_symbol_extraction_smoke(fname, source, expected_names):
    """Ensure we can extract *some* expected symbols from every supported language."""
    with tempfile.TemporaryDirectory() as tmpdir:
        symbols = _write_tmp_and_extract(tmpdir, fname, source)
        # Just check names, as types might vary by tree-sitter query details
        extracted_names = {s["name"] for s in symbols}
        for name in expected_names:
            assert name in extracted_names, f"Expected symbol named '{name}' in {extracted_names} for file {fname}"


# ------------------ Error-Handling Tests ------------------


def test_missing_tags_scm(monkeypatch):
    """Simulate missing *tags.scm* for Ruby and ensure extractor fails gracefully."""

    TreeSitterSymbolExtractor._queries.pop(".rb", None)

    # Mock the read_text method to raise FileNotFoundError for ruby/tags.scm
    original_read_text = Path.read_text

    def _mock_read_text(self, *args, **kwargs):
        if "ruby" in str(self) and self.name == "tags.scm":
            raise FileNotFoundError(f"Simulated missing file: {self}")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _mock_read_text)

    symbols = TreeSitterSymbolExtractor.extract_symbols(".rb", "class Foo; end")
    assert symbols == [], "Expected empty symbol list when tags.scm is missing"


def test_corrupt_tags_scm(monkeypatch):
    """Simulate corrupt *tags.scm* content for Rust and ensure extractor fails gracefully."""

    TreeSitterSymbolExtractor._queries.pop(".rs", None)

    # Mock the read_text method to return invalid query content
    original_read_text = Path.read_text

    def _mock_read_text(self, *args, **kwargs):
        if "rust" in str(self) and self.name == "tags.scm":
            return "this is not valid tree-sitter query"
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _mock_read_text)

    symbols = TreeSitterSymbolExtractor.extract_symbols(".rs", "fn foo() {}")
    assert symbols == [], "Expected empty symbol list when tags.scm is corrupt"


def test_unsupported_extension():
    symbols = TreeSitterSymbolExtractor.extract_symbols(".xyz", "whatever")
    assert symbols == [], "Expected empty symbol list for unsupported extension"
