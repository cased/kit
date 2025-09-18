"""Chroma Package Search integration for searching and analyzing code packages."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ChromaPackageSearch:
    """Client for Chroma's Package Search API."""

    API_BASE_URL = "https://mcp.trychroma.com/package-search/v1"
    DEFAULT_TIMEOUT = 60.0  # Increased timeout for slow responses

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Chroma API key."""
        api_key_value = api_key or os.environ.get("CHROMA_PACKAGE_SEARCH_API_KEY") or os.environ.get("CHROMA_API_KEY")
        if not api_key_value:
            raise ValueError(
                "Chroma Package Search API key not found. "
                "Set CHROMA_PACKAGE_SEARCH_API_KEY or CHROMA_API_KEY environment variable."
            )
        self.api_key: str = api_key_value

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "x-chroma-token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "kit-mcp/2.0",
        }

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool via JSON-RPC protocol."""
        url = f"{self.API_BASE_URL}"
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        with httpx.Client(timeout=self.DEFAULT_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()

            # Parse SSE response
            if response.headers.get("content-type") == "text/event-stream":
                # Extract JSON from SSE data
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data and "content" in data["result"]:
                            # Extract the text content
                            content = data["result"]["content"][0]["text"]
                            return json.loads(content)
            else:
                return response.json()

    def grep(
        self,
        package: str,
        pattern: str,
        max_results: int = 100,
        file_pattern: Optional[str] = None,
        case_sensitive: bool = True,
        registry_name: str = "py_pi",
    ) -> List[Dict[str, Any]]:
        """
        Use regex pattern matching to retrieve relevant lines from source code.

        Args:
            package: Package name to search (e.g., 'numpy', 'django')
            pattern: Regex pattern to search for
            max_results: Maximum number of results to return
            file_pattern: Optional glob pattern to filter files (e.g., '*.py')
            case_sensitive: Whether the search is case-sensitive
            registry_name: Registry name (default: 'py_pi' for Python packages)

        Returns:
            List of matches with file paths, line numbers, and content
        """
        try:
            arguments = {
                "package_name": package,
                "registry_name": registry_name,
                "pattern": pattern,
                "max_results": max_results,
            }
            if not case_sensitive:
                arguments["case_sensitive"] = False
            if file_pattern:
                arguments["file_pattern"] = file_pattern

            result = self._call_mcp_tool("package_search_grep", arguments)

            # Extract results from the response
            if isinstance(result, dict) and "results" in result:
                # Transform the results to our expected format
                formatted_results = []
                for item in result["results"]:
                    if "result" in item:
                        r = item["result"]
                        formatted_results.append(
                            {
                                "file_path": r.get("file_path"),
                                "line_number": r.get("start_line") or r.get("line_number"),
                                "content": r.get("content"),
                                "language": r.get("language"),
                                "filename_sha256": r.get("filename_sha256"),  # Include for read_file
                            }
                        )
                return formatted_results
            return []

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Chroma API key")
            elif e.response.status_code == 404:
                raise ValueError(f"Package '{package}' not found")
            else:
                logger.error(f"HTTP error searching package: {e}")
                raise
        except Exception as e:
            logger.error(f"Error in package grep: {e}")
            raise

    def hybrid_search(
        self,
        package: str,
        query: str,
        regex_filter: Optional[str] = None,
        max_results: int = 20,
        file_pattern: Optional[str] = None,
        registry_name: str = "py_pi",
    ) -> List[Dict[str, Any]]:
        """
        Use semantic search with optional regex filtering.

        Args:
            package: Package name to search
            query: Semantic search query
            regex_filter: Optional regex pattern to filter results
            max_results: Maximum number of results
            file_pattern: Optional glob pattern to filter files
            registry_name: Registry name (default: 'py_pi' for Python packages)

        Returns:
            List of semantically relevant code snippets
        """
        try:
            arguments = {
                "package_name": package,
                "registry_name": registry_name,
                "semantic_queries": [query],  # API expects an array
                "max_results": max_results,
            }
            if regex_filter:
                arguments["regex_filter"] = regex_filter
            if file_pattern:
                arguments["file_pattern"] = file_pattern

            result = self._call_mcp_tool("package_search_hybrid", arguments)

            # Extract and format results
            if isinstance(result, dict) and "results" in result:
                formatted_results = []
                for item in result.get("results", []):
                    # Handle the actual response structure
                    metadata = item.get("metadata", {})
                    formatted_results.append(
                        {
                            "file_path": metadata.get("filename", ""),
                            "snippet": item.get("document", ""),
                            "score": item.get("distance"),  # or score if available
                            "line_number": metadata.get("start_line"),
                            "end_line": metadata.get("end_line"),
                        }
                    )
                return formatted_results
            return []

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Chroma API key")
            elif e.response.status_code == 404:
                raise ValueError(f"Package '{package}' not found")
            else:
                logger.error(f"HTTP error in hybrid search: {e}")
                raise
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            raise

    def read_file(
        self,
        package: str,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        filename_sha256: Optional[str] = None,
        registry_name: str = "py_pi",
    ) -> str:
        """
        Read specific lines from a file in the code package.

        Args:
            package: Package name
            file_path: Path to the file within the package
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (inclusive)
            filename_sha256: SHA256 hash of the file (required by API, auto-fetched if not provided)
            registry_name: Registry name (default: 'py_pi' for Python packages)

        Returns:
            File content or specified line range
        """
        try:
            # If sha256 not provided, try to get it via grep
            if not filename_sha256:
                # Do a quick grep to get the file's sha256
                grep_results = self.grep(
                    package=package,
                    pattern=".",  # Match anything
                    max_results=1,
                    file_pattern=file_path.split("/")[-1],  # Just the filename
                    registry_name=registry_name,
                )
                if grep_results and grep_results[0].get("filename_sha256"):
                    filename_sha256 = grep_results[0]["filename_sha256"]
                else:
                    raise ValueError(f"Could not determine SHA256 for file '{file_path}'. File may not exist.")

            arguments: Dict[str, Any] = {
                "package_name": package,
                "registry_name": registry_name,
                "file_path": file_path,
                "filename_sha256": filename_sha256,
            }
            if start_line is not None:
                arguments["start_line"] = start_line
            if end_line is not None:
                arguments["end_line"] = end_line

            result = self._call_mcp_tool("package_search_read_file", arguments)

            # Extract content from the response
            if isinstance(result, dict):
                return result.get("content", "")
            elif isinstance(result, str):
                return result
            return ""

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Chroma API key")
            elif e.response.status_code == 404:
                if "file" in str(e.response.text).lower():
                    raise ValueError(f"File '{file_path}' not found in package '{package}'")
                else:
                    raise ValueError(f"Package '{package}' not found")
            else:
                logger.error(f"HTTP error reading file: {e}")
                raise
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

    def list_packages(self) -> List[str]:
        """
        List all available packages in the Chroma Package Search index.

        Returns:
            List of available package names
        """
        try:
            # For now, return a static list of known packages
            # The MCP server doesn't expose a list_packages tool yet
            return [
                "numpy",
                "pandas",
                "django",
                "flask",
                "fastapi",
                "requests",
                "tensorflow",
                "pytorch",
                "scikit-learn",
                "matplotlib",
                "seaborn",
                "sqlalchemy",
                "celery",
                "redis",
                "elasticsearch",
                "beautifulsoup4",
                "scrapy",
                "pytest",
                "black",
                "mypy",
                "ruff",
                "poetry",
            ]
        except Exception as e:
            logger.error(f"Error listing packages: {e}")
            raise

    def get_package_info(self, package: str) -> Dict[str, Any]:
        """
        Get metadata about a package.

        Args:
            package: Package name

        Returns:
            Package metadata including version, description, etc.
        """
        # The MCP server doesn't expose a package info tool yet
        # Return basic info for now
        return {"name": package, "registry": "py_pi", "available": True}
