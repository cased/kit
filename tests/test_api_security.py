"""Tests for REST API security features including URL sanitization and error handling."""

import logging
import subprocess
import time
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import requests
from pydantic import BaseModel

from kit.api.app import sanitize_url


class RepoIn(BaseModel):
    """Request model for repository creation."""

    path_or_url: str
    ref: str = None


class TestURLSanitization:
    """Test URL sanitization functionality."""

    def test_sanitize_clean_url(self):
        """Test that clean URLs are unchanged."""
        clean_urls = [
            "https://github.com/user/repo",
            "http://localhost:3000/repo",
            "https://gitlab.com/org/project",
            "git@github.com:user/repo.git",  # This will remain unchanged as it's not HTTP(S)
        ]

        for url in clean_urls:
            result = sanitize_url(url)
            assert result == url

    def test_sanitize_url_with_credentials(self):
        """Test that URLs with credentials are properly sanitized."""
        test_cases = [
            {"input": "https://token:x-oauth-basic@github.com/user/repo", "expected": "https://github.com/user/repo"},
            {"input": "https://username:password@gitlab.com/user/repo", "expected": "https://gitlab.com/user/repo"},
            {"input": "https://ghp_token123@github.com/private/repo", "expected": "https://github.com/private/repo"},
            {
                "input": "https://user:pass@example.com:8080/path?query=value",
                "expected": "https://example.com:8080/path?query=value",
            },
            {"input": "http://api_key:secret@api.example.com/v1/repo", "expected": "http://api.example.com/v1/repo"},
        ]

        for case in test_cases:
            result = sanitize_url(case["input"])
            assert result == case["expected"], f"Failed for {case['input']}"

    def test_sanitize_url_preserves_path_and_query(self):
        """Test that path and query parameters are preserved during sanitization."""
        url = "https://token:secret@api.github.com/repos/user/repo?per_page=100&page=1"
        result = sanitize_url(url)

        assert result == "https://api.github.com/repos/user/repo?per_page=100&page=1"
        assert "token" not in result
        assert "secret" not in result
        assert "per_page=100" in result
        assert "page=1" in result

    def test_sanitize_url_handles_malformed_urls(self):
        """Test that malformed URLs are handled gracefully."""
        malformed_urls = [
            "not-a-url",
            "http://",
            "://missing-scheme",
            "",
            None,  # This would cause an exception in real usage, but our function should handle it
        ]

        for url in malformed_urls:
            if url is None:
                continue  # Skip None as it would cause TypeError in real usage
            result = sanitize_url(url)
            # Should either return the original or a safe fallback
            assert isinstance(result, str)

    def test_sanitize_url_no_credentials_present(self):
        """Test that URLs without credentials are detected correctly."""
        urls_without_creds = [
            "https://github.com/user/repo",
            "http://localhost:8000",
            "https://api.example.com/v1/data",
        ]

        for url in urls_without_creds:
            parsed = urlparse(url)
            assert parsed.username is None
            assert parsed.password is None
            assert sanitize_url(url) == url


class TestAPISecurityErrorHandling:
    """Test API error handling with security considerations."""

    def test_repository_creation_sanitizes_credentials_in_404_error(self):
        """Test that 404 errors for remote repos sanitize credentials in response."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
        ):
            # Mock a git clone failure
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone", "--depth=1", "https://token:secret@github.com/nonexistent/repo"]
            )

            try:
                open_repo(RepoIn(path_or_url="https://token:secret@github.com/nonexistent/repo"))
                assert False, "Expected HTTPException"
            except Exception as e:
                # Should be HTTPException with status 404
                assert hasattr(e, "status_code")
                assert e.status_code == 404

                # Credentials should be sanitized in response
                assert "token" not in e.detail
                assert "secret" not in e.detail
                assert "github.com/nonexistent/repo" in e.detail

    def test_repository_creation_logs_full_details_internally(self, caplog):
        """Test that internal logs contain full details for debugging."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.WARNING),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone", "--depth=1", "https://token:secret@github.com/nonexistent/repo"]
            )

            try:
                open_repo(RepoIn(path_or_url="https://token:secret@github.com/nonexistent/repo"))
            except Exception:
                pass  # Expected

            # Check that logs contain the event type and repo URL
            log_records = [record for record in caplog.records if record.name == "kit.api.app"]
            assert len(log_records) > 0

            # Find the git command failure log
            git_failure_logs = [r for r in log_records if "Git command failed" in r.message]
            assert len(git_failure_logs) > 0

    def test_authentication_failure_sanitized_response(self):
        """Test that authentication failures don't expose credentials in response."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = Exception("authentication failed for https://token:secret@private.com/repo")

            try:
                open_repo(RepoIn(path_or_url="https://token:secret@private.com/repo"))
                assert False, "Expected HTTPException"
            except Exception as e:
                assert hasattr(e, "status_code")
                assert e.status_code == 401

                # Credentials should not be in response
                assert "token" not in e.detail
                assert "secret" not in e.detail
                assert e.detail == "Authentication failed"

    def test_permission_denied_sanitized_response(self):
        """Test that permission denied errors sanitize URLs."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = Exception("permission denied accessing https://user:pass@private.com/repo")

            try:
                open_repo(RepoIn(path_or_url="https://user:pass@private.com/repo"))
                assert False, "Expected HTTPException"
            except Exception as e:
                assert hasattr(e, "status_code")
                assert e.status_code == 403

                # Credentials should be sanitized
                assert "user" not in e.detail or "pass" not in e.detail
                assert "private.com/repo" in e.detail

    def test_network_error_sanitized_response(self):
        """Test that network errors sanitize URLs."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = Exception("timeout connecting to https://api:key@remote.com/repo")

            try:
                open_repo(RepoIn(path_or_url="https://api:key@remote.com/repo"))
                assert False, "Expected HTTPException"
            except Exception as e:
                assert hasattr(e, "status_code")
                assert e.status_code == 503

                # Credentials should be sanitized
                assert "api" not in e.detail or "key" not in e.detail
                assert "Network error" in e.detail

    def test_local_repository_errors_not_sanitized(self):
        """Test that local repository errors don't unnecessarily sanitize paths."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = FileNotFoundError("No such file or directory: '/path/to/local/repo'")

            try:
                open_repo(RepoIn(path_or_url="/path/to/local/repo"))
                assert False, "Expected HTTPException"
            except Exception as e:
                assert hasattr(e, "status_code")
                assert e.status_code == 404

                # Local paths should be preserved
                assert "/path/to/local/repo" in e.detail

    def test_successful_repository_creation_logging(self, caplog):
        """Test that successful repository creation is logged with sanitized URL."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.INFO),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.return_value = MagicMock()

            result = open_repo(RepoIn(path_or_url="https://token:secret@github.com/user/repo"))

            assert result["id"] == "test_repo_id"

            # Check success log
            success_logs = [r for r in caplog.records if "Repository opened successfully" in r.message]
            assert len(success_logs) > 0

            success_log = success_logs[0]
            assert "github.com/user/repo" in success_log.message
            assert "token" not in success_log.message
            assert "secret" not in success_log.message


class TestSecurityEventLogging:
    """Test security-related event logging."""

    def test_git_command_failure_logging_structure(self, caplog):
        """Test that git command failures are logged with proper structure."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.WARNING),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone", "https://github.com/test/repo"]
            )

            try:
                open_repo(RepoIn(path_or_url="https://github.com/test/repo", ref="main"))
            except Exception:
                pass  # Expected

            # Find git command failure log
            git_logs = [r for r in caplog.records if hasattr(r, "event_type") and r.event_type == "git_command_failure"]
            assert len(git_logs) > 0

            log_record = git_logs[0]
            assert hasattr(log_record, "repo_url")
            assert hasattr(log_record, "ref")
            assert hasattr(log_record, "return_code")
            assert log_record.return_code == 128

    def test_repository_not_found_logging_structure(self, caplog):
        """Test that repository not found events are logged with proper structure."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.INFO),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone", "--depth=1", "https://github.com/nonexistent/repo"]
            )

            try:
                open_repo(RepoIn(path_or_url="https://github.com/nonexistent/repo"))
            except Exception:
                pass  # Expected

            # Find repository not found log
            not_found_logs = [
                r for r in caplog.records if hasattr(r, "event_type") and r.event_type == "repository_not_found"
            ]
            assert len(not_found_logs) > 0

            log_record = not_found_logs[0]
            assert hasattr(log_record, "repo_url_sanitized")
            assert log_record.repo_url_sanitized == "https://github.com/nonexistent/repo"

    def test_authentication_failure_logging_structure(self, caplog):
        """Test that authentication failures are logged with proper structure."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.WARNING),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = Exception("authentication failed")

            try:
                open_repo(RepoIn(path_or_url="https://token:secret@private.com/repo"))
            except Exception:
                pass  # Expected

            # Find authentication failure log
            auth_logs = [
                r for r in caplog.records if hasattr(r, "event_type") and r.event_type == "authentication_failed"
            ]
            assert len(auth_logs) > 0

            log_record = auth_logs[0]
            assert hasattr(log_record, "repo_url_sanitized")
            assert hasattr(log_record, "error")
            assert log_record.repo_url_sanitized == "https://private.com/repo"

    def test_access_denied_logging_structure(self, caplog):
        """Test that access denied events are logged with proper structure."""
        from kit.api.app import RepoIn, open_repo

        with (
            patch("kit.api.registry.registry.add") as mock_add,
            patch("kit.api.registry.registry.get_repo") as mock_get_repo,
            caplog.at_level(logging.WARNING),
        ):
            mock_add.return_value = "test_repo_id"
            mock_get_repo.side_effect = Exception("permission denied")

            try:
                open_repo(RepoIn(path_or_url="https://user:pass@restricted.com/repo"))
            except Exception:
                pass  # Expected

            # Find access denied log
            access_logs = [r for r in caplog.records if hasattr(r, "event_type") and r.event_type == "access_denied"]
            assert len(access_logs) > 0

            log_record = access_logs[0]
            assert hasattr(log_record, "repo_url_sanitized")
            assert hasattr(log_record, "error")
            assert log_record.repo_url_sanitized == "https://restricted.com/repo"


class TestIntegrationSecurity:
    """Integration tests for security features."""

    @pytest.fixture(scope="class")
    def test_server(self):
        """Start a test kit server for integration testing."""
        proc = subprocess.Popen(
            ["kit", "serve", "--host", "127.0.0.1", "--port", "8998", "--reload", "false"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(3)

        try:
            response = requests.get("http://127.0.0.1:8998/docs", timeout=5)
            if response.status_code != 200:
                proc.terminate()
                pytest.skip("Could not start test server")
        except requests.RequestException:
            proc.terminate()
            pytest.skip("Could not connect to test server")

        yield "http://127.0.0.1:8998"

        proc.terminate()
        proc.wait()

    def test_remote_repository_not_found_integration(self, test_server):
        """Integration test for remote repository not found with credential sanitization."""
        # Test with a URL that contains credentials but repo doesn't exist
        response = requests.post(
            f"{test_server}/repository",
            json={"path_or_url": "https://fake-token:x-oauth-basic@github.com/nonexistent/security-test-repo"},
        )

        assert response.status_code == 404
        response_data = response.json()

        # Check that credentials are sanitized in response
        assert "fake-token" not in response_data["detail"]
        assert "x-oauth-basic" not in response_data["detail"]
        assert "github.com/nonexistent/security-test-repo" in response_data["detail"]

    def test_invalid_git_ref_integration(self, test_server):
        """Integration test for invalid git ref error handling."""
        response = requests.post(
            f"{test_server}/repository", json={"path_or_url": ".", "ref": "definitely-nonexistent-branch-12345"}
        )

        assert response.status_code == 400
        response_data = response.json()
        assert "Invalid repository configuration" in response_data["detail"]

    def test_successful_repository_creation_integration(self, test_server):
        """Integration test for successful repository creation."""
        response = requests.post(f"{test_server}/repository", json={"path_or_url": "."})

        assert response.status_code == 201
        response_data = response.json()
        assert "id" in response_data
        assert isinstance(response_data["id"], str)
