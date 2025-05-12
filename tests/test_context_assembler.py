from kit import ContextAssembler, Repository


def test_context_assembler_basic(tmp_path):
    # Create a simple repo with one file
    file_path = tmp_path / "foo.py"
    file_path.write_text("print('hi')\n")

    repo = Repository(str(tmp_path))
    assembler = ContextAssembler(repo)
    assembler.add_file("foo.py")
    ctx = assembler.format_context()

    assert "foo.py" in ctx
    assert "print('hi')" in ctx
