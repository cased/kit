"""FastAPI application exposing core kit capabilities."""

from __future__ import annotations

from typing import Dict

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel

from ..llm_context import ContextAssembler
from ..repository import Repository

app = FastAPI(title="kit API", version="0.1.0")


class RepoIn(BaseModel):
    path_or_url: str
    github_token: str | None = None


_repos: Dict[str, Repository] = {}


@app.post("/repository", status_code=201)
def open_repo(body: RepoIn):
    """Create/open a repository and return its ID."""
    repo = Repository(body.path_or_url, github_token=body.github_token)
    repo_id = str(len(_repos) + 1)
    _repos[repo_id] = repo
    return {"id": repo_id}


@app.get("/repository/{repo_id}/file-tree")
def get_file_tree(repo_id: str):
    """Get the file tree of the repository."""
    repo = _repos.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.get_file_tree()


@app.get("/repository/{repo_id}/files/{file_path:path}")
def get_file_content(repo_id: str, file_path: str):
    """Get the content of a specific file in the repository."""
    repo = _repos.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    try:
        content = repo.get_file_content(file_path)
        # Return content as plain text
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/repository/{repo_id}/search")
def search_text(repo_id: str, q: str, pattern: str = "*.py"):
    repo = _repos.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.search_text(q, file_pattern=pattern)


