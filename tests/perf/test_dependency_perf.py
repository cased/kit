"""Performance benchmarks for dependency analyzers.

Run with: pytest tests/perf/test_dependency_perf.py -v --benchmark-only
Or standalone: python tests/perf/test_dependency_perf.py
"""

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from kit import Repository


class PerfResult:
    """Container for performance test results."""

    def __init__(self, name: str, times: List[float], metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.times = times
        self.metadata = metadata or {}

    @property
    def mean(self) -> float:
        return statistics.mean(self.times)

    @property
    def median(self) -> float:
        return statistics.median(self.times)

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.times)

    @property
    def max(self) -> float:
        return max(self.times)

    def __repr__(self) -> str:
        return (
            f"{self.name}: mean={self.mean*1000:.2f}ms, "
            f"median={self.median*1000:.2f}ms, "
            f"min={self.min*1000:.2f}ms, max={self.max*1000:.2f}ms, "
            f"stdev={self.stdev*1000:.2f}ms"
        )


def benchmark(func: Callable, iterations: int = 5, warmup: int = 1) -> List[float]:
    """Run a function multiple times and return timing results."""
    # Warmup runs
    for _ in range(warmup):
        func()

    # Timed runs
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    return times


def generate_python_repo(num_modules: int, imports_per_module: int = 5) -> str:
    """Generate a synthetic Python repo for benchmarking."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_py_")

    os.makedirs(f"{tmpdir}/pkg")
    with open(f"{tmpdir}/pkg/__init__.py", "w") as f:
        f.write("")

    # Create modules
    for i in range(num_modules):
        imports = []
        # Add some stdlib imports
        imports.append("import os")
        imports.append("import sys")

        # Add internal imports (to earlier modules)
        for j in range(min(imports_per_module, i)):
            imports.append(f"from pkg import module_{j}")

        content = "\n".join(imports) + f"\n\ndef func_{i}():\n    pass\n"

        with open(f"{tmpdir}/pkg/module_{i}.py", "w") as f:
            f.write(content)

    return tmpdir


def generate_go_repo(num_packages: int, imports_per_package: int = 3) -> str:
    """Generate a synthetic Go repo for benchmarking."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_go_")

    with open(f"{tmpdir}/go.mod", "w") as f:
        f.write("module github.com/benchmark/test\n\ngo 1.21\n")

    # Create packages
    for i in range(num_packages):
        pkg_dir = f"{tmpdir}/pkg/pkg_{i}"
        os.makedirs(pkg_dir, exist_ok=True)

        imports = ['"fmt"']

        # Add internal imports (to earlier packages)
        for j in range(min(imports_per_package, i)):
            imports.append(f'"github.com/benchmark/test/pkg/pkg_{j}"')

        import_block = "\n\t".join(imports)
        content = f"""package pkg_{i}

import (
	{import_block}
)

func Func{i}() string {{
	return fmt.Sprintf("pkg_{i}")
}}
"""
        with open(f"{pkg_dir}/pkg_{i}.go", "w") as f:
            f.write(content)

    return tmpdir


def run_python_benchmark(num_modules: int, iterations: int = 5) -> PerfResult:
    """Benchmark Python dependency analysis."""
    tmpdir = generate_python_repo(num_modules)

    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("python")
            analyzer.build_dependency_graph()

        times = benchmark(analyze, iterations=iterations)

        # Get some metadata
        analyzer = repo.get_dependency_analyzer("python")
        graph = analyzer.build_dependency_graph()

        return PerfResult(
            f"python_{num_modules}_modules",
            times,
            {
                "num_modules": num_modules,
                "graph_nodes": len(graph),
                "language": "python",
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def run_go_benchmark(num_packages: int, iterations: int = 5) -> PerfResult:
    """Benchmark Go dependency analysis."""
    tmpdir = generate_go_repo(num_packages)

    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("go")
            analyzer.build_dependency_graph()

        times = benchmark(analyze, iterations=iterations)

        # Get some metadata
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        return PerfResult(
            f"go_{num_packages}_packages",
            times,
            {
                "num_packages": num_packages,
                "graph_nodes": len(graph),
                "language": "go",
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def generate_terraform_repo(num_resources: int, refs_per_resource: int = 2) -> str:
    """Generate a synthetic Terraform repo for benchmarking."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_tf_")

    # Create variables
    with open(f"{tmpdir}/variables.tf", "w") as f:
        f.write('variable "region" {\n  default = "us-west-2"\n}\n\n')
        f.write('variable "project" {\n  default = "benchmark"\n}\n\n')
        for i in range(num_resources):
            f.write(f'variable "var_{i}" {{\n  default = "value_{i}"\n}}\n\n')

    # Create locals
    with open(f"{tmpdir}/locals.tf", "w") as f:
        f.write("locals {\n")
        for i in range(num_resources):
            f.write(f'  local_{i} = "${{var.var_{i}}}-local"\n')
        f.write("}\n")

    # Create resources with references
    with open(f"{tmpdir}/main.tf", "w") as f:
        f.write('provider "aws" {\n  region = var.region\n}\n\n')
        for i in range(num_resources):
            refs = []
            # Reference variables and locals
            refs.append(f"var.var_{i}")
            refs.append(f"local.local_{i}")
            # Reference earlier resources
            for j in range(min(refs_per_resource, i)):
                refs.append(f"aws_instance.instance_{j}.id")

            tags = ", ".join([f"ref{k} = {r}" for k, r in enumerate(refs)])
            f.write(f"""resource "aws_instance" "instance_{i}" {{
  ami           = "ami-12345"
  instance_type = "t2.micro"
  tags = {{ {tags} }}
}}

""")

    # Create outputs
    with open(f"{tmpdir}/outputs.tf", "w") as f:
        for i in range(min(5, num_resources)):
            f.write(f'output "instance_{i}_id" {{\n  value = aws_instance.instance_{i}.id\n}}\n\n')

    return tmpdir


def run_terraform_benchmark(num_resources: int, iterations: int = 5) -> PerfResult:
    """Benchmark Terraform dependency analysis."""
    tmpdir = generate_terraform_repo(num_resources)

    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("terraform")
            analyzer.build_dependency_graph()

        times = benchmark(analyze, iterations=iterations)

        # Get some metadata
        analyzer = repo.get_dependency_analyzer("terraform")
        graph = analyzer.build_dependency_graph()

        return PerfResult(
            f"terraform_{num_resources}_resources",
            times,
            {
                "num_resources": num_resources,
                "graph_nodes": len(graph),
                "language": "terraform",
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def run_real_repo_benchmark(repo_path: str, language: str, iterations: int = 3) -> PerfResult:
    """Benchmark against a real repository."""
    repo = Repository(repo_path)

    def analyze():
        analyzer = repo.get_dependency_analyzer(language)
        analyzer.build_dependency_graph()

    times = benchmark(analyze, iterations=iterations)

    # Get metadata
    analyzer = repo.get_dependency_analyzer(language)
    graph = analyzer.build_dependency_graph()

    return PerfResult(
        f"real_{language}_{Path(repo_path).name}",
        times,
        {
            "repo_path": repo_path,
            "graph_nodes": len(graph),
            "language": language,
        },
    )


def print_results(results: List[PerfResult]):
    """Print benchmark results in a formatted table."""
    print("\n" + "=" * 80)
    print("DEPENDENCY ANALYZER PERFORMANCE RESULTS")
    print("=" * 80)

    # Header
    print(f"{'Benchmark':<40} {'Mean':>10} {'Median':>10} {'Min':>10} {'Max':>10} {'Nodes':>8}")
    print("-" * 80)

    for r in results:
        nodes = r.metadata.get("graph_nodes", "N/A")
        print(
            f"{r.name:<40} "
            f"{r.mean*1000:>9.1f}ms "
            f"{r.median*1000:>9.1f}ms "
            f"{r.min*1000:>9.1f}ms "
            f"{r.max*1000:>9.1f}ms "
            f"{nodes:>8}"
        )

    print("=" * 80)


# === Pytest-benchmark compatible tests ===


def test_python_10_modules(benchmark):
    """Benchmark Python analyzer with 10 modules."""
    tmpdir = generate_python_repo(10)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("python")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_python_50_modules(benchmark):
    """Benchmark Python analyzer with 50 modules."""
    tmpdir = generate_python_repo(50)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("python")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_python_100_modules(benchmark):
    """Benchmark Python analyzer with 100 modules."""
    tmpdir = generate_python_repo(100)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("python")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_go_10_packages(benchmark):
    """Benchmark Go analyzer with 10 packages."""
    tmpdir = generate_go_repo(10)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("go")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_go_50_packages(benchmark):
    """Benchmark Go analyzer with 50 packages."""
    tmpdir = generate_go_repo(50)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("go")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_go_100_packages(benchmark):
    """Benchmark Go analyzer with 100 packages."""
    tmpdir = generate_go_repo(100)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("go")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_terraform_10_resources(benchmark):
    """Benchmark Terraform analyzer with 10 resources."""
    tmpdir = generate_terraform_repo(10)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("terraform")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_terraform_50_resources(benchmark):
    """Benchmark Terraform analyzer with 50 resources."""
    tmpdir = generate_terraform_repo(50)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("terraform")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_terraform_100_resources(benchmark):
    """Benchmark Terraform analyzer with 100 resources."""
    tmpdir = generate_terraform_repo(100)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("terraform")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


# === Standalone runner ===

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dependency analyzer performance benchmarks")
    parser.add_argument(
        "--sizes", type=int, nargs="+", default=[10, 50, 100, 200], help="Module/package counts to test"
    )
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations per benchmark")
    parser.add_argument(
        "--language", choices=["python", "go", "terraform", "all"], default="all", help="Language to benchmark"
    )
    parser.add_argument("--repo", type=str, help="Path to real repo to benchmark")
    parser.add_argument("--repo-language", type=str, help="Language for real repo benchmark")
    args = parser.parse_args()

    results = []

    if args.repo and args.repo_language:
        print(f"Benchmarking real repo: {args.repo}")
        results.append(run_real_repo_benchmark(args.repo, args.repo_language, args.iterations))
    else:
        for size in args.sizes:
            if args.language in ("python", "all"):
                print(f"Benchmarking Python with {size} modules...")
                results.append(run_python_benchmark(size, args.iterations))

            if args.language in ("go", "all"):
                print(f"Benchmarking Go with {size} packages...")
                results.append(run_go_benchmark(size, args.iterations))

            if args.language in ("terraform", "all"):
                print(f"Benchmarking Terraform with {size} resources...")
                results.append(run_terraform_benchmark(size, args.iterations))

    print_results(results)
