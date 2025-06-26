"""FastAPI application exposing core kit capabilities."""

from __future__ import annotations

import logging
import subprocess
from typing import Dict, List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kit.summaries import LLMError, SymbolNotFoundError

from .registry import registry

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI(title="kit API", version="0.1.0")


def sanitize_url(url: str) -> str:
    """Remove credentials from URL for safe display in error messages."""
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            # Reconstruct URL without credentials
            sanitized = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                sanitized += f":{parsed.port}"
            sanitized += parsed.path
            if parsed.query:
                sanitized += f"?{parsed.query}"
            return sanitized
        return url
    except Exception:
        # If parsing fails, return a generic message
        return "[sanitized repository URL]"


class RepoIn(BaseModel):
    path_or_url: str
    github_token: str | None = None
    ref: str | None = None


class FilePathsIn(BaseModel):
    paths: List[str]


@app.post("/repository", status_code=201)
def open_repo(body: RepoIn):
    """Register a repository path/URL and return its deterministic ID."""
    try:
        repo_id = registry.add(body.path_or_url, body.ref)
        _ = registry.get_repo(repo_id)
        logger.info(f"Repository opened successfully: {sanitize_url(body.path_or_url)}")
        return {"id": repo_id}
    except subprocess.CalledProcessError as e:
        # Git command failures (clone, checkout, etc.)
        error_msg = str(e)

        # Log full details for debugging (internal only)
        logger.warning(
            f"Git command failed: {error_msg}",
            extra={
                "repo_url": body.path_or_url,
                "ref": body.ref,
                "return_code": e.returncode,
                "event_type": "git_command_failure",
            },
        )

        # For git clone failures (exit code 128 is common for "not found")
        if e.returncode == 128 and "clone" in error_msg:
            # Extract URL from error message if possible, otherwise use generic message
            if body.path_or_url.startswith(("http://", "https://")):
                logger.info(
                    f"Repository not found: {sanitize_url(body.path_or_url)}",
                    extra={"event_type": "repository_not_found", "repo_url_sanitized": sanitize_url(body.path_or_url)},
                )
                raise HTTPException(status_code=404, detail=f"Repository not found: {sanitize_url(body.path_or_url)}")
            else:
                logger.info(
                    f"Local repository not found: {body.path_or_url}",
                    extra={"event_type": "local_repository_not_found"},
                )
                raise HTTPException(status_code=404, detail="Repository not found or inaccessible")
        else:
            raise HTTPException(status_code=500, detail=f"Git operation failed: {error_msg}")
    except FileNotFoundError as e:
        logger.warning(f"File not found: {body.path_or_url}", extra={"event_type": "file_not_found", "error": str(e)})
        raise HTTPException(status_code=404, detail=f"Repository path not found: {e!s}")
    except ValueError as e:
        # Git ref errors, invalid paths, etc.
        logger.warning(
            f"Invalid repository configuration: {body.path_or_url}",
            extra={"event_type": "invalid_configuration", "ref": body.ref, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=f"Invalid repository configuration: {e!s}")
    except Exception as e:
        # All other failures - keep it simple
        error_msg = str(e)
        error_lower = error_msg.lower()

        # Log with appropriate level based on error type
        if "permission denied" in error_lower or "access denied" in error_lower:
            logger.warning(
                "Access denied for repository",
                extra={
                    "event_type": "access_denied",
                    "repo_url_sanitized": sanitize_url(body.path_or_url)
                    if body.path_or_url.startswith(("http://", "https://"))
                    else body.path_or_url,
                    "error": error_msg,
                },
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {sanitize_url(body.path_or_url) if body.path_or_url.startswith(('http://', 'https://')) else 'repository'}",
            )
        elif "authentication failed" in error_lower or "invalid credentials" in error_lower:
            logger.warning(
                "Authentication failed for repository",
                extra={
                    "event_type": "authentication_failed",
                    "repo_url_sanitized": sanitize_url(body.path_or_url)
                    if body.path_or_url.startswith(("http://", "https://"))
                    else body.path_or_url,
                    "error": error_msg,
                },
            )
            raise HTTPException(status_code=401, detail="Authentication failed")
        elif "timeout" in error_lower or "network" in error_lower or "connection" in error_lower:
            logger.warning(
                "Network error for repository",
                extra={
                    "event_type": "network_error",
                    "repo_url_sanitized": sanitize_url(body.path_or_url)
                    if body.path_or_url.startswith(("http://", "https://"))
                    else body.path_or_url,
                    "error": error_msg,
                },
            )
            raise HTTPException(status_code=503, detail="Network error accessing repository")
        elif "repository not found" in error_lower or "not found" in error_lower:
            logger.info(
                "Repository not found",
                extra={
                    "event_type": "repository_not_found",
                    "repo_url_sanitized": sanitize_url(body.path_or_url)
                    if body.path_or_url.startswith(("http://", "https://"))
                    else body.path_or_url,
                },
            )
            raise HTTPException(
                status_code=404,
                detail=f"Repository not found: {sanitize_url(body.path_or_url) if body.path_or_url.startswith(('http://', 'https://')) else body.path_or_url}",
            )
        else:
            logger.error(
                "Unexpected error initializing repository",
                extra={
                    "event_type": "unexpected_error",
                    "repo_url_sanitized": sanitize_url(body.path_or_url)
                    if body.path_or_url.startswith(("http://", "https://"))
                    else body.path_or_url,
                    "error": error_msg,
                },
            )
            raise HTTPException(status_code=500, detail="Failed to initialize repository")


@app.get("/repository/{repo_id}/file-tree")
def get_file_tree(repo_id: str):
    """Get the file tree of the repository."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.get_file_tree()


@app.get("/repository/{repo_id}/files/{file_path:path}")
def get_file_content(repo_id: str, file_path: str):
    """Get the content of a specific file in the repository."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    try:
        content = repo.get_file_content(file_path)
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e!s}")


@app.get("/repository/{repo_id}/search")
def search_text(repo_id: str, q: str, pattern: str = "*.py"):
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.search_text(q, file_pattern=pattern)


@app.get("/repository/{repo_id}/grep")
def grep_text(
    repo_id: str,
    pattern: str,
    case_sensitive: bool = True,
    include_pattern: str | None = None,
    exclude_pattern: str | None = None,
    max_results: int = 1000,
    directory: str | None = None,
    include_hidden: bool = False,
):
    """Perform literal grep search on repository files."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        return repo.grep(
            pattern,
            case_sensitive=case_sensitive,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            max_results=max_results,
            directory=directory,
            include_hidden=include_hidden,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/repository/{repo_id}", status_code=204)
def delete_repo(repo_id: str):
    """Remove a repository from the registry and evict its cache entry."""
    try:
        registry.delete(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    return


@app.get("/repository/{repo_id}/symbols")
def extract_symbols(repo_id: str, file_path: str | None = None, symbol_type: str | None = None):
    """Extract symbols from a specific file or whole repo."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    symbols = repo.extract_symbols(file_path)  # type: ignore[arg-type]
    if symbol_type:
        symbols = [s for s in symbols if s.get("type") == symbol_type]
    return symbols


@app.get("/repository/{repo_id}/usages")
def find_symbol_usages(
    repo_id: str,
    symbol_name: str,
    file_path: str | None = None,
    symbol_type: str | None = None,
):
    """Find all usages of a symbol across the repository."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    usages = repo.find_symbol_usages(symbol_name, symbol_type)
    if file_path:
        usages = [u for u in usages if u.get("file") == file_path]
    return usages


@app.get("/repository/{repo_id}/index")
def get_full_index(repo_id: str):
    """Return combined file tree + symbols index."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.index()


@app.get("/repository/{repo_id}/summary")
def get_summary(repo_id: str, file_path: str, symbol_name: str | None = None):
    """LLM-powered code summary."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        summarizer = repo.get_summarizer()
        summary_text: str | None

        if symbol_name:
            try:
                summary_text = summarizer.summarize_function(file_path, symbol_name)
            except SymbolNotFoundError:
                try:
                    summary_text = summarizer.summarize_class(file_path, symbol_name)
                except SymbolNotFoundError:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Symbol '{symbol_name}' not found as a function or class in '{file_path}'.",
                    )
        else:
            summary_text = summarizer.summarize_file(file_path)

        if summary_text is None:
            raise HTTPException(status_code=500, detail="Failed to generate summary.")

        return {"summary": summary_text}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {e}")
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"LLM service error: {e}")
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Server capability error: Missing LLM SDK: {e}")


@app.get("/repository/{repo_id}/dependencies")
def analyze_dependencies(repo_id: str, file_path: str | None = None, depth: int = 1, language: str = "python"):
    """Dependency analysis for Python or Terraform projects."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        analyzer = repo.get_dependency_analyzer(language)
        graph = analyzer.analyze(file_path=file_path, depth=depth)
        return graph
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/repository/{repo_id}/git-info")
def get_git_info(repo_id: str):
    """Get git metadata for the repository (SHA, branch, remote URL)."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    return {
        "current_sha": repo.current_sha,
        "current_sha_short": repo.current_sha_short,
        "current_branch": repo.current_branch,
        "remote_url": repo.remote_url,
    }


@app.post("/repository/{repo_id}/files")
def get_multiple_file_contents(repo_id: str, body: FilePathsIn) -> Dict[str, str]:
    """Get the contents of multiple files in one call.

    Request body JSON:
        {
            "paths": ["src/main.py", "src/utils/helper.py"]
        }
    """
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    if not body.paths:
        return {}

    try:
        contents = repo.get_file_content(body.paths)
        # Ensure we return mapping of requested path -> content
        return contents  # type: ignore[return-value]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Error reading files: {e!s}")
