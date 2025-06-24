import subprocess
import tempfile
from pathlib import Path

import pytest

from kit import Repository


def test_grep_basic():
    """Test basic grep functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create test files with content
        (repo_path / "main.py").write_text("def main():\n    print('Hello World')\n    # TODO: fix this")
        (repo_path / "utils.py").write_text("def helper():\n    return 'hello'\n")
        (repo_path / "README.md").write_text("# Project\n\nTODO: write docs")

        repo = Repository(str(repo_path))

        # Test basic search
        matches = repo.grep("TODO")
        assert len(matches) == 2

        files_with_todo = {match["file"] for match in matches}
        assert "main.py" in files_with_todo
        assert "README.md" in files_with_todo

        # Verify line numbers and content
        for match in matches:
            if match["file"] == "main.py":
                assert match["line_number"] == 3
                assert "TODO: fix this" in match["line_content"]
            elif match["file"] == "README.md":
                assert match["line_number"] == 3
                assert "TODO: write docs" in match["line_content"]


def test_grep_case_sensitive():
    """Test case sensitivity in grep."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        (repo_path / "test.py").write_text("hello\nHELLO\nHello\n")

        repo = Repository(str(repo_path))

        # Case sensitive search
        matches_sensitive = repo.grep("hello", case_sensitive=True)
        assert len(matches_sensitive) == 1
        assert matches_sensitive[0]["line_number"] == 1

        # Case insensitive search
        matches_insensitive = repo.grep("hello", case_sensitive=False)
        assert len(matches_insensitive) == 3


def test_grep_include_exclude_patterns():
    """Test include/exclude file patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create files with same content but different extensions
        (repo_path / "script.py").write_text("function test() { return 'test'; }")
        (repo_path / "script.js").write_text("function test() { return 'test'; }")
        (repo_path / "README.md").write_text("function test() { return 'test'; }")

        repo = Repository(str(repo_path))

        # Test include pattern
        py_matches = repo.grep("function", include_pattern="*.py")
        assert len(py_matches) == 1
        assert py_matches[0]["file"] == "script.py"

        # Test exclude pattern
        non_md_matches = repo.grep("function", exclude_pattern="*.md")
        files = {match["file"] for match in non_md_matches}
        assert "script.py" in files
        assert "script.js" in files
        assert "README.md" not in files


def test_grep_max_results():
    """Test max results limiting."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create file with multiple matches
        content = "\n".join([f"line {i} with test content" for i in range(100)])
        (repo_path / "large.txt").write_text(content)

        repo = Repository(str(repo_path))

        # Test max results
        matches = repo.grep("test", max_results=10)
        assert len(matches) == 10


def test_grep_no_matches():
    """Test grep when no matches found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        (repo_path / "test.py").write_text("print('hello world')")

        repo = Repository(str(repo_path))

        matches = repo.grep("nonexistent")
        assert len(matches) == 0


@pytest.mark.skipif(
    subprocess.run(["which", "grep"], capture_output=True).returncode != 0, reason="grep command not available"
)
def test_grep_requires_grep_command():
    """Test that grep functionality requires system grep command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        (repo_path / "test.py").write_text("hello")

        repo = Repository(str(repo_path))

        # This should work if grep is available
        matches = repo.grep("hello")
        assert len(matches) >= 0  # Should not raise an exception


def test_grep_literal_search():
    """Test that grep performs literal (not regex) search."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create content with regex special characters
        (repo_path / "test.py").write_text("pattern = r'\\d+'\nregex_pattern = '.*'\nliteral.dot")

        repo = Repository(str(repo_path))

        # Search for literal dot (should find both occurrences of '.')
        matches = repo.grep(".")
        # Should find the literal dots in both "regex_pattern = '.*'" and "literal.dot"
        assert len(matches) == 2
        line_contents = [match["line_content"] for match in matches]
        assert any(".*" in content for content in line_contents)
        assert any("literal.dot" in content for content in line_contents)


def test_grep_directory_filtering():
    """Test directory parameter for limiting search scope."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create directory structure
        (repo_path / "src").mkdir()
        (repo_path / "tests").mkdir()
        (repo_path / "docs").mkdir()

        # Create files with same content in different directories
        (repo_path / "main.py").write_text("def main(): pass")
        (repo_path / "src" / "api.py").write_text("def api_function(): pass")
        (repo_path / "src" / "utils.py").write_text("def helper_function(): pass")
        (repo_path / "tests" / "test_api.py").write_text("def test_function(): pass")
        (repo_path / "docs" / "guide.py").write_text("def example_function(): pass")

        repo = Repository(str(repo_path))

        # Test searching entire repository
        all_matches = repo.grep("def")
        assert len(all_matches) == 5

        # Test searching only src directory
        src_matches = repo.grep("def", directory="src")
        assert len(src_matches) == 2
        files = {match["file"] for match in src_matches}
        assert all(f.startswith("src/") for f in files)

        # Test searching only tests directory
        test_matches = repo.grep("def", directory="tests")
        assert len(test_matches) == 1
        assert test_matches[0]["file"] == "tests/test_api.py"


def test_grep_invalid_directory():
    """Test error handling for invalid directory parameter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        (repo_path / "test.py").write_text("hello")

        repo = Repository(str(repo_path))

        # Test non-existent directory
        with pytest.raises(ValueError, match="Directory not found in repository"):
            repo.grep("hello", directory="nonexistent")


def test_grep_hidden_directory_exclusion():
    """Test hidden directory exclusion behavior."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create hidden directories
        (repo_path / ".git").mkdir()
        (repo_path / ".vscode").mkdir()
        (repo_path / ".github").mkdir()
        (repo_path / "src").mkdir()

        # Create files in both visible and hidden directories
        (repo_path / "src" / "main.py").write_text("function test_visible()")
        (repo_path / ".git" / "config").write_text("function test_git()")
        (repo_path / ".vscode" / "settings.json").write_text("function test_vscode()")
        (repo_path / ".github" / "workflow.yml").write_text("function test_github()")

        repo = Repository(str(repo_path))

        # Test default behavior (exclude hidden directories)
        default_matches = repo.grep("function", include_hidden=False)
        assert len(default_matches) == 1
        assert "src/main.py" in default_matches[0]["file"]

        # Test including hidden directories (but .git still excluded by default)
        all_matches = repo.grep("function", include_hidden=True)
        assert len(all_matches) == 3  # .git is still excluded by smart exclusions
        files = {match["file"] for match in all_matches}
        assert any(".vscode" in f for f in files)
        assert any(".github" in f for f in files)
        assert "src/main.py" in files
        # .git should still be excluded even with include_hidden=True


def test_grep_smart_exclusions():
    """Test that common directories are automatically excluded."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create commonly excluded directories
        for dirname in ["node_modules", "__pycache__", "dist", "build", ".venv", "target"]:
            (repo_path / dirname).mkdir()
            (repo_path / dirname / "test.txt").write_text("function excluded()")

        # Create regular source file
        (repo_path / "src.py").write_text("function included()")

        repo = Repository(str(repo_path))

        # Should only find the file in regular directory
        matches = repo.grep("function")
        assert len(matches) == 1
        assert matches[0]["file"] == "src.py"


def test_grep_directory_and_patterns_combined():
    """Test combining directory filtering with include/exclude patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create directory structure
        (repo_path / "src").mkdir()
        (repo_path / "tests").mkdir()

        # Create files
        (repo_path / "src" / "api.py").write_text("class ApiClient: pass")
        (repo_path / "src" / "utils.js").write_text("class UtilsHelper { }")
        (repo_path / "tests" / "test_api.py").write_text("class TestApi: pass")

        repo = Repository(str(repo_path))

        # Search only Python files in src directory
        matches = repo.grep("class", directory="src", include_pattern="*.py")
        assert len(matches) == 1
        assert matches[0]["file"] == "src/api.py"

        # Search excluding Python files in src directory
        matches = repo.grep("class", directory="src", exclude_pattern="*.py")
        assert len(matches) == 1
        assert matches[0]["file"] == "src/utils.js"
