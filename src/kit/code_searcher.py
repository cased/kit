from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pathspec


@dataclass
class SearchOptions:
    """Configuration options for text search."""

    case_sensitive: bool = True
    context_lines_before: int = 0
    context_lines_after: int = 0
    use_gitignore: bool = True


class CodeSearcher:
    """
    Provides text and regex search across the repository.
    Supports multi-language, file patterns, and returns match details.
    """

    def __init__(self, repo_path: str) -> None:
        """
        Initializes the CodeSearcher with the repository path.

        Args:
        repo_path (str): The path to the repository.
        """
        self.repo_path: Path = Path(repo_path)
        self._gitignore_spec = self._load_gitignore()  # Load gitignore spec

    def _load_gitignore(self):
        """Loads .gitignore rules from the repository root."""
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    return pathspec.PathSpec.from_lines("gitwildmatch", f)
            except Exception as e:
                # Log this error if logging is set up, or print
                print(f"Warning: Could not load .gitignore: {e}")
        return None

    def _should_ignore(self, file: Path) -> bool:
        """Checks if a file should be ignored based on .gitignore rules."""
        if not self._gitignore_spec:
            return False

        # Always ignore .git directory contents directly if pathspec doesn't catch it implicitly
        # (though pathspec usually handles .git/ if specified in .gitignore)
        if ".git" in file.parts:
            return True

        try:
            rel_path = str(file.relative_to(self.repo_path))
            return self._gitignore_spec.match_file(rel_path)
        except ValueError:  # file might not be relative to repo_path, e.g. symlink target outside
            return False  # Or decide to ignore such cases explicitly

    def _has_ripgrep(self) -> bool:
        """Check if ripgrep (rg) is available on the system."""
        try:
            subprocess.run(["rg", "--version"], capture_output=True, check=True, timeout=1)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _is_git_repository(self) -> bool:
        """Check if the repo_path is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists()

    def _parse_ripgrep_json_messages(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse ripgrep JSON output into message list."""
        messages = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                messages.append(data)
            except json.JSONDecodeError:
                continue
        return messages

    def _extract_context_for_match(
        self,
        messages: List[Dict[str, Any]],
        match_index: int,
        file_path: str,
        match_line_number: int,
        options: SearchOptions,
    ) -> tuple[List[str], List[str]]:
        """Extract context lines before and after a match from ripgrep messages."""
        context_before: List[str] = []
        j = match_index - 1
        while j >= 0 and len(context_before) < options.context_lines_before:
            prev_msg = messages[j]
            if prev_msg.get("type") == "context":
                prev_data = prev_msg.get("data", {})
                prev_path = prev_data.get("path", {}).get("text", "")
                prev_line_num = prev_data.get("line_number")

                if prev_path == file_path and prev_line_num < match_line_number:
                    prev_text = prev_data.get("lines", {}).get("text", "").rstrip("\n")
                    context_before.insert(0, prev_text)
                else:
                    break
            elif prev_msg.get("type") == "match":
                break
            j -= 1

        context_after: List[str] = []
        j = match_index + 1
        while j < len(messages) and len(context_after) < options.context_lines_after:
            next_msg = messages[j]
            if next_msg.get("type") == "context":
                next_data = next_msg.get("data", {})
                next_path = next_data.get("path", {}).get("text", "")
                next_line_num = next_data.get("line_number")

                if next_path == file_path and next_line_num > match_line_number:
                    next_text = next_data.get("lines", {}).get("text", "").rstrip("\n")
                    context_after.append(next_text)
                else:
                    break
            elif next_msg.get("type") == "match":
                break
            j += 1

        return context_before, context_after

    def _search_with_ripgrep(
        self, query: str, file_pattern: str, options: SearchOptions
    ) -> Optional[List[Dict[str, Any]]]:
        """Search using ripgrep for better performance."""
        # Ripgrep only respects .gitignore in git repositories
        if options.use_gitignore and self._gitignore_spec and not self._is_git_repository():
            return None

        cmd = ["rg", "--json"]
        if not options.case_sensitive:
            cmd.append("-i")

        # Context lines (capped to prevent DoS)
        context_before_count = min(options.context_lines_before, 100)
        context_after_count = min(options.context_lines_after, 100)
        if context_before_count > 0:
            cmd.extend(["-B", str(context_before_count)])
        if context_after_count > 0:
            cmd.extend(["-A", str(context_after_count)])

        if file_pattern not in ("*", "**/*"):
            cmd.extend(["-g", file_pattern])

        if not options.use_gitignore:
            cmd.append("--no-ignore")

        cmd.extend([query, str(self.repo_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
            messages = self._parse_ripgrep_json_messages(result.stdout)

            matches = []
            for i, msg in enumerate(messages):
                if msg.get("type") == "match":
                    match_data = msg.get("data", {})
                    file_path = match_data.get("path", {}).get("text", "")

                    try:
                        rel_path = str(Path(file_path).relative_to(self.repo_path))
                    except ValueError:
                        rel_path = file_path

                    match_line_number = match_data.get("line_number")
                    line_text = match_data.get("lines", {}).get("text", "").rstrip("\n")

                    context_before, context_after = self._extract_context_for_match(
                        messages, i, file_path, match_line_number, options
                    )

                    matches.append(
                        {
                            "file": rel_path,
                            "line_number": match_line_number,
                            "line": line_text,
                            "context_before": context_before,
                            "context_after": context_after,
                        }
                    )

            return matches
        except (subprocess.TimeoutExpired, Exception):
            return None

    def search_text(
        self, query: str, file_pattern: str = "*.py", options: Optional[SearchOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for a text pattern (regex) in files matching file_pattern.

        Uses ripgrep when available for 10x performance, with automatic fallback to Python.

        Args:
            query (str): The text pattern to search for.
            file_pattern (str): The file pattern to search in. Defaults to "*.py".
            options (Optional[SearchOptions]): Search configuration options.

        Returns:
            List[Dict[str, Any]]: A list of matches. Each match includes:
                - "file" (str): Relative path to the file.
                - "line_number" (int): 1-indexed line number of the match.
                - "line" (str): The content of the matching line.
                - "context_before" (List[str]): Lines immediately preceding the match.
                - "context_after" (List[str]): Lines immediately succeeding the match.
        """
        current_options = options or SearchOptions()

        # Try ripgrep first (10x faster)
        if self._has_ripgrep():
            results = self._search_with_ripgrep(query, file_pattern, current_options)
            if results is not None:
                return results

        # Fall back to Python implementation
        matches: List[Dict[str, Any]] = []

        regex_flags = 0 if current_options.case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(query, regex_flags)
        except re.error:
            # Invalid regex pattern, return empty results
            return matches

        # Cap context lines to prevent DoS (same as ripgrep implementation)
        context_before_count = min(current_options.context_lines_before, 100)
        context_after_count = min(current_options.context_lines_after, 100)

        for file in self.repo_path.rglob(file_pattern):
            if current_options.use_gitignore and self._should_ignore(file):
                continue
            if not file.is_file():
                continue
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()  # Read all lines to handle context

                for i, line_content in enumerate(lines):
                    if regex.search(line_content):
                        start_context_before = max(0, i - context_before_count)
                        context_before = [l.rstrip("\n") for l in lines[start_context_before:i]]

                        # Context after should not include the matching line itself
                        start_context_after = i + 1
                        end_context_after = start_context_after + context_after_count
                        context_after = [l.rstrip("\n") for l in lines[start_context_after:end_context_after]]

                        matches.append(
                            {
                                "file": str(file.relative_to(self.repo_path)),
                                "line_number": i + 1,  # 1-indexed
                                "line": line_content.rstrip("\n"),
                                "context_before": context_before,
                                "context_after": context_after,
                            }
                        )
            except Exception as e:
                # Log the exception for debugging purposes
                print(f"Error searching file {file}: {e}")
                continue
        return matches
