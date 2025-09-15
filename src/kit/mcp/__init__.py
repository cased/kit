"""kit.mcp – Model Context Protocol server wrapper."""

from __future__ import annotations

from .dev import main as main
from .dev_server import serve as serve

__all__ = ["main", "serve"]
