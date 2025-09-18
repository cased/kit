#!/usr/bin/env python
"""Real-world tests for Package Search integration.

Usage:
    python scripts/test_package_search_real.py [API_KEY]

If API_KEY is not provided, will use CHROMA_PACKAGE_SEARCH_API_KEY or CHROMA_API_KEY env vars.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from kit.package_search import ChromaPackageSearch


def setup_api_key(api_key: Optional[str] = None):
    """Setup API key from arg, env var, or fail."""
    if api_key:
        os.environ["CHROMA_PACKAGE_SEARCH_API_KEY"] = api_key
    elif not os.environ.get("CHROMA_PACKAGE_SEARCH_API_KEY"):
        if os.environ.get("CHROMA_API_KEY"):
            os.environ["CHROMA_PACKAGE_SEARCH_API_KEY"] = os.environ["CHROMA_API_KEY"]
        else:
            print("❌ Error: No API key provided")
            print("   Provide via argument: python test_package_search_real.py YOUR_KEY")
            print("   Or set environment variable: export CHROMA_PACKAGE_SEARCH_API_KEY=YOUR_KEY")
            sys.exit(1)


def test_cli_commands():
    """Test CLI commands directly."""
    print("\n" + "=" * 60)
    print("CLI COMMAND TESTS")
    print("=" * 60)

    tests = [
        {
            "name": "Grep search",
            "cmd": "kit package-search-grep requests 'class HTTPAdapter' --json",
        },
        {
            "name": "Hybrid search",
            "cmd": "kit package-search-hybrid requests 'connection pooling' --json",
        },
        {
            "name": "Read file",
            "cmd": "kit package-search-read requests 'src/requests/__init__.py' --start 1 --end 10",
        },
    ]

    for test in tests:
        print(f"\n📝 {test['name']}")
        print(f"   Command: {test['cmd']}")

        result = os.popen(test["cmd"]).read()

        if result.strip():
            if test["name"] == "Read file":
                lines = result.split("\n")
                print(f"   ✅ Read {len(lines)} lines")
            else:
                try:
                    data = json.loads(result)
                    print(f"   ✅ Got {len(data)} results")
                except:  # noqa: E722
                    print(f"   ✅ Got response: {result[:100]}...")
        else:
            print("   ⚠️ No results")


def test_python_client():
    """Test Python client directly."""
    print("\n" + "=" * 60)
    print("PYTHON CLIENT TESTS")
    print("=" * 60)

    try:
        client = ChromaPackageSearch()
    except ValueError as e:
        print(f"❌ Failed to create client: {e}")
        return

    # Test 1: Grep
    print("\n📝 Testing grep...")
    try:
        start = time.time()
        results = client.grep(package="requests", pattern="def get", max_results=5)
        elapsed = time.time() - start

        print(f"   ✅ Found {len(results)} results in {elapsed:.2f}s")
        if results:
            r = results[0]
            print(f"   First: {r.get('file_path')}:{r.get('line_number')}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Hybrid search
    print("\n📝 Testing hybrid search...")
    try:
        start = time.time()
        results = client.hybrid_search(package="requests", query="session management", max_results=5)
        elapsed = time.time() - start

        print(f"   ✅ Found {len(results)} results in {elapsed:.2f}s")
        if results:
            r = results[0]
            print(f"   First: {r.get('file_path')}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Read file
    print("\n📝 Testing read file...")
    try:
        start = time.time()
        content = client.read_file(
            package="requests", file_path="src/requests/__version__.py", start_line=1, end_line=5
        )
        elapsed = time.time() - start

        lines = content.split("\n") if content else []
        print(f"   ✅ Read {len(lines)} lines in {elapsed:.2f}s")
        if content:
            print(f"   Preview: {content[:60]}...")

    except Exception as e:
        print(f"   ❌ Error: {e}")


async def test_mcp_server():
    """Test MCP server integration."""
    print("\n" + "=" * 60)
    print("MCP SERVER TESTS")
    print("=" * 60)

    server_params = StdioServerParameters(command="python", args=["-m", "kit.mcp.dev_server"], env=dict(os.environ))

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List tools
                tools = await session.list_tools()
                package_tools = [t for t in tools.tools if "package_search" in t.name]
                print(f"\n✅ Found {len(package_tools)} package search tools")

                # Test grep
                print("\n📝 Testing MCP grep...")
                try:
                    result = await session.call_tool(
                        "package_search_grep", arguments={"package": "numpy", "pattern": "def array", "max_results": 3}
                    )

                    if result.content:
                        content = json.loads(result.content[0].text)
                        results = content.get("results", [])
                        print(f"   ✅ Found {len(results)} results")
                    else:
                        print("   ⚠️ No results")

                except Exception as e:
                    print(f"   ❌ Error: {e}")

                # Test deep research
                print("\n📝 Testing deep_research_package with Chroma...")
                try:
                    result = await session.call_tool(
                        "deep_research_package",
                        arguments={
                            "package_name": "requests",
                            "research_goal": "How are HTTP headers handled?",
                            "max_search_depth": 2,
                            "provider": "chroma",
                        },
                    )

                    if result.content:
                        content = result.content[0].text
                        print(f"   ✅ Research completed ({len(content)} chars)")
                    else:
                        print("   ⚠️ No results")

                except Exception as e:
                    print(f"   ❌ Error: {e}")

    except Exception as e:
        print(f"❌ MCP server error: {e}")


def test_performance():
    """Test performance with various loads."""
    print("\n" + "=" * 60)
    print("PERFORMANCE TESTS")
    print("=" * 60)

    try:
        client = ChromaPackageSearch()
    except ValueError as e:
        print(f"❌ Failed to create client: {e}")
        return

    sizes = [10, 50, 100]

    for size in sizes:
        print(f"\n⏱️ Fetching {size} results...")
        try:
            start = time.time()
            results = client.grep(package="numpy", pattern="import", max_results=size)
            elapsed = time.time() - start

            print(f"   ✅ Got {len(results)} results in {elapsed:.2f}s")
            if results:
                print(f"   Speed: {len(results) / elapsed:.1f} results/second")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Brief pause to avoid rate limiting
        time.sleep(0.5)


def main():
    """Run all real-world tests."""
    parser = argparse.ArgumentParser(description="Test Package Search integration")
    parser.add_argument("api_key", nargs="?", help="Chroma API key (optional)")
    parser.add_argument("--skip-cli", action="store_true", help="Skip CLI tests")
    parser.add_argument("--skip-mcp", action="store_true", help="Skip MCP tests")
    parser.add_argument("--skip-perf", action="store_true", help="Skip performance tests")

    args = parser.parse_args()

    # Setup API key
    setup_api_key(args.api_key)

    print("\n" + "=" * 60)
    print("CHROMA PACKAGE SEARCH - REAL WORLD TESTS")
    print("=" * 60)
    print(f"API Key: {'✅ Set' if os.environ.get('CHROMA_PACKAGE_SEARCH_API_KEY') else '❌ Missing'}")

    # Run tests
    if not args.skip_cli:
        test_cli_commands()

    test_python_client()

    if not args.skip_mcp:
        asyncio.run(test_mcp_server())

    if not args.skip_perf:
        test_performance()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
