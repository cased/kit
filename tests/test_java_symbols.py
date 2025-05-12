import os
import tempfile

from kit import Repository


def _extract(tmpdir: str, filename: str, content: str):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    return Repository(tmpdir).extract_symbols(filename)


def test_java_symbols():
    code = """
public class Foo {
    public int x;
    public Foo() {}
    public void bar() {}
}

interface Baz {}

enum Color { RED, GREEN }
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        symbols = _extract(tmpdir, "Foo.java", code)
        names = {s["name"] for s in symbols}
        assert {"Foo", "bar", "Baz", "Color"}.issubset(names)
