#!/usr/bin/env python
"""Benchmark ripgrep and Python implementations for code search."""

import time

from kit.code_searcher import CodeSearcher, SearchOptions


def benchmark_search(searcher, query, file_pattern, options, method="auto"):
    """Benchmark a single search operation.

    Args:
        searcher: CodeSearcher instance
        query: Search query
        file_pattern: File pattern
        options: Search options
        method: "auto", "ripgrep", or "python"
    """
    original_ripgrep = searcher._has_ripgrep

    if method == "ripgrep":
        pass  # Use ripgrep
    elif method == "python":
        searcher._has_ripgrep = lambda: False

    start = time.perf_counter()
    results = searcher.search_text(query, file_pattern=file_pattern, options=options)
    elapsed = time.perf_counter() - start

    searcher._has_ripgrep = original_ripgrep

    return elapsed, len(results)


def main():
    repo_path = "/Users/tnm/kit"
    searcher = CodeSearcher(repo_path)

    # Check availability
    has_rg = searcher._has_ripgrep()
    print(f"Ripgrep available: {has_rg}")
    print(f"Repository: {repo_path}")
    print("=" * 80)

    benchmarks = [
        {
            "name": "Simple search (common term)",
            "query": "def ",
            "pattern": "*.py",
            "options": SearchOptions(),
        },
        {
            "name": "Case-insensitive search",
            "query": "repository",
            "pattern": "*.py",
            "options": SearchOptions(case_sensitive=False),
        },
        {
            "name": "Regex search (function definitions)",
            "query": r"def \w+\(",
            "pattern": "*.py",
            "options": SearchOptions(),
        },
        {
            "name": "Search with context (2 lines each)",
            "query": "class ",
            "pattern": "*.py",
            "options": SearchOptions(context_lines_before=2, context_lines_after=2),
        },
        {
            "name": "All files search (no gitignore)",
            "query": "import",
            "pattern": "*.py",
            "options": SearchOptions(use_gitignore=True),
        },
        {
            "name": "Rare term search",
            "query": "TreeSitterSymbolExtractor",
            "pattern": "*.py",
            "options": SearchOptions(),
        },
    ]

    results = []

    for bench in benchmarks:
        print(f"\n{bench['name']}")
        print(f"  Query: {bench['query']}")
        print(f"  Pattern: {bench['pattern']}")
        print("-" * 80)

        # Warm up
        searcher.search_text(bench["query"], file_pattern=bench["pattern"], options=bench["options"])

        bench_result = {"name": bench["name"]}

        if has_rg:
            # Benchmark with ripgrep
            rg_times = []
            for _ in range(5):
                elapsed, count = benchmark_search(
                    searcher, bench["query"], bench["pattern"], bench["options"], method="ripgrep"
                )
                rg_times.append(elapsed)
            rg_avg = sum(rg_times) / len(rg_times)
            rg_min = min(rg_times)
            print(f"  Ripgrep:  avg={rg_avg * 1000:.1f}ms  min={rg_min * 1000:.1f}ms  ({count} matches)")
            bench_result["rg_avg"] = rg_avg
            bench_result["matches"] = count

        # Benchmark with Python
        py_times = []
        for _ in range(5):
            elapsed, count = benchmark_search(
                searcher, bench["query"], bench["pattern"], bench["options"], method="python"
            )
            py_times.append(elapsed)
        py_avg = sum(py_times) / len(py_times)
        py_min = min(py_times)
        print(f"  Python:   avg={py_avg * 1000:.1f}ms  min={py_min * 1000:.1f}ms  ({count} matches)")
        bench_result["py_avg"] = py_avg
        if "matches" not in bench_result:
            bench_result["matches"] = count

        # Calculate speedups
        if has_rg:
            speedup_rg = py_avg / rg_avg
            print(f"  Speedup:  {speedup_rg:.1f}x faster with ripgrep vs Python")
            bench_result["speedup_rg"] = speedup_rg

        results.append(bench_result)

    # Summary
    if results:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if has_rg:
            avg_speedup_rg = sum(r.get("speedup_rg", 0) for r in results) / len(results)
            print(f"Ripgrep average speedup: {avg_speedup_rg:.1f}x vs Python")
            best = max((r for r in results if "speedup_rg" in r), key=lambda r: r["speedup_rg"])
            worst = min((r for r in results if "speedup_rg" in r), key=lambda r: r["speedup_rg"])
            print(f"  Best: {best['speedup_rg']:.1f}x ({best['name']})")
            print(f"  Worst: {worst['speedup_rg']:.1f}x ({worst['name']})")

        print(f"\nTotal time for all {len(results)} searches:")
        total_py = sum(r["py_avg"] for r in results)
        print(f"  Python:  {total_py * 1000:.1f}ms")

        if has_rg:
            total_rg = sum(r.get("rg_avg", 0) for r in results)
            saved_ms = (total_py - total_rg) * 1000
            saved_pct = (1 - total_rg / total_py) * 100
            print(f"  Ripgrep: {total_rg * 1000:.1f}ms (saved {saved_ms:.1f}ms, {saved_pct:.0f}%)")


if __name__ == "__main__":
    main()
