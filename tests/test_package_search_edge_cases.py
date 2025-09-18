"""Edge case tests for Package Search integration."""

from unittest.mock import MagicMock, patch

import pytest

from kit.package_search import ChromaPackageSearch


class TestPackageSearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_api_key(self, monkeypatch):
        """Set mock API key for tests."""
        monkeypatch.setenv("CHROMA_PACKAGE_SEARCH_API_KEY", "test_api_key")

    @pytest.fixture
    def client(self, mock_api_key):
        """Create a ChromaPackageSearch client."""
        return ChromaPackageSearch()

    @patch("kit.package_search.httpx.Client")
    def test_grep_with_special_characters(self, mock_httpx, client):
        """Test grep with regex special characters."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Test with special regex characters
        results = client.grep(package="test", pattern="function\\(.*\\)", max_results=10)

        assert results == []

        # Verify the pattern was passed correctly
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["arguments"]["pattern"] == "function\\(.*\\)"

    @patch("kit.package_search.httpx.Client")
    def test_hybrid_search_empty_query(self, mock_httpx, client):
        """Test hybrid search with empty query."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Test with empty query
        results = client.hybrid_search(
            package="test",
            query="",  # Empty query
            max_results=10,
        )

        assert results == []

    @patch("kit.package_search.httpx.Client")
    def test_read_file_auto_fetch_sha256_failure(self, mock_httpx, client):
        """Test read_file when auto-fetch SHA256 fails."""
        # Setup mock for grep that returns no results
        mock_grep_response = MagicMock()
        mock_grep_response.headers = {"content-type": "text/event-stream"}
        mock_grep_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_grep_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_grep_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Should raise error when can't get SHA256
        with pytest.raises(ValueError, match="Could not determine SHA256"):
            client.read_file(package="test", file_path="test/file.py", start_line=1, end_line=10)

    @patch("kit.package_search.httpx.Client")
    def test_read_file_with_provided_sha256(self, mock_httpx, client):
        """Test read_file with manually provided SHA256."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"content\\":\\"test content\\"}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Test with provided SHA256
        content = client.read_file(
            package="test",
            file_path="test/file.py",
            filename_sha256="abc123",  # Provided directly
            start_line=1,
            end_line=10,
        )

        assert content == "test content"

        # Verify grep was not called
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["name"] == "package_search_read_file"
        assert payload["params"]["arguments"]["filename_sha256"] == "abc123"

    @patch("kit.package_search.httpx.Client")
    def test_malformed_sse_response(self, mock_httpx, client):
        """Test handling of malformed SSE response."""
        # Setup mock with malformed SSE
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = "invalid sse format"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Should handle gracefully
        results = client.grep(package="test", pattern="test")
        assert results == []

    @patch("kit.package_search.httpx.Client")
    def test_network_connectivity_error(self, mock_httpx, client):
        """Test handling of network errors."""
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Should raise the underlying error
        with pytest.raises(httpx.ConnectError):
            client.grep(package="test", pattern="test")

    @patch("kit.package_search.httpx.Client")
    def test_rate_limiting_429(self, mock_httpx, client):
        """Test handling of rate limiting errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Should handle 429 gracefully
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.grep(package="test", pattern="test")

        assert exc_info.value.response.status_code == 429

    @patch("kit.package_search.httpx.Client")
    def test_truncated_results_message(self, mock_httpx, client):
        """Test handling of truncated results."""
        # Setup mock with truncation message
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[{\\"result\\":{\\"file_path\\":\\"test.py\\",\\"content\\":\\"test\\",\\"start_line\\":1}}],\\"truncation_message\\":\\"Results truncated\\"}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Should return available results
        results = client.grep(package="test", pattern="test")
        assert len(results) == 1
        assert results[0]["file_path"] == "test.py"

    def test_list_packages_returns_static_list(self, client):
        """Test that list_packages returns expected packages."""
        packages = client.list_packages()
        assert isinstance(packages, list)
        assert "numpy" in packages
        assert "requests" in packages
        assert "django" in packages

    def test_get_package_info_basic(self, client):
        """Test get_package_info returns basic structure."""
        info = client.get_package_info("test-package")
        assert isinstance(info, dict)
        assert info["name"] == "test-package"
        assert info["registry"] == "py_pi"
        assert info["available"] is True

    @patch("kit.package_search.httpx.Client")
    def test_hybrid_search_with_all_parameters(self, mock_httpx, client):
        """Test hybrid search with all optional parameters."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"results\\":[]}"}],"isError":false}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Test with all parameters
        client.hybrid_search(
            package="test",
            query="search query",
            regex_filter="test.*pattern",
            max_results=25,
            file_pattern="*.py",
            registry_name="custom_registry",
        )

        # Verify all parameters were passed
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        args = payload["params"]["arguments"]

        assert args["semantic_queries"] == ["search query"]
        assert args["regex_filter"] == "test.*pattern"
        assert args["max_results"] == 25
        assert args["file_pattern"] == "*.py"
        assert args["registry_name"] == "custom_registry"
