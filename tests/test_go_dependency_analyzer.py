import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kit import Repository


def test_go_dependency_analyzer_basic():
    """Test basic functionality of the GoDependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create go.mod
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/myapp

go 1.21
""")

        # Create main.go
        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	"fmt"
	"github.com/example/myapp/pkg/utils"
)

func main() {
	fmt.Println(utils.Hello())
}
""")

        # Create pkg/utils directory and file
        os.makedirs(f"{tmpdir}/pkg/utils")
        with open(f"{tmpdir}/pkg/utils/utils.go", "w") as f:
            f.write("""package utils

import "strings"

func Hello() string {
	return strings.ToUpper("hello")
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        graph = analyzer.build_dependency_graph()

        # Check that we found the main package
        assert "github.com/example/myapp" in graph
        # Check that we found the utils package
        assert "github.com/example/myapp/pkg/utils" in graph
        # Check stdlib imports
        assert "fmt" in graph
        assert "strings" in graph

        # Check dependencies
        main_deps = graph["github.com/example/myapp"]["dependencies"]
        assert "fmt" in main_deps
        assert "github.com/example/myapp/pkg/utils" in main_deps

        utils_deps = graph["github.com/example/myapp/pkg/utils"]["dependencies"]
        assert "strings" in utils_deps


def test_go_dependency_analyzer_import_types():
    """Test classification of imports as internal, stdlib, or external."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/myapp

go 1.21

require github.com/gorilla/mux v1.8.0
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	"fmt"
	"net/http"
	"github.com/gorilla/mux"
	"github.com/example/myapp/internal/handler"
)

func main() {
	r := mux.NewRouter()
	r.HandleFunc("/", handler.Home)
	http.ListenAndServe(":8080", r)
}
""")

        os.makedirs(f"{tmpdir}/internal/handler")
        with open(f"{tmpdir}/internal/handler/handler.go", "w") as f:
            f.write("""package handler

import "net/http"

func Home(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("Hello"))
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        graph = analyzer.build_dependency_graph()

        # Check type classifications
        assert graph["fmt"]["type"] == "stdlib"
        assert graph["net/http"]["type"] == "stdlib"
        assert graph["github.com/gorilla/mux"]["type"] == "external"
        assert graph["github.com/example/myapp"]["type"] == "internal"
        assert graph["github.com/example/myapp/internal/handler"]["type"] == "internal"


def test_go_dependency_analyzer_cycles():
    """Test cycle detection in Go packages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/cyclic

go 1.21
""")

        os.makedirs(f"{tmpdir}/pkg/a")
        os.makedirs(f"{tmpdir}/pkg/b")
        os.makedirs(f"{tmpdir}/pkg/c")

        with open(f"{tmpdir}/pkg/a/a.go", "w") as f:
            f.write("""package a

import "github.com/example/cyclic/pkg/b"

func FuncA() string {
	return b.FuncB()
}
""")

        with open(f"{tmpdir}/pkg/b/b.go", "w") as f:
            f.write("""package b

import "github.com/example/cyclic/pkg/c"

func FuncB() string {
	return c.FuncC()
}
""")

        with open(f"{tmpdir}/pkg/c/c.go", "w") as f:
            f.write("""package c

import "github.com/example/cyclic/pkg/a"

func FuncC() string {
	return a.FuncA()
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        analyzer.build_dependency_graph()
        cycles = analyzer.find_cycles()

        assert len(cycles) > 0

        # Check that we found the cycle between a, b, and c
        found_cycle = False
        for cycle in cycles:
            pkg_names = [p.split("/")[-1] for p in cycle]
            if "a" in pkg_names and "b" in pkg_names and "c" in pkg_names:
                found_cycle = True
                break

        assert found_cycle, "Expected cycle between a, b, and c was not found"


def test_go_dependency_analyzer_export_json():
    """Test JSON export of Go dependency graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/simple

go 1.21
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "fmt"

func main() {
	fmt.Println("Hello")
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        result = analyzer.export_dependency_graph(output_format="json")

        assert isinstance(result, dict)
        assert "github.com/example/simple" in result
        assert "fmt" in result
        assert isinstance(result["github.com/example/simple"]["dependencies"], list)


def test_go_dependency_analyzer_export_dot():
    """Test DOT format export of Go dependency graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/simple

go 1.21
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "fmt"

func main() {
	fmt.Println("Hello")
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        result = analyzer.export_dependency_graph(output_format="dot")

        assert isinstance(result, str)
        assert "digraph G" in result
        assert "github.com/example/simple" in result


def test_go_dependency_analyzer_aliased_imports():
    """Test handling of aliased imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/aliases

go 1.21
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	f "fmt"
	. "strings"
	_ "net/http/pprof"
)

func main() {
	f.Println(ToUpper("hello"))
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        graph = analyzer.build_dependency_graph()

        # All these imports should be detected
        assert "fmt" in graph
        assert "strings" in graph
        assert "net/http/pprof" in graph


def test_go_dependency_analyzer_single_import():
    """Test handling of single-line imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/single

go 1.21
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "fmt"

func main() {
	fmt.Println("Hello")
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        graph = analyzer.build_dependency_graph()

        assert "fmt" in graph
        assert "fmt" in graph["github.com/example/single"]["dependencies"]


def test_go_dependency_analyzer_get_dependents():
    """Test getting packages that depend on a given package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/deps

go 1.21
""")

        os.makedirs(f"{tmpdir}/pkg/shared")
        os.makedirs(f"{tmpdir}/pkg/a")
        os.makedirs(f"{tmpdir}/pkg/b")

        with open(f"{tmpdir}/pkg/shared/shared.go", "w") as f:
            f.write("""package shared

func Common() string {
	return "shared"
}
""")

        with open(f"{tmpdir}/pkg/a/a.go", "w") as f:
            f.write("""package a

import "github.com/example/deps/pkg/shared"

func FuncA() string {
	return shared.Common()
}
""")

        with open(f"{tmpdir}/pkg/b/b.go", "w") as f:
            f.write("""package b

import "github.com/example/deps/pkg/shared"

func FuncB() string {
	return shared.Common()
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        analyzer.build_dependency_graph()
        dependents = analyzer.get_dependents("github.com/example/deps/pkg/shared")

        assert "github.com/example/deps/pkg/a" in dependents
        assert "github.com/example/deps/pkg/b" in dependents


def test_go_dependency_analyzer_llm_context():
    """Test LLM context generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("""module github.com/example/context

go 1.21
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Println(os.Args)
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        context = analyzer.generate_llm_context(output_format="markdown")

        assert "# Dependency Analysis Summary" in context
        assert "Go-Specific Insights" in context
        assert "github.com/example/context" in context


def test_go_dependency_analyzer_no_go_mod():
    """Test analyzer behavior when go.mod is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "fmt"

func main() {
	fmt.Println("Hello")
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")

        # Should not raise, just use directory-based naming
        graph = analyzer.build_dependency_graph()

        assert "fmt" in graph
        # Without go.mod, the main package should still be detected
        assert len([p for p, d in graph.items() if d["type"] == "internal"]) >= 1


def test_go_dependency_analyzer_factory():
    """Test that the factory method correctly returns GoDependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module test\n")
        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("package main\n")

        repo = Repository(tmpdir)

        # Test both "go" and "golang" work
        analyzer1 = repo.get_dependency_analyzer("go")
        analyzer2 = repo.get_dependency_analyzer("golang")

        from kit.dependency_analyzer.go_dependency_analyzer import GoDependencyAnalyzer

        assert isinstance(analyzer1, GoDependencyAnalyzer)
        assert isinstance(analyzer2, GoDependencyAnalyzer)
