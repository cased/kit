"""FastAPI application exposing core kit capabilities."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .registry import registry

app = FastAPI(title="kit API", version="0.1.0")


class RepoIn(BaseModel):
    path_or_url: str
    github_token: str | None = None
    ref: str | None = None


@app.post("/repository", status_code=201)
def open_repo(body: RepoIn):
    """Register a repository path/URL and return its deterministic ID."""
    repo_id = registry.add(body.path_or_url, body.ref)
    # Warm cache so first follow-up request is fast
    _ = registry.get_repo(repo_id)
    return {"id": repo_id}


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
        # Return content as plain text
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


@app.delete("/repository/{repo_id}", status_code=204)
def delete_repo(repo_id: str):
    """Remove a repository from the registry and evict its cache entry."""
    try:
        registry.delete(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")
    return


# ------------------------------------------------------------------
# Additional endpoints
# ------------------------------------------------------------------


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
    file_path: str | None = None,  # kept for parity with MCP even though unused
    symbol_type: str | None = None,
):
    """Find all usages of a symbol across the repository."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    usages = repo.find_symbol_usages(symbol_name, symbol_type)
    # If caller narrowed to a particular file we filter
    if file_path:
        usages = [u for u in usages if u.get("file") == file_path]
    return usages


# ---------------------- New Capability Routes ----------------------


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
    """LLM-powered code summary (requires summaries extra)."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        summary = repo.get_code_summary(file_path, symbol_name=symbol_name)  # type: ignore[attr-defined]
    except Exception:
        # Summaries extra not installed
        raise HTTPException(status_code=501, detail="Summary capability not available on server")
    return summary


@app.get("/repository/{repo_id}/semantic-search")
def semantic_search(repo_id: str, q: str, top_k: int = 5):
    """Embedding-based search. Falls back to 501 if vector search backend unavailable."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    # Simple deterministic embedding if user hasn't built index yet.
    def _naive_embed(text: str):
        return [sum(map(ord, text)) % 1000]

    try:
        results = repo.search_semantic(q, top_k=top_k, embed_fn=_naive_embed)
    except Exception:
        raise HTTPException(status_code=501, detail="Semantic search not available on server")
    return results


@app.get("/repository/{repo_id}/dependencies")
def analyze_dependencies(repo_id: str, file_path: str | None = None, depth: int = 1, language: str = "python"):
    """Dependency analysis (only works if analyzers are installed)."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        analyzer = repo.get_dependency_analyzer(language)
        graph = analyzer.analyze(file_path=file_path, depth=depth)
        return graph
    except Exception:
        raise HTTPException(status_code=501, detail="Dependency analyzer not available for this language")
