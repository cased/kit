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


def test_go_dependency_analyzer_multiple_files_same_package():
    """Test handling of multiple files in the same package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/multifile\n\ngo 1.21\n")

        os.makedirs(f"{tmpdir}/pkg/utils")

        # Multiple files in same package with different imports
        with open(f"{tmpdir}/pkg/utils/strings.go", "w") as f:
            f.write("""package utils

import "strings"

func ToUpper(s string) string {
	return strings.ToUpper(s)
}
""")

        with open(f"{tmpdir}/pkg/utils/numbers.go", "w") as f:
            f.write("""package utils

import "strconv"

func ParseInt(s string) int {
	i, _ := strconv.Atoi(s)
	return i
}
""")

        with open(f"{tmpdir}/pkg/utils/format.go", "w") as f:
            f.write("""package utils

import "fmt"

func Format(v interface{}) string {
	return fmt.Sprintf("%v", v)
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # All imports from different files should be aggregated
        utils_deps = graph["github.com/example/multifile/pkg/utils"]["dependencies"]
        assert "strings" in utils_deps
        assert "strconv" in utils_deps
        assert "fmt" in utils_deps


def test_go_dependency_analyzer_excludes_test_files():
    """Test that _test.go files are excluded from production dependency analysis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/testfiles\n\ngo 1.21\n")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "fmt"

func Hello() string {
	return "hello"
}

func main() {
	fmt.Println(Hello())
}
""")

        with open(f"{tmpdir}/main_test.go", "w") as f:
            f.write("""package main

import "testing"

func TestHello(t *testing.T) {
	if Hello() != "hello" {
		t.Error("unexpected result")
	}
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # Test files are excluded from analysis (production deps only)
        # So "testing" package should NOT be in the graph
        assert "testing" not in graph
        # Only fmt should be in dependencies (from main.go)
        main_deps = graph["github.com/example/testfiles"]["dependencies"]
        assert "fmt" in main_deps


def test_go_dependency_analyzer_vendor_directory():
    """Test that vendor directory is handled appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/vendored\n\ngo 1.21\n")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "github.com/pkg/errors"

func main() {
	_ = errors.New("test")
}
""")

        # Create vendor directory with vendored package
        os.makedirs(f"{tmpdir}/vendor/github.com/pkg/errors")
        with open(f"{tmpdir}/vendor/github.com/pkg/errors/errors.go", "w") as f:
            f.write("""package errors

func New(text string) error {
	return nil
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # External package should still be detected
        assert "github.com/pkg/errors" in graph


def test_go_dependency_analyzer_nested_packages():
    """Test deeply nested package structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/nested\n\ngo 1.21\n")

        # Create deeply nested package structure
        os.makedirs(f"{tmpdir}/pkg/api/v1/handlers/user")

        with open(f"{tmpdir}/pkg/api/v1/handlers/user/user.go", "w") as f:
            f.write("""package user

import "net/http"

func GetUser(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("user"))
}
""")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "github.com/example/nested/pkg/api/v1/handlers/user"

func main() {
	_ = user.GetUser
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # Deeply nested package should be detected
        assert "github.com/example/nested/pkg/api/v1/handlers/user" in graph
        main_deps = graph["github.com/example/nested"]["dependencies"]
        assert "github.com/example/nested/pkg/api/v1/handlers/user" in main_deps


def test_go_dependency_analyzer_empty_package():
    """Test handling of package with no imports that is imported by another."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/empty\n\ngo 1.21\n")

        os.makedirs(f"{tmpdir}/pkg/constants")
        with open(f"{tmpdir}/pkg/constants/constants.go", "w") as f:
            f.write("""package constants

const (
	MaxSize = 100
	MinSize = 1
)
""")

        # Main package that imports the constants package
        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import "github.com/example/empty/pkg/constants"

func main() {
	_ = constants.MaxSize
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # Package with no imports should be in graph (as it's imported by main)
        assert "github.com/example/empty/pkg/constants" in graph
        # Dependencies can be a list or set depending on implementation
        deps = graph["github.com/example/empty/pkg/constants"]["dependencies"]
        assert len(deps) == 0


def test_go_dependency_analyzer_comment_in_imports():
    """Test handling of comments in import blocks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/comments\n\ngo 1.21\n")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	// Standard library
	"fmt"
	"os"

	// Third party
	// "github.com/pkg/errors" // disabled for now
)

func main() {
	fmt.Println(os.Args)
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # Only non-commented imports should be detected
        main_deps = graph["github.com/example/comments"]["dependencies"]
        assert "fmt" in main_deps
        assert "os" in main_deps
        # Commented import should not be detected
        assert "github.com/pkg/errors" not in graph


def test_go_dependency_analyzer_graph_dependencies_field():
    """Test that dependencies field in graph contains correct data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/getdeps\n\ngo 1.21\n")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	"fmt"
	"os"
	"strings"
)

func main() {
	fmt.Println(strings.ToUpper(os.Args[0]))
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # Access dependencies directly from the graph
        deps = graph["github.com/example/getdeps"]["dependencies"]

        assert "fmt" in deps
        assert "os" in deps
        assert "strings" in deps


def test_go_dependency_analyzer_stdlib_subpackages():
    """Test detection of stdlib subpackages like net/http, encoding/json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/go.mod", "w") as f:
            f.write("module github.com/example/stdlib\n\ngo 1.21\n")

        with open(f"{tmpdir}/main.go", "w") as f:
            f.write("""package main

import (
	"encoding/json"
	"net/http"
	"path/filepath"
	"database/sql"
)

func main() {
	_ = json.Marshal
	_ = http.Get
	_ = filepath.Join
	_ = sql.Open
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("go")
        graph = analyzer.build_dependency_graph()

        # All stdlib subpackages should be detected as stdlib
        assert graph["encoding/json"]["type"] == "stdlib"
        assert graph["net/http"]["type"] == "stdlib"
        assert graph["path/filepath"]["type"] == "stdlib"
        assert graph["database/sql"]["type"] == "stdlib"
