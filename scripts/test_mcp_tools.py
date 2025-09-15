#!/usr/bin/env python
"""
Manual test script for kit-dev-mcp functionality.
Tests all major features including Context7 integration.

Usage:
    python scripts/test_mcp_tools.py
"""

from pathlib import Path

from kit.mcp.dev_server import LocalDevServerLogic


def test_repository_management(server):
    """Test repository opening and file tree."""
    print("\n📁 Testing Repository Management...")

    repo_path = str(Path.cwd())
    repo_id = server.open_repository(repo_path)
    print(f"  ✓ Opened repository: {repo_id}")

    tree = server.get_file_tree(repo_id)
    print(f"  ✓ File tree contains {len(tree)} items")

    return repo_id


def test_symbol_extraction(server, repo_id):
    """Test extracting symbols from Python files."""
    print("\n🔍 Testing Symbol Extraction...")

    symbols = server.extract_symbols(repo_id, "src/kit/mcp/dev_server.py")
    print(f"  ✓ Extracted {len(symbols)} symbols")

    if symbols:
        classes = [s for s in symbols if s["type"] == "class"]
        functions = [s for s in symbols if s["type"] == "function"]
        print(f"  ✓ Found {len(classes)} classes, {len(functions)} functions")


def test_code_search(server, repo_id):
    """Test different search capabilities."""
    print("\n🔎 Testing Code Search...")

    # Regular text search
    results = server.search_code(repo_id, "Context7")
    print(f"  ✓ Text search found {len(results)} matches for 'Context7'")

    # Grep with pattern
    grep_results = server.grep_code(repo_id, "def.*async")
    print(f"  ✓ Grep found {len(grep_results)} async function definitions")


def test_ast_search(server, repo_id):
    """Test AST-based pattern matching."""
    print("\n🌳 Testing AST Search...")

    # Find async functions
    async_funcs = server.grep_ast(repo_id, "async def", mode="simple")
    print(f"  ✓ Found {len(async_funcs)} async functions")

    # Find try blocks
    try_blocks = server.grep_ast(repo_id, '{"type": "try_statement"}', mode="pattern")
    print(f"  ✓ Found {len(try_blocks)} try blocks")

    # Find class definitions
    classes = server.grep_ast(repo_id, "class", mode="simple")
    print(f"  ✓ Found {len(classes)} class definitions")


def test_context7_research(server):
    """Test Context7 documentation research."""
    print("\n📚 Testing Context7 Documentation Research...")

    # Test with a popular package
    result = server.deep_research_package("requests", query="authentication")

    print(f"  ✓ Researched package: {result['package']}")
    print(f"  ✓ Execution time: {result['execution_time']:.2f}s")

    if isinstance(result["documentation"], dict):
        if "context7_status" in result["documentation"]:
            status = result["documentation"]["context7_status"]
            print(f"  ✓ Context7 status: {status}")

            if status == "success":
                sources = result["documentation"].get("context7_sources", 0)
                print(f"  ✓ Aggregated {sources} documentation sources")

        if "combined_documentation" in result["documentation"]:
            confidence = result["documentation"]["combined_documentation"].get("confidence", "unknown")
            print(f"  ✓ Documentation confidence: {confidence}")
    else:
        print("  ✓ LLM-generated documentation received")


def test_smart_context(server, repo_id):
    """Test smart context building for tasks."""
    print("\n🧠 Testing Smart Context Building...")

    context = server.build_smart_context(
        repo_id,
        "Add rate limiting to the MCP server",
        include_tests=True,
        include_docs=True,
        include_dependencies=True,
        max_files=5,
    )

    print("  ✓ Built context for task")
    print(f"  ✓ Found {len(context.get('relevant_files', []))} relevant files")
    print(f"  ✓ Found {len(context.get('test_files', []))} test files")

    if context.get("suggestions"):
        print(f"  ✓ Generated {len(context['suggestions'])} suggestions")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Kit-Dev-MCP Manual Test Suite")
    print("=" * 60)

    # Initialize server
    server = LocalDevServerLogic()

    try:
        # Run tests
        repo_id = test_repository_management(server)
        test_symbol_extraction(server, repo_id)
        test_code_search(server, repo_id)
        test_ast_search(server, repo_id)
        test_context7_research(server)
        test_smart_context(server, repo_id)

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
