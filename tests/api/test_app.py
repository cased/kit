import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Assuming your FastAPI app instance is in src.kit.api.app
# Adjust the import path if your project structure is different
from kit.api.app import app
from kit.api.registry import registry

client = TestClient(app)


# Fixture to create a temporary test repository
@pytest.fixture(scope="function")
def test_repo_path(tmp_path_factory):
    # Create a unique temporary directory for each test function
    repo_path = tmp_path_factory.mktemp("test_repo_")

    # Create some dummy files and directories
    (repo_path / "dir1").mkdir()
    (repo_path / "file1.txt").write_text("content of file1")
    (repo_path / "dir1" / "file2.py").write_text("# python file")

    yield repo_path
    # Teardown: Clean up the _repos dictionary to avoid state leakage between tests
    # This is a simple way; for more complex scenarios, you might need a more robust reset
    # or ensure each test uses a unique, ephemeral repo_id if the server manages them.
    # For now, we assume tests might reuse repo IDs if not careful, or that the server
    # uses a simple incrementing ID.

    # Let's find and remove the repo_id associated with this test_repo_path
    # This is a bit hacky as we're reaching into the app's internals (_repos)
    # A better approach would be a dedicated /repository/{repo_id} DELETE endpoint
    # or ensuring the test client doesn't cause persistent state changes in _repos.

    # For now, since we are adding one repo at a time in tests and they get a numeric ID,
    # and the test cleanup is scoped to function, we can try to clear _repos
    # or more safely, ensure each test that creates a repo also has a way to signal its removal
    # if the server supported it.

    # Simplest approach for now, if tests are run sequentially and create one repo:
    # Find the key in _repos that matches the path. This assumes path_or_url is stored or accessible.
    # The current Repository class stores local_path.

    # Let's clear all repos after each test function for simplicity in this initial setup.
    # This ensures no state from one test affects another.
    registry._cache.clear()  # type: ignore


def test_create_repo_and_get_id(test_repo_path: Path):
    response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    repo_id = data["id"]

    # Verify that the repo can be resolved via the registry
    repo_obj = registry.get_repo(repo_id)
    assert repo_obj.repo_path == str(test_repo_path.resolve())


def test_get_file_tree_success(test_repo_path: Path):
    # First, create a repository
    post_response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert post_response.status_code == 201
    repo_id = post_response.json()["id"]

    # Now, get the file tree
    response = client.get(f"/repository/{repo_id}/file-tree")
    assert response.status_code == 200
    file_tree = response.json()
    assert isinstance(file_tree, list)

    # Check for expected files/dirs (names can vary based on OS/tmp_path behavior with hidden files)
    # We know we created file1.txt, dir1, and dir1/file2.py
    paths_in_tree = {item["path"] for item in file_tree}
    assert "file1.txt" in paths_in_tree
    assert "dir1" in paths_in_tree
    assert os.path.join("dir1", "file2.py") in paths_in_tree  # Use os.path.join for OS compatibility


def test_get_file_tree_invalid_repo_id():
    response = client.get("/repository/invalid_repo_id_123/file-tree")
    assert response.status_code == 404


def test_get_file_content_success(test_repo_path: Path):
    post_response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert post_response.status_code == 201
    repo_id = post_response.json()["id"]

    file_to_get = "file1.txt"
    expected_content = (test_repo_path / file_to_get).read_text()

    response = client.get(f"/repository/{repo_id}/files/{file_to_get}")
    assert response.status_code == 200
    assert response.text == expected_content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


def test_get_file_content_nested_file_success(test_repo_path: Path):
    post_response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert post_response.status_code == 201
    repo_id = post_response.json()["id"]

    file_to_get = os.path.join("dir1", "file2.py")  # Nested file
    expected_content = (test_repo_path / file_to_get).read_text()

    response = client.get(f"/repository/{repo_id}/files/{file_to_get}")
    assert response.status_code == 200
    assert response.text == expected_content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


def test_get_file_content_invalid_repo_id(test_repo_path: Path):
    # Use a real file path but an invalid repo_id
    response = client.get("/repository/invalid_repo_id_456/files/file1.txt")
    assert response.status_code == 404


def test_get_file_content_file_not_found(test_repo_path: Path):
    post_response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert post_response.status_code == 201
    repo_id = post_response.json()["id"]

    response = client.get(f"/repository/{repo_id}/files/non_existent_file.txt")
    assert response.status_code == 404


# More tests will follow here

# ---------------- New endpoint tests -----------------


def test_extract_symbols_endpoint(test_repo_path: Path):
    """Ensure /symbols returns expected symbols for a TypeScript-ish file."""
    file_content = """function alpha() {}\nclass Beta {}\n"""
    (test_repo_path / "sample.js").write_text(file_content)

    repo_id = client.post("/repository", json={"path_or_url": str(test_repo_path)}).json()["id"]

    resp = client.get(f"/repository/{repo_id}/symbols", params={"file_path": "sample.js"})
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert {"alpha", "Beta"}.issubset(names)


def test_find_symbol_usages_endpoint(test_repo_path: Path):
    file_content = """def foo():\n    pass\n\nfoo()\n"""
    (test_repo_path / "example.py").write_text(file_content)

    repo_id = client.post("/repository", json={"path_or_url": str(test_repo_path)}).json()["id"]

    # Ensure symbol extraction has happened implicitly
    resp_symbols = client.get(f"/repository/{repo_id}/symbols", params={"file_path": "example.py"})
    assert resp_symbols.status_code == 200

    resp_usages = client.get(f"/repository/{repo_id}/usages", params={"symbol_name": "foo", "symbol_type": "function"})
    assert resp_usages.status_code == 200
    usages = resp_usages.json()
    # There should be at least one usage at line containing foo()
    assert any("foo" in str(u.get("context", "")) for u in usages)


def test_repo_id_changes_with_git_ref(tmp_path):
    """Ensure that specifying different refs yields different IDs."""
    import subprocess

    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()

    # Init git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    (repo_dir / "a.py").write_text("print('v1')\n")
    subprocess.run(["git", "add", "a.py"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "v1"], cwd=repo_dir, check=True)

    sha1 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()

    # second commit
    (repo_dir / "a.py").write_text("print('v2')\n")
    subprocess.run(["git", "commit", "-am", "v2"], cwd=repo_dir, check=True)
    sha2 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()

    # Register repo with first ref
    id1 = client.post("/repository", json={"path_or_url": str(repo_dir), "ref": sha1}).json()["id"]

    # Register repo with second ref
    id2 = client.post("/repository", json={"path_or_url": str(repo_dir), "ref": sha2}).json()["id"]

    assert id1 != id2, "Different commits should yield different repository IDs"
