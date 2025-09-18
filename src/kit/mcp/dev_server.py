"""Enhanced MCP server for development with advanced code intelligence.

This MCP server provides comprehensive development tools:

1. Real-time file watching and change detection
2. Deep documentation research for any package (using LLM)
3. Semantic code search
4. Smart context building from multiple sources
5. Git integration with AI-powered diff reviews
6. Production-grade repository analysis
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from .. import __version__ as KIT_VERSION
from ..ast_search import ASTSearcher
from ..doc_providers import DocumentationService, UpstashProvider
from ..package_search import ChromaPackageSearch
from ..pr_review.config import ReviewConfig
from ..pr_review.local_reviewer import LocalDiffReviewer
from ..repository import Repository
from ..summaries import AnthropicConfig, OpenAIConfig

logger = logging.getLogger("kit-dev-mcp")

# MCP error codes
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Context limits removed for better performance - let the AI handle context management


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# Compatibility alias for different MCP versions
try:
    from mcp.types import EmbeddedResource

    ResourceContent: type[Union[EmbeddedResource, TextContent]] = EmbeddedResource
except ImportError:
    ResourceContent = TextContent


# Parameter classes from standard server
class OpenRepoParams(BaseModel):
    path_or_url: str
    github_token: Optional[str] = None
    ref: Optional[str] = None


class SearchParams(BaseModel):
    repo_id: str
    query: str
    pattern: str = "*.py"


class GrepParams(BaseModel):
    repo_id: str
    pattern: str
    case_sensitive: bool = True
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    max_results: int = 1000
    directory: Optional[str] = None
    include_hidden: bool = False


class GetFileContentParams(BaseModel):
    repo_id: str
    file_path: Union[str, List[str]]


class GetMultipleFileContentsParams(BaseModel):
    repo_id: str
    file_paths: List[str]


class ExtractSymbolsParams(BaseModel):
    repo_id: str
    file_path: str
    symbol_type: Optional[str] = None


class FindSymbolUsagesParams(BaseModel):
    repo_id: str
    symbol_name: str
    symbol_type: Optional[str] = None
    file_path: Optional[str] = None


class GetFileTreeParams(BaseModel):
    repo_id: str


class GetCodeSummaryParams(BaseModel):
    repo_id: str
    file_path: str
    symbol_name: Optional[str] = None


class GitInfoParams(BaseModel):
    repo_id: str


class ReviewDiffParams(BaseModel):
    repo_id: str
    diff_spec: str
    priority_filter: Optional[List[str]] = None
    max_files: int = 10
    model: Optional[str] = None


class GrepASTParams(BaseModel):
    """Search code using AST patterns."""

    repo_id: str
    pattern: str = Field(description="AST pattern to search for")
    mode: str = Field(default="simple", description="Search mode: simple, pattern, or query")
    file_pattern: str = Field(default="**/*.py", description="File glob pattern")
    max_results: int = Field(default=20, ge=1, le=50)


class KitServerLogic:
    def __init__(self) -> None:
        self._repos: Dict[str, Repository] = {}

    def open_repository(self, path_or_url: str, github_token: Optional[str] = None, ref: Optional[str] = None) -> str:
        """Open a repository and return its ID."""
        import os

        # Check for GitHub token in environment if not provided
        if github_token is None:
            github_token = os.environ.get("KIT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")

        try:
            repo = Repository(path_or_url, github_token=github_token, ref=ref)
            repo_id = f"repo_{int(time.time() * 1000)}"
            self._repos[repo_id] = repo
            return repo_id
        except Exception as e:
            raise MCPError(INVALID_PARAMS, f"Failed to open repository: {e}")

    def get_repo(self, repo_id: str) -> Repository:
        """Get a repository by ID."""
        if repo_id not in self._repos:
            raise MCPError(INVALID_PARAMS, f"Repository {repo_id} not found")
        return self._repos[repo_id]

    def get_file_content(self, repo_id: str, file_path: Union[str, List[str]]) -> Union[str, Dict[str, Any]]:
        """Get file content."""
        repo = self.get_repo(repo_id)
        try:
            if isinstance(file_path, list):
                result = {}
                for fp in file_path:
                    # Securely validate path to prevent traversal
                    try:
                        # Join the file path with repo path, then resolve
                        repo_path = Path(repo.repo_path).resolve()
                        safe_path = (repo_path / fp).resolve()

                        # Ensure resolved path is within repo bounds
                        if not safe_path.is_relative_to(repo_path):
                            raise MCPError(INVALID_PARAMS, f"Path traversal attempted: {fp}")

                        # Get the content directly with the original path
                        content = repo.get_file_content(fp)
                        result[fp] = content
                    except MCPError:
                        # Re-raise MCPError for path traversal
                        raise
                    except FileNotFoundError:
                        result[fp] = f"File not found: {fp}"
                    except ValueError as e:
                        if "outside repository" in str(e).lower():
                            raise MCPError(INVALID_PARAMS, f"Path traversal attempted: {e}")
                        raise MCPError(INVALID_PARAMS, str(e))
                    except Exception as e:
                        result[fp] = f"Error reading file: {e!s}"
                return result
            else:
                # Securely validate single file path
                repo_path = Path(repo.repo_path).resolve()
                safe_path = (repo_path / file_path).resolve()

                # Ensure resolved path is within repo bounds
                if not safe_path.is_relative_to(repo_path):
                    raise MCPError(INVALID_PARAMS, f"Path traversal attempted: {file_path}")

                # Get the content directly with the original path
                return repo.get_file_content(file_path)
        except ValueError as e:
            if "outside repository bounds" in str(e):
                raise MCPError(INVALID_PARAMS, f"Path traversal attempted: {e}")
            raise MCPError(INVALID_PARAMS, str(e))
        except FileNotFoundError as e:
            raise MCPError(INVALID_PARAMS, str(e))

    def get_multiple_file_contents(self, repo_id: str, file_paths: List[str]) -> Dict[str, Any]:
        """Get multiple file contents."""
        result = self.get_file_content(repo_id, file_paths)
        if isinstance(result, dict):
            return result
        # Should not happen as we're passing a list
        return {"error": "Unexpected result type"}

    def grep_code(
        self,
        repo_id: str,
        pattern: str,
        case_sensitive: bool = True,
        include_pattern: Optional[str] = None,
        exclude_pattern: Optional[str] = None,
        max_results: int = 1000,
        directory: Optional[str] = None,
        include_hidden: bool = False,
    ) -> List[Dict[str, Any]]:
        """Grep for patterns in code with context limits."""
        repo = self.get_repo(repo_id)
        try:
            results = repo.grep(
                pattern,
                case_sensitive=case_sensitive,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
                max_results=max_results,
                directory=directory,
                include_hidden=include_hidden,
            )

            return results
        except ValueError as e:
            raise MCPError(INVALID_PARAMS, str(e))

    def get_file_tree(self, repo_id: str) -> List[Dict[str, Any]]:
        """Get file tree."""
        repo = self.get_repo(repo_id)
        return repo.get_file_tree()

    def extract_symbols(self, repo_id: str, file_path: str, symbol_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract symbols from a file."""
        repo = self.get_repo(repo_id)
        # Repository.extract_symbols doesn't accept symbol_type parameter
        try:
            return repo.extract_symbols(file_path)
        except ValueError as e:
            if "outside repository bounds" in str(e):
                raise MCPError(INVALID_PARAMS, f"Path traversal attempted: {e}")
            raise MCPError(INVALID_PARAMS, str(e))

    def find_symbol_usages(
        self, repo_id: str, symbol_name: str, symbol_type: Optional[str] = None, file_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find symbol usages."""
        repo = self.get_repo(repo_id)
        # Repository.find_symbol_usages doesn't accept keyword arguments
        return repo.find_symbol_usages(symbol_name)

    def get_code_summary(self, repo_id: str, file_path: str, symbol_name: Optional[str] = None) -> Dict[str, Any]:
        """Get code summary."""
        repo = self.get_repo(repo_id)
        # Repository doesn't have get_code_summary, so we'll implement a basic one
        try:
            content = repo.get_file_content(file_path)
            symbols = repo.extract_symbols(file_path)
        except (ValueError, FileNotFoundError) as e:
            raise MCPError(INVALID_PARAMS, str(e))

        summary = {
            "file": file_path,
            "content_preview": content[:500] if content else "",
            "symbols": symbols[:10] if symbols else [],  # First 10 symbols
            "line_count": len(content.splitlines()) if content else 0,
        }

        if symbol_name:
            # Find specific symbol
            matching_symbols = [s for s in symbols if s.get("name") == symbol_name]
            if matching_symbols:
                summary["requested_symbol"] = matching_symbols[0]

        return {"summary": summary}

    def get_git_info(self, repo_id: str) -> Dict[str, Any]:
        """Get git information."""
        repo = self.get_repo(repo_id)
        # Repository doesn't have get_git_info, construct it from available methods
        return {
            "current_sha": repo.current_sha,
            "current_sha_short": repo.current_sha_short,
            "current_branch": repo.current_branch,
            "remote_url": repo.remote_url,
            "is_dirty": repo.is_dirty,
            "tags": repo.tags,
            "branches": repo.branches,
        }

    def review_diff(
        self,
        repo_id: str,
        diff_spec: str,
        priority_filter: Optional[List[str]] = None,
        max_files: int = 10,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Review a diff."""

        repo = self.get_repo(repo_id)

        try:
            # Create review config
            config = ReviewConfig.from_file()
            if model:
                config.llm.model = model

            # Create reviewer
            reviewer = LocalDiffReviewer(config, repo.repo_path)

            # Perform review
            result = reviewer.review(diff_spec)

            # Extract cost from result if present
            import re

            cost_match = re.search(r"Cost: \$(\d+\.\d+)", result)
            cost = float(cost_match.group(1)) if cost_match else 0.0

            return {"review": result, "diff_spec": diff_spec, "cost": cost, "model": model or "gpt-4"}
        except Exception as e:
            raise MCPError(INTERNAL_ERROR, f"Failed to review diff: {e}")

    def search_code(self, repo_id: str, query: str, pattern: str = "*.py") -> List[Dict[str, Any]]:
        """Search code with context limits."""
        repo = self.get_repo(repo_id)
        # Repository uses search_text, not search_code
        results = repo.search_text(query, file_pattern=pattern)

        return results

    async def grep_ast_async(
        self, repo_id: str, pattern: str, mode: str = "simple", file_pattern: str = "**/*.py", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search code using AST patterns with async execution to prevent blocking.

        Examples:
            - pattern="async def" - Find all async functions
            - pattern="class $NAME(BaseModel)" - Find classes extending BaseModel
            - pattern='{"type": "try_statement"}' - Find all try blocks
        """
        repo = self.get_repo(repo_id)

        # Run the heavy AST parsing in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = await loop.run_in_executor(
                executor, self._grep_ast_sync, repo.repo_path, pattern, file_pattern, mode, max_results
            )

        return results

    def _grep_ast_sync(
        self, repo_path: str, pattern: str, file_pattern: str, mode: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Synchronous AST search implementation for thread pool execution."""
        # Create AST searcher
        searcher = ASTSearcher(repo_path)

        # Perform search
        results = searcher.search_pattern(
            pattern=pattern, file_pattern=file_pattern, mode=mode, max_results=max_results
        )

        # Add a preview of the match
        for result in results:
            if "text" in result:
                lines = result["text"].split("\n")
                result["preview"] = lines[0] if lines else ""
                if len(result["preview"]) > 100:
                    result["preview"] = result["preview"][:100] + "..."

        return results

    def grep_ast(
        self, repo_id: str, pattern: str, mode: str = "simple", file_pattern: str = "**/*.py", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search code using AST patterns with context limits (synchronous wrapper).

        Examples:
            - pattern="async def" - Find all async functions
            - pattern="class $NAME(BaseModel)" - Find classes extending BaseModel
            - pattern='{"type": "try_statement"}' - Find all try blocks
        """
        # For backward compatibility, provide a sync wrapper
        # This is called from the MCP server, which will handle async execution
        repo = self.get_repo(repo_id)
        return self._grep_ast_sync(repo.repo_path, pattern, file_pattern, mode, max_results)

    def list_prompts(self) -> List[Any]:
        """List available prompts."""
        return [
            Prompt(
                name="review_diff",
                description="Review a local git diff",
                arguments=[
                    PromptArgument(name="repo_id", description="Repository ID", required=True),
                    PromptArgument(
                        name="diff_spec", description="Git diff spec (e.g., 'HEAD~1..HEAD', '--staged')", required=True
                    ),
                    PromptArgument(name="priority_filter", description="Priority levels to include", required=False),
                    PromptArgument(name="max_files", description="Maximum number of files to review", required=False),
                    PromptArgument(name="model", description="LLM model to use", required=False),
                ],
            )
        ]

    def get_prompt(self, name: str, arguments: dict) -> Any:
        """Get a specific prompt."""
        # This would normally handle prompt requests
        from mcp.types import GetPromptResult, PromptMessage, TextContent

        if name == "review_diff":
            repo_id = arguments.get("repo_id")
            diff_spec = arguments.get("diff_spec", "HEAD~1..HEAD")

            # Keep repo_id as string for review_diff
            if not repo_id:
                raise MCPError(INVALID_PARAMS, "repo_id is required")
            result = self.review_diff(repo_id, diff_spec)

            return GetPromptResult(
                description=f"AI review of diff: {diff_spec}",
                messages=[PromptMessage(role="assistant", content=TextContent(type="text", text=result["review"]))],
            )

        raise MCPError(INVALID_PARAMS, f"Unknown prompt: {name}")

    def list_tools(self) -> List[Tool]:
        """List standard Kit tools."""
        return [
            Tool(
                name="open_repository",
                description="Open a local or remote Git repository",
                inputSchema=OpenRepoParams.model_json_schema(),
            ),
            Tool(
                name="grep_code", description="Fast literal string search", inputSchema=GrepParams.model_json_schema()
            ),
            Tool(
                name="get_file_tree",
                description="Get repository file structure",
                inputSchema=GetFileTreeParams.model_json_schema(),
            ),
            Tool(
                name="extract_symbols",
                description="Extract symbols from a file",
                inputSchema=ExtractSymbolsParams.model_json_schema(),
            ),
            Tool(
                name="find_symbol_usages",
                description="Find where symbols are used",
                inputSchema=FindSymbolUsagesParams.model_json_schema(),
            ),
            Tool(
                name="review_diff",
                description="Review a local git diff with AI",
                inputSchema=ReviewDiffParams.model_json_schema(),
            ),
            Tool(
                name="grep_ast",
                description="Search code using AST patterns (semantic search)",
                inputSchema=GrepASTParams.model_json_schema(),
            ),
        ]


class DeepResearchParams(BaseModel):
    """Deep research documentation for a package."""

    package_name: str = Field(description="Package or library name (e.g., 'react', 'django', 'tensorflow')")
    query: Optional[str] = Field(default=None, description="Specific question or topic about the package")


class PackageSearchGrepParams(BaseModel):
    """Parameters for package search grep."""

    package: str = Field(description="Package name to search (e.g., 'numpy', 'django', 'tensorflow')")
    pattern: str = Field(description="Regex pattern to search for")
    max_results: int = Field(default=100, description="Maximum number of results to return")
    file_pattern: Optional[str] = Field(
        default=None, description="Optional glob pattern to filter files (e.g., '*.py')"
    )
    case_sensitive: bool = Field(default=True, description="Whether the search is case-sensitive")


class PackageSearchHybridParams(BaseModel):
    """Parameters for package search hybrid (semantic + regex)."""

    package: str = Field(description="Package name to search")
    query: str = Field(description="Semantic search query")
    regex_filter: Optional[str] = Field(default=None, description="Optional regex pattern to filter results")
    max_results: int = Field(default=20, description="Maximum number of results")
    file_pattern: Optional[str] = Field(default=None, description="Optional glob pattern to filter files")


class PackageSearchReadFileParams(BaseModel):
    """Parameters for reading a file from a package."""

    package: str = Field(description="Package name")
    file_path: str = Field(description="Path to the file within the package")
    start_line: Optional[int] = Field(default=None, description="Starting line number (1-indexed)")
    end_line: Optional[int] = Field(default=None, description="Ending line number (inclusive)")
    filename_sha256: Optional[str] = Field(
        default=None, description="SHA256 hash of the file (auto-fetched if not provided)"
    )


class LocalDevServerLogic(KitServerLogic):
    """Enhanced MCP server logic for development."""

    def __init__(self) -> None:
        super().__init__()
        self._test_results: Dict[str, Dict] = {}
        self._context_cache: Dict[str, Any] = {}
        self._package_search: Optional[ChromaPackageSearch] = None

    def open_repository(self, path_or_url: str, github_token: Optional[str] = None, ref: Optional[str] = None) -> str:
        """Open a repository."""
        try:
            repo = Repository(path_or_url, github_token=github_token, ref=ref)
            repo_id = f"repo_{len(self._repos)}"
            self._repos[repo_id] = repo
            logger.info(f"Opened repository at {path_or_url} with ID {repo_id}")
            return repo_id
        except Exception as e:
            logger.error(f"Failed to open repository: {e}")
            raise

    def deep_research_package(self, package_name: str, query: Optional[str] = None) -> Dict[str, Any]:
        """Deep research on a package - combines real docs + optional LLM synthesis.

        Now supports multiple documentation providers:
        1. Chroma Package Search - for source code exploration
        2. Upstash/Context7 - for general documentation
        """
        import os

        from ..deep_research import DeepResearch
        from ..summaries import AnthropicConfig, OpenAIConfig

        # Check if we should use Chroma Package Search
        use_chroma = False
        chroma_results = None

        if os.environ.get("CHROMA_PACKAGE_SEARCH_API_KEY") or os.environ.get("CHROMA_API_KEY"):
            try:
                # Try Chroma first for source code exploration
                client = self._get_package_search()

                # If user has a specific query, use hybrid search
                if query:
                    chroma_results = client.hybrid_search(package=package_name, query=query, max_results=5)
                else:
                    # Otherwise, get general overview with grep
                    chroma_results = client.grep(
                        package=package_name,
                        pattern="(class|def|interface|function|const)\\s+\\w+",
                        max_results=10,
                        case_sensitive=True,
                    )

                if chroma_results:
                    use_chroma = True
            except Exception as e:
                # Chroma failed, fall back to Context7
                logger.debug(f"Chroma Package Search not available: {e}")
                pass

        # Initialize documentation service (using our abstracted provider)
        doc_service = DocumentationService(UpstashProvider())

        # Try different strategies to get documentation
        library_id = package_name
        doc_result = None
        search_results: Dict[str, Any] = {"results": []}

        # Strategy 0: If it already looks like a library ID (contains / or starts with /), try it directly
        if "/" in package_name or package_name.startswith("/"):
            library_id = package_name
            doc_result = doc_service.get_documentation(library_id, tokens=5000, topic=query)
            if doc_result and doc_result.get("status") == "success":
                # Found it directly, no need to search
                search_results = {"results": [], "note": "Used provided library ID directly"}
            else:
                # Didn't work, proceed with search
                search_results = doc_service.search_packages(package_name)
        else:
            # Normal package name, start with search
            search_results = doc_service.search_packages(package_name)

        # Strategy 1: If we got search results, try each result until one works
        if search_results.get("results") and len(search_results["results"]) > 0:
            for result in search_results["results"][:3]:  # Try top 3 results
                library_id = result.get("id", package_name)
                doc_result = doc_service.get_documentation(library_id, tokens=5000, topic=query)
                if doc_result and doc_result.get("status") == "success":
                    break  # Found working documentation

        # Strategy 2: If that didn't work and package doesn't have /, try common pattern
        if (not doc_result or doc_result.get("status") != "success") and "/" not in package_name:
            # Try common pattern: package/package (works for django/django, redis/redis, etc.)
            library_id = f"{package_name}/{package_name}"
            doc_result = doc_service.get_documentation(library_id, tokens=5000, topic=query)

        # If still no docs, we'll return the search results for the agent to choose from
        if not doc_result:
            doc_result = {"status": "not_found"}

        # Check if we got useful documentation from either source
        has_real_docs = (
            doc_result.get("status") == "success"
            and doc_result.get("documentation")
            and doc_result.get("documentation", {}).get("snippets")
        ) or use_chroma

        # If we got good docs and user has a specific query, optionally enhance with LLM
        if (
            (has_real_docs or use_chroma)
            and query
            and (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
        ):
            # Use LLM to synthesize an answer based on the real docs
            config: Union[OpenAIConfig, AnthropicConfig, None] = None
            if os.environ.get("OPENAI_API_KEY"):
                config = OpenAIConfig(model="gpt-4o", max_tokens=2000)
            elif os.environ.get("ANTHROPIC_API_KEY"):
                config = AnthropicConfig(model="claude-3-5-sonnet-20241022", max_tokens=2000)

            if config:
                try:
                    researcher = DeepResearch(config)

                    # Build context from available sources
                    context_parts = []

                    # Add Chroma results if available
                    if use_chroma and chroma_results:
                        context_parts.append("=== SOURCE CODE FROM CHROMA PACKAGE SEARCH ===")
                        for i, result in enumerate(chroma_results[:5], 1):
                            if "file_path" in result and "content" in result:
                                context_parts.append(f"\nFile: {result['file_path']}")
                                if "line_number" in result:
                                    context_parts.append(f"Line {result['line_number']}: {result['content']}")
                                else:
                                    context_parts.append(result["content"][:500])
                            elif "snippet" in result:
                                context_parts.append(f"\nSnippet {i}:\n{result['snippet'][:500]}")

                    # Add Context7 documentation if available
                    if has_real_docs:
                        doc_snippets = doc_result.get("documentation", {}).get("snippets", [])[:5]
                        if doc_snippets:
                            context_parts.append("\n\n=== DOCUMENTATION FROM CONTEXT7 ===")
                            for s in doc_snippets:
                                context_parts.append(
                                    f"\n{s.get('title', 'Example')}: {s.get('description', '')}\n{s.get('code', '')[:500]}"
                                )

                    context = "\n".join(context_parts)

                    research_query = f"""Based on this official documentation for {package_name}:

{context}

Answer this specific question: {query}"""

                    llm_result = researcher.research(research_query)

                    llm_response: Dict[str, Any] = {
                        "package": package_name,
                        "query": query,
                        "status": "success",
                        "answer": llm_result.answer,
                        "source": "multi_source+llm" if use_chroma else "real_docs+llm",
                        "providers": [],
                        "version": KIT_VERSION,
                    }

                    # Add provider information
                    inner_providers: List[str] = []
                    if use_chroma:
                        inner_providers.append("ChromaPackageSearch")
                        llm_response["chroma_results"] = chroma_results[:3] if chroma_results else []

                    if has_real_docs:
                        inner_providers.append(doc_result.get("provider", "UpstashProvider"))
                        llm_response["documentation"] = doc_result.get("documentation")

                    llm_response["providers"] = inner_providers

                    return llm_response
                except Exception:
                    # If LLM fails, still return the real docs
                    pass

        # Return comprehensive response
        response: Dict[str, Any] = {
            "package": package_name,
            "query": query,
            "library_id_attempted": library_id,
            "status": "success" if (use_chroma or has_real_docs) else "not_found",
            "source": "multi_source" if use_chroma else "real_docs",
            "providers": [],
            "version": KIT_VERSION,
        }

        # Add provider information
        providers_list: List[str] = []
        if use_chroma and chroma_results:
            providers_list.append("ChromaPackageSearch")
            response["chroma_results"] = chroma_results[:5] if chroma_results else []

        if doc_result:
            providers_list.append(doc_result.get("provider", "UpstashProvider"))

        response["providers"] = providers_list

        if has_real_docs or use_chroma:
            # Success - we found documentation or source code
            if has_real_docs and doc_result:
                response["documentation"] = doc_result.get("documentation")
            response["resolution_method"] = "automatic"
        else:
            # No docs found - provide rich information and PROMPT FOR RETRY
            response["available_libraries"] = search_results.get("results", [])
            response["action_required"] = "CALL_AGAIN_WITH_LIBRARY_ID"
            resolution_guidance: Dict[str, Any] = {
                "message": f"Multiple libraries found for '{package_name}'. Please call deep_research_package again with the specific library ID.",
                "instruction": "Call deep_research_package with package_name set to one of the library IDs below",
                "search_found": f"{len(search_results.get('results', []))} potential matches",
                "recommended_id": search_results["results"][0]["id"] if search_results.get("results") else None,
                "selection_criteria": {
                    "trust_score": "Higher scores (7-10) are more authoritative",
                    "code_snippets": "More snippets mean better documentation",
                },
            }
            response["resolution_guidance"] = resolution_guidance

        return response

    def _get_package_search(self) -> ChromaPackageSearch:
        """Get or create the package search client."""
        if self._package_search is None:
            self._package_search = ChromaPackageSearch()
        return self._package_search

    def package_search_grep(
        self,
        package: str,
        pattern: str,
        max_results: int = 100,
        file_pattern: Optional[str] = None,
        case_sensitive: bool = True,
    ) -> Dict[str, Any]:
        """Search package code using regex patterns."""
        try:
            client = self._get_package_search()
            results = client.grep(
                package=package,
                pattern=pattern,
                max_results=max_results,
                file_pattern=file_pattern,
                case_sensitive=case_sensitive,
            )
            return {"results": results}
        except ValueError as e:
            raise MCPError(INVALID_PARAMS, str(e))
        except Exception as e:
            logger.error(f"Package search grep error: {e}")
            raise MCPError(INTERNAL_ERROR, f"Package search failed: {e}")

    def package_search_hybrid(
        self,
        package: str,
        query: str,
        regex_filter: Optional[str] = None,
        max_results: int = 20,
        file_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search package code using semantic search with optional regex filtering."""
        try:
            client = self._get_package_search()
            results = client.hybrid_search(
                package=package,
                query=query,
                regex_filter=regex_filter,
                max_results=max_results,
                file_pattern=file_pattern,
            )
            return {"results": results}
        except ValueError as e:
            raise MCPError(INVALID_PARAMS, str(e))
        except Exception as e:
            logger.error(f"Package hybrid search error: {e}")
            raise MCPError(INTERNAL_ERROR, f"Hybrid search failed: {e}")

    def package_search_read_file(
        self,
        package: str,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        filename_sha256: Optional[str] = None,
    ) -> str:
        """Read a specific file from a package."""
        try:
            client = self._get_package_search()
            content = client.read_file(
                package=package,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                filename_sha256=filename_sha256,
            )
            return content
        except ValueError as e:
            raise MCPError(INVALID_PARAMS, str(e))
        except Exception as e:
            logger.error(f"Package read file error: {e}")
            raise MCPError(INTERNAL_ERROR, f"Failed to read file: {e}")

    def _internal_resolve_library_id(self, query: str) -> Dict[str, Any]:
        """INTERNAL: Resolve library ID - not exposed as a tool."""
        doc_service = DocumentationService(UpstashProvider())
        return doc_service.search_packages(query)

    def _internal_fetch_library_docs(
        self, library_id: str, tokens: int = 5000, topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """INTERNAL: Fetch docs directly - not exposed as a tool."""
        doc_service = DocumentationService(UpstashProvider())
        return doc_service.get_documentation(library_id, tokens=tokens, topic=topic)

    def list_tools(self) -> List[Tool]:
        """List all available tools."""
        # Get base tools from parent class
        parent_tools = super().list_tools()

        # Add our enhanced development tools
        dev_tools = [
            # Combined documentation tool (wraps Context7-like functionality)
            Tool(
                name="deep_research_package",
                description="Get real-time documentation for any package/library with optional Q&A",
                inputSchema=DeepResearchParams.model_json_schema(),
            ),
            # Chroma Package Search tools
            Tool(
                name="package_search_grep",
                description="Use regex pattern matching to retrieve relevant lines from package source code",
                inputSchema=PackageSearchGrepParams.model_json_schema(),
            ),
            Tool(
                name="package_search_hybrid",
                description="Use semantic search with optional regex filtering to explore package source code",
                inputSchema=PackageSearchHybridParams.model_json_schema(),
            ),
            Tool(
                name="package_search_read_file",
                description="Read specific lines from a single file in a code package",
                inputSchema=PackageSearchReadFileParams.model_json_schema(),
            ),
        ]

        # Note: We DON'T expose _internal_resolve_library_id or _internal_fetch_library_docs
        # Those are only used internally by deep_research_package

        # Return combined tools
        return parent_tools + dev_tools


async def serve():
    """Serve the enhanced development MCP server."""
    server = Server("kit-dev-mcp", version=KIT_VERSION)
    logic = LocalDevServerLogic()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls."""
        try:
            # Handle internal tools (not for direct user access)
            if name.startswith("_internal_"):
                # These tools can only be called by our own code, not directly by users
                # You could add additional validation here if needed
                pass

            # Handle development-specific tools
            if name == "deep_research_package":
                research_params = DeepResearchParams(**arguments)
                result = logic.deep_research_package(research_params.package_name, research_params.query)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            # Handle package search tools
            elif name == "package_search_grep":
                pkg_grep_params = PackageSearchGrepParams(**arguments)
                result = logic.package_search_grep(
                    package=pkg_grep_params.package,
                    pattern=pkg_grep_params.pattern,
                    max_results=pkg_grep_params.max_results,
                    file_pattern=pkg_grep_params.file_pattern,
                    case_sensitive=pkg_grep_params.case_sensitive,
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "package_search_hybrid":
                pkg_hybrid_params = PackageSearchHybridParams(**arguments)
                result = logic.package_search_hybrid(
                    package=pkg_hybrid_params.package,
                    query=pkg_hybrid_params.query,
                    regex_filter=pkg_hybrid_params.regex_filter,
                    max_results=pkg_hybrid_params.max_results,
                    file_pattern=pkg_hybrid_params.file_pattern,
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "package_search_read_file":
                pkg_read_params = PackageSearchReadFileParams(**arguments)
                result = logic.package_search_read_file(
                    package=pkg_read_params.package,
                    file_path=pkg_read_params.file_path,
                    start_line=pkg_read_params.start_line,
                    end_line=pkg_read_params.end_line,
                    filename_sha256=pkg_read_params.filename_sha256,
                )
                return [TextContent(type="text", text=result)]  # Return as plain text, not JSON

            # For all other tools, delegate to parent class handling
            elif name in [
                "open_repository",
                "search_code",
                "grep_code",
                "get_file_content",
                "get_multiple_file_contents",
                "extract_symbols",
                "find_symbol_usages",
                "get_file_tree",
                "get_code_summary",
                "get_git_info",
                "review_diff",
                "grep_ast",
            ]:
                # Route to parent class method
                if name == "open_repository":
                    open_params = OpenRepoParams(**arguments)
                    repo_id = logic.open_repository(open_params.path_or_url, open_params.github_token, open_params.ref)
                    return [TextContent(type="text", text=f"Opened repository with ID: {repo_id}")]
                elif name == "search_code":
                    search_params = SearchParams(**arguments)
                    result = logic.search_code(search_params.repo_id, search_params.query, search_params.pattern)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "grep_code":
                    grep_params = GrepParams(**arguments)
                    result = logic.grep_code(
                        grep_params.repo_id,
                        grep_params.pattern,
                        grep_params.case_sensitive,
                        grep_params.include_pattern,
                        grep_params.exclude_pattern,
                        grep_params.max_results,
                        grep_params.directory,
                        grep_params.include_hidden,
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "get_file_content":
                    file_params = GetFileContentParams(**arguments)
                    result = logic.get_file_content(file_params.repo_id, file_params.file_path)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "get_multiple_file_contents":
                    multi_params = GetMultipleFileContentsParams(**arguments)
                    result = logic.get_multiple_file_contents(multi_params.repo_id, multi_params.file_paths)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "extract_symbols":
                    symbol_params = ExtractSymbolsParams(**arguments)
                    result = logic.extract_symbols(
                        symbol_params.repo_id, symbol_params.file_path, symbol_params.symbol_type
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "find_symbol_usages":
                    usage_params = FindSymbolUsagesParams(**arguments)
                    result = logic.find_symbol_usages(
                        usage_params.repo_id, usage_params.symbol_name, usage_params.file_path
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "get_file_tree":
                    tree_params = GetFileTreeParams(**arguments)
                    result = logic.get_file_tree(tree_params.repo_id)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "get_code_summary":
                    summary_params = GetCodeSummaryParams(**arguments)
                    result = logic.get_code_summary(
                        summary_params.repo_id, summary_params.file_path, summary_params.symbol_name
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "get_git_info":
                    git_params = GitInfoParams(**arguments)
                    result = logic.get_git_info(git_params.repo_id)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "review_diff":
                    review_params = ReviewDiffParams(**arguments)
                    result = logic.review_diff(
                        review_params.repo_id,
                        review_params.diff_spec,
                        review_params.priority_filter,
                        review_params.max_files,
                        review_params.model,
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "grep_ast":
                    ast_params = GrepASTParams(**arguments)
                    result = logic.grep_ast(
                        ast_params.repo_id,
                        ast_params.pattern,
                        ast_params.mode,
                        ast_params.file_pattern,
                        ast_params.max_results,
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                else:
                    # Should not happen since we checked the name is in the list
                    return [TextContent(type="text", text=f"Tool {name} is recognized but not implemented")]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error in tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {e!s}")]

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return logic.list_tools()

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="analyze_codebase",
                description="Comprehensive codebase analysis with all features",
                arguments=[
                    PromptArgument(name="path", description="Path to the repository", required=True),
                    PromptArgument(name="task", description="What you want to accomplish", required=True),
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
        """Get a specific prompt."""
        if name == "analyze_codebase":
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Analyze the codebase at {arguments['path']} "
                            f"for the task: {arguments['task']}. "
                            "Use all available tools including file watching, "
                            "test running, performance analysis, and context building.",
                        ),
                    )
                ]
            )
        else:
            raise MCPError(INVALID_PARAMS, f"Unknown prompt: {name}")

    options = server.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    import asyncio

    asyncio.run(serve())
