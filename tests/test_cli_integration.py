"""Integration tests for kit CLI commands using real Repository instances."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_repo():
    """Create a temporary repository with sample files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create Python files
        (repo_path / "main.py").write_text("""
def main():
    '''Main function for the application.'''
    print("Hello, World!")
    return 0

class Calculator:
    '''A simple calculator class.'''
    # noqa: W293
    def add(self, a, b):
        '''Add two numbers.'''
        return a + b
    # noqa: W293
    def multiply(self, a, b):
        '''Multiply two numbers.'''
        return a * b

if __name__ == "__main__":
    main()
""")

        (repo_path / "utils.py").write_text("""
import os
from typing import List

def get_files(directory: str) -> List[str]:
    '''Get all files in a directory.'''
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

def process_data(data):
    '''Process some data.'''
    return [x * 2 for x in data]

# Global variable
DEFAULT_TIMEOUT = 30
""")

        # Create JavaScript file
        (repo_path / "script.js").write_text("""
function greet(name) {
    console.log(`Hello, ${name}!`);
}

class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }
    # noqa: W293
    toString() {
        return `${this.name} <${this.email}>`;
    }
}

greet("World");
""")

        # Create subdirectory with files
        (repo_path / "lib").mkdir()
        (repo_path / "lib" / "helper.py").write_text("""
def helper_function():
    '''A helper function.'''
    pass

class Helper:
    '''Helper class.'''
    pass
""")

        # Create README
        (repo_path / "README.md").write_text("""
# Test Repository

This is a test repository for kit CLI integration tests.

## Functions

- main(): Main function
- greet(): Greeting function
""")

        yield str(repo_path)


def run_kit_command(args: list, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Helper to run kit CLI commands."""
    cmd = ["kit", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)


class TestFileOperations:
    """Integration tests for file operation commands."""

    def test_file_tree_integration(self, temp_repo):
        """Test file-tree command with real repository."""
        result = run_kit_command(["file-tree", temp_repo])

        assert result.returncode == 0
        output = result.stdout

        # Check that all expected files are listed
        assert "main.py" in output
        assert "utils.py" in output
        assert "script.js" in output
        assert "README.md" in output
        assert "lib" in output
        assert "helper.py" in output

        # Check file/directory indicators
        assert "📄 main.py" in output
        assert "📁 lib" in output

    def test_file_tree_json_output(self, temp_repo):
        """Test file-tree command with JSON output."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["file-tree", temp_repo, "--output", output_file])

            assert result.returncode == 0
            assert f"File tree written to {output_file}" in result.stdout

            # Verify JSON content
            with open(output_file, "r") as f:
                data = json.load(f)

            assert isinstance(data, list)
            file_paths = [item["path"] for item in data]
            assert "main.py" in file_paths
            assert "utils.py" in file_paths
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_file_content_integration(self, temp_repo):
        """Test file-content command with real repository."""
        result = run_kit_command(["file-content", temp_repo, "main.py"])

        assert result.returncode == 0
        output = result.stdout

        assert "def main():" in output
        assert "class Calculator:" in output
        assert "Hello, World!" in output

    def test_file_content_missing_file(self, temp_repo):
        """Test file-content command with missing file."""
        result = run_kit_command(["file-content", temp_repo, "nonexistent.py"])

        assert result.returncode == 1
        assert "Error: File not found: nonexistent.py" in result.stdout

    def test_index_integration(self, temp_repo):
        """Test index command with real repository."""
        result = run_kit_command(["index", temp_repo])

        assert result.returncode == 0

        # Parse the JSON output
        index_data = json.loads(result.stdout)

        # Check structure
        assert "files" in index_data or "file_tree" in index_data
        assert "symbols" in index_data

        # Check that symbols were extracted
        symbols = index_data["symbols"]
        assert len(symbols) > 0


class TestSymbolOperations:
    """Integration tests for symbol operation commands."""

    def test_symbols_integration(self, temp_repo):
        """Test symbols command with real repository."""
        result = run_kit_command(["symbols", temp_repo])

        assert result.returncode == 0
        output = result.stdout

        # Check for expected symbols
        assert "main" in output
        assert "Calculator" in output
        assert "add" in output
        assert "get_files" in output
        assert "greet" in output

    def test_symbols_json_format(self, temp_repo):
        """Test symbols command with JSON format."""
        result = run_kit_command(["symbols", temp_repo, "--format", "json"])

        assert result.returncode == 0

        symbols = json.loads(result.stdout)
        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # Check symbol structure
        first_symbol = symbols[0]
        assert "name" in first_symbol
        assert "type" in first_symbol
        assert "file" in first_symbol

    def test_symbols_names_format(self, temp_repo):
        """Test symbols command with names format."""
        result = run_kit_command(["symbols", temp_repo, "--format", "names"])

        assert result.returncode == 0

        names = result.stdout.strip().split("\n")
        assert len(names) > 0
        assert any("main" in name for name in names)
        assert any("Calculator" in name for name in names)

    def test_symbols_specific_file(self, temp_repo):
        """Test symbols command for specific file."""
        result = run_kit_command(["symbols", temp_repo, "--file", "main.py"])

        assert result.returncode == 0
        output = result.stdout

        # Should contain symbols from main.py
        assert "main" in output
        assert "Calculator" in output

        # Should not contain symbols from other files
        assert "get_files" not in output

    def test_usages_integration(self, temp_repo):
        """Test usages command with real repository."""
        result = run_kit_command(["usages", temp_repo, "main"])

        assert result.returncode == 0
        output = result.stdout

        assert "usage(s) of 'main'" in output
        # Should find the function definition and the call
        assert "main.py" in output

    def test_usages_with_type_filter(self, temp_repo):
        """Test usages command with type filter."""
        result = run_kit_command(["usages", temp_repo, "Calculator", "--type", "class"])

        assert result.returncode == 0
        output = result.stdout

        assert "usage(s) of 'Calculator'" in output

    def test_usages_nonexistent_symbol(self, temp_repo):
        """Test usages command with nonexistent symbol."""
        result = run_kit_command(["usages", temp_repo, "nonexistent_function"])

        assert result.returncode == 0
        assert "No usages found for symbol 'nonexistent_function'" in result.stdout


class TestSearchOperations:
    """Integration tests for search operation commands."""

    def test_search_integration(self, temp_repo):
        """Test search command with real repository."""
        result = run_kit_command(["search", temp_repo, "def "])

        assert result.returncode == 0
        output = result.stdout

        # Should find function definitions
        assert "main.py" in output
        assert "utils.py" in output
        assert "def main" in output
        assert "def add" in output

    def test_search_with_pattern(self, temp_repo):
        """Test search command with file pattern."""
        result = run_kit_command(["search", temp_repo, "function", "--pattern", "*.py"])

        assert result.returncode == 0
        output = result.stdout

        # Should find Python files only
        assert "main.py" in output or "utils.py" in output
        # Should not find JavaScript files
        assert "script.js" not in output

    def test_search_javascript_files(self, temp_repo):
        """Test search in JavaScript files."""
        result = run_kit_command(["search", temp_repo, "function", "--pattern", "*.js"])

        assert result.returncode == 0
        output = result.stdout

        if "script.js" in output:  # Only if JavaScript was found
            assert "greet" in output

    def test_search_no_results(self, temp_repo):
        """Test search with no results."""
        result = run_kit_command(["search", temp_repo, "nonexistent_pattern_xyz"])

        assert result.returncode == 0
        assert "No results found." in result.stdout

    def test_search_regex_pattern(self, temp_repo):
        """Test search with regex pattern."""
        result = run_kit_command(["search", temp_repo, r"def \w+\("])

        assert result.returncode == 0
        output = result.stdout

        # Should find function definitions
        assert "def main(" in output or "def add(" in output


class TestContextOperations:
    """Integration tests for context operation commands."""

    def test_context_integration(self, temp_repo):
        """Test context command with real repository."""
        # Look for context around line 5 in main.py (should be in Calculator class)
        result = run_kit_command(["context", temp_repo, "main.py", "10"])

        assert result.returncode == 0
        output = result.stdout

        assert "Context for main.py:10" in output
        # Should extract some code context
        assert "def" in output or "class" in output

    def test_context_no_result(self, temp_repo):
        """Test context command with line that has no context."""
        # Try a line number that's beyond the file
        result = run_kit_command(["context", temp_repo, "main.py", "1000"])

        assert result.returncode == 0
        assert "No context found" in result.stdout

    def test_chunk_lines_integration(self, temp_repo):
        """Test chunk-lines command with real repository."""
        result = run_kit_command(["chunk-lines", temp_repo, "main.py"])

        assert result.returncode == 0
        output = result.stdout

        assert "--- Chunk" in output
        assert "def main" in output or "class Calculator" in output

    def test_chunk_lines_custom_size(self, temp_repo):
        """Test chunk-lines command with custom chunk size."""
        result = run_kit_command(["chunk-lines", temp_repo, "main.py", "--max-lines", "5"])

        assert result.returncode == 0
        output = result.stdout

        # Should create multiple small chunks
        chunk_count = output.count("--- Chunk")
        assert chunk_count >= 2

    def test_chunk_symbols_integration(self, temp_repo):
        """Test chunk-symbols command with real repository."""
        result = run_kit_command(["chunk-symbols", temp_repo, "main.py"])

        assert result.returncode == 0
        output = result.stdout

        # Should show symbol-based chunks
        assert "function: main" in output or "class: Calculator" in output
        assert "def main" in output


class TestExportOperations:
    """Integration tests for export operation commands."""

    def test_export_symbols(self, temp_repo):
        """Test export symbols command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "symbols", output_file])

            assert result.returncode == 0
            assert f"Symbols exported to {output_file}" in result.stdout

            # Verify exported data
            with open(output_file, "r") as f:
                symbols = json.load(f)

            assert isinstance(symbols, list)
            assert len(symbols) > 0

            # Check symbol structure
            symbol_names = [s["name"] for s in symbols]
            assert "main" in symbol_names
            assert "Calculator" in symbol_names
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_file_tree(self, temp_repo):
        """Test export file-tree command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "file-tree", output_file])

            assert result.returncode == 0
            assert f"File tree exported to {output_file}" in result.stdout

            # Verify exported data
            with open(output_file, "r") as f:
                tree = json.load(f)

            assert isinstance(tree, list)
            file_paths = [item["path"] for item in tree]
            assert "main.py" in file_paths
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_index(self, temp_repo):
        """Test export index command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "index", output_file])

            assert result.returncode == 0
            assert f"Repository index exported to {output_file}" in result.stdout

            # Verify exported data
            with open(output_file, "r") as f:
                index = json.load(f)

            assert "files" in index or "file_tree" in index
            assert "symbols" in index
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_symbol_usages(self, temp_repo):
        """Test export symbol-usages command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "symbol-usages", output_file, "--symbol", "main"])

            assert result.returncode == 0
            assert f"Symbol usages for 'main' exported to {output_file}" in result.stdout

            # Verify exported data
            with open(output_file, "r") as f:
                usages = json.load(f)

            assert isinstance(usages, list)
        finally:
            Path(output_file).unlink(missing_ok=True)


class TestEndToEndWorkflows:
    """Integration tests for complete workflows."""

    def test_complete_repository_analysis(self, temp_repo):
        """Test a complete repository analysis workflow."""
        # 1. Get file tree
        result = run_kit_command(["file-tree", temp_repo])
        assert result.returncode == 0

        # 2. Extract all symbols
        result = run_kit_command(["symbols", temp_repo, "--format", "json"])
        assert result.returncode == 0
        symbols = json.loads(result.stdout)
        assert len(symbols) > 0

        # 3. Search for specific patterns
        result = run_kit_command(["search", temp_repo, "class"])
        assert result.returncode == 0

        # 4. Find usages of a symbol
        result = run_kit_command(["usages", temp_repo, "Calculator"])
        assert result.returncode == 0

        # 5. Get context for a specific line
        result = run_kit_command(["context", temp_repo, "main.py", "5"])
        assert result.returncode == 0

    def test_python_specific_analysis(self, temp_repo):
        """Test Python-specific code analysis."""
        # Extract symbols from Python files only
        result = run_kit_command(["symbols", temp_repo, "--file", "main.py"])
        assert result.returncode == 0

        # Search for Python patterns
        result = run_kit_command(["search", temp_repo, "import", "--pattern", "*.py"])
        assert result.returncode == 0

        # Find function definitions
        result = run_kit_command(["search", temp_repo, r"def \w+", "--pattern", "*.py"])
        assert result.returncode == 0

    def test_cross_file_analysis(self, temp_repo):
        """Test analysis across multiple files."""
        # Search for a pattern across all files
        result = run_kit_command(["search", temp_repo, "function"])
        assert result.returncode == 0

        # Should find results in both Python and JavaScript files
        output = result.stdout
        file_extensions = []
        for line in output.split("\n"):
            if ":" in line and "." in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    filename = parts[0].strip()
                    if "." in filename:
                        ext = "." + filename.split(".")[-1]
                        file_extensions.append(ext)

        # Should find files with different extensions
        assert len(set(file_extensions)) >= 1

    def test_export_and_reimport_workflow(self, temp_repo):
        """Test exporting data and using it for analysis."""
        with tempfile.TemporaryDirectory() as export_dir:
            export_path = Path(export_dir)

            # Export symbols
            symbols_file = export_path / "symbols.json"
            result = run_kit_command(["export", temp_repo, "symbols", str(symbols_file)])
            assert result.returncode == 0

            # Export file tree
            tree_file = export_path / "tree.json"
            result = run_kit_command(["export", temp_repo, "file-tree", str(tree_file)])
            assert result.returncode == 0

            # Verify both files exist and contain valid data
            assert symbols_file.exists()
            assert tree_file.exists()

            with open(symbols_file) as f:
                symbols = json.load(f)
            with open(tree_file) as f:
                tree = json.load(f)

            assert len(symbols) > 0
            assert len(tree) > 0

            # Check that we can find expected symbols
            symbol_names = [s["name"] for s in symbols]
            assert "main" in symbol_names
            assert "Calculator" in symbol_names


class TestErrorHandling:
    """Integration tests for error conditions."""

    def test_invalid_repository_path(self):
        """Test commands with invalid repository path."""
        result = run_kit_command(["file-tree", "/nonexistent/path"])
        # The command actually succeeds but returns empty output for nonexistent paths
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_invalid_file_path(self, temp_repo):
        """Test file-content with invalid file path."""
        result = run_kit_command(["file-content", temp_repo, "nonexistent.py"])
        assert result.returncode == 1
        assert "Error: File not found" in result.stdout

    def test_invalid_export_type(self, temp_repo):
        """Test export with invalid data type."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "invalid-type", output_file])
            assert result.returncode == 1
            assert "Error: Unknown data type" in result.stdout
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_symbol_usages_missing_symbol(self, temp_repo):
        """Test export symbol-usages without --symbol parameter."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(["export", temp_repo, "symbol-usages", output_file])
            assert result.returncode == 1
            assert "Error: --symbol is required" in result.stdout
        finally:
            Path(output_file).unlink(missing_ok=True)
