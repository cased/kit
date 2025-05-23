"""MCP server implementation for kit."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
    ToolAnnotations,
)
from pydantic.networks import AnyUrl

# Newer releases renamed ``ResourceContent`` ➔ ``EmbeddedResource``.  Import
# them independently so the absence of one does not mask the other.
#
# The strategy is:
#   1. Prefer ``EmbeddedResource`` and alias it to ``ResourceContent`` so we can
#      continue to refer to a single symbol in the rest of the module.
#   2. Fall back to an actual ``ResourceContent`` if the older name still
#      exists.
#   3. As a last resort, synthesize a minimal stub so unit-tests can still
#      import the module even when the MCP SDK is unavailable.

# ---------------------------------------------------------------------------
# ResourceContent (aka EmbeddedResource)
# ---------------------------------------------------------------------------

try:
    from mcp.types import EmbeddedResource as ResourceContent  # type: ignore
except ImportError:  # pragma: no cover – older SDK
    try:
        from mcp.types import ResourceContent  # type: ignore
    except ImportError:
        from pydantic import BaseModel

        class ResourceContent(BaseModel):  # type: ignore
            resource: str
            uri: str

# ---------------------------------------------------------------------------
# ErrorContent (removed in newer specs)
# ---------------------------------------------------------------------------

try:
    from mcp.types import ErrorContent  # type: ignore
except ImportError:  # pragma: no cover – define minimal stub
    from pydantic import BaseModel

    class ErrorContent(BaseModel):  # type: ignore
        error: ErrorData


from pydantic import BaseModel, ValidationError

from .. import __version__ as KIT_VERSION
from ..docstring_indexer import DocstringIndexer
from ..repository import Repository
from ..summaries import Summarizer
from ..tree_sitter_symbol_extractor import TreeSitterSymbolExtractor
from ..vector_searcher import VectorSearcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("kit-mcp")


def create_error_content(code: int, message: str) -> ErrorContent:
    return ErrorContent(error=ErrorData(code=code, message=message))


class MCPError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

    def to_error_data(self) -> ErrorData:
        return ErrorData(code=self.code, message=self.message)


class OpenRepoParams(BaseModel):
    path_or_url: str
    github_token: Optional[str] = None
    ref: Optional[str] = None


class SearchParams(BaseModel):
    repo_id: str
    query: str
    pattern: str = "*.py"


class GetFileContentParams(BaseModel):
    repo_id: str
    file_path: str


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


class SemanticSearchParams(BaseModel):
    repo_id: str
    query: str


class GetDocumentationParams(BaseModel):
    repo_id: str
    symbol_name: Optional[str] = None
    file_path: Optional[str] = None


class GetCodeSummaryParams(BaseModel):
    repo_id: str
    file_path: str
    symbol_name: Optional[str] = None


class GitInfoParams(BaseModel):
    repo_id: str


class KitServerLogic:
    def __init__(self):
        self._repos: Dict[str, Repository] = {}
        self._analyzers: Dict[str, Dict[str, Any]] = {}

    def get_repo(self, repo_id: str) -> Repository:
        repo = self._repos.get(repo_id)
        if not repo:
            raise MCPError(code=INVALID_PARAMS, message=f"Repository {repo_id} not found")
        return repo

    def open_repository(self, path_or_url: str, github_token: Optional[str] = None, ref: Optional[str] = None) -> str:
        try:
            repo = Repository(path_or_url, github_token=github_token, ref=ref)
            repo_id = str(uuid.uuid4())
            self._repos[repo_id] = repo
            self._analyzers[repo_id] = {}
            return repo_id
        except FileNotFoundError as e:
            raise MCPError(code=INVALID_PARAMS, message=f"Repository path not found: {e!s}")
        except Exception as e:
            raise MCPError(code=INVALID_PARAMS, message=str(e))

    def search_code(self, repo_id: str, query: str, pattern: str = "*.py") -> list[dict[str, Any]]:
        repo = self.get_repo(repo_id)
        try:
            return repo.search_text(query, file_pattern=pattern)
        except Exception as e:
            raise MCPError(code=INVALID_PARAMS, message=f"Invalid search pattern: {e!s}")

    def get_file_content(self, repo_id: str, file_path: str) -> str:
        repo = self.get_repo(repo_id)
        # Validate that the requested path stays within repo
        safe_path = self._check_within_repo(repo, file_path)
        rel_path = str(safe_path.relative_to(Path(repo.repo_path)))
        try:
            return repo.get_file_content(rel_path)
        except FileNotFoundError as e:
            raise MCPError(code=INVALID_PARAMS, message=str(e))
        except Exception as e:
            raise MCPError(code=INVALID_PARAMS, message=f"Error reading file: {e!s}")

    def extract_symbols(self, repo_id: str, file_path: str, symbol_type: Optional[str] = None) -> list[dict]:
        repo = self.get_repo(repo_id)
        try:
            safe_path = self._check_within_repo(repo, file_path)
            rel_path = str(safe_path.relative_to(Path(repo.repo_path)))
            symbols = repo.extract_symbols(rel_path)
            return [s for s in symbols if s["type"] == symbol_type] if symbol_type else symbols
        except FileNotFoundError as e:
            raise MCPError(code=INVALID_PARAMS, message=str(e))
        except Exception as e:
            raise MCPError(code=INVALID_PARAMS, message=f"Error extracting symbols: {e!s}")

    def find_symbol_usages(
        self,
        repo_id: str,
        symbol_name: str,
        file_path: Optional[str] = None,
        symbol_type: Optional[str] = None,
    ) -> list[dict]:
        repo = self.get_repo(repo_id)
        if file_path:
            # validate path but use only relative path for comparison
            safe_path = self._check_within_repo(repo, file_path)
            file_path_rel = str(safe_path.relative_to(Path(repo.repo_path)))
        else:
            file_path_rel = None

        usages = repo.find_symbol_usages(symbol_name, symbol_type=symbol_type)
        if file_path_rel:
            usages = [u for u in usages if u.get("file") == file_path_rel]
        return usages

    def get_file_tree(
        self,
        repo_id: str,
    ) -> Any:
        repo = self.get_repo(repo_id)
        tree_list = repo.get_file_tree()

        return tree_list

    def get_analyzer(self, repo_id: str, analyzer_name: str, kwargs: Optional[dict] = None) -> Any:
        if repo_id not in self._analyzers:
            raise MCPError(code=INVALID_PARAMS, message=f"Repository {repo_id} not found")
        if analyzer_name not in self._analyzers[repo_id]:
            repo = self._repos[repo_id]
            if analyzer_name == "vector_searcher":
                embed_fn = (kwargs or {}).get("embed_fn")
                # Fallback to dummy embeddings if none provided → avoids crash
                if embed_fn is None:

                    def embed_fn(sents):
                        return [[0.0] * 768 for _ in sents]

                self._analyzers[repo_id][analyzer_name] = VectorSearcher(repo, embed_fn=embed_fn)
            elif analyzer_name == "docstring_indexer":
                # DocstringIndexer requires a Summarizer instance
                summarizer = Summarizer(repo)
                self._analyzers[repo_id][analyzer_name] = DocstringIndexer(repo, summarizer)
            elif analyzer_name == "code_summarizer":
                self._analyzers[repo_id][analyzer_name] = Summarizer(repo)
            elif analyzer_name == "symbol_extractor":
                # TreeSitterSymbolExtractor has a static API; no init args.
                self._analyzers[repo_id][analyzer_name] = TreeSitterSymbolExtractor()
            else:
                raise MCPError(code=INVALID_PARAMS, message=f"Unknown analyzer: {analyzer_name}")
        return self._analyzers[repo_id][analyzer_name]

    def semantic_search(self, repo_id: str, query: str) -> Any:
        analyzer = self.get_analyzer(repo_id, "vector_searcher")
        if analyzer is None:
            raise MCPError(code=INTERNAL_ERROR, message="Vector search not available")
        return analyzer.search(query)

    def get_documentation(self, repo_id: str, symbol_name: Optional[str], file_path: Optional[str]) -> Any:
        analyzer = self.get_analyzer(repo_id, "docstring_indexer")
        if file_path:
            safe = self._check_within_repo(self.get_repo(repo_id), file_path)
            file_path = str(safe.relative_to(Path(self.get_repo(repo_id).repo_path)))
        return analyzer.get_documentation(symbol_name=symbol_name, file_path=file_path)

    def get_code_summary(self, repo_id: str, file_path: str, symbol_name: Optional[str] = None) -> Any:
        repo = self.get_repo(repo_id)
        # validate path
        safe_path = self._check_within_repo(repo, file_path)
        rel_path = str(safe_path.relative_to(Path(repo.repo_path)))
        try:
            analyzer = self.get_analyzer(repo_id, "code_summarizer")
            # Get all three types of summaries
            summaries: Dict[str, Any] = {}
            # Always get file summary
            summaries["file"] = analyzer.summarize_file(rel_path)

            # Get function and class summaries only if symbol_name is provided
            if symbol_name:
                try:
                    summaries["function"] = analyzer.summarize_function(rel_path, symbol_name)
                except ValueError:
                    # If symbol is not a function, set to None
                    summaries["function"] = None

                try:
                    summaries["class"] = analyzer.summarize_class(rel_path, symbol_name)
                except ValueError:
                    # If symbol is not a class, set to None
                    summaries["class"] = None

            return summaries

        except Exception as e:
            raise MCPError(code=INVALID_PARAMS, message=str(e))

    def get_git_info(self, repo_id: str) -> dict[str, Any]:
        """Get git metadata for a repository."""
        repo = self.get_repo(repo_id)
        return {
            "current_sha": repo.current_sha,
            "current_sha_short": repo.current_sha_short,
            "current_branch": repo.current_branch,
            "remote_url": repo.remote_url,
        }

    def list_tools(self) -> list[Tool]:
        ro_ann = ToolAnnotations(readOnlyHint=True)
        tools_to_return = [
            Tool(
                name="open_repository",
                description="Open a repository and return its ID",
                inputSchema=OpenRepoParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="search_code",
                description="Search text in a repository",
                inputSchema=SearchParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="get_file_content",
                description="Get file contents",
                inputSchema=GetFileContentParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="extract_symbols",
                description="Extract symbols from a file",
                inputSchema=ExtractSymbolsParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="find_symbol_usages",
                description="Find symbol usages",
                inputSchema=FindSymbolUsagesParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="get_file_tree",
                description="Return repo file structure",
                inputSchema=GetFileTreeParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="get_code_summary",
                description="Get a summary of code for a given file. If symbol_name is provided, also attempts to summarize it as a function and class.",
                inputSchema=GetCodeSummaryParams.model_json_schema(),
                annotations=ro_ann,
            ),
            Tool(
                name="get_git_info",
                description="Get git repository metadata (SHA, branch, remote URL)",
                inputSchema=GitInfoParams.model_json_schema(),
                annotations=ro_ann,
            ),
        ]
        logger.info(f"KitServerLogic.list_tools is returning: {[tool.name for tool in tools_to_return]}")
        return tools_to_return

    def list_prompts(self) -> list[Prompt]:
        return [
            Prompt(
                name="open_repo",
                description="Open a repository and explore its contents",
                arguments=[
                    PromptArgument(
                        name="path_or_url", description="Path to local repository or GitHub URL", required=True
                    ),
                    PromptArgument(
                        name="github_token", description="GitHub token for private repositories", required=False
                    ),
                ],
            ),
            Prompt(
                name="search_repo",
                description="Search for code in a repository",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                    PromptArgument(name="query", description="Text search query", required=True),
                    PromptArgument(name="pattern", description="Optional file pattern (e.g. *.py)", required=False),
                ],
            ),
            Prompt(
                name="get_file_content",
                description="Get the content of a specific file",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                    PromptArgument(name="file_path", description="Path to the file", required=True),
                ],
            ),
            Prompt(
                name="extract_symbols",
                description="Extract functions, classes or symbols from a file",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                    PromptArgument(name="file_path", description="Path to the file", required=True),
                    PromptArgument(
                        name="symbol_type", description="Optional filter: function or class", required=False
                    ),
                ],
            ),
            Prompt(
                name="find_symbol_usages",
                description="Find all usages of a given symbol",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                    PromptArgument(name="symbol_name", description="Name of the symbol to find", required=True),
                    PromptArgument(
                        name="file_path", description="Optional file path to narrow the search", required=False
                    ),
                ],
            ),
            Prompt(
                name="get_file_tree",
                description="Get the file structure of the repository",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                ],
            ),
            Prompt(
                name="get_code_summary",
                description="Get a summary of code for a given file. If symbol_name is provided, also attempts to summarize it as a function and class.",
                arguments=[
                    PromptArgument(name="repo_id", description="ID of the repository", required=True),
                    PromptArgument(name="file_path", description="Path to the file", required=True),
                    PromptArgument(
                        name="symbol_name",
                        description="Optional name of a function or class to summarize. If provided, will attempt to summarize it as both a function and class.",
                        required=False,
                    ),
                ],
            ),
        ]

    def get_prompt(self, name: str, arguments: dict | None) -> GetPromptResult:
        if not arguments:
            raise MCPError(code=INVALID_PARAMS, message="Arguments are required")

        try:
            match name:
                case "open_repo":
                    open_args = OpenRepoParams(**arguments)
                    repo_id = self.open_repository(open_args.path_or_url, open_args.github_token, open_args.ref)
                    repo = self._repos[repo_id]
                    return GetPromptResult(
                        description=f"Repository opened with ID: {repo_id}",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(
                                    type="text", text=f"Opened repo {repo_id} with tree:\n{repo.get_file_tree()}"
                                ),
                            )
                        ],
                    )
                case "search_repo":
                    search_args = SearchParams(**arguments)
                    results = self.search_code(search_args.repo_id, search_args.query, search_args.pattern)
                    return GetPromptResult(
                        description="Search results",
                        messages=[PromptMessage(role="user", content=TextContent(type="text", text=str(results)))],
                    )
                case "get_file_content":
                    gfc_args = GetFileContentParams(**arguments)
                    # Validate path access but avoid sending full file in-band
                    self.get_file_content(gfc_args.repo_id, gfc_args.file_path)
                    return GetPromptResult(
                        description="File content",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(
                                    type="text", text=f"/repos/{gfc_args.repo_id}/files/{gfc_args.file_path}"
                                ),
                            )
                        ],
                    )
                case "extract_symbols":
                    es_args = ExtractSymbolsParams(**arguments)
                    symbols = self.extract_symbols(es_args.repo_id, es_args.file_path, es_args.symbol_type)
                    return GetPromptResult(
                        description="Extracted symbols",
                        messages=[
                            PromptMessage(
                                role="user", content=TextContent(type="text", text=json.dumps(symbols, indent=2))
                            )
                        ],
                    )
                case "find_symbol_usages":
                    fu_args = FindSymbolUsagesParams(**arguments)
                    usages = self.find_symbol_usages(
                        fu_args.repo_id, fu_args.symbol_name, fu_args.file_path, fu_args.symbol_type
                    )
                    return GetPromptResult(
                        description="Symbol usages",
                        messages=[
                            PromptMessage(
                                role="user", content=TextContent(type="text", text=json.dumps(usages, indent=2))
                            )
                        ],
                    )
                case "get_file_tree":
                    gft_args = GetFileTreeParams(**arguments)
                    tree = self.get_file_tree(gft_args.repo_id)
                    return GetPromptResult(
                        description="File tree",
                        messages=[
                            PromptMessage(
                                role="user", content=TextContent(type="text", text=json.dumps(tree, indent=2))
                            )
                        ],
                    )
                case "get_code_summary":
                    gcs_args = GetCodeSummaryParams(**arguments)
                    summary = self.get_code_summary(gcs_args.repo_id, gcs_args.file_path, gcs_args.symbol_name)
                    return GetPromptResult(
                        description="Code summary",
                        messages=[
                            PromptMessage(
                                role="user", content=TextContent(type="text", text=json.dumps(summary, indent=2))
                            )
                        ],
                    )
                case "get_git_info":
                    git_args = GitInfoParams(**arguments)
                    git_info = self.get_git_info(git_args.repo_id)
                    return GetPromptResult(
                        description="Git repository metadata",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=json.dumps(git_info, indent=2)),
                            )
                        ],
                    )
                case _:
                    raise MCPError(code=INVALID_PARAMS, message=f"Unknown prompt: {name}")
        except KeyError as e:
            raise MCPError(code=INVALID_PARAMS, message=f"Missing required argument: {e.args[0]}")
        except ValidationError as e:
            # Attempt to find the first missing field for a more specific error
            missing_field = next(
                (err.get("loc", [None])[0] for err in e.errors() if err.get("type") == "missing"), None
            )
            if missing_field:
                raise MCPError(code=INVALID_PARAMS, message=f"Missing required argument: {missing_field}")
            # Fallback to generic ValidationError message if no specific missing field found
            raise MCPError(code=INVALID_PARAMS, message=str(e))
        # Let other MCPError instances or unexpected Exceptions bubble up if not caught by specific cases above
        # The async get_prompt handler will catch them.

    def list_resources(self) -> list[Resource]:
        """Expose heavyweight artifacts via resources."""
        return [
            Resource(
                uri=cast(AnyUrl, "mcp://file/{repo_id}/{file_path}"),
                name="file",
                description="Raw file contents",
                mimeType="text/plain",
            ),
            Resource(
                uri=cast(AnyUrl, "mcp://tree/{repo_id}"),
                name="tree",
                description="Serialized repo tree JSON",
                mimeType="application/json",
            ),
        ]

    def list_resource_templates(self) -> list[ResourceTemplate]:  # type: ignore[name-defined]
        """Return RFC6570-style templates so clients can construct URIs."""
        from mcp.types import ResourceTemplate

        return [
            ResourceTemplate(
                uriTemplate="mcp://file/{repo_id}/{file_path}",
                name="file",
                description="Raw file contents",
                mimeType="text/plain",
            ),
            ResourceTemplate(
                uriTemplate="mcp://tree/{repo_id}",
                name="tree",
                description="Serialized repo tree JSON",
                mimeType="application/json",
            ),
        ]

    def read_resource(self, uri: str) -> tuple[str, str]:
        """Return (mime_type, text) for the requested resource uri."""
        from urllib.parse import unquote, urlparse

        parsed = urlparse(uri)
        if parsed.scheme != "mcp":
            raise MCPError(INVALID_PARAMS, "Unsupported URI scheme")

        path_parts = [p for p in parsed.path.split("/") if p]
        if not path_parts:
            raise MCPError(INVALID_PARAMS, "Invalid MCP URI")

        kind = path_parts[0]
        if kind == "file" and len(path_parts) >= 3:
            repo_id = path_parts[1]
            file_path = "/".join(path_parts[2:])
            content = self.get_file_content(repo_id, unquote(file_path))
            return "text/plain", content
        elif kind == "tree" and len(path_parts) == 2:
            repo_id = path_parts[1]
            tree = self.get_file_tree(repo_id)
            return "application/json", json.dumps(tree)
        else:
            raise MCPError(INVALID_PARAMS, "Unknown resource URI")

    def analyze_dependencies(self, repo_id: str, file_path: Optional[str], depth: int) -> Any:
        analyzer = self.get_analyzer(repo_id, "dependency_analyzer")
        if file_path:
            safe = self._check_within_repo(self.get_repo(repo_id), file_path)
            file_path = str(safe.relative_to(Path(self.get_repo(repo_id).repo_path)))
        return analyzer.analyze(file_path=file_path, depth=depth)

    # ---------------------------------------------------------------------
    # Internal path guard
    # ---------------------------------------------------------------------

    def _check_within_repo(self, repo: Repository, path: str) -> Path:
        """Resolve *path* against the repo root and ensure it stays inside it.

        Raises MCPError(INVALID_PARAMS) if the resolved path escapes the
        repository.  Returns the absolute ``Path`` on success.
        """
        requested = (Path(repo.repo_path) / path).resolve()
        if not str(requested).startswith(str(Path(repo.repo_path).resolve())):
            raise MCPError(INVALID_PARAMS, "Path traversal outside repository root")
        return requested


async def serve() -> None:
    server: Server = Server("kit")
    logic = KitServerLogic()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ErrorContent | ResourceContent]:
        try:
            if name == "open_repository":
                open_args = OpenRepoParams(**arguments)
                repo_id = logic.open_repository(open_args.path_or_url, open_args.github_token, open_args.ref)
                return [TextContent(type="text", text=repo_id)]
            elif name == "search_code":
                search_args = SearchParams(**arguments)
                results = logic.search_code(search_args.repo_id, search_args.query, search_args.pattern)
                return [TextContent(type="text", text=json.dumps(results, indent=2))]
            elif name == "get_file_content":
                gfc_args = GetFileContentParams(**arguments)
                # Validate path access but avoid sending full file in-band
                logic.get_file_content(gfc_args.repo_id, gfc_args.file_path)
                return [TextContent(type="text", text=f"/repos/{gfc_args.repo_id}/files/{gfc_args.file_path}")]
            elif name == "extract_symbols":
                es_args = ExtractSymbolsParams(**arguments)
                symbols = logic.extract_symbols(es_args.repo_id, es_args.file_path, es_args.symbol_type)
                return [TextContent(type="text", text=json.dumps(symbols, indent=2))]
            elif name == "find_symbol_usages":
                fu_args = FindSymbolUsagesParams(**arguments)
                usages = logic.find_symbol_usages(
                    fu_args.repo_id, fu_args.symbol_name, fu_args.file_path, fu_args.symbol_type
                )
                return [TextContent(type="text", text=json.dumps(usages, indent=2))]
            elif name == "get_file_tree":
                gft_args = GetFileTreeParams(**arguments)
                tree = logic.get_file_tree(gft_args.repo_id)
                return [TextContent(type="text", text=json.dumps(tree, indent=2))]
            elif name == "get_code_summary":
                gcs_args = GetCodeSummaryParams(**arguments)
                summary = logic.get_code_summary(gcs_args.repo_id, gcs_args.file_path, gcs_args.symbol_name)
                return [TextContent(type="text", text=json.dumps(summary, indent=2))]
            elif name == "get_git_info":
                git_args = GitInfoParams(**arguments)
                git_info = logic.get_git_info(git_args.repo_id)
                return [TextContent(type="text", text=json.dumps(git_info, indent=2))]
            else:
                raise MCPError(code=INVALID_PARAMS, message=f"Unknown tool: {name}")
        except ValidationError as e:
            # Wrap ErrorContent in TextContent to satisfy Pydantic Union validation
            error_payload = create_error_content(INVALID_PARAMS, str(e))
            return [TextContent(type="text", text=json.dumps({"error": error_payload.error.model_dump()}))]
        except MCPError as e:
            error_payload = create_error_content(e.code, e.message)
            return [TextContent(type="text", text=json.dumps({"error": error_payload.error.model_dump()}))]
        except Exception as e:
            logger.exception("Unhandled error in call_tool")
            error_payload = create_error_content(INTERNAL_ERROR, str(e))
            return [TextContent(type="text", text=json.dumps({"error": error_payload.error.model_dump()}))]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        try:
            return logic.list_tools()
        except Exception:
            logger.exception("ERROR: Failed in list_tools method")
            raise

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        try:
            return logic.list_prompts()
        except Exception:
            logger.exception("ERROR: Failed in list_prompts method")
            raise

    @server.list_resource_templates()
    async def _list_resource_templates() -> list[ResourceTemplate]:  # type: ignore[name-defined]
        try:
            return logic.list_resource_templates()
        except Exception:
            logger.exception("ERROR: Failed in list_resource_templates")
            raise

    @server.read_resource()
    async def _read_resource(uri: AnyUrl):  # type: ignore[name-defined]
        try:
            mime, text = logic.read_resource(str(uri))
            from mcp.types import TextResourceContents

            return TextResourceContents(uri=uri, mimeType=mime, text=text)
        except MCPError:
            raise
        except Exception:
            logger.exception("ERROR: Failed in read_resource")
            raise

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        # Added try-except for robust logging
        try:
            return logic.get_prompt(name, arguments)
        except MCPError as e:  # Already handled MCPError specifically
            logger.warn(f"MCPError in get_prompt ({name}): {e.message}")
            raise
        except Exception:
            logger.exception(f"ERROR: Unhandled error in get_prompt ({name})")
            raise

    # Now, add logging around options creation
    logger.info("Attempting to create MCP initialization options...")
    try:
        options = server.create_initialization_options()
        logger.info("MCP initialization options created successfully.")
        # Print to *raw* stderr so that hosts which capture only raw stderr (like
        # Claude Desktop) always see at least one line confirming startup.
        print("kit-mcp: initialization options ready", file=sys.stderr, flush=True)
    except Exception:
        logger.exception("ERROR: Failed to create MCP initialization options")
        raise  # Re-raise to stop the server if options are critical

    kit_version = KIT_VERSION
    logger.info("Starting MCP server (version: %s) run loop with stdio...", kit_version)
    print(f"kit-mcp: starting run loop (kit {kit_version})", file=sys.stderr, flush=True)

    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
        except Exception as e:
            # Print trace to stderr for hosts that don't capture Python logging
            import io
            import traceback

            buf = io.StringIO()
            traceback.print_exc(file=buf)
            print("kit-mcp: fatal error\n" + buf.getvalue(), file=sys.stderr, flush=True)
            buf.close()
            logger.exception("Fatal error in server.run: %s", e)
            raise
