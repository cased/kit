from pathlib import Path

import pytest

from kit import Repository


def test_typescript_symbol_extraction(tmp_path: Path):
    # Minimal TypeScript code with a function and a class
    ts_code = """
function foo() {}
class Bar {}
"""
    ts_file = tmp_path / "example.ts"
    ts_file.write_text(ts_code)
    repository = Repository(str(tmp_path))
    try:
        symbols = repository.extract_symbols("example.ts")
    except Exception as e:
        pytest.fail(f"Symbol extraction failed: {e}")
    names_types = {(s.get("name"), s.get("type")) for s in symbols}
    assert ("foo", "function") in names_types
    assert ("Bar", "class") in names_types
