from fastapi.testclient import TestClient
import pytest
import os
import shutil
from pathlib import Path

# Assuming your FastAPI app instance is in src.kit.api.app
# Adjust the import path if your project structure is different
from kit.api.app import app, _repos  # Import _repos to clean up

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
    _repos.clear()


def test_create_repo_and_get_id(test_repo_path: Path):
    response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    repo_id = data["id"]
    
    # Verify that the repo was actually added to the app's internal state (optional, internal check)
    # This requires importing _repos from your app module
    from kit.api.app import _repos 
    assert repo_id in _repos
    assert _repos[repo_id].repo_path == str(test_repo_path.resolve())


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
    assert os.path.join("dir1", "file2.py") in paths_in_tree # Use os.path.join for OS compatibility

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

    file_to_get = os.path.join("dir1", "file2.py") # Nested file
    expected_content = (test_repo_path / file_to_get).read_text()

    response = client.get(f"/repository/{repo_id}/files/{file_to_get}")
    assert response.status_code == 200
    assert response.text == expected_content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

def test_get_file_content_invalid_repo_id(test_repo_path: Path):
    # Use a real file path but an invalid repo_id
    response = client.get(f"/repository/invalid_repo_id_456/files/file1.txt")
    assert response.status_code == 404

def test_get_file_content_file_not_found(test_repo_path: Path):
    post_response = client.post("/repository", json={"path_or_url": str(test_repo_path)})
    assert post_response.status_code == 201
    repo_id = post_response.json()["id"]

    response = client.get(f"/repository/{repo_id}/files/non_existent_file.txt")
    assert response.status_code == 404

# More tests will follow here 