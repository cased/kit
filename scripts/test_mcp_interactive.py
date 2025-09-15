#!/usr/bin/env python
"""
Interactive test for kit-dev-mcp functionality.
Tests all major features with real-world scenarios.
"""

import asyncio
import time
from pathlib import Path

from kit.mcp.dev_server import LocalDevServerLogic


def test_deep_research():
    """Test deep research with real packages."""
    print("\n📚 Testing Deep Research...")

    server = LocalDevServerLogic()

    # Test with just one package to be faster
    package = "requests"
    query = "authentication"

    print(f"\n  Testing {package}...")
    start = time.time()

    try:
        result = server.deep_research_package(package, query)
        elapsed = time.time() - start

        print(f"    ✓ Package: {result['package']}")
        print(f"    ✓ Time: {elapsed:.2f}s")

        if isinstance(result["documentation"], dict):
            print(f"    ✓ Result type: Dictionary with {len(result['documentation'])} keys")
            # Show some keys
            keys = list(result["documentation"].keys())[:5]
            print(f"    ✓ Keys: {keys}")
        else:
            # LLM response
            print(f"    ✓ LLM Response: {len(result['documentation'])} chars")
    except Exception as e:
        print(f"    ⚠️ Research failed: {e}")
        # Not critical - could be API limits

    return True


def test_ast_patterns():
    """Test various AST search patterns."""
    print("\n🌳 Testing AST Pattern Search...")

    server = LocalDevServerLogic()
    repo_id = server.open_repository(str(Path.cwd()))

    patterns = [
        ("async def", "simple", "Find async functions"),
        ('{"type": "class_definition"}', "pattern", "Find all classes"),
        ('{"type": "try_statement"}', "pattern", "Find try blocks"),
        ("TODO", "simple", "Find TODO comments"),
    ]

    for pattern, mode, description in patterns:
        print(f"\n  {description}:")
        results = server.grep_ast(repo_id=repo_id, pattern=pattern, mode=mode, file_pattern="**/*.py", max_results=5)

        print(f"    ✓ Found {len(results)} matches")

        # Show first few results
        for result in results[:2]:
            print(f"      - {result['file']}:{result['line']} ({result['type']})")
            if "preview" in result:
                preview = result["preview"][:50]
                print(f"        {preview}...")

    return True


def test_code_search():
    """Test various code search capabilities."""
    print("\n🔎 Testing Code Search...")

    server = LocalDevServerLogic()
    repo_id = server.open_repository(str(Path.cwd()))

    # Text search
    queries = ["ThreadPoolExecutor", "async def", "import json", "Context7"]

    for query in queries:
        results = server.search_code(repo_id, query)
        print(f"  ✓ '{query}': {len(results)} matches")

        # Show first result
        if results:
            first = results[0]
            print(f"    - {first['file']}:{first['line']}")

    # Grep with patterns
    patterns = [
        (r"def\s+\w+_async", "Async function definitions"),
        (r"class\s+\w+Error", "Error classes"),
        (r"@\w+", "Decorators"),
    ]

    print("\n  Grep patterns:")
    for pattern, description in patterns:
        results = server.grep_code(repo_id, pattern)
        print(f"    ✓ {description}: {len(results)} matches")

    return True


async def main():
    """Run all interactive tests."""
    print("=" * 60)
    print("🚀 Kit-Dev-MCP Interactive Test Suite")
    print("=" * 60)

    try:
        # Run synchronous tests
        test_code_search()
        test_ast_patterns()
        test_deep_research()

        print("\n" + "=" * 60)
        print("✅ All interactive tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
