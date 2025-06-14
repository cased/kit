"""Comprehensive benchmark script for kit repository analysis."""

import argparse
import json
import statistics
import time
from typing import Dict

from kit.repository import Repository as Repo


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def format_size(bytes_size: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}TB"


def benchmark_traditional_indexing(repo: Repo, runs: int = 3) -> Dict:
    """Benchmark traditional repository indexing."""
    print(f"🔍 Benchmarking traditional indexing ({runs} runs)...")

    times = []
    results = []

    for i in range(runs):
        print(f"  Run {i + 1}/{runs}...", end=" ", flush=True)
        start = time.time()
        idx = repo.index()
        elapsed = time.time() - start
        times.append(elapsed)
        results.append(idx)
        print(f"{format_duration(elapsed)}")

    # Use the last result for stats
    idx = results[-1]
    num_files = len(idx["file_tree"])
    num_symbols = sum(len(syms) for syms in idx["symbols"].values())

    return {
        "name": "Traditional Indexing",
        "runs": runs,
        "times": times,
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
        "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        "files": num_files,
        "symbols": num_symbols,
        "symbols_per_sec": num_symbols / statistics.mean(times),
        "files_per_sec": num_files / statistics.mean(times),
    }


def benchmark_incremental_analysis(repo: Repo, runs: int = 3) -> Dict:
    """Benchmark incremental analysis with cold and warm cache."""
    print("🚀 Benchmarking incremental analysis...")

    # Clear cache first
    repo.clear_incremental_cache()

    # Cold cache benchmark
    print(f"  Cold cache ({runs} runs)...", end=" ", flush=True)
    cold_times = []
    for i in range(runs):
        repo.clear_incremental_cache()
        start = time.time()
        symbols = repo.extract_symbols_incremental()
        elapsed = time.time() - start
        cold_times.append(elapsed)
        if i == 0:
            num_symbols = len(symbols)

    cold_avg = statistics.mean(cold_times)
    print(f"avg {format_duration(cold_avg)}")

    # Warm cache benchmark
    print(f"  Warm cache ({runs} runs)...", end=" ", flush=True)
    warm_times = []
    for i in range(runs):
        start = time.time()
        symbols = repo.extract_symbols_incremental()
        elapsed = time.time() - start
        warm_times.append(elapsed)

    warm_avg = statistics.mean(warm_times)
    print(f"avg {format_duration(warm_avg)}")

    # Get cache stats
    stats = repo.get_incremental_stats()

    speedup = cold_avg / warm_avg if warm_avg > 0 else 0

    return {
        "name": "Incremental Analysis",
        "cold_cache": {
            "runs": runs,
            "times": cold_times,
            "avg_time": cold_avg,
            "min_time": min(cold_times),
            "max_time": max(cold_times),
            "std_dev": statistics.stdev(cold_times) if len(cold_times) > 1 else 0,
            "symbols_per_sec": num_symbols / cold_avg,
        },
        "warm_cache": {
            "runs": runs,
            "times": warm_times,
            "avg_time": warm_avg,
            "min_time": min(warm_times),
            "max_time": max(warm_times),
            "std_dev": statistics.stdev(warm_times) if len(warm_times) > 1 else 0,
            "symbols_per_sec": num_symbols / warm_avg,
        },
        "symbols": num_symbols,
        "speedup": speedup,
        "cache_stats": stats,
    }


def benchmark_file_analysis_patterns(repo: Repo) -> Dict:
    """Benchmark different file analysis patterns."""
    print("📁 Benchmarking file analysis patterns...")

    # Get some files to test with
    all_files = list(repo.local_path.rglob("*.py"))[:20]  # Test with first 20 Python files
    if not all_files:
        return {"error": "No Python files found for testing"}

    analyzer = repo.incremental_analyzer
    analyzer.clear_cache()

    results = {}

    # Single file analysis
    test_file = all_files[0]
    print("  Single file analysis...", end=" ", flush=True)
    start = time.time()
    symbols = analyzer.analyze_file(test_file)
    single_time = time.time() - start
    print(f"{format_duration(single_time)} ({len(symbols)} symbols)")

    results["single_file"] = {
        "time": single_time,
        "symbols": len(symbols),
        "file": str(test_file.relative_to(repo.local_path)),
    }

    # Batch analysis
    batch_files = all_files[:10]
    print(f"  Batch analysis ({len(batch_files)} files)...", end=" ", flush=True)
    analyzer.clear_cache()
    start = time.time()
    batch_results = analyzer.analyze_changed_files(batch_files)
    batch_time = time.time() - start
    total_symbols = sum(len(symbols) for symbols in batch_results.values())
    print(f"{format_duration(batch_time)} ({total_symbols} symbols)")

    results["batch_analysis"] = {
        "time": batch_time,
        "files": len(batch_files),
        "symbols": total_symbols,
        "files_per_sec": len(batch_files) / batch_time,
        "symbols_per_sec": total_symbols / batch_time,
    }

    # Cache hit performance
    print("  Cache hit performance...", end=" ", flush=True)
    start = time.time()
    analyzer.analyze_changed_files(batch_files)
    cache_time = time.time() - start
    cache_speedup = batch_time / cache_time if cache_time > 0 else 0
    print(f"{format_duration(cache_time)} ({cache_speedup:.1f}x speedup)")

    results["cache_hits"] = {
        "time": cache_time,
        "speedup": cache_speedup,
        "files": len(batch_files),
    }

    return results


def benchmark_memory_usage(repo: Repo) -> Dict:
    """Benchmark memory usage patterns."""
    print("💾 Benchmarking memory usage...")

    try:
        import psutil

        process = psutil.Process()
    except ImportError:
        return {"error": "psutil not available for memory benchmarking"}

    # Baseline memory
    baseline_memory = process.memory_info().rss

    # Memory after traditional indexing
    print("  Traditional indexing memory...", end=" ", flush=True)
    repo.index()
    traditional_memory = process.memory_info().rss
    traditional_delta = traditional_memory - baseline_memory
    print(f"{format_size(traditional_delta)}")

    # Memory after incremental analysis
    print("  Incremental analysis memory...", end=" ", flush=True)
    repo.clear_incremental_cache()
    repo.extract_symbols_incremental()
    incremental_memory = process.memory_info().rss
    incremental_delta = incremental_memory - baseline_memory
    print(f"{format_size(incremental_delta)}")

    # Cache memory usage
    cache_stats = repo.get_incremental_stats()

    return {
        "baseline_memory": baseline_memory,
        "traditional_delta": traditional_delta,
        "incremental_delta": incremental_delta,
        "memory_efficiency": traditional_delta / incremental_delta if incremental_delta > 0 else 0,
        "cache_size": cache_stats.get("cache_size_bytes", 0),
    }


def benchmark_scalability(repo: Repo) -> Dict:
    """Benchmark scalability with different file counts."""
    print("📈 Benchmarking scalability...")

    all_files = list(repo.local_path.rglob("*.py"))
    if len(all_files) < 10:
        return {"error": "Not enough Python files for scalability testing"}

    analyzer = repo.incremental_analyzer
    results = {}

    # Test with different file counts
    file_counts = [1, 5, 10, 20, 50]
    file_counts = [count for count in file_counts if count <= len(all_files)]

    for count in file_counts:
        print(f"  Testing with {count} files...", end=" ", flush=True)
        test_files = all_files[:count]

        # Clear cache and measure
        analyzer.clear_cache()
        start = time.time()
        file_results = analyzer.analyze_changed_files(test_files)
        elapsed = time.time() - start

        total_symbols = sum(len(symbols) for symbols in file_results.values())

        results[f"{count}_files"] = {
            "files": count,
            "time": elapsed,
            "symbols": total_symbols,
            "files_per_sec": count / elapsed,
            "symbols_per_sec": total_symbols / elapsed,
        }

        print(f"{format_duration(elapsed)} ({total_symbols} symbols)")

    return results


def run_comprehensive_benchmark(repo_path: str, runs: int = 3, output_file: str | None = None) -> Dict:
    """Run comprehensive benchmark suite."""
    print(f"🎯 Running comprehensive benchmark for: {repo_path}")
    print(f"📊 Runs per test: {runs}")
    print("=" * 60)

    repo = Repo(repo_path)

    # Gather basic repo info
    try:
        all_files = list(repo.local_path.rglob("*"))
        code_files = [f for f in all_files if f.suffix in {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c"}]
        repo_info = {
            "path": repo_path,
            "total_files": len(all_files),
            "code_files": len(code_files),
            "size_bytes": sum(f.stat().st_size for f in all_files if f.is_file()),
        }
        print(f"📁 Repository: {repo_info['total_files']} files ({repo_info['code_files']} code files)")
        print(f"💽 Size: {format_size(repo_info['size_bytes'])}")
        print()
    except Exception as e:
        repo_info = {"error": str(e)}

    results = {"timestamp": time.time(), "repo_info": repo_info, "benchmarks": {}}

    # Run benchmarks
    try:
        results["benchmarks"]["traditional"] = benchmark_traditional_indexing(repo, runs)
        print()

        results["benchmarks"]["incremental"] = benchmark_incremental_analysis(repo, runs)
        print()

        results["benchmarks"]["file_patterns"] = benchmark_file_analysis_patterns(repo)
        print()

        results["benchmarks"]["memory"] = benchmark_memory_usage(repo)
        print()

        results["benchmarks"]["scalability"] = benchmark_scalability(repo)
        print()

    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        results["error"] = str(e)

    # Print summary
    print_benchmark_summary(results)

    # Save results if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"📄 Results saved to: {output_file}")

    return results


def print_benchmark_summary(results: Dict):
    """Print a summary of benchmark results."""
    print("=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)

    benchmarks = results.get("benchmarks", {})

    # Traditional vs Incremental comparison
    if "traditional" in benchmarks and "incremental" in benchmarks:
        trad = benchmarks["traditional"]
        incr = benchmarks["incremental"]

        print("🔄 TRADITIONAL vs INCREMENTAL ANALYSIS")
        print(f"Traditional: {format_duration(trad['avg_time'])} ({trad['symbols_per_sec']:.0f} symbols/sec)")
        cold_time = format_duration(incr["cold_cache"]["avg_time"])
        cold_rate = incr["cold_cache"]["symbols_per_sec"]
        print(f"Incremental (cold): {cold_time} ({cold_rate:.0f} symbols/sec)")
        warm_time = format_duration(incr["warm_cache"]["avg_time"])
        warm_rate = incr["warm_cache"]["symbols_per_sec"]
        print(f"Incremental (warm): {warm_time} ({warm_rate:.0f} symbols/sec)")
        print(f"Speedup (warm): {incr['speedup']:.1f}x faster")
        print()

    # Cache performance
    if "incremental" in benchmarks:
        cache_stats = benchmarks["incremental"].get("cache_stats", {})
        if "cache_hit_rate" in cache_stats:
            print("💾 CACHE PERFORMANCE")
            hit_rate = cache_stats["cache_hit_rate"]
            if isinstance(hit_rate, str):
                print(f"Hit rate: {hit_rate}")
            else:
                print(f"Hit rate: {hit_rate:.1f}%")
            print(f"Cached files: {cache_stats.get('cached_files', 0)}")
            print(f"Cache size: {format_size(cache_stats.get('cache_size_bytes', 0))}")
            print()

    # Memory efficiency
    if "memory" in benchmarks:
        mem = benchmarks["memory"]
        if "memory_efficiency" in mem:
            print("💾 MEMORY EFFICIENCY")
            print(f"Traditional: {format_size(mem['traditional_delta'])}")
            print(f"Incremental: {format_size(mem['incremental_delta'])}")
            print(f"Efficiency: {mem['memory_efficiency']:.1f}x more memory efficient")
            print()

    # Scalability insights
    if "scalability" in benchmarks:
        scale = benchmarks["scalability"]
        if not scale.get("error"):
            file_counts = [k for k in scale.keys() if k.endswith("_files")]
            if len(file_counts) >= 2:
                first_key = min(file_counts, key=lambda x: int(x.split("_")[0]))
                last_key = max(file_counts, key=lambda x: int(x.split("_")[0]))

                first = scale[first_key]
                last = scale[last_key]

                print("📈 SCALABILITY")
                print(f"{first['files']} files: {first['symbols_per_sec']:.0f} symbols/sec")
                print(f"{last['files']} files: {last['symbols_per_sec']:.0f} symbols/sec")

                efficiency = last["symbols_per_sec"] / first["symbols_per_sec"]
                print(f"Scaling efficiency: {efficiency:.2f}")
                print()


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(description="Comprehensive benchmark for kit repository analysis.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to repo root (default: .)")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per benchmark (default: 3)")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark (fewer tests)")
    parser.add_argument("--traditional-only", action="store_true", help="Run only traditional indexing benchmark")
    parser.add_argument("--incremental-only", action="store_true", help="Run only incremental analysis benchmark")

    args = parser.parse_args()

    if args.traditional_only:
        print(f"🔍 Running traditional indexing benchmark for: {args.repo}")
        repo = Repo(args.repo)
        results = benchmark_traditional_indexing(repo, args.runs)
        print(f"\n📊 Results: {format_duration(results['avg_time'])} avg, {results['symbols_per_sec']:.0f} symbols/sec")

    elif args.incremental_only:
        print(f"🚀 Running incremental analysis benchmark for: {args.repo}")
        repo = Repo(args.repo)
        results = benchmark_incremental_analysis(repo, args.runs)
        print(f"\n📊 Cold cache: {format_duration(results['cold_cache']['avg_time'])}")
        warm_time = format_duration(results["warm_cache"]["avg_time"])
        speedup = results["speedup"]
        print(f"📊 Warm cache: {warm_time} ({speedup:.1f}x speedup)")

    else:
        # Run comprehensive benchmark
        run_comprehensive_benchmark(args.repo, args.runs, args.output)


if __name__ == "__main__":
    main()
