import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kit import Repository


def test_dependency_analyzer_basic():
    """Test basic functionality of the DependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/mypackage")

        with open(f"{tmpdir}/mypackage/__init__.py", "w") as f:
            f.write("# Empty init file\n")

        with open(f"{tmpdir}/mypackage/module1.py", "w") as f:
            f.write("""
from mypackage import module2

def function1():
    return module2.function2()
""")

        with open(f"{tmpdir}/mypackage/module2.py", "w") as f:
            f.write("""
import os
import sys

def function2():
    return os.path.join('a', 'b')
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        graph = analyzer.build_dependency_graph()

        assert "mypackage.module1" in graph
        assert "mypackage.module2" in graph
        assert "os" in graph

        assert "mypackage.module2" in graph["mypackage.module1"]["dependencies"]
        assert "os" in graph["mypackage.module2"]["dependencies"]


def test_dependency_analyzer_cycles():
    """Test the cycle detection in the DependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/cyclicpackage")

        with open(f"{tmpdir}/cyclicpackage/__init__.py", "w") as f:
            f.write("# Empty init file\n")

        with open(f"{tmpdir}/cyclicpackage/a.py", "w") as f:
            f.write("""
from cyclicpackage import b

def func_a():
    return b.func_b()
""")

        with open(f"{tmpdir}/cyclicpackage/b.py", "w") as f:
            f.write("""
from cyclicpackage import c

def func_b():
    return c.func_c()
""")

        with open(f"{tmpdir}/cyclicpackage/c.py", "w") as f:
            f.write("""
from cyclicpackage import a

def func_c():
    return a.func_a()
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        cycles = analyzer.find_cycles()

        assert len(cycles) > 0

        found_cycle = False
        for cycle in cycles:
            if "cyclicpackage.a" in cycle and "cyclicpackage.b" in cycle and "cyclicpackage.c" in cycle:
                found_cycle = True
                break

        assert found_cycle, "Expected cycle between a, b, and c was not found"


def test_dependency_analyzer_exports():
    """Test the export functionality of the DependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/main.py", "w") as f:
            f.write("""
import helper

def main():
    return helper.helper_func()
""")

        with open(f"{tmpdir}/helper.py", "w") as f:
            f.write("""
import os

def helper_func():
    return os.path.exists('test')
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        export_file = f"{tmpdir}/deps.json"
        result = analyzer.export_dependency_graph(output_format="json", output_path=export_file)

        assert os.path.exists(export_file)
        assert result == export_file

        with open(export_file, "r") as f:
            data = json.load(f)
            assert "main" in data
            assert "helper" in data["main"]["dependencies"]

        dot_file = f"{tmpdir}/deps.dot"
        result = analyzer.export_dependency_graph(output_format="dot", output_path=dot_file)

        assert os.path.exists(dot_file)
        with open(dot_file, "r") as f:
            content = f.read()
            assert "digraph G" in content
            assert '"main" -> "helper"' in content


def test_get_module_dependencies():
    """Test getting dependencies for a specific module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/complex.py", "w") as f:
            f.write("""
import os
import sys
import json
from datetime import datetime

def complex_func():
    return os.path.join(str(datetime.now()), 'file.json')
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        direct_deps = analyzer.get_module_dependencies("complex")

        assert "os" in direct_deps
        assert "sys" in direct_deps
        assert "json" in direct_deps
        assert "datetime" in direct_deps


def test_get_dependents():
    """Test getting modules that depend on a specified module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/utils.py", "w") as f:
            f.write("""
def utility_func():
    return "util"
""")

        with open(f"{tmpdir}/module1.py", "w") as f:
            f.write("import utils\ndef func1(): return utils.utility_func()")

        with open(f"{tmpdir}/module2.py", "w") as f:
            f.write("from utils import utility_func\ndef func2(): return utility_func()")

        with open(f"{tmpdir}/module3.py", "w") as f:
            f.write("import module1\ndef func3(): return module1.func1()")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        direct_dependents = analyzer.get_dependents("utils")
        assert "module1" in direct_dependents
        assert "module2" in direct_dependents
        assert "module3" not in direct_dependents

        all_dependents = analyzer.get_dependents("utils", include_indirect=True)
        assert "module1" in all_dependents
        assert "module2" in all_dependents
        assert "module3" in all_dependents


def test_file_dependencies():
    """Test getting detailed dependency information for a specific file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/app.py", "w") as f:
            f.write("""
import os
import sys
import json

def app_function():
    return json.dumps({'status': 'ok'})
""")

        with open(f"{tmpdir}/server.py", "w") as f:
            f.write("""
import app

def start_server():
    return app.app_function()
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        file_deps = analyzer.get_file_dependencies("app.py")

        assert file_deps["file_path"] == "app.py"
        assert file_deps["module_name"] == "app"

        dependencies = {d["module"] for d in file_deps["dependencies"]}
        assert "os" in dependencies
        assert "sys" in dependencies
        assert "json" in dependencies

        dependents = {d["module"] for d in file_deps["dependents"]}
        assert "server" in dependents


def test_dependency_report():
    """Test generating a comprehensive dependency report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/myproject")

        with open(f"{tmpdir}/myproject/__init__.py", "w") as f:
            f.write("# Project init\n")

        with open(f"{tmpdir}/myproject/core.py", "w") as f:
            f.write("""
import os
import sys

def core_function():
    return os.path.join('a', 'b')
""")

        with open(f"{tmpdir}/myproject/api.py", "w") as f:
            f.write("""
from myproject import core
import json

def api_function():
    return json.dumps(core.core_function())
""")

        with open(f"{tmpdir}/myproject/utils.py", "w") as f:
            f.write("""
import os
import datetime

def utils_function():
    return os.path.join(str(datetime.datetime.now()), 'log.txt')
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        report_file = f"{tmpdir}/report.json"
        report = analyzer.generate_dependency_report(report_file)

        assert "summary" in report
        assert "external_dependencies" in report

        assert os.path.exists(report_file)

        assert report["summary"]["total_modules"] > 5
        assert "os" in report["external_dependencies"]


def test_generate_llm_context():
    """Test generating LLM-friendly context from dependency analysis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/myproject")

        with open(f"{tmpdir}/myproject/__init__.py", "w") as f:
            f.write("# Project init\n")

        with open(f"{tmpdir}/myproject/core.py", "w") as f:
            f.write("""
# Core functionality module
import os
import sys
import json

def core_function():
    return json.dumps({'path': os.path.join('a', 'b')})
""")

        with open(f"{tmpdir}/myproject/utils.py", "w") as f:
            f.write("""
# Utility functions
import os
import datetime

def get_timestamp_path(filename):
    return os.path.join(str(datetime.datetime.now()), filename)
""")

        with open(f"{tmpdir}/myproject/api.py", "w") as f:
            f.write("""
# API module
from myproject import core
from myproject import utils
import requests  # External third-party dependency

def api_call():
    path = utils.get_timestamp_path('data.json')
    return requests.get(core.core_function())
""")

        with open(f"{tmpdir}/myproject/circular_a.py", "w") as f:
            f.write("""
import myproject.circular_b

def function_a():
    return myproject.circular_b.function_b()
""")

        with open(f"{tmpdir}/myproject/circular_b.py", "w") as f:
            f.write("""
import myproject.circular_a

def function_b():
    return myproject.circular_a.function_a()
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("python")

        analyzer.build_dependency_graph()

        md_output = analyzer.generate_llm_context(output_format="markdown")

        assert "# Dependency Analysis Summary" in md_output
        assert "## Overview" in md_output
        assert "## Key Components" in md_output
        assert "## Python-Specific Insights" in md_output

        assert "## Circular Dependencies" in md_output

        text_output = analyzer.generate_llm_context(output_format="text")

        assert "DEPENDENCY ANALYSIS SUMMARY" in text_output
        assert "OVERVIEW:" in text_output
        assert "KEY COMPONENTS:" in text_output
        assert "PYTHON-SPECIFIC INSIGHTS:" in text_output

        output_file = f"{tmpdir}/llm_context.md"
        analyzer.generate_llm_context(output_path=output_file)

        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            content = f.read()
            assert "Dependency Analysis Summary" in content
