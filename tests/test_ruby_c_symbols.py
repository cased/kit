# -*- coding: utf-8 -*-
"""Tests for Ruby and C symbol extraction."""

import os
import tempfile

from kit import Repository


def _extract(tmpdir: str, filename: str, content: str):
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return Repository(tmpdir).extract_symbols(filename)


def test_ruby_symbols():
    code = """
class Foo; end
module Bar; end

def baz; end
class Foo
  def qux; end
end
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        symbols = _extract(tmpdir, "main.rb", code)
        names = {s["name"] for s in symbols}
        assert {"Foo", "Bar", "baz", "qux"}.issubset(names)


def test_c_symbols():
    code = """
struct Person { int age; };

enum Color { RED, GREEN };

int add(int a,int b){ return a+b; }
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        symbols = _extract(tmpdir, "main.c", code)
        names = {s["name"] for s in symbols}
        assert {"Person", "Color", "add"}.issubset(names)
