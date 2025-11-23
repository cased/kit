from __future__ import annotations

import logging
import os
import re
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
        """Load all .gitignore files in repository tree and merge them.

        Returns a PathSpec that respects all .gitignore files, with proper
        precedence (deeper paths override shallower ones).
        """
        gitignore_files = []

        # Collect all .gitignore files
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            # Skip .git directory
            if ".git" in Path(dirpath).parts:
                continue

            if ".gitignore" in filenames:
                gitignore_path = Path(dirpath) / ".gitignore"
                gitignore_files.append(gitignore_path)

        if not gitignore_files:
            return None

        # Sort by depth (deepest first) for correct precedence
        gitignore_files.sort(key=lambda p: len(p.parts), reverse=True)

        # Collect all patterns with proper path prefixes
        all_patterns = []
        for gitignore_path in gitignore_files:
            gitignore_dir = gitignore_path.parent

            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    patterns = f.readlines()

                # Calculate relative base path from repo root
                try:
                    rel_base = gitignore_dir.relative_to(self.repo_path)
                except ValueError:
                    # gitignore outside repo (shouldn't happen, but be safe)
                    continue

                # Process each pattern
                for pattern in patterns:
                    pattern = pattern.strip()

                    # Skip empty lines and comments
                    if not pattern or pattern.startswith("#"):
                        continue

                    # Adjust pattern to be relative to repo root
                    if str(rel_base) != ".":
                        # Pattern is in subdirectory - prefix with path
                        if pattern.startswith("/"):
                            # Absolute pattern (from gitignore dir) - make relative to repo
                            adjusted = f"{rel_base}/{pattern[1:]}"
                        else:
                            # Relative pattern - prefix with directory path
                            adjusted = f"{rel_base}/{pattern}"
                    else:
                        # Pattern is in root .gitignore - use as-is
                        adjusted = pattern

                    all_patterns.append(adjusted)

            except Exception as e:
                # Log warning but continue processing other .gitignore files
                logging.warning(f"Could not load {gitignore_path}: {e}")
                continue

        if not all_patterns:
            return None

        # Create single merged pathspec
        return pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)

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

    def search_text(
        self, query: str, file_pattern: str = "*.py", options: Optional[SearchOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for a text pattern (regex) in files matching file_pattern.

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
        matches: List[Dict[str, Any]] = []
        current_options = options or SearchOptions()  # Use defaults if none provided

        regex_flags = 0 if current_options.case_sensitive else re.IGNORECASE
        regex = re.compile(query, regex_flags)

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
                        start_context_before = max(0, i - current_options.context_lines_before)
                        context_before = [l.rstrip("\n") for l in lines[start_context_before:i]]

                        # Context after should not include the matching line itself
                        start_context_after = i + 1
                        end_context_after = start_context_after + current_options.context_lines_after
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
