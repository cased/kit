# Tests for Kotlin symbol extraction
import os

from kit import Repository


def _extract(tmpdir: str, filename: str, content: str):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    return Repository(tmpdir).extract_symbols(filename)


def test_kotlin_symbols(tmp_path):
    code = """
class Foo {
    fun bar() {}
    companion object {
        const val PI = 3.14
    }
}

object Singleton {
    fun baz() {}
}

enum class Color { RED, GREEN }
"""
    symbols = _extract(str(tmp_path), "sample.kt", code)
    names = {s["name"] for s in symbols}
    assert {"Foo", "Color", "Singleton", "bar", "baz"}.issubset(names)
