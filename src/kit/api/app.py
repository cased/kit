"""FastAPI application exposing core kit capabilities."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kit.summaries import LLMError, SymbolNotFoundError

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
        summarizer = repo.get_summarizer()  # Get the Summarizer instance
        summary_text: str | None

        if symbol_name:
            try:
                summary_text = summarizer.summarize_function(file_path, symbol_name)
            except SymbolNotFoundError:
                try:
                    summary_text = summarizer.summarize_class(file_path, symbol_name)
                except SymbolNotFoundError:
                    # Explicitly raise HTTPException for symbol not found after trying both
                    raise HTTPException(
                        status_code=404,
                        detail=f"Symbol '{symbol_name}' not found as a function or class in '{file_path}'.",
                    )
        else:
            summary_text = summarizer.summarize_file(file_path)

        if summary_text is None:
            # This case should ideally be covered by specific errors above,
            # but as a fallback if a summary somehow results in None without an error.
            raise HTTPException(status_code=500, detail="Failed to generate summary.")

        return {"summary": summary_text}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # ValueError for API key issues from Configs (e.g., OpenAIConfig)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {e}")
    # LLMError for issues during LLM communication or if LLM returns empty
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"LLM service error: {e}")
    # ImportError if an SDK is missing (should be rare as they are core deps)
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Server capability error: Missing LLM SDK: {e}")
    # Allow other unexpected errors to be handled by FastAPI's default 500 handler
    # No generic `except Exception:` here to re-raise as 501.


@app.get("/repository/{repo_id}/semantic-search")
def semantic_search(repo_id: str, q: str, top_k: int = 5):
    """Embedding-based search (uses ChromaDB and a naive fallback embedder)."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    # Simple deterministic embedding if user hasn't built index yet or no embed_fn provided.
    def _naive_embed(text: str) -> list[float]:  # Added type hint for clarity
        # Simple embedding: sum of ASCII values, modulo 1000, as a single-dimension vector.
        # This ensures it returns List[float] as expected by some VectorDB backends.
        return [float(sum(map(ord, text)) % 1000)]

    try:
        # The embed_fn=_naive_embed ensures that search_semantic doesn't fail
        # if a more sophisticated embedding function (e.g., from sentence-transformers)
        # isn't available or configured for the VectorSearcher.
        results = repo.search_semantic(q, top_k=top_k, embed_fn=_naive_embed)
    except ImportError as e:
        # This might catch if chromadb itself is missing, though it's a core dep.
        raise HTTPException(status_code=501, detail=f"Server capability error: Missing vector search dependency: {e}")
    except ValueError as e:
        # Catch potential ValueErrors from VectorSearcher or its backend, e.g., bad top_k value.
        raise HTTPException(status_code=400, detail=f"Search parameter error: {e}")
    # Allow other unexpected errors (e.g., issues within chromadb operations)
    # to be handled by FastAPI's default 500 handler.

    return results


@app.get("/repository/{repo_id}/dependencies")
def analyze_dependencies(repo_id: str, file_path: str | None = None, depth: int = 1, language: str = "python"):
    """Dependency analysis for Python or Terraform projects."""
    try:
        repo = registry.get_repo(repo_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        analyzer = repo.get_dependency_analyzer(language)
        graph = analyzer.analyze(file_path=file_path, depth=depth)  # depth is currently ignored by the analyzer
        return graph
    except ValueError as e:  # Raised by get_dependency_analyzer for unsupported language
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:  # If file_path is provided but not found by the analyzer
        raise HTTPException(status_code=404, detail=str(e))
    # Allow other unexpected errors (e.g. issues during hcl2.loads or ast.parse)
    # to be handled by FastAPI's default 500 handler.
    # No generic `except Exception:` here to re-raise as 501.
