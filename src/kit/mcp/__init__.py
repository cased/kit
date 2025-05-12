"""kit.mcp – Model Context Protocol server wrapper."""

from __future__ import annotations

from .main import main as main
from .server import serve as serve

__all__ = ["main", "serve"]
