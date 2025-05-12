from pathlib import Path

import pytest

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

# Map each sample fixture to the set of symbol names we must find.
SAMPLE_EXPECTATIONS = {
    "python_sample.py": {"greet", "Greeter"},
    "javascript_sample.js": {"greet", "Greeter"},
    "typescript_sample.ts": {"greet", "Greeter"},
    "tsx_sample.tsx": {"MyComponent"},
    "go_sample.go": {"Greet", "Greeter"},
    "rust_sample.rs": {"greet", "Greeter"},
    "c_sample.c": {"greet"},
    "ruby_sample.rb": {"greet", "Greeter"},
    "java_sample.java": {"Greeter"},
}

SAMPLES_DIR = Path(__file__).parent / "sample_code"


@pytest.mark.parametrize("filename,expected", SAMPLE_EXPECTATIONS.items())
def test_sample_symbol_extraction(filename: str, expected: set[str]):
    path = SAMPLES_DIR / filename
    assert path.exists(), f"Sample file missing: {path}"

    code = path.read_text()
    ext = path.suffix  # includes the leading dot

    # Ensure we actually have support for this language in the environment.
    parser = TreeSitterSymbolExtractor.get_parser(ext)
    query = TreeSitterSymbolExtractor.get_query(ext)
    if not parser or not query:
        pytest.skip(f"Language for {ext} not supported in this environment")

    symbols = TreeSitterSymbolExtractor.extract_symbols(ext, code)
    names = {s["name"] for s in symbols if "name" in s}

    missing = expected - names
    assert not missing, f"Expected symbols not found in {filename}: {missing}"
