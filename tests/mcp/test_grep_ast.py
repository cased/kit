"""Tests for grep_ast functionality in MCP server."""

from unittest.mock import Mock, patch

import pytest

from kit.mcp.dev_server import KitServerLogic


class TestGrepAST:
    """Test the grep_ast tool in MCP server."""

    @pytest.fixture
    def logic(self):
        return KitServerLogic()

    @pytest.fixture
    def mock_repo(self):
        repo = Mock()
        repo.repo_path = "/test/repo"
        return repo

    def test_grep_ast_simple_mode(self, logic, mock_repo):
        """Test grep_ast with simple mode."""
        logic._repos = {"repo1": mock_repo}

        with patch("kit.mcp.dev_server.ASTSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search_pattern.return_value = [
                {
                    "file": "test.py",
                    "line": 10,
                    "column": 0,
                    "type": "function_definition",
                    "text": "async def test_function():\n    pass",
                    "context": {"node_type": "function_definition"},
                }
            ]
            mock_searcher_class.return_value = mock_searcher

            result = logic.grep_ast(
                repo_id="repo1", pattern="async def", mode="simple", file_pattern="**/*.py", max_results=10
            )

            assert len(result) == 1
            assert result[0]["file"] == "test.py"
            assert result[0]["line"] == 10
            assert result[0]["type"] == "function_definition"
            assert "preview" in result[0]

            # Check that search was called correctly
            mock_searcher.search_pattern.assert_called_once_with(
                pattern="async def", file_pattern="**/*.py", mode="simple", max_results=10
            )

    def test_grep_ast_pattern_mode(self, logic, mock_repo):
        """Test grep_ast with pattern mode."""
        logic._repos = {"repo1": mock_repo}

        with patch("kit.mcp.dev_server.ASTSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search_pattern.return_value = [
                {
                    "file": "error_handler.py",
                    "line": 25,
                    "column": 4,
                    "type": "try_statement",
                    "text": "try:\n    risky_operation()\nexcept Exception as e:\n    log(e)",
                    "context": {"node_type": "try_statement", "parent_function_definition": "handle_error"},
                }
            ]
            mock_searcher_class.return_value = mock_searcher

            result = logic.grep_ast(
                repo_id="repo1",
                pattern='{"type": "try_statement"}',
                mode="pattern",
                file_pattern="**/*.py",
                max_results=5,
            )

            assert len(result) == 1
            assert result[0]["type"] == "try_statement"
            assert result[0]["file"] == "error_handler.py"

    def test_grep_ast_no_truncation(self, logic, mock_repo):
        """Test that grep_ast no longer truncates text."""
        logic._repos = {"repo1": mock_repo}

        long_text = "def long_function():\n" + "    pass\n" * 200

        with patch("kit.mcp.dev_server.ASTSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search_pattern.return_value = [
                {
                    "file": "long.py",
                    "line": 1,
                    "column": 0,
                    "type": "function_definition",
                    "text": long_text,
                    "context": {"node_type": "function_definition"},
                }
            ]
            mock_searcher_class.return_value = mock_searcher

            result = logic.grep_ast(
                repo_id="repo1", pattern="def", mode="simple", file_pattern="**/*.py", max_results=1
            )

            # Check that text is NOT truncated anymore
            assert result[0]["text"] == long_text  # Full text returned
            assert len(result[0]["preview"]) <= 103  # Preview still limited

    def test_grep_ast_max_results_limit(self, logic, mock_repo):
        """Test that grep_ast no longer enforces artificial limit."""
        logic._repos = {"repo1": mock_repo}

        # Create more results than allowed
        many_results = [
            {
                "file": f"file{i}.py",
                "line": i,
                "column": 0,
                "type": "function_definition",
                "text": f"def func{i}(): pass",
                "context": {},
            }
            for i in range(50)
        ]

        with patch("kit.mcp.dev_server.ASTSearcher") as mock_searcher_class:
            mock_searcher = Mock()

            # Mock should return limited results based on max_results passed
            def mock_search(pattern, file_pattern, mode, max_results):
                return many_results[:max_results]

            mock_searcher.search_pattern.side_effect = mock_search
            mock_searcher_class.return_value = mock_searcher

            result = logic.grep_ast(
                repo_id="repo1",
                pattern="def",
                mode="simple",
                file_pattern="**/*.py",
                max_results=50,  # Request 50 and get 50
            )

            # Should get all 50 results (no artificial limit)
            assert len(result) == 50

            # Verify the searcher was called with the requested max_results
            mock_searcher.search_pattern.assert_called_once_with(
                pattern="def",
                file_pattern="**/*.py",
                mode="simple",
                max_results=50,  # Should pass through unchanged
            )
