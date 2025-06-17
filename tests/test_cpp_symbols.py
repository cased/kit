import os

from kit import Repository


def _extract(tmpdir: str, filename: str, content: str):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    return Repository(tmpdir).extract_symbols(filename)


def test_cpp_symbols(tmp_path):
    code = """
class Foo {
public:
    void bar() {}
};

struct Baz {};

namespace ns {
int x = 0;
}

enum Color { RED, BLUE };
"""
    dir_str = str(tmp_path)
    fname = "sample.cpp"
    symbols = _extract(dir_str, fname, code)
    names = {s["name"] for s in symbols}
    # Currently extracts: classes, structs, enums
    # TODO: Add support for methods and namespaces
    assert {"Foo", "Baz", "Color"}.issubset(names)
