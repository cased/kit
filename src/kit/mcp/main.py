"""Console-script entry point for the Kit MCP server."""

from __future__ import annotations

import asyncio
import logging
import sys

from .server import serve


def main() -> None:
    """Launch the Kit MCP server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:  # pragma: no cover
        logging.error(f"Server error: {e!s}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
