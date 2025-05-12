import pytest
from tree_sitter_language_pack import get_parser

LANG_SAMPLES = {
    "python": b"def foo():\n    return 42\n",
    "javascript": b"function foo() { return 42; }\n",
    "typescript": b"function foo(): number { return 42; }\n",
    "tsx": b"const foo = <T extends unknown>() => <div />;\n",
    "go": b"func foo() int { return 42 }\n",
    "rust": b"fn foo() -> i32 { 42 }\n",
    "hcl": b'variable "foo" { default = 42 }\n',
    "c": b"int foo() { return 42; }\n",
}


@pytest.mark.parametrize("lang,src", LANG_SAMPLES.items())
def test_parser_root_node(lang, src):
    parser = get_parser(lang)
    tree = parser.parse(src)
    root = tree.root_node
    assert root is not None
    # Root node type should be non-empty string
    assert isinstance(root.type, str) and root.type
    # Should have at least one child node
    assert root.child_count > 0
    # Print for debug
    print(f"{lang} root: {root.type}, children: {root.child_count}")
