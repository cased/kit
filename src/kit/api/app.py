"""FastAPI application exposing core kit capabilities."""
from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel

from ..repository import Repository
from ..llm_context import ContextAssembler

app = FastAPI(title="kit API", version="0.1.0")


class RepoIn(BaseModel):
    path_or_url: str
    github_token: str | None = None


_repos: Dict[str, Repository] = {}


@app.post("/repos", status_code=201)
def open_repo(body: RepoIn):
    """Create/open a repository and return its ID."""
    repo = Repository(body.path_or_url, github_token=body.github_token)
    repo_id = str(len(_repos) + 1)
    _repos[repo_id] = repo
    return {"id": repo_id}


@app.get("/repos/{repo_id}/search")
def search_text(repo_id: str, q: str, pattern: str = "*.py"):
    repo = _repos.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo.search_text(q, file_pattern=pattern)


@app.post("/repos/{repo_id}/context")
def build_context(repo_id: str, diff: str = Body(..., embed=True)):
    repo = _repos.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    assembler: ContextAssembler = repo.get_context_assembler()
    assembler.add_diff(diff)
    return {"context": assembler.format_context()}
