import os
import tempfile
import pytest
from kit.repo import Repo

def test_typescript_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        ts_path = os.path.join(tmpdir, "golden_typescript.ts")
        with open(ts_path, "w") as f:
            f.write(open(os.path.join(os.path.dirname(__file__), "golden_typescript.ts")).read())
        repo = Repo(tmpdir)
        symbols = repo.extract_symbols("golden_typescript.ts")
        names_types = {(s["name"], s["type"]) for s in symbols}
        assert ("MyClass", "class") in names_types
        assert ("MyInterface", "interface") in names_types
        assert ("MyEnum", "enum") in names_types
        assert ("helper", "function") in names_types
