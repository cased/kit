"""Abstract documentation provider system for fetching real-time package documentation."""

import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DocumentationProvider(ABC):
    """Abstract base class for documentation providers."""

    @abstractmethod
    def search(self, query: str) -> Dict[str, Any]:
        """Search for packages/libraries."""
        pass

    @abstractmethod
    def fetch(self, package_id: str, **kwargs: Any) -> Optional[str]:
        """Fetch documentation for a specific package."""
        pass

    @abstractmethod
    def parse_response(self, text: str) -> Dict[str, Any]:
        """Parse the provider's response into structured data."""
        pass


class UpstashProvider(DocumentationProvider):
    """Documentation provider using Upstash's aggregated documentation service."""

    API_BASE_URL = "https://context7.com/api"
    DEFAULT_TYPE = "txt"
    DEFAULT_TOKENS = 5000
    MINIMUM_TOKENS = 1000

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key."""
        self.api_key = api_key or os.environ.get("UPSTASH_API_KEY") or os.environ.get("CONTEXT7_API_KEY")

    def _generate_headers(self) -> Dict[str, str]:
        """Generate headers for API requests."""
        headers = {
            "User-Agent": "kit-dev-mcp/2.0",
            "X-Source": "kit-mcp-server",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Generate unique session ID for rate limiting
            unique_id = f"{os.getpid()}_{time.time()}"
            session_hash = hashlib.md5(unique_id.encode()).hexdigest()
            headers["X-Session-Id"] = session_hash

        return headers

    def search(self, query: str) -> Dict[str, Any]:
        """Search for packages matching the query."""
        try:
            url = f"{self.API_BASE_URL}/v1/search"
            params = {"query": query}
            headers = self._generate_headers()

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params, headers=headers)

                if response.status_code == 429:
                    return {"results": [], "error": "Rate limited. Please try again later.", "status": "rate_limited"}
                elif response.status_code == 401:
                    return {
                        "results": [],
                        "error": "Unauthorized. Please check your API key.",
                        "status": "unauthorized",
                    }
                elif response.status_code != 200:
                    return {
                        "results": [],
                        "error": f"Search failed with code {response.status_code}",
                        "status": "error",
                    }

                data = response.json()
                return {"results": data.get("results", []), "status": "success"}

        except Exception as e:
            logger.error(f"Error searching packages: {e}")
            return {"results": [], "error": str(e), "status": "error"}

    def fetch(self, package_id: str, **kwargs: Any) -> Optional[str]:
        """Fetch documentation for a specific package."""
        tokens = kwargs.get("tokens", self.DEFAULT_TOKENS)
        topic = kwargs.get("topic", None)

        try:
            # Clean up library ID (just like Context7 does)
            if package_id.startswith("/"):
                package_id = package_id[1:]

            # Ensure minimum tokens
            tokens = max(tokens, self.MINIMUM_TOKENS)

            url = f"{self.API_BASE_URL}/v1/{package_id}"
            params = {
                "tokens": str(tokens),
                "type": self.DEFAULT_TYPE,
            }
            if topic:
                params["topic"] = topic

            headers = self._generate_headers()

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=headers)

                if response.status_code == 429:
                    logger.error("Rate limited")
                    return None
                elif response.status_code == 404:
                    logger.info(f"Package {package_id} not found")
                    return None
                elif response.status_code == 401:
                    logger.error("Unauthorized")
                    return None
                elif response.status_code != 200:
                    logger.error(f"Failed to fetch: {response.status_code}")
                    return None

                text = response.text
                if not text or text in ["No content available", "No context data available"]:
                    return None

                return text

        except Exception as e:
            logger.error(f"Error fetching documentation for {package_id}: {e}")
            return None

    def parse_response(self, text: str) -> Dict[str, Any]:
        """Parse the provider's text response into structured data."""
        if not text:
            return {"snippets": [], "overview": "No documentation available"}

        snippets = []
        current_snippet: Dict[str, Any] = {}
        lines = text.split("\n")

        for line in lines:
            if line.startswith("TITLE:"):
                if current_snippet:
                    snippets.append(current_snippet)
                current_snippet = {"title": line[6:].strip()}
            elif line.startswith("DESCRIPTION:"):
                current_snippet["description"] = line[12:].strip()
            elif line.startswith("SOURCE:"):
                current_snippet["source"] = line[7:].strip()
            elif line.startswith("LANGUAGE:"):
                current_snippet["language"] = line[9:].strip()
            elif line.startswith("CODE:"):
                current_snippet["code"] = []
            elif "code" in current_snippet and line and not line.startswith("==="):
                if isinstance(current_snippet["code"], list):
                    current_snippet["code"].append(line)

        # Add last snippet
        if current_snippet:
            snippets.append(current_snippet)

        # Join code lines
        for snippet in snippets:
            if "code" in snippet and isinstance(snippet["code"], list):
                snippet["code"] = "\n".join(snippet["code"]).strip()

        return {
            "snippets": snippets,
            "total_snippets": len(snippets),
            "overview": f"Found {len(snippets)} code examples and documentation snippets",
        }


class DocumentationService:
    """Service for managing documentation providers."""

    def __init__(self, provider: Optional[DocumentationProvider] = None):
        """Initialize with a documentation provider."""
        self.provider = provider or UpstashProvider()

    def search_packages(self, query: str) -> Dict[str, Any]:
        """Search for packages across providers."""
        return self.provider.search(query)

    def get_documentation(self, package_id: str, **kwargs) -> Dict[str, Any]:
        """Get documentation for a package."""
        # Fetch raw documentation
        doc_text = self.provider.fetch(package_id, **kwargs)

        if not doc_text:
            return {
                "package": package_id,
                "status": "not_found",
                "documentation": None,
                "provider": self.provider.__class__.__name__,
            }

        # Parse into structured format
        parsed = self.provider.parse_response(doc_text)

        return {
            "package": package_id,
            "status": "success",
            "documentation": parsed,
            "provider": self.provider.__class__.__name__,
            "raw_preview": doc_text[:500] if len(doc_text) > 500 else doc_text,
        }


# Default service instance
default_service = DocumentationService()
