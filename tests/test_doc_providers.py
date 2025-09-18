"""Tests for documentation provider system."""

from unittest.mock import MagicMock, patch

import pytest

from kit.doc_providers import DocumentationService, UpstashProvider


class TestUpstashProvider:
    """Test the UpstashProvider implementation."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        provider = UpstashProvider(api_key="test-key-123")
        assert provider.api_key == "test-key-123"

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("UPSTASH_API_KEY", "env-key-456")
        provider = UpstashProvider()
        assert provider.api_key == "env-key-456"

    def test_init_context7_env_fallback(self, monkeypatch):
        """Test fallback to CONTEXT7_API_KEY env var."""
        monkeypatch.setenv("CONTEXT7_API_KEY", "context7-key-789")
        provider = UpstashProvider()
        assert provider.api_key == "context7-key-789"

    def test_generate_headers_with_api_key(self):
        """Test header generation with API key."""
        provider = UpstashProvider(api_key="test-key")
        headers = provider._generate_headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert "X-Session-Id" not in headers

    def test_generate_headers_without_api_key(self, monkeypatch):
        """Test header generation without API key (uses session ID)."""
        # Clear any existing API keys from environment
        monkeypatch.delenv("UPSTASH_API_KEY", raising=False)
        monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)

        provider = UpstashProvider()
        headers = provider._generate_headers()
        assert "Authorization" not in headers
        assert "X-Session-Id" in headers
        assert len(headers["X-Session-Id"]) == 32  # MD5 hash length

    @patch("httpx.Client.get")
    def test_search_success(self, mock_get):
        """Test successful package search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "/django/django", "title": "Django", "trust_score": 9},
                {"id": "/django/docs", "title": "Django Docs", "trust_score": 7},
            ]
        }
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        result = provider.search("django")

        assert result["status"] == "success"
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "/django/django"

    @patch("httpx.Client.get")
    def test_search_rate_limited(self, mock_get):
        """Test search when rate limited."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        result = provider.search("django")

        assert result["status"] == "rate_limited"
        assert "Rate limited" in result["error"]
        assert result["results"] == []

    @patch("httpx.Client.get")
    def test_search_unauthorized(self, mock_get):
        """Test search when unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        result = provider.search("django")

        assert result["status"] == "unauthorized"
        assert "Unauthorized" in result["error"]
        assert result["results"] == []

    @patch("httpx.Client.get")
    def test_fetch_success(self, mock_get):
        """Test successful documentation fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """TITLE: Django Overview
DESCRIPTION: Web framework for Python
SOURCE: https://github.com/django/django
LANGUAGE: Python
CODE:
from django.http import HttpResponse

def view(request):
    return HttpResponse("Hello")
================"""
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        result = provider.fetch("django/django", tokens=5000)

        assert result is not None
        assert "Django Overview" in result

    @patch("httpx.Client.get")
    def test_fetch_strips_leading_slash(self, mock_get):
        """Test that fetch strips leading slash from library ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Documentation content"
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        provider.fetch("/django/django")

        # Check that the URL was constructed without double slash
        call_args = mock_get.call_args
        url = str(call_args[0][0])
        assert "v1/django/django" in url
        assert "v1//django" not in url

    @patch("httpx.Client.get")
    def test_fetch_not_found(self, mock_get):
        """Test fetch when package not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        result = provider.fetch("nonexistent/package")

        assert result is None

    @patch("httpx.Client.get")
    def test_fetch_with_topic(self, mock_get):
        """Test fetch with specific topic."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Topic-specific documentation"
        mock_get.return_value = mock_response

        provider = UpstashProvider()
        provider.fetch("django/django", topic="models")

        # Check that topic was included in params
        call_args = mock_get.call_args
        assert call_args[1]["params"]["topic"] == "models"

    def test_parse_response_empty(self):
        """Test parsing empty response."""
        provider = UpstashProvider()
        result = provider.parse_response("")

        assert result["snippets"] == []
        assert result["overview"] == "No documentation available"

    def test_parse_response_with_snippets(self):
        """Test parsing response with code snippets."""
        text = """TITLE: Django Views
DESCRIPTION: How to create views in Django
SOURCE: https://github.com/django/django
LANGUAGE: Python
CODE:
def my_view(request):
    return HttpResponse("Hello")
================
TITLE: Django Models
DESCRIPTION: Creating models
SOURCE: https://github.com/django/django
LANGUAGE: Python
CODE:
class MyModel(models.Model):
    name = models.CharField(max_length=100)
================"""

        provider = UpstashProvider()
        result = provider.parse_response(text)

        assert len(result["snippets"]) == 2
        assert result["snippets"][0]["title"] == "Django Views"
        assert "def my_view" in result["snippets"][0]["code"]
        assert result["snippets"][1]["title"] == "Django Models"
        assert result["total_snippets"] == 2


class TestDocumentationService:
    """Test the DocumentationService orchestrator."""

    def test_init_with_provider(self):
        """Test initialization with specific provider."""
        provider = UpstashProvider(api_key="test")
        service = DocumentationService(provider)
        assert service.provider == provider

    def test_init_default_provider(self):
        """Test initialization with default provider."""
        service = DocumentationService()
        assert isinstance(service.provider, UpstashProvider)

    @patch.object(UpstashProvider, "search")
    def test_search_packages(self, mock_search):
        """Test search packages delegates to provider."""
        mock_search.return_value = {"results": ["test"], "status": "success"}

        service = DocumentationService(UpstashProvider())
        result = service.search_packages("django")

        assert result["results"] == ["test"]
        mock_search.assert_called_once_with("django")

    @patch.object(UpstashProvider, "fetch")
    @patch.object(UpstashProvider, "parse_response")
    def test_get_documentation_success(self, mock_parse, mock_fetch):
        """Test successful documentation retrieval."""
        mock_fetch.return_value = "Raw documentation text"
        mock_parse.return_value = {
            "snippets": [{"title": "Example"}],
            "total_snippets": 1,
        }

        service = DocumentationService(UpstashProvider())
        result = service.get_documentation("django/django", tokens=5000)

        assert result["status"] == "success"
        assert result["package"] == "django/django"
        assert result["documentation"]["snippets"][0]["title"] == "Example"
        assert "UpstashProvider" in result["provider"]
        assert "Raw documentation text" in result["raw_preview"]

    @patch.object(UpstashProvider, "fetch")
    def test_get_documentation_not_found(self, mock_fetch):
        """Test documentation not found."""
        mock_fetch.return_value = None

        service = DocumentationService(UpstashProvider())
        result = service.get_documentation("nonexistent/package")

        assert result["status"] == "not_found"
        assert result["documentation"] is None
        assert result["package"] == "nonexistent/package"


class TestMCPIntegration:
    """Test the MCP server integration with documentation providers."""

    @pytest.fixture
    def dev_server_logic(self):
        """Create a LocalDevServerLogic instance for testing."""
        from kit.mcp.dev_server import LocalDevServerLogic

        return LocalDevServerLogic()

    @patch("kit.mcp.dev_server.DocumentationService")
    def test_deep_research_direct_library_id(self, mock_doc_service_class, dev_server_logic):
        """Test deep_research_package with direct library ID (contains /)."""
        mock_service = MagicMock()
        mock_doc_service_class.return_value = mock_service

        # Mock successful direct fetch
        mock_service.get_documentation.return_value = {
            "status": "success",
            "documentation": {"snippets": [{"title": "Test"}]},
            "provider": "UpstashProvider",
        }

        result = dev_server_logic.deep_research_package("django/django")

        assert result["status"] == "success"
        assert result["library_id_attempted"] == "django/django"
        assert result["resolution_method"] == "automatic"
        assert "documentation" in result

        # Should try direct fetch first for IDs with /
        mock_service.get_documentation.assert_called()

    @patch("kit.mcp.dev_server.DocumentationService")
    def test_deep_research_search_fallback(self, mock_doc_service_class, dev_server_logic):
        """Test deep_research_package falls back to search results."""
        mock_service = MagicMock()
        mock_doc_service_class.return_value = mock_service

        # Mock search returns results
        mock_service.search_packages.return_value = {
            "results": [
                {"id": "/django/django", "title": "Django", "trust_score": 9},
                {"id": "/django/docs", "title": "Django Docs", "trust_score": 7},
            ]
        }

        # Mock first result works (needs non-empty snippets to be considered successful)
        mock_service.get_documentation.side_effect = [
            {"status": "success", "documentation": {"snippets": [{"title": "Test"}]}, "provider": "UpstashProvider"},
        ]

        result = dev_server_logic.deep_research_package("django")

        assert result["status"] == "success"
        assert "documentation" in result

    @patch("kit.mcp.dev_server.DocumentationService")
    def test_deep_research_common_pattern(self, mock_doc_service_class, dev_server_logic):
        """Test deep_research_package tries common package/package pattern."""
        mock_service = MagicMock()
        mock_doc_service_class.return_value = mock_service

        # Mock search returns no results
        mock_service.search_packages.return_value = {"results": []}

        # Mock package/package pattern works
        def get_doc_side_effect(library_id, **kwargs):
            if library_id == "django/django":
                return {
                    "status": "success",
                    "documentation": {"snippets": [{"title": "Django"}]},
                    "provider": "UpstashProvider",
                }
            return {"status": "not_found"}

        mock_service.get_documentation.side_effect = get_doc_side_effect

        result = dev_server_logic.deep_research_package("django")

        # Should try django/django pattern
        assert any(call[0][0] == "django/django" for call in mock_service.get_documentation.call_args_list)
        assert result["status"] == "success"

    @patch("kit.mcp.dev_server.DocumentationService")
    def test_deep_research_returns_guidance_on_failure(self, mock_doc_service_class, dev_server_logic):
        """Test deep_research_package returns helpful guidance when no docs found."""
        mock_service = MagicMock()
        mock_doc_service_class.return_value = mock_service

        # Mock search returns results but none work
        mock_service.search_packages.return_value = {
            "results": [
                {"id": "/some/package", "title": "Some Package", "trust_score": 5},
            ]
        }

        # All fetch attempts fail
        mock_service.get_documentation.return_value = {"status": "not_found"}

        result = dev_server_logic.deep_research_package("unknown")

        assert result["status"] == "not_found"
        assert "available_libraries" in result
        assert "resolution_guidance" in result
        assert result["action_required"] == "CALL_AGAIN_WITH_LIBRARY_ID"
        assert "recommended_id" in result["resolution_guidance"]
        assert len(result["available_libraries"]) == 1

    @patch("kit.mcp.dev_server.DocumentationService")
    @patch("kit.deep_research.DeepResearch")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_deep_research_with_llm_synthesis(self, mock_deep_research_class, mock_doc_service_class, dev_server_logic):
        """Test deep_research_package with LLM synthesis when query provided."""
        mock_service = MagicMock()
        mock_doc_service_class.return_value = mock_service

        mock_researcher = MagicMock()
        mock_deep_research_class.return_value = mock_researcher

        # Mock successful documentation fetch
        mock_service.search_packages.return_value = {"results": []}
        mock_service.get_documentation.return_value = {
            "status": "success",
            "documentation": {"snippets": [{"title": "Example", "description": "Test", "code": "print('hello')"}]},
            "provider": "UpstashProvider",
        }

        # Mock LLM response
        mock_researcher.research.return_value = MagicMock(
            answer="Django is a web framework",
            model="gpt-4o",
            execution_time=1.5,
        )

        result = dev_server_logic.deep_research_package("django", query="what is django")

        # Accept either source depending on whether Chroma is available
        assert result["source"] in ["real_docs+llm", "multi_source+llm"]
        assert "answer" in result
        assert result["answer"] == "Django is a web framework"
