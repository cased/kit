"""Utilities to assemble rich prompts for LLMs.

This is intentionally lightweight – it glues together repository data
(diff, file bodies, search hits, etc.) into a single string that can be
fed straight into a chat completion.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

if TYPE_CHECKING:
    from .repository import Repository


class ContextAssembler:
    """Collects pieces of context and spits out a prompt blob.

    Parameters
    ----------
    repo
        A :class:`kit.repository.Repository` object representing the codebase
        we want to reason about. The assembler uses it to fetch file content
        and (in the future) symbol relationships.
    title
        Optional global title prepended to the context (not used by default).
    """

    def __init__(self, repo: Repository, *, title: Optional[str] = None) -> None:
        self.repo = repo
        self._sections: List[str] = []
        if title:
            self._sections.append(f"# {title}\n")

    def add_diff(self, diff: str) -> None:
        """Add a raw git diff section."""
        if not diff.strip():
            return
        self._sections.append("## Diff\n```diff\n" + diff.strip() + "\n```")

    def add_file(
        self,
        file_path: str,
        *,
        highlight_changes: bool = False,
        max_lines: int | None = None,
        max_bytes: int | None = None,
        skip_if_name_in: Optional[Sequence[str]] = None,
    ) -> None:
        """Embed full file content.

        If *highlight_changes* is true we still just inline raw content –
        markup is left to the caller/LLM.
        """
        # Guard: skip by exact filename
        if skip_if_name_in and Path(file_path).name in skip_if_name_in:
            return

        try:
            code = self.repo.get_file_content(file_path)
        except FileNotFoundError:
            return

        # Guards: size limits
        if max_bytes is not None and len(code.encode("utf-8", "ignore")) > max_bytes:
            return
        if max_lines is not None and code.count("\n") + 1 > max_lines:
            return

        lang = Path(file_path).suffix.lstrip(".") or "text"
        header = f"## {file_path} (full)" if not highlight_changes else f"## {file_path} (with changes highlighted)"
        self._sections.append(f"{header}\n```{lang}\n{code}\n```")

    def add_search_results(self, results: Sequence[Dict[str, Any]], *, query: str) -> None:
        """Append semantic search matches to the context."""
        if not results:
            return
        blob = [f"## Semantic search for: {query}"]
        for i, res in enumerate(results, 1):
            code = res.get("code") or res.get("snippet") or ""
            file = res.get("file", f"result_{i}")
            blob.append(f"### {file}\n```\n{code}\n```")
        self._sections.append("\n".join(blob))

    def format_context(self) -> str:
        """Return the accumulated context."""
        return "\n\n".join(self._sections)
