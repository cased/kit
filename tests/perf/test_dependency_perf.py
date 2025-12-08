"""Performance benchmarks for dependency analyzers.

Run with: pytest tests/perf/test_dependency_perf.py -v --benchmark-only
Or standalone: python tests/perf/test_dependency_perf.py

Note: pytest-benchmark tests are skipped if pytest-benchmark is not installed.
"""

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from kit import Repository

# Skip all benchmark tests if pytest-benchmark is not installed
try:
    import pytest_benchmark  # noqa: F401

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False

pytestmark = pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")


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


def generate_rust_repo(num_modules: int, imports_per_module: int = 3) -> str:
    """Generate a synthetic Rust repo for benchmarking."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_rs_")

    # Create Cargo.toml
    with open(f"{tmpdir}/Cargo.toml", "w") as f:
        f.write("""[package]
name = "benchmark_crate"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = "1.0"
""")

    os.makedirs(f"{tmpdir}/src")

    # Create lib.rs with mod declarations
    mod_decls = "\n".join([f"mod module_{i};" for i in range(num_modules)])
    with open(f"{tmpdir}/src/lib.rs", "w") as f:
        f.write(f"""use std::collections::HashMap;
use serde::Serialize;

{mod_decls}

pub fn main_func() -> HashMap<String, String> {{
    HashMap::new()
}}
""")

    # Create modules
    for i in range(num_modules):
        imports = ["use std::io;"]

        # Add internal imports (to earlier modules)
        for j in range(min(imports_per_module, i)):
            imports.append(f"use crate::module_{j}::func_{j};")

        import_block = "\n".join(imports)
        content = f"""{import_block}

pub fn func_{i}() -> i32 {{
    {i}
}}
"""
        with open(f"{tmpdir}/src/module_{i}.rs", "w") as f:
            f.write(content)

    return tmpdir


def run_rust_benchmark(num_modules: int, iterations: int = 5) -> PerfResult:
    """Benchmark Rust dependency analysis."""
    tmpdir = generate_rust_repo(num_modules)

    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("rust")
            analyzer.build_dependency_graph()

        times = benchmark(analyze, iterations=iterations)

        # Get some metadata
        analyzer = repo.get_dependency_analyzer("rust")
        graph = analyzer.build_dependency_graph()

        return PerfResult(
            f"rust_{num_modules}_modules",
            times,
            {
                "num_modules": num_modules,
                "graph_nodes": len(graph),
                "language": "rust",
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def generate_javascript_repo(num_modules: int, imports_per_module: int = 5) -> str:
    """Generate a synthetic JavaScript repo for benchmarking."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_js_")

    # Create package.json
    with open(f"{tmpdir}/package.json", "w") as f:
        f.write('{"name": "benchmark-app", "version": "1.0.0"}\n')

    os.makedirs(f"{tmpdir}/src")

    # Create modules
    for i in range(num_modules):
        imports = []
        # Add some external imports
        imports.append("import path from 'path';")
        imports.append("import fs from 'fs';")

        # Add internal imports (to earlier modules)
        for j in range(min(imports_per_module, i)):
            imports.append(f"import {{ func{j} }} from './module_{j}.js';")

        content = "\n".join(imports) + f"\n\nexport function func{i}() {{\n  return {i};\n}}\n"

        with open(f"{tmpdir}/src/module_{i}.js", "w") as f:
            f.write(content)

    return tmpdir


def run_javascript_benchmark(num_modules: int, iterations: int = 5) -> PerfResult:
    """Benchmark JavaScript dependency analysis."""
    tmpdir = generate_javascript_repo(num_modules)

    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("javascript")
            analyzer.build_dependency_graph()

        times = benchmark(analyze, iterations=iterations)

        # Get some metadata
        analyzer = repo.get_dependency_analyzer("javascript")
        graph = analyzer.build_dependency_graph()

        return PerfResult(
            f"javascript_{num_modules}_modules",
            times,
            {
                "num_modules": num_modules,
                "graph_nodes": len(graph),
                "language": "javascript",
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
    print("\n" + "=" * 90)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("=" * 90)

    # Header
    print(f"{'Benchmark':<45} {'Mean':>10} {'Median':>10} {'Min':>10} {'Max':>10} {'Items':>8}")
    print("-" * 90)

    for r in results:
        # Try different metadata keys for item count
        items = (
            r.metadata.get("graph_nodes")
            or r.metadata.get("total_files")
            or r.metadata.get("total_entries")
            or r.metadata.get("total_symbols")
            or r.metadata.get("tree_entries")
            or "N/A"
        )
        print(
            f"{r.name:<45} "
            f"{r.mean*1000:>9.1f}ms "
            f"{r.median*1000:>9.1f}ms "
            f"{r.min*1000:>9.1f}ms "
            f"{r.max*1000:>9.1f}ms "
            f"{items:>8}"
        )

    print("=" * 90)


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


def test_javascript_10_modules(benchmark):
    """Benchmark JavaScript analyzer with 10 modules."""
    tmpdir = generate_javascript_repo(10)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("javascript")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_javascript_50_modules(benchmark):
    """Benchmark JavaScript analyzer with 50 modules."""
    tmpdir = generate_javascript_repo(50)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("javascript")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_javascript_100_modules(benchmark):
    """Benchmark JavaScript analyzer with 100 modules."""
    tmpdir = generate_javascript_repo(100)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("javascript")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_rust_10_modules(benchmark):
    """Benchmark Rust analyzer with 10 modules."""
    tmpdir = generate_rust_repo(10)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("rust")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_rust_50_modules(benchmark):
    """Benchmark Rust analyzer with 50 modules."""
    tmpdir = generate_rust_repo(50)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("rust")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_rust_100_modules(benchmark):
    """Benchmark Rust analyzer with 100 modules."""
    tmpdir = generate_rust_repo(100)
    try:
        repo = Repository(tmpdir)

        def analyze():
            analyzer = repo.get_dependency_analyzer("rust")
            return analyzer.build_dependency_graph()

        result = benchmark(analyze)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


# === File Tree Performance Tests (Rust-accelerated) ===


def generate_large_file_tree(num_dirs: int, files_per_dir: int = 10) -> str:
    """Generate a synthetic repo with many files for file tree benchmarks."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_tree_")

    # Create a .gitignore to test gitignore handling
    with open(f"{tmpdir}/.gitignore", "w") as f:
        f.write("*.pyc\n__pycache__/\n.git/\n*.log\n")

    for i in range(num_dirs):
        dir_path = f"{tmpdir}/pkg_{i}"
        os.makedirs(dir_path, exist_ok=True)

        for j in range(files_per_dir):
            # Mix of file types
            extensions = [".py", ".go", ".ts", ".json", ".md"]
            ext = extensions[j % len(extensions)]
            with open(f"{dir_path}/file_{j}{ext}", "w") as f:
                f.write(f"# File {i}-{j}\n" * 10)

        # Also create some files that should be ignored
        with open(f"{dir_path}/cache.pyc", "w") as f:
            f.write("should be ignored")
        with open(f"{dir_path}/debug.log", "w") as f:
            f.write("should be ignored")

    return tmpdir


def run_file_tree_benchmark(num_dirs: int, files_per_dir: int = 10, iterations: int = 5) -> PerfResult:
    """Benchmark file tree walking (Rust-accelerated)."""
    tmpdir = generate_large_file_tree(num_dirs, files_per_dir)

    try:
        repo = Repository(tmpdir)

        def get_tree():
            # Force fresh tree each time
            repo.mapper._file_tree = None
            return repo.get_file_tree()

        times = benchmark(get_tree, iterations=iterations)

        # Get metadata
        tree = repo.get_file_tree()

        return PerfResult(
            f"file_tree_{num_dirs}dirs_{files_per_dir}files",
            times,
            {
                "num_dirs": num_dirs,
                "files_per_dir": files_per_dir,
                "total_files": len([f for f in tree if not f["is_dir"]]),
                "total_entries": len(tree),
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def run_symbol_extraction_benchmark(num_files: int, lines_per_file: int = 50, iterations: int = 5) -> PerfResult:
    """Benchmark symbol extraction from Python files."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_symbols_")

    try:
        os.makedirs(f"{tmpdir}/pkg")
        with open(f"{tmpdir}/pkg/__init__.py", "w") as f:
            f.write("")

        for i in range(num_files):
            content = f'''"""Module {i} docstring."""

class Class{i}:
    """Class {i} docstring."""

    def method_{i}_a(self, arg1: str, arg2: int) -> bool:
        """Method a docstring."""
        return True

    def method_{i}_b(self) -> None:
        pass

    @property
    def prop_{i}(self) -> str:
        return "value"


def function_{i}_main(x: int, y: int) -> int:
    """Main function for module {i}."""
    return x + y


def function_{i}_helper() -> None:
    pass


CONSTANT_{i} = "value"
'''
            with open(f"{tmpdir}/pkg/module_{i}.py", "w") as f:
                f.write(content)

        repo = Repository(tmpdir)

        def extract_symbols():
            symbols = []
            for i in range(num_files):
                s = repo.extract_symbols(f"pkg/module_{i}.py")
                symbols.extend(s)
            return symbols

        times = benchmark(extract_symbols, iterations=iterations)

        # Get metadata
        all_symbols = extract_symbols()

        return PerfResult(
            f"symbol_extraction_{num_files}files",
            times,
            {
                "num_files": num_files,
                "total_symbols": len(all_symbols),
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def run_repo_map_benchmark(num_files: int, iterations: int = 3) -> PerfResult:
    """Benchmark full repository mapping (file tree + symbols)."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_repomap_")

    try:
        os.makedirs(f"{tmpdir}/src")

        for i in range(num_files):
            content = f"""class Handler{i}:
    def handle(self, request):
        return self.process(request)

    def process(self, data):
        return data

def main_{i}():
    h = Handler{i}()
    return h.handle({{}})
"""
            with open(f"{tmpdir}/src/handler_{i}.py", "w") as f:
                f.write(content)

        repo = Repository(tmpdir)

        def get_repo_map():
            return repo.mapper.get_repo_map()

        times = benchmark(get_repo_map, iterations=iterations, warmup=1)

        # Get metadata
        repo_map = repo.mapper.get_repo_map()

        return PerfResult(
            f"repo_map_{num_files}files",
            times,
            {
                "num_files": num_files,
                "tree_entries": len(repo_map["file_tree"]),
                "files_with_symbols": len(repo_map["symbols"]),
            },
        )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


# === Pytest-benchmark tests for file tree ===


def test_file_tree_100_files(benchmark):
    """Benchmark file tree with 100 files (10 dirs x 10 files)."""
    tmpdir = generate_large_file_tree(10, 10)
    try:
        repo = Repository(tmpdir)

        def get_tree():
            repo.mapper._file_tree = None
            return repo.get_file_tree()

        result = benchmark(get_tree)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_file_tree_500_files(benchmark):
    """Benchmark file tree with 500 files (50 dirs x 10 files)."""
    tmpdir = generate_large_file_tree(50, 10)
    try:
        repo = Repository(tmpdir)

        def get_tree():
            repo.mapper._file_tree = None
            return repo.get_file_tree()

        result = benchmark(get_tree)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_file_tree_1000_files(benchmark):
    """Benchmark file tree with 1000 files (100 dirs x 10 files)."""
    tmpdir = generate_large_file_tree(100, 10)
    try:
        repo = Repository(tmpdir)

        def get_tree():
            repo.mapper._file_tree = None
            return repo.get_file_tree()

        result = benchmark(get_tree)
        assert len(result) > 0
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_symbol_extraction_20_files(benchmark):
    """Benchmark symbol extraction from 20 Python files."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_sym_")
    try:
        os.makedirs(f"{tmpdir}/pkg")
        with open(f"{tmpdir}/pkg/__init__.py", "w") as f:
            f.write("")

        for i in range(20):
            content = f"""class Class{i}:
    def method_a(self): pass
    def method_b(self): pass

def func_{i}(): pass
"""
            with open(f"{tmpdir}/pkg/mod_{i}.py", "w") as f:
                f.write(content)

        repo = Repository(tmpdir)

        def extract():
            return [repo.extract_symbols(f"pkg/mod_{i}.py") for i in range(20)]

        result = benchmark(extract)
        assert len(result) == 20
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_symbol_extraction_50_files(benchmark):
    """Benchmark symbol extraction from 50 Python files."""
    tmpdir = tempfile.mkdtemp(prefix="kit_perf_sym_")
    try:
        os.makedirs(f"{tmpdir}/pkg")
        with open(f"{tmpdir}/pkg/__init__.py", "w") as f:
            f.write("")

        for i in range(50):
            content = f"""class Class{i}:
    def method_a(self): pass
    def method_b(self): pass

def func_{i}(): pass
"""
            with open(f"{tmpdir}/pkg/mod_{i}.py", "w") as f:
                f.write(content)

        repo = Repository(tmpdir)

        def extract():
            return [repo.extract_symbols(f"pkg/mod_{i}.py") for i in range(50)]

        result = benchmark(extract)
        assert len(result) == 50
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
        "--benchmark",
        choices=["deps", "filetree", "symbols", "repomap", "all"],
        default="all",
        help="Type of benchmark to run",
    )
    parser.add_argument(
        "--language", choices=["python", "go", "terraform", "javascript", "rust", "all"], default="all", help="Language to benchmark (deps)"
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
            # Dependency analyzer benchmarks
            if args.benchmark in ("deps", "all"):
                if args.language in ("python", "all"):
                    print(f"Benchmarking Python dependency analyzer with {size} modules...")
                    results.append(run_python_benchmark(size, args.iterations))

                if args.language in ("go", "all"):
                    print(f"Benchmarking Go dependency analyzer with {size} packages...")
                    results.append(run_go_benchmark(size, args.iterations))

                if args.language in ("terraform", "all"):
                    print(f"Benchmarking Terraform dependency analyzer with {size} resources...")
                    results.append(run_terraform_benchmark(size, args.iterations))

                if args.language in ("javascript", "all"):
                    print(f"Benchmarking JavaScript dependency analyzer with {size} modules...")
                    results.append(run_javascript_benchmark(size, args.iterations))

                if args.language in ("rust", "all"):
                    print(f"Benchmarking Rust dependency analyzer with {size} modules...")
                    results.append(run_rust_benchmark(size, args.iterations))

            # File tree benchmarks (Rust-accelerated)
            if args.benchmark in ("filetree", "all"):
                print(f"Benchmarking file tree with {size} dirs x 10 files...")
                results.append(run_file_tree_benchmark(size, 10, args.iterations))

            # Symbol extraction benchmarks
            if args.benchmark in ("symbols", "all"):
                print(f"Benchmarking symbol extraction with {size} files...")
                results.append(run_symbol_extraction_benchmark(size, iterations=args.iterations))

            # Repo map benchmarks
            if args.benchmark in ("repomap", "all"):
                print(f"Benchmarking repo map with {size} files...")
                results.append(run_repo_map_benchmark(size, iterations=min(3, args.iterations)))

    print_results(results)
