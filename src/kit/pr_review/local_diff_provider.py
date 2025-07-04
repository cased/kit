"""Provides local git diff information for PR review analysis."""

import subprocess
from typing import Dict, List


class LocalDiffProvider:
    """Provides local git diff information."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def get_diff(self, diff_spec: str) -> str:
        """Get the diff for a given specification."""
        try:
            result = subprocess.run(
                ["git", "diff", diff_spec], cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git diff for '{diff_spec}': {e.stderr or str(e)}")

    def get_changed_files(self, diff_spec: str) -> List[str]:
        """Get the list of changed files for a given diff specification."""
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
        try:
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
            current_branch = branch_result.stdout.strip()
            
            if ".." in diff_spec:
                base_ref, head_ref = diff_spec.split("..", 1)
            else:
                base_ref = f"{diff_spec}~1"
                head_ref = diff_spec
        except subprocess.CalledProcessError:
            commits = []
            current_branch = "unknown"
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