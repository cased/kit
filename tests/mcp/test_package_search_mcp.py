"""Tests for Package Search MCP tools integration."""

from unittest.mock import MagicMock, patch

import pytest

from kit.mcp.dev_server import LocalDevServerLogic, MCPError


class TestPackageSearchMCP:
    """Test suite for Package Search MCP integration."""

    @pytest.fixture
    def server_logic(self):
        """Create a LocalDevServerLogic instance."""
        return LocalDevServerLogic()

    @pytest.fixture
    def mock_api_key(self, monkeypatch):
        """Set mock API key for tests."""
        monkeypatch.setenv("CHROMA_PACKAGE_SEARCH_API_KEY", "test_api_key")

    @patch("kit.mcp.dev_server.ChromaPackageSearch")
    def test_package_search_grep_tool(self, mock_chroma_class, server_logic, mock_api_key):
        """Test package_search_grep MCP tool."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.grep.return_value = [
            {"file_path": "fastapi/main.py", "line_number": 10, "content": "async def startup():"}
        ]
        mock_chroma_class.return_value = mock_client

        # Execute
        results = server_logic.package_search_grep(package="fastapi", pattern="async def", max_results=10)

        # Verify - results are now wrapped in dict
        assert "results" in results
        assert len(results["results"]) == 1
        assert results["results"][0]["file_path"] == "fastapi/main.py"
        assert "async def" in results["results"][0]["content"]

        # Check that the client was called correctly
        mock_client.grep.assert_called_once_with(
            package="fastapi", pattern="async def", max_results=10, file_pattern=None, case_sensitive=True
        )

    @patch("kit.mcp.dev_server.ChromaPackageSearch")
    def test_package_search_hybrid_tool(self, mock_chroma_class, server_logic, mock_api_key):
        """Test package_search_hybrid MCP tool."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.hybrid_search.return_value = [
            {"file_path": "django/auth/middleware.py", "snippet": "Authentication middleware implementation"}
        ]
        mock_chroma_class.return_value = mock_client

        # Execute
        results = server_logic.package_search_hybrid(package="django", query="authentication", max_results=5)

        # Verify - results are now wrapped in dict
        assert "results" in results
        assert len(results["results"]) == 1
        assert results["results"][0]["file_path"] == "django/auth/middleware.py"

        # Check client call
        mock_client.hybrid_search.assert_called_once_with(
            package="django", query="authentication", regex_filter=None, max_results=5, file_pattern=None
        )

    @patch("kit.mcp.dev_server.ChromaPackageSearch")
    def test_package_search_read_file_tool(self, mock_chroma_class, server_logic, mock_api_key):
        """Test package_search_read_file MCP tool."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.read_file.return_value = "class Request:\n    pass"
        mock_chroma_class.return_value = mock_client

        # Execute
        content = server_logic.package_search_read_file(package="requests", file_path="requests/models.py")

        # Verify
        assert "class Request" in content

        # Check client call
        mock_client.read_file.assert_called_once_with(
            package="requests", file_path="requests/models.py", start_line=None, end_line=None, filename_sha256=None
        )

    @patch("kit.mcp.dev_server.ChromaPackageSearch")
    def test_package_search_error_handling(self, mock_chroma_class, server_logic, mock_api_key):
        """Test error handling in package search tools."""
        # Setup mock to raise ValueError
        mock_client = MagicMock()
        mock_client.grep.side_effect = ValueError("Invalid package")
        mock_chroma_class.return_value = mock_client

        # Execute and verify
        with pytest.raises(MCPError) as exc_info:
            server_logic.package_search_grep(package="nonexistent", pattern="test")

        assert exc_info.value.code == -32602  # INVALID_PARAMS
        assert "Invalid package" in exc_info.value.message

    def test_tools_list_includes_package_search(self, server_logic):
        """Test that package search tools are included in the tools list."""
        tools = server_logic.list_tools()
        tool_names = [tool.name for tool in tools]

        # Verify all package search tools are present
        assert "package_search_grep" in tool_names
        assert "package_search_hybrid" in tool_names
        assert "package_search_read_file" in tool_names

        # Verify tool descriptions
        grep_tool = next(t for t in tools if t.name == "package_search_grep")
        assert "regex pattern matching" in grep_tool.description.lower()

        hybrid_tool = next(t for t in tools if t.name == "package_search_hybrid")
        assert "semantic search" in hybrid_tool.description.lower()

        read_tool = next(t for t in tools if t.name == "package_search_read_file")
        assert "read" in read_tool.description.lower() and "file" in read_tool.description.lower()

    @patch("kit.mcp.dev_server.ChromaPackageSearch")
    def test_deep_research_with_chroma_integration(self, mock_chroma_class, server_logic, mock_api_key):
        """Test that deep_research_package integrates with Chroma when available."""
        # Setup mock Chroma client
        mock_client = MagicMock()
        mock_client.hybrid_search.return_value = [{"file_path": "numpy/fft.py", "snippet": "FFT implementation"}]
        mock_chroma_class.return_value = mock_client

        # Mock Context7/Upstash provider
        with patch("kit.mcp.dev_server.DocumentationService") as mock_doc_service:
            mock_doc_instance = MagicMock()
            mock_doc_instance.search_packages.return_value = {"results": []}
            mock_doc_instance.get_documentation.return_value = {"status": "not_found"}
            mock_doc_service.return_value = mock_doc_instance

            # Execute
            result = server_logic.deep_research_package(package_name="numpy", query="FFT implementation")

            # Verify Chroma was used
            assert "ChromaPackageSearch" in result["providers"]
            assert "chroma_results" in result
            assert len(result["chroma_results"]) > 0
            assert result["chroma_results"][0]["file_path"] == "numpy/fft.py"

            # Verify the hybrid search was called with the query
            mock_client.hybrid_search.assert_called_once_with(
                package="numpy", query="FFT implementation", max_results=5
            )

    def test_deep_research_without_chroma_key(self, server_logic, monkeypatch):
        """Test that deep_research_package works without Chroma API key."""
        # Remove Chroma API keys
        monkeypatch.delenv("CHROMA_PACKAGE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("CHROMA_API_KEY", raising=False)

        # Mock Context7/Upstash provider
        with patch("kit.mcp.dev_server.DocumentationService") as mock_doc_service:
            mock_doc_instance = MagicMock()
            mock_doc_instance.search_packages.return_value = {"results": [{"id": "numpy/numpy", "name": "NumPy"}]}
            mock_doc_instance.get_documentation.return_value = {
                "status": "success",
                "documentation": {"snippets": [{"title": "NumPy basics", "code": "import numpy"}]},
                "provider": "UpstashProvider",
            }
            mock_doc_service.return_value = mock_doc_instance

            # Execute
            result = server_logic.deep_research_package(package_name="numpy", query="arrays")

            # Verify Chroma was NOT used
            assert "ChromaPackageSearch" not in result.get("providers", [])
            assert "chroma_results" not in result
            assert "UpstashProvider" in result.get("providers", [])
            assert result["status"] == "success"
