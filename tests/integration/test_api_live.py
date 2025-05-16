"""Integration tests that run the FastAPI server with Uvicorn and hit real HTTP endpoints."""

import json
import socket
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn

SERVER_HOST = "127.0.0.1"


def _find_free_port() -> int:
    """Ask the OS for an unused port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((SERVER_HOST, 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Spin up Uvicorn in a background thread and yield the base URL."""
    port = _find_free_port()
    config = uvicorn.Config("kit.api.app:app", host=SERVER_HOST, port=port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until server is ready
    timeout = 10
    start = time.time()
    while not server.started and (time.time() - start) < timeout:
        time.sleep(0.1)
    if not server.started:
        raise RuntimeError("Uvicorn server failed to start within timeout")

    base_url = f"http://{SERVER_HOST}:{port}"
    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def realistic_repo_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "realistic_repo"


# ---------------- Tests -----------------

def test_end_to_end_file_tree(live_server: str, realistic_repo_path: Path):
    # 1. Open repo
    resp = requests.post(f"{live_server}/repository", json={"path_or_url": str(realistic_repo_path)})
    assert resp.status_code == 201
    repo_id = resp.json()["id"]

    # 2. Get file tree
    tree_resp = requests.get(f"{live_server}/repository/{repo_id}/file-tree")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()
    assert any(item["path"].endswith("models/user.py") for item in tree)


def test_get_file_content_live(live_server: str, realistic_repo_path: Path):
    resp = requests.post(f"{live_server}/repository", json={"path_or_url": str(realistic_repo_path)})
    repo_id = resp.json()["id"]

    file_rel = "models/user.py"
    content_resp = requests.get(f"{live_server}/repository/{repo_id}/files/{file_rel}")
    assert content_resp.status_code == 200
    assert "class User" in content_resp.text


def test_symbol_and_usage_live(live_server: str, realistic_repo_path: Path):
    repo_id = requests.post(f"{live_server}/repository", json={"path_or_url": str(realistic_repo_path)}).json()[
        "id"
    ]

    sym_resp = requests.get(
        f"{live_server}/repository/{repo_id}/symbols", params={"file_path": "services/auth.py"}
    )
    assert sym_resp.status_code == 200
    symbols = sym_resp.json()
    assert any(s["name"] == "login" for s in symbols)

    usage_resp = requests.get(
        f"{live_server}/repository/{repo_id}/usages",
        params={"symbol_name": "login", "symbol_type": "function"},
    )
    assert usage_resp.status_code == 200
    usages = usage_resp.json()
    assert usages, "Expected at least one usage of 'login'"


def test_search_and_delete_live(live_server: str, realistic_repo_path: Path):
    repo_id = requests.post(f"{live_server}/repository", json={"path_or_url": str(realistic_repo_path)}).json()[
        "id"
    ]

    # search
    s_resp = requests.get(
        f"{live_server}/repository/{repo_id}/search", params={"q": "def", "pattern": "*.py"}
    )
    assert s_resp.status_code == 200
    assert isinstance(s_resp.json(), list)

    # index
    idx = requests.get(f"{live_server}/repository/{repo_id}/index")
    assert idx.status_code == 200
    data = idx.json()
    assert "files" in data and "symbols" in data

    # delete
    del_resp = requests.delete(f"{live_server}/repository/{repo_id}")
    assert del_resp.status_code == 204

    # subsequent request 404s
    r404 = requests.get(f"{live_server}/repository/{repo_id}/file-tree")
    assert r404.status_code == 404 