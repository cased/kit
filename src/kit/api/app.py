"""FastAPI application exposing core kit capabilities."""
from __future__ import annotations

import os
from typing import Dict, Optional

from fastapi import FastAPI

from ..repository import Repository
from .repository_routes import router as repository_api_router

app = FastAPI(title="kit REST API", version="0.1.0")

# Function to initialize repository and add REST API routes
def _configure_repository_api(app_to_configure: FastAPI, repo_path_str: Optional[str]):
    if repo_path_str:
        try:
            abs_repo_path = os.path.abspath(repo_path_str)
            if not os.path.isdir(abs_repo_path):
                print(f"ERROR: Repository path '{abs_repo_path}' not found or not a directory. REST API will be limited.")
                app_to_configure.state.repository = None
            else:
                print(f"INFO: Initializing repository for REST API from: {abs_repo_path}")
                repository_instance = Repository(abs_repo_path)
                app_to_configure.state.repository = repository_instance
                app_to_configure.include_router(repository_api_router) # Add our /repository routes
                print(f"INFO: Repository REST API enabled for {abs_repo_path}.")
        except Exception as e:
            print(f"ERROR: Error initializing repository from '{repo_path_str}': {e}. REST API will be limited.")
            app_to_configure.state.repository = None
    else:
        print("INFO: No repository path provided. Repository REST API will be limited/unavailable.")
        app_to_configure.state.repository = None

# Configure the app when this module is imported, based on KIT_REPO_PATH set by cli.py
_repo_path_on_load = os.environ.get("KIT_REPO_PATH")
_configure_repository_api(app, _repo_path_on_load)
