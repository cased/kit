from kit import Repository


def make_repo(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


def test_skip_by_filename(tmp_path):
    repo_root = make_repo(tmp_path)
    (repo_root / "package-lock.json").write_text("{}\n")

    repo = Repository(str(repo_root))
    assembler = repo.get_context_assembler()

    assembler.add_file(
        "package-lock.json",
        skip_if_name_in=["package-lock.json"],
    )

    ctx = assembler.format_context()
    # lock file should be skipped -> context empty
    assert "package-lock.json" not in ctx


def test_skip_by_max_lines(tmp_path):
    repo_root = make_repo(tmp_path)
    big_file = repo_root / "big.py"
    big_file.write_text("\n".join(["print('x')"] * 500))

    repo = Repository(str(repo_root))
    assembler = repo.get_context_assembler()

    assembler.add_file("big.py", max_lines=100)
    ctx = assembler.format_context()
    assert "big.py" not in ctx


def test_include_small_file(tmp_path):
    repo_root = make_repo(tmp_path)
    small = repo_root / "small.py"
    small.write_text("print('hi')\n")

    repo = Repository(str(repo_root))
    assembler = repo.get_context_assembler()
    assembler.add_file("small.py", max_lines=100)

    ctx = assembler.format_context()
    assert "small.py" in ctx
