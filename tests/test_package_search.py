"""Tests for Chroma Package Search integration."""

from unittest.mock import MagicMock, patch

import pytest

from kit.package_search import ChromaPackageSearch


class TestChromaPackageSearch:
    """Test suite for ChromaPackageSearch client."""

    @pytest.fixture
    def mock_api_key(self, monkeypatch):
        """Set mock API key for tests."""
        monkeypatch.setenv("CHROMA_PACKAGE_SEARCH_API_KEY", "test_api_key")

    @pytest.fixture
    def client(self, mock_api_key):
        """Create a ChromaPackageSearch client with mocked API key."""
        return ChromaPackageSearch()

    def test_init_with_api_key_env(self, mock_api_key):
        """Test initialization with environment variable."""
        client = ChromaPackageSearch()
        assert client.api_key == "test_api_key"

    def test_init_with_explicit_api_key(self):
        """Test initialization with explicit API key."""
        client = ChromaPackageSearch(api_key="explicit_key")
        assert client.api_key == "explicit_key"

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("CHROMA_PACKAGE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("CHROMA_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Chroma Package Search API key not found"):
            ChromaPackageSearch()

    @patch("kit.package_search.httpx.Client")
    def test_grep_success(self, mock_httpx, client):
        """Test successful grep search."""
        # Setup mock SSE response like the real API
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"result\\":{\\"file_path\\":\\"numpy/core/fft.py\\",\\"start_line\\":42,\\"content\\":\\"def fft(a, n=None, axis=-1):\\"}}]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        results = client.grep(package="numpy", pattern="def fft", max_results=10)

        # Verify
        assert len(results) == 1
        assert results[0]["file_path"] == "numpy/core/fft.py"
        assert results[0]["line_number"] == 42

        # Check API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://mcp.trychroma.com/package-search/v1"
        payload = call_args[1]["json"]
        assert payload["method"] == "tools/call"
        assert payload["params"]["name"] == "package_search_grep"
        assert payload["params"]["arguments"]["package_name"] == "numpy"
        assert payload["params"]["arguments"]["pattern"] == "def fft"

    @patch("kit.package_search.httpx.Client")
    def test_hybrid_search_success(self, mock_httpx, client):
        """Test successful hybrid search."""
        # Setup mock SSE response
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"id\\":\\"abc123\\",\\"document\\":\\"class AuthenticationMiddleware:\\",\\"metadata\\":{\\"filename\\":\\"django/contrib/auth/middleware.py\\",\\"start_line\\":10}}]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        results = client.hybrid_search(package="django", query="authentication middleware", max_results=5)

        # Verify
        assert len(results) == 1
        assert results[0]["file_path"] == "django/contrib/auth/middleware.py"
        assert results[0]["snippet"] == "class AuthenticationMiddleware:"
        assert results[0]["line_number"] == 10

        # Check API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://mcp.trychroma.com/package-search/v1"
        payload = call_args[1]["json"]
        assert payload["method"] == "tools/call"
        assert payload["params"]["name"] == "package_search_hybrid"
        assert payload["params"]["arguments"]["semantic_queries"] == ["authentication middleware"]

    @patch("kit.package_search.httpx.Client")
    def test_read_file_success(self, mock_httpx, client):
        """Test successful file reading."""
        # Setup mock for both grep (to get SHA256) and read_file
        mock_grep_response = MagicMock()
        mock_grep_response.headers = {"content-type": "text/event-stream"}
        mock_grep_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"result\\":{\\"file_path\\":\\"requests/models.py\\",\\"filename_sha256\\":\\"abc123sha256\\",\\"content\\":\\"import\\"}}]}"}],"isError":false}}'
        mock_grep_response.raise_for_status = MagicMock()

        mock_read_response = MagicMock()
        mock_read_response.headers = {"content-type": "text/event-stream"}
        mock_read_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"content\\":\\"import requests\\\\n\\\\nclass Response:\\\\n    pass\\"}"}],"isError":false}}'
        mock_read_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        # Return different responses for grep vs read_file calls
        mock_client.post.side_effect = [mock_grep_response, mock_read_response]
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        content = client.read_file(package="requests", file_path="requests/models.py", start_line=1, end_line=10)

        # Verify
        assert "import requests" in content
        assert "class Response" in content

        # Check API calls (grep for SHA256, then read_file)
        assert mock_client.post.call_count == 2

        # First call should be grep to get SHA256
        first_call = mock_client.post.call_args_list[0]
        assert first_call[0][0] == "https://mcp.trychroma.com/package-search/v1"
        grep_payload = first_call[1]["json"]
        assert grep_payload["params"]["name"] == "package_search_grep"

        # Second call should be read_file with SHA256
        second_call = mock_client.post.call_args_list[1]
        read_payload = second_call[1]["json"]
        assert read_payload["params"]["name"] == "package_search_read_file"
        assert read_payload["params"]["arguments"]["file_path"] == "requests/models.py"
        assert read_payload["params"]["arguments"]["filename_sha256"] == "abc123sha256"

    @patch("kit.package_search.httpx.Client")
    def test_api_error_handling(self, mock_httpx, client):
        """Test API error handling."""
        import httpx

        # Setup mock response with 401 error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute and verify
        with pytest.raises(ValueError, match="Invalid Chroma API key"):
            client.grep(package="numpy", pattern="test")

    @patch("kit.package_search.httpx.Client")
    def test_package_not_found(self, mock_httpx, client):
        """Test handling of package not found error."""
        import httpx

        # Setup mock response with 404 error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute and verify
        with pytest.raises(ValueError, match="Package 'nonexistent' not found"):
            client.grep(package="nonexistent", pattern="test")

    @patch("kit.package_search.httpx.Client")
    def test_mcp_response_parsing(self, mock_httpx, client):
        """Test parsing of MCP SSE response format."""
        # Setup mock SSE response like the real API returns
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"result\\":{\\"content\\":\\"def fft(a, n=None):\\",\\"file_path\\":\\"numpy/fft.py\\",\\"start_line\\":42}}]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        results = client.grep(package="numpy", pattern="def fft")

        # Verify
        assert len(results) == 1
        assert results[0]["file_path"] == "numpy/fft.py"
        assert results[0]["line_number"] == 42
        assert "def fft" in results[0]["content"]

    @patch("kit.package_search.httpx.Client")
    def test_empty_results(self, mock_httpx, client):
        """Test handling of empty search results."""
        # Setup mock response with empty results
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        results = client.grep(package="numpy", pattern="nonexistent_pattern")

        # Verify
        assert results == []

    @patch("kit.package_search.httpx.Client")
    def test_hybrid_search_with_filter(self, mock_httpx, client):
        """Test hybrid search with regex filter."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"id\\":\\"xyz456\\",\\"document\\":\\"Authentication middleware\\",\\"metadata\\":{\\"filename\\":\\"django/auth.py\\"},\\"distance\\":0.95}]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        results = client.hybrid_search(
            package="django", query="authentication", regex_filter="class.*Auth", max_results=5
        )

        # Verify
        assert len(results) == 1
        assert results[0]["file_path"] == "django/auth.py"
        assert results[0]["snippet"] == "Authentication middleware"
        # Score is mapped from distance field
        assert results[0]["snippet"] == "Authentication middleware"

        # Check API call includes filter
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["arguments"]["regex_filter"] == "class.*Auth"

    @patch("kit.package_search.httpx.Client")
    def test_read_file_with_line_range(self, mock_httpx, client):
        """Test reading file with specific line range."""
        # Setup mock for both grep and read_file
        mock_grep_response = MagicMock()
        mock_grep_response.headers = {"content-type": "text/event-stream"}
        mock_grep_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"result\\":{\\"file_path\\":\\"requests/models.py\\",\\"filename_sha256\\":\\"xyz789sha256\\",\\"content\\":\\"class\\"}}]}"}],"isError":false}}'
        mock_grep_response.raise_for_status = MagicMock()

        mock_read_response = MagicMock()
        mock_read_response.headers = {"content-type": "text/event-stream"}
        mock_read_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"content\\":\\"class Request:\\\\n    def __init__(self):\\\\n        pass\\"}"}],"isError":false}}'
        mock_read_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.side_effect = [mock_grep_response, mock_read_response]
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        content = client.read_file(package="requests", file_path="requests/models.py", start_line=100, end_line=103)

        # Verify
        assert "class Request:" in content
        assert "def __init__(self):" in content

        # Check both API calls were made
        assert mock_client.post.call_count == 2

        # Second call should have the line range and SHA256
        second_call = mock_client.post.call_args_list[1]
        read_payload = second_call[1]["json"]
        assert read_payload["params"]["arguments"]["start_line"] == 100
        assert read_payload["params"]["arguments"]["end_line"] == 103
        assert read_payload["params"]["arguments"]["filename_sha256"] == "xyz789sha256"

    def test_list_packages(self, client):
        """Test listing available packages."""
        packages = client.list_packages()
        assert isinstance(packages, list)
        assert len(packages) > 0
        assert "numpy" in packages
        assert "django" in packages
        assert "requests" in packages

    def test_get_package_info(self, client):
        """Test getting package metadata."""
        info = client.get_package_info("numpy")
        assert isinstance(info, dict)
        assert info["name"] == "numpy"
        assert info["registry"] == "py_pi"
        assert info["available"] is True

    @patch("kit.package_search.httpx.Client")
    def test_network_timeout(self, mock_httpx, client):
        """Test handling of network timeout."""
        import httpx

        # Setup mock to raise timeout
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute and verify
        with pytest.raises(httpx.TimeoutException):
            client.grep(package="numpy", pattern="test")

    @patch("kit.package_search.httpx.Client")
    def test_case_insensitive_search(self, mock_httpx, client):
        """Test case-insensitive grep search."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute
        client.grep(package="numpy", pattern="FFT", case_sensitive=False)

        # Verify case_sensitive flag is passed correctly
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["arguments"]["case_sensitive"] is False
