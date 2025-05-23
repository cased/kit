"""Tests for REST API with ref parameter and git metadata support."""

import subprocess
import time

import pytest
import requests


@pytest.fixture(scope="module")
def test_server():
    """Start a test kit server for API testing."""
    # Start the server on a different port to avoid conflicts
    proc = subprocess.Popen(
        ["kit", "serve", "--host", "127.0.0.1", "--port", "8999", "--reload", "false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(3)

    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8999/docs", timeout=5)
        if response.status_code != 200:
            proc.terminate()
            pytest.skip("Could not start test server")
    except requests.RequestException:
        proc.terminate()
        pytest.skip("Could not connect to test server")

    yield "http://127.0.0.1:8999"

    # Cleanup
    proc.terminate()
    proc.wait()


class TestAPIRefParameter:
    """Test REST API with ref parameter support."""

    def test_create_repository_with_ref(self, test_server):
        """Test creating repository with ref parameter."""
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})

        assert response.status_code == 201
        repo_data = response.json()
        assert "id" in repo_data
        assert isinstance(repo_data["id"], str)

        return repo_data["id"]

    def test_create_repository_without_ref(self, test_server):
        """Test creating repository without ref parameter."""
        response = requests.post(f"{test_server}/repository", json={"path_or_url": "."})

        assert response.status_code == 201
        repo_data = response.json()
        assert "id" in repo_data

    def test_git_info_endpoint(self, test_server):
        """Test the git-info endpoint."""
        # First create a repository
        response = requests.post(f"{test_server}/repository", json={"path_or_url": "."})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Test git-info endpoint
        response = requests.get(f"{test_server}/repository/{repo_id}/git-info")
        assert response.status_code == 200

        git_data = response.json()
        assert "current_sha" in git_data
        assert "current_sha_short" in git_data
        assert "current_branch" in git_data
        assert "remote_url" in git_data

        # Check that we have actual git data (not all null)
        assert git_data["current_sha"] is not None
        assert len(git_data["current_sha"]) == 40  # Full SHA
        assert git_data["current_sha_short"] is not None
        assert len(git_data["current_sha_short"]) == 7  # Short SHA

    def test_git_info_with_ref(self, test_server):
        """Test git-info endpoint with repository created with ref."""
        # Create repository with ref
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Test git-info endpoint
        response = requests.get(f"{test_server}/repository/{repo_id}/git-info")
        assert response.status_code == 200

        git_data = response.json()
        assert git_data["current_sha"] is not None

    def test_file_tree_with_ref(self, test_server):
        """Test file-tree endpoint with ref parameter."""
        # Create repository with ref
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Test file-tree endpoint
        response = requests.get(f"{test_server}/repository/{repo_id}/file-tree")
        assert response.status_code == 200

        file_tree = response.json()
        assert isinstance(file_tree, list)
        assert len(file_tree) > 0

    def test_symbols_with_ref(self, test_server):
        """Test symbols endpoint with ref parameter."""
        # Create repository with ref
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Test symbols endpoint
        response = requests.get(f"{test_server}/repository/{repo_id}/symbols")
        assert response.status_code == 200

        symbols = response.json()
        assert isinstance(symbols, dict)

    def test_search_with_ref(self, test_server):
        """Test search endpoint with ref parameter."""
        # Create repository with ref
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Test search endpoint
        response = requests.get(f"{test_server}/repository/{repo_id}/search", params={"q": "Repository"})
        assert response.status_code == 200

        search_results = response.json()
        assert isinstance(search_results, list)

    def test_invalid_ref_error(self, test_server):
        """Test that invalid ref returns appropriate error."""
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "nonexistent-ref-12345"})

        # Should return an error status
        assert response.status_code != 201

    def test_repository_id_deterministic_with_ref(self, test_server):
        """Test that repository IDs are deterministic when including ref."""
        # Create same repository with same ref twice
        repo_data1 = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"}).json()

        repo_data2 = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"}).json()

        # Should return same ID
        assert repo_data1["id"] == repo_data2["id"]

    def test_repository_id_different_with_different_ref(self, test_server):
        """Test that repository IDs differ with different refs."""
        # Create repository without ref
        repo_data1 = requests.post(f"{test_server}/repository", json={"path_or_url": "."}).json()

        # Create repository with ref
        repo_data2 = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"}).json()

        # Should return different IDs
        assert repo_data1["id"] != repo_data2["id"]

    def test_git_info_404_for_nonexistent_repo(self, test_server):
        """Test that git-info returns 404 for nonexistent repository."""
        response = requests.get(f"{test_server}/repository/nonexistent/git-info")
        assert response.status_code == 404

    def test_repository_cleanup(self, test_server):
        """Test repository deletion with ref."""
        # Create repository with ref
        response = requests.post(f"{test_server}/repository", json={"path_or_url": ".", "ref": "main"})
        assert response.status_code == 201
        repo_id = response.json()["id"]

        # Delete repository
        response = requests.delete(f"{test_server}/repository/{repo_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = requests.get(f"{test_server}/repository/{repo_id}/git-info")
        assert response.status_code == 404
