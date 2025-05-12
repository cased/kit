import os
import shutil
import tempfile

from kit import Repository

TEST_FILES = {
    "a.py": """
def foo():
    pass

def bar():
    foo()
""",
    "b.py": """
from a import foo

def baz():
    foo()
""",
}


def setup_test_repo():
    tmpdir = tempfile.mkdtemp()
    for fname, content in TEST_FILES.items():
        with open(os.path.join(tmpdir, fname), "w") as f:
            f.write(content)
    return tmpdir


def test_find_symbol_usages():
    repo_dir = setup_test_repo()
    try:
        repository = Repository(repo_dir)
        usages = repository.find_symbol_usages("foo", symbol_type="function")
        usage_files = sorted(set(u["file"].split(os.sep)[-1] for u in usages))
        assert "a.py" in usage_files
        assert "b.py" in usage_files
        # Should find both the definition and calls/imports
        found_types = set(u.get("type") for u in usages if u.get("type"))
        assert "function" in found_types
        # Should find at least one usage with context containing 'foo()'
        assert any("foo()" in (u.get("context") or "") for u in usages)
    finally:
        shutil.rmtree(repo_dir)
