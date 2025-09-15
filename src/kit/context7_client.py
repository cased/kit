"""
Context7 integration for fetching real documentation from multiple sources.
Context7 aggregates up-to-date documentation from official sources, GitHub, Stack Overflow, etc.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class Context7Client:
    """Client for interacting with Context7 documentation service."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Context7 client.

        Args:
            api_key: Optional API key for Context7. If not provided, will try to use
                    environment variable CONTEXT7_API_KEY.
        """
        self.api_key = api_key or os.environ.get("CONTEXT7_API_KEY")
        self.base_url = "https://context7.com"
        self.api_base_url = "https://api.context7.com"

    def fetch_documentation(self, package_name: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Fetch documentation for a package from Context7.

        Args:
            package_name: Name of the package/library to fetch docs for
            topic: Optional specific topic within the package

        Returns:
            Dictionary containing aggregated documentation from multiple sources
        """
        # Input validation to prevent SSRF attacks
        import re

        # Validate package name - only allow alphanumeric, hyphens, underscores, dots, @, /
        # Common patterns: "react", "@angular/core", "lodash.debounce"
        if not re.match(r"^[@a-zA-Z0-9._/-]+$", package_name):
            raise ValueError(f"Invalid package name format: {package_name}")

        # Limit length to prevent DoS
        if len(package_name) > 100:
            raise ValueError(f"Package name too long: {package_name[:50]}...")

        if topic and len(topic) > 100:
            raise ValueError(f"Topic too long: {topic[:50]}...")

        try:
            # Map common packages to their Context7 paths
            package_mapping = {
                "nextjs": "vercel/next.js",
                "next.js": "vercel/next.js",
                "next": "vercel/next.js",
                "fastapi": "fastapi",
                "django": "django/django",
                "flask": "pallets/flask",
                "react": "facebook/react",
                "vue": "vuejs/core",
                "svelte": "sveltejs/svelte",
                "express": "expressjs/express",
                "numpy": "numpy/numpy",
                "pandas": "pandas-dev/pandas",
                "tensorflow": "tensorflow/tensorflow",
                "pytorch": "pytorch/pytorch",
                "torch": "pytorch/pytorch",
            }

            # Get the mapped package path or use the original
            mapped_package = package_mapping.get(package_name.lower(), package_name)

            # Try to fetch from Context7's llms.txt endpoint
            url = f"{self.base_url}/{mapped_package}/llms.txt"

            # Add retry limits and proper timeout configuration
            with httpx.Client(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                max_redirects=3,
            ) as client:
                # Try to get documentation page
                response = client.get(
                    url,
                    headers={"User-Agent": "kit-dev-mcp/1.0", "Accept": "application/json, text/html"},
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    # Parse the response - Context7 may return different formats
                    content_type = response.headers.get("content-type", "")

                    if "application/json" in content_type:
                        data = response.json()
                        return self._format_context7_response(data, package_name)
                    elif url.endswith("/llms.txt") and response.text.startswith("================"):
                        # LLMs.txt format with code snippets
                        return self._parse_llms_txt(response.text, package_name)
                    else:
                        # HTML response - extract documentation sections
                        return self._parse_html_docs(response.text, package_name)

        except Exception as e:
            logger.warning(f"Failed to fetch from Context7: {e}")

        # Fallback: Return structured data indicating Context7 couldn't be reached
        return {
            "package": package_name,
            "source": "context7_fallback",
            "status": "unavailable",
            "documentation": {
                "overview": f"Unable to fetch real-time documentation for {package_name} from Context7.",
                "suggestion": "Using LLM-based research as fallback.",
                "sources": [],
            },
        }

    def _format_context7_response(self, data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Format Context7 API response into our standard format."""
        return {
            "package": package_name,
            "source": "context7",
            "status": "success",
            "documentation": {
                "overview": data.get("overview", ""),
                "installation": data.get("installation", ""),
                "api_reference": data.get("api", {}),
                "examples": data.get("examples", []),
                "sources": data.get("sources", []),
                "last_updated": data.get("updated", ""),
                "snippets": data.get("snippets", []),
            },
        }

    def _parse_llms_txt(self, content: str, package_name: str) -> Dict[str, Any]:
        """Parse llms.txt format documentation from Context7."""
        snippets = []
        current_snippet = {}

        lines = content.split('\n')
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
                # Start collecting code
                current_snippet["code"] = []
            elif "code" in current_snippet and line and not line.startswith("==="):
                current_snippet["code"].append(line)

        # Add last snippet
        if current_snippet:
            snippets.append(current_snippet)

        # Join code lines
        for snippet in snippets:
            if "code" in snippet:
                snippet["code"] = "\n".join(snippet["code"]).strip()

        return {
            "package": package_name,
            "source": "context7",
            "status": "success",
            "documentation": {
                "overview": f"Code snippets and documentation for {package_name} from Context7",
                "sources": ["context7.com/llms.txt"],
                "snippets": snippets[:10],  # Limit to first 10 snippets
                "total_snippets": len(snippets),
            },
        }

    def _parse_html_docs(self, html: str, package_name: str) -> Dict[str, Any]:
        """Parse HTML documentation page from Context7."""
        # Basic parsing - in production we'd use BeautifulSoup
        docs = {
            "package": package_name,
            "source": "context7_web",
            "status": "success",
            "documentation": {
                "overview": f"Documentation for {package_name} from Context7",
                "sources": ["context7.com"],
                "raw_html": html[:5000],  # Store first 5000 chars for processing
            },
        }

        # Extract any JSON-LD or structured data if present
        if '<script type="application/ld+json">' in html:
            try:
                start = html.find('<script type="application/ld+json">') + len('<script type="application/ld+json">')
                end = html.find("</script>", start)
                json_data = json.loads(html[start:end])
                # Cast to dict to make mypy happy with indexed assignment
                documentation = docs["documentation"]
                if isinstance(documentation, dict):
                    documentation["structured_data"] = json_data
            except (json.JSONDecodeError, ValueError):
                pass

        return docs


def integrate_with_llm(context7_docs: Dict[str, Any], llm_response: str) -> Dict[str, Any]:
    """Integrate Context7 real documentation with LLM synthesis.

    Args:
        context7_docs: Documentation fetched from Context7
        llm_response: LLM's synthesis/analysis of the documentation

    Returns:
        Combined response with real docs + LLM insights
    """
    return {
        "package": context7_docs.get("package"),
        "sources": {"context7": context7_docs, "llm_synthesis": llm_response},
        "combined_documentation": {
            "overview": context7_docs.get("documentation", {}).get("overview", llm_response),
            "real_sources": context7_docs.get("documentation", {}).get("sources", []),
            "llm_insights": llm_response,
            "confidence": "high" if context7_docs.get("status") == "success" else "medium",
        },
    }
