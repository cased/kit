"""Utility helpers for exposing kit's MCP tool schema to LLM runtimes.

This module lets you grab the same JSON-Schema objects that the MCP server
would advertise, without having to spin up a server.  Pass the list directly
as the `tools` / `functions` parameter to OpenAI, Anthropic, etc.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Avoid importing heavy MCP dependencies at module-import time to prevent
# unnecessary ImportError for users who never need the helper.  Everything is
# imported lazily inside the function.

__all__ = ["get_tool_schemas"]


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return the JSON-serialisable schema for every kit tool.

    Example
    -------
    >>> from kit.tool_schemas import get_tool_schemas
    >>> openai_client.chat.completions.create(
    ...     model="gpt-4o",
    ...     tools=get_tool_schemas(),
    ...     messages=[...],
    ... )
    """
    # Late imports to avoid circular dependencies *and* to keep MCP optional
    try:
        from mcp.types import Tool  # type: ignore

        from kit.mcp.server import KitServerLogic  # type: ignore
    except ImportError as e:  # pragma: no cover – pack not installed
        raise ImportError(
            "`get_tool_schemas()` requires the optional `mcp` package. \n"
            "Install it via `pip install mcp-spec` or `pip install cased-kit[mcp]`."
        ) from e

    logic = KitServerLogic()
    tools: List[Tool] = logic.list_tools()
    # `model_dump` is a Pydantic method (v2) that returns plain dicts ready for JSON
    return [tool.model_dump(mode="json") for tool in tools]
