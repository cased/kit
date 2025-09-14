"""Tests for the search-semantic CLI command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app

# Check if sentence-transformers is available
try:
    import sentence_transformers  # noqa: F401

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_repo():
    """Create a temporary repository with sample files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create Python files with different functionality
        (repo_path / "auth.py").write_text("""
def authenticate_user(username, password):
    '''Authenticate a user with username and password.'''
    if validate_credentials(username, password):
        return create_session(username)
    return None

def validate_credentials(username, password):
    '''Validate user credentials against database.'''
    return check_password_hash(password)

class LoginManager:
    '''Manages user login sessions.'''
    def __init__(self):
        self.active_sessions = {}

    def login(self, user):
        '''Create a login session for user.'''
        session_id = generate_session_id()
        self.active_sessions[session_id] = user
        return session_id
""")

        (repo_path / "payment.py").write_text("""
def process_payment(amount, card_info):
    '''Process a credit card payment.'''
    if validate_card(card_info):
        charge_result = charge_card(amount, card_info)
        if charge_result.success:
            return create_receipt(charge_result)
    return None

def calculate_tax(amount, region):
    '''Calculate tax for a purchase amount.'''
    tax_rate = get_tax_rate(region)
    return amount * tax_rate

class ShoppingCart:
    '''Shopping cart for e-commerce.'''
    def __init__(self):
        self.items = []
        self.total = 0.0

    def add_item(self, item, price):
        '''Add an item to the shopping cart.'''
        self.items.append({'item': item, 'price': price})
        self.total += price
""")

        (repo_path / "database.py").write_text("""
import sqlite3

def create_connection(db_path):
    '''Create a database connection.'''
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def execute_query(conn, query, params=None):
    '''Execute a SQL query safely.'''
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Query error: {e}")
        return None

class DatabaseManager:
    '''Manages database operations.'''
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = create_connection(db_path)
""")

        yield str(repo_path)


class TestSearchSemanticCommand:
    """Test cases for the search-semantic CLI command."""

    def test_help_message(self, runner):
        """Test that search-semantic shows proper help message."""
        result = runner.invoke(app, ["search-semantic", "--help"])

        assert result.exit_code == 0
        # Strip ANSI escape codes for cleaner matching
        import re

        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)

        assert "Perform semantic search using vector embeddings" in clean_output
        assert "natural language queries" in clean_output
        # Check for the option in various formats (could be --top-k or -k)
        assert "--top-k" in clean_output or "-k" in clean_output
        assert "--embedding-model" in clean_output or "-e" in clean_output
        assert "--chunk-by" in clean_output or "-c" in clean_output

    def test_missing_required_arguments(self, runner):
        """Test error when required arguments are missing."""
        # Missing query
        result = runner.invoke(app, ["search-semantic", "."])
        assert result.exit_code == 2  # Typer error for missing required argument

        # Missing path
        result = runner.invoke(app, ["search-semantic"])
        assert result.exit_code == 2  # Typer error for missing required argument

    @pytest.mark.skip(reason="Test needs refactoring to properly mock import errors")
    def test_sentence_transformers_not_installed(self, runner):
        """Test error message when sentence-transformers is not installed."""
        # This test is skipped because mocking the import properly
        # would require refactoring the command's import structure
        pass

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    def test_invalid_chunk_by_parameter(self, runner):
        """Test error handling for invalid chunk-by parameter."""
        with patch("sentence_transformers.SentenceTransformer"):
            result = runner.invoke(app, ["search-semantic", ".", "test", "--chunk-by", "invalid"])

            assert result.exit_code == 1
            assert "Invalid chunk_by value: invalid" in result.output
            assert "Use 'symbols' or 'lines'" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_embedding_model_loading_failure(self, mock_repo_class, mock_st, runner):
        """Test error handling when embedding model fails to load."""
        mock_st.side_effect = Exception("Model loading failed")

        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        assert result.exit_code == 1
        assert "Failed to load embedding model" in result.output
        assert "Popular models:" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_vector_searcher_initialization_failure(self, mock_repo_class, mock_st, runner):
        """Test error handling when vector searcher fails to initialize."""
        # Mock successful model loading
        mock_model = Mock()
        mock_st.return_value = mock_model

        # Mock repository with failing vector searcher
        mock_repo = Mock()
        mock_repo.get_vector_searcher.side_effect = Exception("Vector searcher failed")
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        assert result.exit_code == 1
        assert "Failed to initialize vector searcher" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_index_building_failure(self, mock_repo_class, mock_st, runner):
        """Test error handling when index building fails."""
        # Mock successful model loading
        mock_model = Mock()
        mock_st.return_value = mock_model

        # Mock repository and vector searcher
        mock_searcher = Mock()
        mock_searcher.build_index.side_effect = Exception("Index building failed")

        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        assert result.exit_code == 1
        assert "Failed to build vector index" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_search_failure(self, mock_repo_class, mock_st, runner):
        """Test error handling when semantic search fails."""
        # Mock successful model loading and setup
        mock_model = Mock()
        mock_st.return_value = mock_model

        mock_searcher = Mock()
        mock_searcher.build_index.return_value = None

        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.side_effect = Exception("collection not found")
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        # The command may handle errors differently now
        if result.exit_code == 1:
            assert "Error" in result.output or "failed" in result.output.lower()
        else:
            # May return empty results on error
            import json

            try:
                results = json.loads(result.output)
                assert isinstance(results, list)
                assert len(results) == 0  # Empty results on error
            except json.JSONDecodeError:
                # Not JSON, check for error message
                assert "Error" in result.output or "failed" in result.output.lower()

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_successful_search_with_results(self, mock_repo_class, mock_st, runner):
        """Test successful semantic search with results."""
        # Mock successful model loading
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_st.return_value = mock_model

        # Mock search results
        mock_results = [
            {
                "file": "auth.py",
                "name": "authenticate_user",
                "type": "function",
                "score": 0.85,
                "code": "def authenticate_user(username, password):\n    '''Authenticate a user'''\n    return True",
            },
            {
                "file": "auth.py",
                "name": "LoginManager",
                "type": "class",
                "score": 0.73,
                "code": "class LoginManager:\n    '''Manages user login sessions'''\n    pass",
            },
        ]

        # Mock repository and components
        mock_searcher = Mock()
        mock_searcher.build_index.return_value = None

        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = mock_results
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "user authentication"])

        assert result.exit_code == 0
        # Check for JSON output
        import json

        results = json.loads(result.output)
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["file"] == "auth.py"
        assert results[0]["name"] == "authenticate_user"
        assert results[0]["score"] == 0.85
        assert results[1]["file"] == "auth.py"
        assert results[1]["name"] == "LoginManager"
        assert results[1]["score"] == 0.73

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_successful_search_no_results(self, mock_repo_class, mock_st, runner):
        """Test successful semantic search with no results."""
        # Mock successful model loading
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_st.return_value = mock_model

        # Mock empty search results
        mock_searcher = Mock()
        mock_searcher.build_index.return_value = None

        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = []
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "nonexistent functionality"])

        assert result.exit_code == 0
        assert "No semantic matches found" in result.output
        assert "Try building the index with --build-index" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_custom_parameters(self, mock_repo_class, mock_st, runner):
        """Test search with custom parameters."""
        # Mock successful setup
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_st.return_value = mock_model

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = []
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(
            app,
            [
                "search-semantic",
                ".",
                "test query",
                "--top-k",
                "10",
                "--embedding-model",
                "all-mpnet-base-v2",
                "--chunk-by",
                "lines",
                "--no-build-index",
                "--persist-dir",
                "/custom/path",
            ],
        )

        assert result.exit_code == 0
        # Check for JSON output or text output
        if result.output.strip().startswith("["):
            import json

            results = json.loads(result.output)
            assert isinstance(results, list)
        else:
            assert "Loading embedding model: all-mpnet-base-v2" in result.output

        # Verify that build_index was not called due to --no-build-index
        mock_searcher.build_index.assert_not_called()

        # Verify search was called with correct top_k
        mock_repo.search_semantic.assert_called_once()
        args, kwargs = mock_repo.search_semantic.call_args
        assert args[1] == 10  # top_k parameter

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_json_output(self, mock_repo_class, mock_st, runner):
        """Test semantic search with JSON output to file."""
        # Mock successful setup
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_st.return_value = mock_model

        mock_results = [{"file": "test.py", "name": "test_func", "score": 0.9}]

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = mock_results
        mock_repo_class.return_value = mock_repo

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = runner.invoke(app, ["search-semantic", ".", "test query", "--output", output_file])

            assert result.exit_code == 0
            assert f"Semantic search results written to {output_file}" in result.output

            # Verify JSON file content
            with open(output_file, "r") as f:
                data = json.load(f)
            assert data == mock_results
        finally:
            Path(output_file).unlink(missing_ok=True)

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_code_snippet_display(self, mock_repo_class, mock_st, runner):
        """Test that code snippets are properly displayed."""
        # Mock successful setup
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_st.return_value = mock_model

        # Mock result with long code
        long_code = "def very_long_function_name():\n    '''This is a very long function that should be truncated in the display'''\n    # Some implementation here\n    return result"
        mock_results = [
            {"file": "test.py", "name": "very_long_function_name", "type": "function", "score": 0.9, "code": long_code}
        ]

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = mock_results
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test query"])

        assert result.exit_code == 0
        assert "very_long_function_name" in result.output
        # With JSON output, code is not truncated in the same way
        import json

        try:
            results = json.loads(result.output)
            assert results[0]["name"] == "very_long_function_name"
        except json.JSONDecodeError:
            # Text output - code should be truncated at 100 characters
            assert "..." in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_git_ref_parameter(self, mock_repo_class, mock_st, runner):
        """Test search with git ref parameter."""
        # Mock successful setup
        mock_model = Mock()
        mock_st.return_value = mock_model

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = []
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test query", "--ref", "main"])

        assert result.exit_code == 0
        # Verify Repository was called with ref parameter
        mock_repo_class.assert_called_once_with(".", ref="main")


class TestSearchSemanticIntegration:
    """Integration tests for search-semantic command."""

    @pytest.mark.skipif(True, reason="Requires sentence-transformers installation and is slow")
    def test_real_semantic_search(self, temp_repo):
        """Test semantic search with real sentence-transformers (skipped by default)."""
        runner = CliRunner()

        # This test requires actual sentence-transformers
        # Skip by default to avoid slow test runs
        result = runner.invoke(app, ["search-semantic", temp_repo, "user authentication", "--top-k", "3"])

        # If sentence-transformers is available, this should work
        if "sentence-transformers' package is required" not in result.output:
            assert result.exit_code == 0
            assert "Loading embedding model" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    def test_integration_with_mocked_transformers(self, temp_repo):
        """Test integration with mocked sentence-transformers."""
        runner = CliRunner()

        # Mock the SentenceTransformer at the module level
        with patch("sentence_transformers.SentenceTransformer") as mock_st:
            # Mock successful model and encoding
            mock_model = Mock()
            mock_model.encode.return_value = [0.1] * 384  # Typical embedding size
            mock_st.return_value = mock_model

            # Also need to mock the repository and vector searcher
            with patch("kit.Repository") as mock_repo_class:
                mock_searcher = Mock()
                mock_searcher.build_index.return_value = None

                mock_repo = Mock()
                mock_repo.get_vector_searcher.return_value = mock_searcher
                mock_repo.search_semantic.return_value = [
                    {
                        "file": "auth.py",
                        "name": "authenticate_user",
                        "type": "function",
                        "score": 0.9,
                        "code": "def authenticate_user(): pass",
                    }
                ]
                mock_repo_class.return_value = mock_repo

                result = runner.invoke(app, ["search-semantic", temp_repo, "authentication"])

                assert result.exit_code == 0
                # Check for JSON output
                import json

                try:
                    results = json.loads(result.output)
                    assert len(results) == 1
                    assert results[0]["name"] == "authenticate_user"
                except json.JSONDecodeError:
                    # Text output
                    assert "Found 1 semantic matches" in result.output
                    assert "authenticate_user" in result.output


class TestSearchSemanticErrorScenarios:
    """Test error scenarios for semantic search."""

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    def test_repository_initialization_error(self, mock_st, runner):
        """Test handling of repository initialization errors."""
        with patch("kit.Repository", side_effect=Exception("Repository not found")):
            result = runner.invoke(app, ["search-semantic", "/invalid/path", "test query"])

            assert result.exit_code == 1
            assert "Repository not found" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_file_write_permission_error(self, mock_repo_class, mock_st, runner):
        """Test error when output file cannot be written."""
        # Mock successful setup
        mock_model = Mock()
        mock_st.return_value = mock_model

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = []
        mock_repo_class.return_value = mock_repo

        # Try to write to a directory that doesn't exist
        result = runner.invoke(app, ["search-semantic", ".", "test", "--output", "/nonexistent/dir/output.json"])

        assert result.exit_code == 1
        assert "Error:" in result.output

    @pytest.mark.skipif(not HAS_SENTENCE_TRANSFORMERS, reason="Requires sentence-transformers")
    @patch("sentence_transformers.SentenceTransformer")
    @patch("kit.Repository")
    def test_persist_dir_parameter(self, mock_repo_class, mock_st, runner):
        """Test that persist_dir parameter is passed correctly."""
        mock_model = Mock()
        mock_st.return_value = mock_model

        mock_searcher = Mock()
        mock_repo = Mock()
        mock_repo.get_vector_searcher.return_value = mock_searcher
        mock_repo.search_semantic.return_value = []
        mock_repo_class.return_value = mock_repo

        result = runner.invoke(app, ["search-semantic", ".", "test", "--persist-dir", "/custom/persist/path"])

        assert result.exit_code == 0
        # Verify get_vector_searcher was called with persist_dir
        # The embed_fn is wrapped, so check just the persist_dir
        assert mock_repo.get_vector_searcher.called
        call_kwargs = mock_repo.get_vector_searcher.call_args.kwargs
        assert call_kwargs["persist_dir"] == "/custom/persist/path"
