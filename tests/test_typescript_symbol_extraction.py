import os
from kit.repo import Repo

def test_typescript_symbol_extraction(tmp_path):
    # Minimal TypeScript code with a function and a class
    ts_code = '''
function foo() {}
class Bar {}
'''
    ts_file = tmp_path / "example.ts"
    ts_file.write_text(ts_code)
    repo = Repo(str(tmp_path))
    symbols = repo.extract_symbols(str(ts_file))
    names_types = {(s.get("name"), s.get("type")) for s in symbols}
    assert ("foo", "function") in names_types
    assert ("Bar", "class") in names_types
