from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from kit.repository import Repository

router = APIRouter(
    prefix="/repository",
    tags=["Repository"]
)

# Dependency to get the repository from app.state
# This assumes the Repository instance is stored in request.app.state.repository
# by the main app setup (e.g., in cli.py based on --repo-path)
def get_repository(request: Request) -> Repository:
    if not hasattr(request.app.state, 'repository') or request.app.state.repository is None:
        raise HTTPException(
            status_code=503, 
            detail="Repository not configured or available. Ensure --repo-path is set when starting the server."
        )
    return request.app.state.repository

@router.get("/file_tree", response_model=List[Dict[str, Any]])
async def get_repo_file_tree(repo: Repository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """
    Provides the complete file and directory structure of the loaded repository.
    """
    try:
        return repo.get_file_tree()
    except Exception as e:
        # Consider logging the exception e
        raise HTTPException(status_code=500, detail=f"Error fetching file tree: {str(e)}")

@router.get("/file_content", response_class=PlainTextResponse)
async def get_repo_file_content(path: str, repo: Repository = Depends(get_repository)) -> str:
    """
    Provides the text content of a specific file.
    Requires query parameter: `path` (string, relative to repo root)
    """
    if not path:
        raise HTTPException(status_code=400, detail="'path' query parameter is required.")
    try:
        return repo.get_file_content(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        # Consider logging the exception e
        raise HTTPException(status_code=500, detail=f"Error fetching file content for {path}: {str(e)}")

@router.get("/symbols", response_model=List[Dict[str, Any]])
async def get_repo_symbols(file_path: str, repo: Repository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """
    Provides a list of extracted symbols (functions, classes, etc.) for a specific file.
    Requires query parameter: `file_path` (string, relative to repo root)
    """
    if not file_path:
        raise HTTPException(status_code=400, detail="'file_path' query parameter is required.")
    try:
        return repo.extract_symbols(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found for symbol extraction: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting symbols for {file_path}: {str(e)}")

@router.get("/search_text", response_model=List[Dict[str, Any]])
async def get_repo_search_text(
    query: str, 
    file_pattern: Optional[str] = None, 
    repo: Repository = Depends(get_repository)
) -> List[Dict[str, Any]]:
    """
    Performs a textual or regex search across the codebase.
    Requires query parameter: `query` (string)
    Optional query parameter: `file_pattern` (string, e.g., "*.py")
    """
    if not query:
        raise HTTPException(status_code=400, detail="'query' query parameter is required.")
    try:
        return repo.search_text(query=query, file_pattern=file_pattern)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during text search: {str(e)}")
