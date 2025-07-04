"""Provides local git diff information for PR review analysis."""

import shlex
import subprocess
from typing import Dict, List


class LocalDiffProvider:
    """Provides local git diff information."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _validate_diff_spec(self, diff_spec: str):
        """Validate the diff spec to prevent command injection."""
        if not diff_spec or not diff_spec.strip():
            raise ValueError("diff_spec cannot be empty.")

        # Use shlex to break down the spec. We expect 1 or 2 parts.
        parts = shlex.split(diff_spec)
        if not 1 <= len(parts) <= 2:
            raise ValueError("Invalid diff_spec format.")

        for part in parts:
            if part.startswith("-"):
                raise ValueError(f"Invalid diff_spec part '{part}': cannot start with '-'.")

            # Disallow shell metacharacters
            metachars = ";|&<>()$`\\"
            if any(char in part for char in metachars):
                raise ValueError(f"Invalid characters in diff_spec. Found one of {metachars}")

            # Prevent path traversal
            if "../" in part or "/.." in part:
                raise ValueError("Invalid diff_spec: path traversal is not allowed.")

    def get_diff(self, diff_spec: str) -> str:
        """Get the diff for a given specification."""
        self._validate_diff_spec(diff_spec)
        try:
            result = subprocess.run(
                ["git", "diff", diff_spec], cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git diff for '{diff_spec}': {e.stderr or str(e)}")

    def get_changed_files(self, diff_spec: str) -> List[str]:
        """Get the list of changed files for a given diff specification."""
        self._validate_diff_spec(diff_spec)
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", diff_spec],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get changed files for '{diff_spec}': {e.stderr or str(e)}")

    def get_mock_pr_details(self, diff_spec: str) -> Dict:
        """Get mock PR details for a local diff."""
        self._validate_diff_spec(diff_spec)
        try:
            # The --oneline format is a standard and generally reliable way to get a commit summary.
            # While it might not handle all edge cases of unusual commit messages perfectly,
            # it's a good heuristic for generating a title for a mock PR review.
            # Using a more structured format like %H would give us only the hash, which is less descriptive.
            log_result = subprocess.run(
                ["git", "log", "--oneline", diff_spec], cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            commits = log_result.stdout.strip().split("\n") if log_result.stdout.strip() else []

            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branch_result.stdout.strip()

            if ".." in diff_spec:
                base_ref, head_ref = diff_spec.split("..", 1)
            else:
                base_ref = f"{diff_spec}~1"
                head_ref = diff_spec
        except subprocess.CalledProcessError:
            commits = []
            base_ref, head_ref = "base", "head"

        if commits:
            title = commits[0] if len(commits) == 1 else f"Changes in {diff_spec} ({len(commits)} commits)"
        else:
            title = f"Local changes: {diff_spec}"

        return {
            "title": title,
            "user": {"login": "local-user"},
            "base": {"ref": base_ref},
            "head": {"ref": head_ref, "sha": head_ref},
            "number": 0,
        }

    def get_mock_files(self, diff_spec: str, changed_files: List[str]) -> List[Dict]:
        """Get mock file objects for a local diff."""
        self._validate_diff_spec(diff_spec)
        mock_files = []
        for filename in changed_files:
            try:
                stats_result = subprocess.run(
                    ["git", "diff", "--numstat", diff_spec, "--", filename],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if stats_result.stdout.strip():
                    parts = stats_result.stdout.strip().split("\t")
                    additions = int(parts[0]) if parts[0] != "-" else 0
                    deletions = int(parts[1]) if parts[1] != "-" else 0
                else:
                    additions, deletions = 0, 0
            except (subprocess.CalledProcessError, ValueError, IndexError):
                additions, deletions = 0, 0

            mock_files.append(
                {
                    "filename": filename,
                    "status": "modified",
                    "additions": additions,
                    "deletions": deletions,
                    "changes": additions + deletions,
                }
            )
        return mock_files
