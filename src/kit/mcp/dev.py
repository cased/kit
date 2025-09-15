#!/usr/bin/env python3
"""Entry point for the kit-dev-mcp server.

This MCP server provides enhanced code intelligence and documentation research:
- Real-time file watching and change detection
- Deep research documentation for any package
- Smart context building from multiple sources
- Semantic code search with AI embeddings
- Git integration with AI-powered diff reviews
- Production-grade repository analysis

To use with Claude Desktop, add to your config:

{
  "mcpServers": {
    "kit-dev-mcp": {
      "command": "python",
      "args": ["-m", "kit.mcp.dev"]
    }
  }
}
"""

import argparse
import asyncio
import sys

from .. import __version__
from .dev_server import serve


def main():
    """Main entry point for the kit-dev-mcp server."""
    parser = argparse.ArgumentParser(
        prog="kit-dev-mcp",
        description="Enhanced MCP server for AI-powered development with Kit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"kit-dev-mcp {__version__}",
    )

    # Parse arguments (this handles --version automatically)
    parser.parse_args()

    # If we get here, start the server
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nShutting down kit-dev-mcp server...", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
