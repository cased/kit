"""Shared utility functions for kit."""

from pathlib import Path
from typing import Optional


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def format_size(bytes_size: int) -> str:
    """Format size in human-readable format."""
    size = float(bytes_size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def validate_relative_path(base_path: Path, relative_path: str) -> Path:
    """Validate that relative_path stays within base_path bounds."""
    if not relative_path or relative_path == ".":
        return base_path

    # Security check: prevent '..' traversal that could escape repository bounds
    if ".." in Path(relative_path).parts:
        # Check if '..' traversal would escape the repository
        parts = Path(relative_path).parts
        depth = 0
        for part in parts:
            if part == "..":
                depth -= 1
                if depth < 0:
                    raise ValueError(f"Path '{relative_path}' is outside repository bounds")
            elif part != "." and part:
                depth += 1

    # Return joined path without resolving to maintain compatibility
    return base_path / relative_path


def parse_git_url(url: str) -> Optional[tuple[str, str]]:
    """Parse a git URL to extract owner and repo name."""
    if "github.com" in url:
        # Handle both https and ssh formats
        if url.startswith("git@"):
            # git@github.com:owner/repo.git
            parts = url.split(":")
            if len(parts) >= 2:
                path = parts[1].replace(".git", "")
                if "/" in path:
                    path_parts = path.split("/")
                    if len(path_parts) >= 2:
                        return path_parts[0], path_parts[1]
        elif url.startswith("https://"):
            # https://github.com/owner/repo.git or https://github.com/owner/repo
            parts = url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
    return None


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
