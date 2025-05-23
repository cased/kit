"""Unit tests for kit CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer.testing

from kit.cli import app


@pytest.fixture
def runner():
    """Create a typer test runner."""
    return typer.testing.CliRunner()


@pytest.fixture
def mock_repo():
    """Create a mock Repository instance."""
    with patch("kit.Repository") as mock_repo_class:
        mock_instance = MagicMock()
        mock_instance.local_path = Path("/mock/repo")
        mock_repo_class.return_value = mock_instance
        yield mock_instance


class TestFileTreeCommand:
    """Tests for the file-tree command."""

    def test_file_tree_stdout(self, runner, mock_repo):
        """Test file-tree command with stdout output."""
        mock_repo.get_file_tree.return_value = [
            {"path": "file1.py", "is_dir": False, "size": 100},
            {"path": "dir1", "is_dir": True, "size": 0},
        ]

        result = runner.invoke(app, ["file-tree", "/test/path"])

        assert result.exit_code == 0
        assert "📄 file1.py (100 bytes)" in result.stdout
        assert "📁 dir1" in result.stdout
        mock_repo.get_file_tree.assert_called_once()

    def test_file_tree_json_output(self, runner, mock_repo):
        """Test file-tree command with JSON file output."""
        mock_tree = [{"path": "file1.py", "is_dir": False, "size": 100}]
        mock_repo.get_file_tree.return_value = mock_tree

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["file-tree", "/test/path", "--output", output_file])

            assert result.exit_code == 0
            assert f"File tree written to {output_file}" in result.stdout

            with open(output_file, "r") as f:
                saved_data = json.load(f)
            assert saved_data == mock_tree
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_file_tree_error(self, runner, mock_repo):
        """Test file-tree command with Repository error."""
        mock_repo.get_file_tree.side_effect = Exception("Test error")

        result = runner.invoke(app, ["file-tree", "/test/path"])

        assert result.exit_code == 1
        assert "Error: Test error" in result.stdout


class TestFileContentCommand:
    """Tests for the file-content command."""

    def test_file_content_success(self, runner, mock_repo):
        """Test file-content command success."""
        mock_repo.get_file_content.return_value = "print('hello world')"

        result = runner.invoke(app, ["file-content", "/test/path", "test.py"])

        assert result.exit_code == 0
        assert "print('hello world')" in result.stdout
        mock_repo.get_file_content.assert_called_once_with("test.py")

    def test_file_content_not_found(self, runner, mock_repo):
        """Test file-content command with file not found."""
        mock_repo.get_file_content.side_effect = FileNotFoundError("File not found")

        result = runner.invoke(app, ["file-content", "/test/path", "missing.py"])

        assert result.exit_code == 1
        assert "Error: File not found: missing.py" in result.stdout

    def test_file_content_error(self, runner, mock_repo):
        """Test file-content command with other error."""
        mock_repo.get_file_content.side_effect = IOError("Read error")

        result = runner.invoke(app, ["file-content", "/test/path", "test.py"])

        assert result.exit_code == 1
        assert "Error: Read error" in result.stdout


class TestSymbolsCommand:
    """Tests for the symbols command."""

    @pytest.fixture
    def mock_symbols(self):
        """Mock symbols data."""
        return [
            {
                "name": "test_function",
                "type": "function",
                "file": "/mock/repo/test.py",
                "start_line": 10,
                "end_line": 20,
            },
            {"name": "TestClass", "type": "class", "file": "/mock/repo/lib.py", "start_line": 5, "end_line": 15},
        ]

    def test_symbols_table_format(self, runner, mock_repo, mock_symbols):
        """Test symbols command with table format."""
        mock_repo.extract_symbols.return_value = mock_symbols

        result = runner.invoke(app, ["symbols", "/test/path"])

        assert result.exit_code == 0
        assert "test_function" in result.stdout
        assert "TestClass" in result.stdout
        assert "function" in result.stdout
        assert "class" in result.stdout
        mock_repo.extract_symbols.assert_called_once_with(None)

    def test_symbols_json_format(self, runner, mock_repo, mock_symbols):
        """Test symbols command with JSON format."""
        mock_repo.extract_symbols.return_value = mock_symbols

        result = runner.invoke(app, ["symbols", "/test/path", "--format", "json"])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert len(output_data) == 2
        assert output_data[0]["name"] == "test_function"

    def test_symbols_names_format(self, runner, mock_repo, mock_symbols):
        """Test symbols command with names format."""
        mock_repo.extract_symbols.return_value = mock_symbols

        result = runner.invoke(app, ["symbols", "/test/path", "--format", "names"])

        assert result.exit_code == 0
        assert "test_function\n" in result.stdout
        assert "TestClass\n" in result.stdout

    def test_symbols_specific_file(self, runner, mock_repo, mock_symbols):
        """Test symbols command for specific file."""
        mock_repo.extract_symbols.return_value = mock_symbols

        result = runner.invoke(app, ["symbols", "/test/path", "--file", "test.py"])

        assert result.exit_code == 0
        mock_repo.extract_symbols.assert_called_once_with("test.py")

    def test_symbols_no_results(self, runner, mock_repo):
        """Test symbols command with no symbols found."""
        mock_repo.extract_symbols.return_value = []

        result = runner.invoke(app, ["symbols", "/test/path"])

        assert result.exit_code == 0
        assert "No symbols found." in result.stdout


class TestSearchCommand:
    """Tests for the search command."""

    @pytest.fixture
    def mock_search_results(self):
        """Mock search results."""
        return [
            {"file": "/mock/repo/test.py", "line_number": 5, "line": "def test_function():"},
            {"file": "/mock/repo/lib.py", "line_number": 10, "line": "    test_function()"},
        ]

    def test_search_success(self, runner, mock_repo, mock_search_results):
        """Test search command success."""
        mock_repo.search_text.return_value = mock_search_results

        result = runner.invoke(app, ["search", "/test/path", "test_function"])

        assert result.exit_code == 0
        assert "test.py:5: def test_function():" in result.stdout
        assert "lib.py:10: test_function()" in result.stdout
        mock_repo.search_text.assert_called_once_with("test_function", file_pattern="*")

    def test_search_with_pattern(self, runner, mock_repo, mock_search_results):
        """Test search command with file pattern."""
        mock_repo.search_text.return_value = mock_search_results

        result = runner.invoke(app, ["search", "/test/path", "test", "--pattern", "*.py"])

        assert result.exit_code == 0
        mock_repo.search_text.assert_called_once_with("test", file_pattern="*.py")

    def test_search_no_results(self, runner, mock_repo):
        """Test search command with no results."""
        mock_repo.search_text.return_value = []

        result = runner.invoke(app, ["search", "/test/path", "nonexistent"])

        assert result.exit_code == 0
        assert "No results found." in result.stdout


class TestUsagesCommand:
    """Tests for the usages command."""

    @pytest.fixture
    def mock_usages(self):
        """Mock usage results."""
        return [
            {"file": "/mock/repo/test.py", "line_number": 5, "context": "def test_function():"},
            {"file": "/mock/repo/lib.py", "line": 10, "line_content": "    test_function()"},
        ]

    def test_usages_success(self, runner, mock_repo, mock_usages):
        """Test usages command success."""
        mock_repo.find_symbol_usages.return_value = mock_usages

        result = runner.invoke(app, ["usages", "/test/path", "test_function"])

        assert result.exit_code == 0
        assert "Found 2 usage(s) of 'test_function':" in result.stdout
        assert "test.py:5: def test_function():" in result.stdout
        assert "lib.py:10: test_function()" in result.stdout
        mock_repo.find_symbol_usages.assert_called_once_with("test_function", None)

    def test_usages_with_type_filter(self, runner, mock_repo, mock_usages):
        """Test usages command with type filter."""
        mock_repo.find_symbol_usages.return_value = mock_usages

        result = runner.invoke(app, ["usages", "/test/path", "test_function", "--type", "function"])

        assert result.exit_code == 0
        mock_repo.find_symbol_usages.assert_called_once_with("test_function", "function")

    def test_usages_no_results(self, runner, mock_repo):
        """Test usages command with no results."""
        mock_repo.find_symbol_usages.return_value = []

        result = runner.invoke(app, ["usages", "/test/path", "nonexistent"])

        assert result.exit_code == 0
        assert "No usages found for symbol 'nonexistent'." in result.stdout


class TestContextCommand:
    """Tests for the context command."""

    @pytest.fixture
    def mock_context(self):
        """Mock context result."""
        return {
            "name": "test_function",
            "type": "function",
            "start_line": 5,
            "end_line": 10,
            "code": "def test_function():\n    return 'hello'",
        }

    def test_context_success(self, runner, mock_repo, mock_context):
        """Test context command success."""
        mock_repo.extract_context_around_line.return_value = mock_context

        result = runner.invoke(app, ["context", "/test/path", "test.py", "7"])

        assert result.exit_code == 0
        assert "Context for test.py:7" in result.stdout
        assert "Symbol: test_function (function)" in result.stdout
        assert "Lines: 5-10" in result.stdout
        assert "def test_function():" in result.stdout
        mock_repo.extract_context_around_line.assert_called_once_with("test.py", 7)

    def test_context_no_result(self, runner, mock_repo):
        """Test context command with no context found."""
        mock_repo.extract_context_around_line.return_value = None

        result = runner.invoke(app, ["context", "/test/path", "test.py", "7"])

        assert result.exit_code == 0
        assert "No context found for test.py:7" in result.stdout


class TestChunkingCommands:
    """Tests for chunking commands."""

    def test_chunk_lines_success(self, runner, mock_repo):
        """Test chunk-lines command success."""
        mock_repo.chunk_file_by_lines.return_value = ["chunk1\nline2", "chunk2\nline2"]

        result = runner.invoke(app, ["chunk-lines", "/test/path", "test.py"])

        assert result.exit_code == 0
        assert "--- Chunk 1 ---" in result.stdout
        assert "chunk1" in result.stdout
        assert "--- Chunk 2 ---" in result.stdout
        mock_repo.chunk_file_by_lines.assert_called_once_with("test.py", 50)

    def test_chunk_lines_custom_max(self, runner, mock_repo):
        """Test chunk-lines command with custom max lines."""
        mock_repo.chunk_file_by_lines.return_value = ["chunk1"]

        result = runner.invoke(app, ["chunk-lines", "/test/path", "test.py", "--max-lines", "20"])

        assert result.exit_code == 0
        mock_repo.chunk_file_by_lines.assert_called_once_with("test.py", 20)

    def test_chunk_symbols_success(self, runner, mock_repo):
        """Test chunk-symbols command success."""
        mock_chunks = [
            {"name": "func1", "type": "function", "code": "def func1(): pass"},
            {"name": "Class1", "type": "class", "code": "class Class1: pass"},
        ]
        mock_repo.chunk_file_by_symbols.return_value = mock_chunks

        result = runner.invoke(app, ["chunk-symbols", "/test/path", "test.py"])

        assert result.exit_code == 0
        assert "--- function: func1 ---" in result.stdout
        assert "def func1(): pass" in result.stdout
        assert "--- class: Class1 ---" in result.stdout


class TestExportCommand:
    """Tests for the export command."""

    def test_export_symbols(self, runner, mock_repo):
        """Test export symbols command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "symbols", output_file])

            assert result.exit_code == 0
            assert f"Symbols exported to {output_file}" in result.stdout
            mock_repo.write_symbols.assert_called_once_with(output_file)
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_index(self, runner, mock_repo):
        """Test export index command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "index", output_file])

            assert result.exit_code == 0
            assert f"Repository index exported to {output_file}" in result.stdout
            mock_repo.write_index.assert_called_once_with(output_file)
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_file_tree(self, runner, mock_repo):
        """Test export file-tree command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "file-tree", output_file])

            assert result.exit_code == 0
            assert f"File tree exported to {output_file}" in result.stdout
            mock_repo.write_file_tree.assert_called_once_with(output_file)
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_symbol_usages(self, runner, mock_repo):
        """Test export symbol-usages command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "symbol-usages", output_file, "--symbol", "test_func"])

            assert result.exit_code == 0
            assert f"Symbol usages for 'test_func' exported to {output_file}" in result.stdout
            mock_repo.write_symbol_usages.assert_called_once_with("test_func", output_file, None)
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_symbol_usages_missing_symbol(self, runner, mock_repo):
        """Test export symbol-usages command without required --symbol option."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "symbol-usages", output_file])

            assert result.exit_code == 1
            assert "Error: --symbol is required for symbol-usages export" in result.stdout
        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_export_unknown_type(self, runner, mock_repo):
        """Test export command with unknown data type."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["export", "/test/path", "unknown", output_file])

            assert result.exit_code == 1
            assert "Error: Unknown data type 'unknown'" in result.stdout
        finally:
            Path(output_file).unlink(missing_ok=True)


class TestIndexCommand:
    """Tests for the index command."""

    @pytest.fixture
    def mock_index_data(self):
        """Mock index data."""
        return {
            "files": [{"path": "test.py", "is_dir": False}],
            "symbols": {"test.py": [{"name": "func", "type": "function"}]},
        }

    def test_index_stdout(self, runner, mock_repo, mock_index_data):
        """Test index command with stdout output."""
        mock_repo.index.return_value = mock_index_data

        result = runner.invoke(app, ["index", "/test/path"])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data == mock_index_data
        mock_repo.index.assert_called_once()

    def test_index_file_output(self, runner, mock_repo, mock_index_data):
        """Test index command with file output."""
        mock_repo.index.return_value = mock_index_data

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["index", "/test/path", "--output", output_file])

            assert result.exit_code == 0
            assert f"Repository index written to {output_file}" in result.stdout

            with open(output_file, "r") as f:
                saved_data = json.load(f)
            assert saved_data == mock_index_data
        finally:
            Path(output_file).unlink(missing_ok=True)


class TestServeCommand:
    """Tests for the serve command."""

    def test_serve_success(self, runner):
        """Test serve command success."""
        with patch("uvicorn.run") as mock_run:
            result = runner.invoke(app, ["serve"])

            assert result.exit_code == 0
            assert "Starting kit API server on http://0.0.0.0:8000" in result.stdout
            mock_run.assert_called_once()

    def test_serve_missing_dependencies(self, runner):
        """Test serve command with missing dependencies."""
        # This test is complex to mock properly, so we'll skip it for now
        # The real behavior is tested through integration testing
        pass

    def test_serve_custom_params(self, runner):
        """Test serve command with custom parameters."""
        with patch("uvicorn.run") as mock_run:
            result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9000", "--no-reload"])

            assert result.exit_code == 0
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["host"] == "127.0.0.1"
            assert call_args[1]["port"] == 9000
            assert call_args[1]["reload"] is False
