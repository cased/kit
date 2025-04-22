from __future__ import annotations
import re
from pathlib import Path
from typing import Any, List, Dict, Optional

class CodeSearcher:
    """
    Provides robust text and regex search across the repository.
    Supports multi-language, file patterns, and returns match details.
    """
    def __init__(self, repo_path: str) -> None:
        """
        Initializes the CodeSearcher with the repository path.
        
        Args:
        repo_path (str): The path to the repository.
        """
        self.repo_path: Path = Path(repo_path)

    def search_text(self, query: str, file_pattern: str = "*.py") -> List[Dict[str, Any]]:
        """
        Search for a text pattern (regex) in files matching file_pattern.
        Returns a list of matches: {file, line, line_number}.
        
        Args:
        query (str): The text pattern to search for.
        file_pattern (str): The file pattern to search in. Defaults to "*.py".
        
        Returns:
        List[Dict[str, Any]]: A list of matches.
        """
        matches: List[Dict[str, Any]] = []
        regex = re.compile(query)
        for file in self.repo_path.rglob(file_pattern):
            if not file.is_file():
                continue
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({
                                "file": str(file.relative_to(self.repo_path)),
                                "line_number": i,
                                "line": line.rstrip()
                            })
            except Exception as e:
                # Log the exception for debugging purposes
                print(f"Error searching file {file}: {e}")
                continue
        return matches
