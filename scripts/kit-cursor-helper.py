#!/usr/bin/env python3
"""
Helper script to use kit-dev-mcp tools from Cursor.
Run this from the Cursor terminal to interact with kit tools.

Usage:
    python kit-cursor-helper.py open /path/to/repo
    python kit-cursor-helper.py search "async def"
    python kit-cursor-helper.py grep-ast "try_statement"
    python kit-cursor-helper.py research fastapi
"""

import asyncio
import json
import sys
from pathlib import Path

# Add kit to path
sys.path.insert(0, str(Path(__file__).parent))

import os

from kit.mcp.dev_server import LocalDevServerLogic


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    logic = LocalDevServerLogic()

    try:
        if command == "open":
            if len(sys.argv) < 3:
                print("Usage: python kit-cursor-helper.py open /path/to/repo")
                sys.exit(1)

            result = await logic.open_repository({"path": sys.argv[2]})
            print(f"✅ Opened repository: {result['repo_id']}")
            print(f"   Path: {result['path']}")
            print(f"   Files: {result.get('file_count', 'N/A')}")

        elif command == "search":
            if len(sys.argv) < 3:
                print("Usage: python kit-cursor-helper.py search 'pattern'")
                sys.exit(1)

            # Get the most recent repo
            repos = list(logic.repositories.keys())
            if not repos:
                print("❌ No repository open. Run 'open' first.")
                sys.exit(1)

            repo_id = repos[-1]
            result = await logic.search_code({"repo_id": repo_id, "pattern": sys.argv[2], "max_results": 10})

            print(f"🔍 Search results for '{sys.argv[2]}':")
            for match in result.get("matches", [])[:10]:
                print(f"   {match['file']}:{match['line']}: {match['text'][:80]}")

        elif command == "grep-ast":
            if len(sys.argv) < 3:
                print("Usage: python kit-cursor-helper.py grep-ast 'ast_pattern'")
                sys.exit(1)

            repos = list(logic.repositories.keys())
            if not repos:
                print("❌ No repository open. Run 'open' first.")
                sys.exit(1)

            repo_id = repos[-1]
            result = await logic.grep_ast({"repo_id": repo_id, "pattern": sys.argv[2]})

            print(f"🌳 AST search results for '{sys.argv[2]}':")
            for match in result.get("matches", [])[:10]:
                print(f"   {match['file']}:{match.get('line', '?')}: {match.get('text', 'N/A')[:80]}")

        elif command == "research":
            if len(sys.argv) < 3:
                print("Usage: python kit-cursor-helper.py research package_name")
                sys.exit(1)

            print(f"📚 Researching {sys.argv[2]}...")

            # Check for API key
            if not os.environ.get("OPENAI_API_KEY"):
                print("❌ OPENAI_API_KEY not set. Set it to use research features.")
                sys.exit(1)

            result = await logic.deep_research_package({"package_name": sys.argv[2]})

            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"\n📖 Documentation for {sys.argv[2]}:")
                print(f"\nOverview: {result.get('overview', 'N/A')[:500]}...")
                print(f"\nInstallation: {result.get('installation', 'N/A')}")
                print(f"\nKey Features: {json.dumps(result.get('key_features', []), indent=2)}")

        elif command == "tree":
            repos = list(logic.repositories.keys())
            if not repos:
                print("❌ No repository open. Run 'open' first.")
                sys.exit(1)

            repo_id = repos[-1]
            result = await logic.get_file_tree({"repo_id": repo_id, "max_depth": 3})

            print("📁 Repository structure:")
            for item in result.get("tree", [])[:50]:
                indent = "  " * (item["path"].count("/") - 1)
                icon = "📁" if item["type"] == "directory" else "📄"
                print(f"{indent}{icon} {Path(item['path']).name}")

        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
