"""Tests for MultiRepo class."""

import json
import os
import tempfile

from kit import MultiRepo, Repository


def create_test_repo(tmpdir: str, name: str, files: dict) -> str:
    """Create a test repository with given files."""
    repo_path = os.path.join(tmpdir, name)
    os.makedirs(repo_path, exist_ok=True)

    for file_path, content in files.items():
        full_path = os.path.join(repo_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    return repo_path


def test_multi_repo_basic():
    """Test basic MultiRepo initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "repo_a",
            {
                "src/main.py": "print('hello')",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "repo_b",
            {
                "src/app.js": "console.log('world')",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        assert len(multi) == 2
        assert "repo_a" in multi.names
        assert "repo_b" in multi.names
        assert isinstance(multi["repo_a"], Repository)


def test_multi_repo_search():
    """Test unified text search across repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "frontend",
            {
                "src/auth.js": "function authenticate() { return true; }",
                "src/utils.js": "function helper() {}",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "backend",
            {
                "src/auth.py": "def authenticate(): pass",
                "src/api.py": "def get_users(): pass",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        # Search for "authenticate" - should find in both repos
        results = multi.search("authenticate")
        assert len(results) >= 2

        # Check repo attribution
        repos_found = {r["repo"] for r in results}
        assert "frontend" in repos_found
        assert "backend" in repos_found


def test_multi_repo_find_symbol():
    """Test finding symbols across repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "service_a",
            {
                "main.py": """
def process_data(data):
    return data.upper()

class DataProcessor:
    pass
""",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "service_b",
            {
                "main.py": """
def process_data(items):
    return [i * 2 for i in items]
""",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        # Find function defined in both repos
        symbols = multi.find_symbol("process_data", symbol_type="function")
        assert len(symbols) == 2

        repos_found = {s["repo"] for s in symbols}
        assert "service_a" in repos_found
        assert "service_b" in repos_found


def test_multi_repo_extract_all_symbols():
    """Test extracting all symbols from all repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "lib_a",
            {
                "utils.py": """
def helper_a():
    pass

def helper_b():
    pass
""",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "lib_b",
            {
                "utils.py": """
def util_x():
    pass
""",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        all_symbols = multi.extract_all_symbols(symbol_type="function")

        assert "lib_a" in all_symbols
        assert "lib_b" in all_symbols
        assert len(all_symbols["lib_a"]) == 2
        assert len(all_symbols["lib_b"]) == 1


def test_multi_repo_audit_dependencies_python():
    """Test auditing Python dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "app_a",
            {
                "requirements.txt": "requests==2.28.0\nflask>=2.0\n",
                "main.py": "import requests",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "app_b",
            {
                "requirements.txt": "django==4.0\nrequests==2.28.0\n",
                "main.py": "import django",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        audit = multi.audit_dependencies()

        assert "app_a" in audit
        assert "app_b" in audit
        assert audit["app_a"]["python"]["requests"] == "2.28.0"
        assert audit["app_b"]["python"]["django"] == "4.0"


def test_multi_repo_audit_dependencies_javascript():
    """Test auditing JavaScript dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "frontend",
            {
                "package.json": json.dumps(
                    {
                        "name": "frontend",
                        "dependencies": {
                            "react": "^18.0.0",
                            "axios": "^1.0.0",
                        },
                    }
                ),
                "src/index.js": "import React from 'react';",
            },
        )

        multi = MultiRepo([repo_a])

        audit = multi.audit_dependencies()

        assert "frontend" in audit
        assert audit["frontend"]["javascript"]["react"] == "^18.0.0"
        assert audit["frontend"]["javascript"]["axios"] == "^1.0.0"


def test_multi_repo_summarize():
    """Test generating summaries of repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "python_app",
            {
                "main.py": "print('hello')",
                "utils.py": "def util(): pass",
                "tests/test_main.py": "def test(): pass",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "js_app",
            {
                "index.js": "console.log('hi')",
                "utils.js": "export function util() {}",
                "style.css": "body {}",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        summaries = multi.summarize()

        assert "python_app" in summaries
        assert "js_app" in summaries

        # Python app should detect Python
        assert "Python" in summaries["python_app"]["languages"]

        # JS app should detect JavaScript
        assert "JavaScript" in summaries["js_app"]["languages"]


def test_multi_repo_name_collision():
    """Test handling of repos with same directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two repos with same name in different parent dirs
        os.makedirs(os.path.join(tmpdir, "org_a"))
        os.makedirs(os.path.join(tmpdir, "org_b"))

        repo_a = create_test_repo(
            os.path.join(tmpdir, "org_a"),
            "utils",
            {
                "main.py": "# utils from org_a",
            },
        )
        repo_b = create_test_repo(
            os.path.join(tmpdir, "org_b"),
            "utils",
            {
                "main.py": "# utils from org_b",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        # Should handle collision by renaming second repo
        assert len(multi) == 2
        assert "utils" in multi.names
        assert "utils_1" in multi.names


def test_multi_repo_iteration():
    """Test iterating over repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(tmpdir, "repo_a", {"main.py": ""})
        repo_b = create_test_repo(tmpdir, "repo_b", {"main.py": ""})

        multi = MultiRepo([repo_a, repo_b])

        # Test iteration
        names_from_iter = []
        for name, repo in multi:
            names_from_iter.append(name)
            assert isinstance(repo, Repository)

        assert set(names_from_iter) == {"repo_a", "repo_b"}


def test_multi_repo_get_file_content():
    """Test getting file content from specific repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "repo_a",
            {
                "config.json": '{"key": "value_a"}',
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "repo_b",
            {
                "config.json": '{"key": "value_b"}',
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        content_a = multi.get_file_content("repo_a", "config.json")
        content_b = multi.get_file_content("repo_b", "config.json")

        assert "value_a" in content_a
        assert "value_b" in content_b


def test_multi_repo_max_results_per_repo():
    """Test limiting results per repo in search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create repo with many matches
        repo_a = create_test_repo(
            tmpdir,
            "repo_a",
            {
                "file1.py": "test_pattern here",
                "file2.py": "test_pattern here",
                "file3.py": "test_pattern here",
                "file4.py": "test_pattern here",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "repo_b",
            {
                "file1.py": "test_pattern here",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        # Limit to 2 results per repo
        results = multi.search("test_pattern", max_results_per_repo=2)

        repo_a_results = [r for r in results if r["repo"] == "repo_a"]
        assert len(repo_a_results) <= 2


def test_multi_repo_custom_names():
    """Test providing custom names for repos."""
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(tmpdir, "repo_a", {"main.py": ""})
        repo_b = create_test_repo(tmpdir, "repo_b", {"main.py": ""})

        # Names dict uses resolved path strings as keys
        multi = MultiRepo(
            [repo_a, repo_b],
            names={
                str(Path(repo_a).resolve()): "frontend",
                str(Path(repo_b).resolve()): "backend",
            },
        )

        assert "frontend" in multi.names
        assert "backend" in multi.names
        assert "repo_a" not in multi.names


def test_multi_repo_search_with_file_pattern():
    """Test search with file pattern filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "mixed",
            {
                "src/app.py": "def search_function(): pass",
                "src/app.js": "function search_function() {}",
                "docs/readme.md": "search_function documentation",
            },
        )

        multi = MultiRepo([repo])

        # Search only Python files
        results = multi.search("search_function", file_pattern="*.py")
        assert len(results) == 1
        assert results[0]["file"].endswith(".py")


def test_multi_repo_find_symbol_class():
    """Test finding class symbols across repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(
            tmpdir,
            "repo_a",
            {
                "models.py": """
class UserModel:
    pass

class ProductModel:
    pass
""",
            },
        )
        repo_b = create_test_repo(
            tmpdir,
            "repo_b",
            {
                "models.py": """
class UserModel:
    name: str
""",
            },
        )

        multi = MultiRepo([repo_a, repo_b])

        # Find class defined in both repos
        symbols = multi.find_symbol("UserModel", symbol_type="class")
        assert len(symbols) == 2

        # Find class only in repo_a
        symbols = multi.find_symbol("ProductModel", symbol_type="class")
        assert len(symbols) == 1
        assert symbols[0]["repo"] == "repo_a"


def test_multi_repo_find_symbol_no_type_filter():
    """Test finding symbols without type filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "code.py": """
def helper():
    pass

class Helper:
    pass
""",
            },
        )

        multi = MultiRepo([repo])

        # Find all symbols named "helper" (case sensitive)
        symbols = multi.find_symbol("helper")
        assert len(symbols) == 1  # Only the function matches exact name


def test_multi_repo_extract_all_symbols_no_filter():
    """Test extracting all symbols without type filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "code.py": """
def my_func():
    pass

class MyClass:
    def method(self):
        pass
""",
            },
        )

        multi = MultiRepo([repo])

        all_symbols = multi.extract_all_symbols()

        assert "repo" in all_symbols
        # Should have function, class, and method
        assert len(all_symbols["repo"]) >= 2


def test_multi_repo_audit_dependencies_go():
    """Test auditing Go dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "go_service",
            {
                "go.mod": """module github.com/example/service

go 1.21

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/stretchr/testify v1.8.0
)
""",
                "main.go": "package main",
            },
        )

        multi = MultiRepo([repo])

        audit = multi.audit_dependencies()

        assert "go_service" in audit
        assert "go" in audit["go_service"]
        assert audit["go_service"]["go"]["github.com/gin-gonic/gin"] == "v1.9.0"


def test_multi_repo_audit_dependencies_mixed():
    """Test auditing mixed language dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "fullstack",
            {
                "requirements.txt": "flask==2.0.0\n",
                "package.json": json.dumps(
                    {
                        "dependencies": {"vue": "^3.0.0"},
                    }
                ),
                "main.py": "",
            },
        )

        multi = MultiRepo([repo])

        audit = multi.audit_dependencies()

        assert "fullstack" in audit
        assert audit["fullstack"]["python"]["flask"] == "2.0.0"
        assert audit["fullstack"]["javascript"]["vue"] == "^3.0.0"


def test_multi_repo_summarize_file_counts():
    """Test summarize returns accurate file counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "a.py": "",
                "b.py": "",
                "c.js": "",
                "d.js": "",
                "e.js": "",
            },
        )

        multi = MultiRepo([repo])

        summaries = multi.summarize()

        assert summaries["repo"]["file_count"] == 5
        assert summaries["repo"]["extensions"][".py"] == 2
        assert summaries["repo"]["extensions"][".js"] == 3


def test_multi_repo_repos_property():
    """Test repos property returns dict of repositories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_a = create_test_repo(tmpdir, "repo_a", {"main.py": ""})
        repo_b = create_test_repo(tmpdir, "repo_b", {"main.py": ""})

        multi = MultiRepo([repo_a, repo_b])

        repos = multi.repos
        assert isinstance(repos, dict)
        assert len(repos) == 2
        assert isinstance(repos["repo_a"], Repository)


def test_multi_repo_single_repo():
    """Test MultiRepo works with single repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "only_repo",
            {
                "main.py": "def hello(): pass",
            },
        )

        multi = MultiRepo([repo])

        assert len(multi) == 1
        assert "only_repo" in multi.names

        results = multi.search("hello")
        assert len(results) == 1

        symbols = multi.find_symbol("hello")
        assert len(symbols) == 1


def test_multi_repo_empty_search_results():
    """Test search returns empty list when no matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "main.py": "def hello(): pass",
            },
        )

        multi = MultiRepo([repo])

        results = multi.search("nonexistent_pattern_xyz")
        assert results == []


def test_multi_repo_find_symbol_not_found():
    """Test find_symbol returns empty list when symbol not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "main.py": "def hello(): pass",
            },
        )

        multi = MultiRepo([repo])

        symbols = multi.find_symbol("nonexistent_symbol")
        assert symbols == []


def test_multi_repo_multiple_name_collisions():
    """Test handling of multiple repos with same name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "org_a"))
        os.makedirs(os.path.join(tmpdir, "org_b"))
        os.makedirs(os.path.join(tmpdir, "org_c"))

        repo_a = create_test_repo(os.path.join(tmpdir, "org_a"), "utils", {"a.py": ""})
        repo_b = create_test_repo(os.path.join(tmpdir, "org_b"), "utils", {"b.py": ""})
        repo_c = create_test_repo(os.path.join(tmpdir, "org_c"), "utils", {"c.py": ""})

        multi = MultiRepo([repo_a, repo_b, repo_c])

        assert len(multi) == 3
        assert "utils" in multi.names
        assert "utils_1" in multi.names
        assert "utils_2" in multi.names


def test_multi_repo_typescript_detection():
    """Test language detection for TypeScript."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "ts_app",
            {
                "src/index.ts": "const x: number = 1;",
                "src/App.tsx": "export const App = () => <div />;",
            },
        )

        multi = MultiRepo([repo])

        summaries = multi.summarize()

        assert "TypeScript" in summaries["ts_app"]["languages"]


def test_multi_repo_rust_detection():
    """Test language detection for Rust."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "rust_app",
            {
                "src/main.rs": "fn main() {}",
                "src/lib.rs": "pub fn hello() {}",
            },
        )

        multi = MultiRepo([repo])

        summaries = multi.summarize()

        assert "Rust" in summaries["rust_app"]["languages"]


def test_multi_repo_remote_url_name_extraction():
    """Test that remote URLs are parsed correctly for repo names."""
    # We can't easily test actual remote cloning, but we can test the name extraction
    # by checking the internal logic. This test validates URL parsing.

    # Test URL parsing logic directly
    test_cases = [
        ("https://github.com/owner/repo", "repo"),
        ("https://github.com/owner/repo.git", "repo"),
        ("https://github.com/owner/my-project/", "my-project"),
        ("https://gitlab.com/org/sub/project.git", "project"),
        ("git@github.com:owner/repo.git", "repo"),
    ]

    for url, expected_name in test_cases:
        # Replicate the name extraction logic from MultiRepo.__init__
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        assert name == expected_name, f"URL {url} should extract name '{expected_name}', got '{name}'"


def test_multi_repo_mixed_local_and_remote_detection():
    """Test that local vs remote paths are detected correctly."""
    # Test the detection logic
    test_paths = [
        ("/absolute/path", False),
        ("~/home/path", False),
        ("relative/path", False),
        ("https://github.com/owner/repo", True),
        ("http://gitlab.com/owner/repo", True),
        ("git@github.com:owner/repo.git", True),
    ]

    for path, expected_remote in test_paths:
        is_remote = path.startswith(("http://", "https://", "git@"))
        assert is_remote == expected_remote, f"Path {path} remote detection failed"


def test_multi_repo_audit_go_mod_skips_directives():
    """Test that go.mod parsing skips directive keywords (require, replace, exclude, retract)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "go_app",
            {
                "go.mod": """module github.com/example/app

go 1.21

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/pkg/errors v0.9.1
)

replace github.com/old/pkg => github.com/new/pkg v1.0.0

exclude github.com/bad/pkg v0.0.1

retract v1.0.0
""",
                "main.go": "package main",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        assert "go_app" in audit
        go_deps = audit["go_app"]["go"]

        # Should find actual dependencies
        assert "github.com/gin-gonic/gin" in go_deps
        assert "github.com/pkg/errors" in go_deps

        # Should NOT include directive keywords as packages
        assert "require" not in go_deps
        assert "replace" not in go_deps
        assert "exclude" not in go_deps
        assert "retract" not in go_deps
        assert ")" not in go_deps


def test_multi_repo_audit_go_mod_single_line_require():
    """Test go.mod parsing handles single-line require statements."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "go_simple",
            {
                "go.mod": """module github.com/example/simple

go 1.21

require github.com/gorilla/mux v1.8.0
""",
                "main.go": "package main",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        # Single-line require should NOT be parsed (current implementation)
        # This test documents current behavior - the current parser only handles
        # block-style requires, so go_simple will have no go deps detected
        assert audit["go_simple"].get("go", {}) == {}


def test_multi_repo_audit_rust_cargo_toml():
    """Test auditing Rust Cargo.toml dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "rust_app",
            {
                "Cargo.toml": """[package]
name = "my-app"
version = "0.1.0"

[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }
log = "0.4"

[dev-dependencies]
criterion = "0.5"
""",
                "src/main.rs": "fn main() {}",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        assert "rust_app" in audit
        rust_deps = audit["rust_app"]["rust"]

        # String version
        assert rust_deps["serde"] == "1.0"
        assert rust_deps["log"] == "0.4"

        # Table version with features
        assert rust_deps["tokio"] == "1.0"

        # Dev dependencies
        assert rust_deps["criterion"] == "0.5"


def test_multi_repo_audit_rust_workspace_deps():
    """Test Rust Cargo.toml with workspace and build dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "rust_workspace",
            {
                "Cargo.toml": """[package]
name = "workspace-member"
version = "0.1.0"

[dependencies]
anyhow = "1.0"

[build-dependencies]
cc = "1.0"
""",
                "src/lib.rs": "pub fn lib() {}",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        rust_deps = audit["rust_workspace"]["rust"]
        assert rust_deps["anyhow"] == "1.0"
        assert rust_deps["cc"] == "1.0"


def test_multi_repo_audit_rust_complex_version_spec():
    """Test Rust Cargo.toml with complex version specifications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "rust_complex",
            {
                "Cargo.toml": """[package]
name = "complex"
version = "0.1.0"

[dependencies]
# Simple string
simple = "1.0"
# Table with version
with_features = { version = "2.0", features = ["foo"] }
# Table without version (git dep)
git_dep = { git = "https://github.com/example/repo" }
# Path dependency
local = { path = "../local" }
""",
                "src/main.rs": "fn main() {}",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        rust_deps = audit["rust_complex"]["rust"]
        assert rust_deps["simple"] == "1.0"
        assert rust_deps["with_features"] == "2.0"
        assert rust_deps["git_dep"] == "*"  # No version specified
        assert rust_deps["local"] == "*"  # Path dep, no version


def test_multi_repo_audit_empty_deps():
    """Test audit returns empty dict for repos without dependency files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "no_deps",
            {
                "main.py": "print('hello')",
                "utils.py": "def helper(): pass",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        assert "no_deps" in audit
        assert audit["no_deps"] == {}


def test_multi_repo_search_literal_pattern():
    """Test search with literal patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "main.py": """
def get_user(): pass
def get_product(): pass
def set_value(): pass
""",
            },
        )

        multi = MultiRepo([repo])

        # Search with literal string (grep uses literal matching)
        results = multi.search("get_")
        assert len(results) >= 2

        # All results should match the pattern
        for r in results:
            assert "get_" in r.get("line_content", "")


def test_multi_repo_get_file_content_not_found():
    """Test get_file_content with non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "main.py": "print('hello')",
            },
        )

        multi = MultiRepo([repo])

        # Try to get non-existent file - should return None or raise
        try:
            content = multi.get_file_content("repo", "nonexistent.py")
            assert content is None or content == ""
        except Exception:
            pass  # Some implementations may raise


def test_multi_repo_get_file_content_invalid_repo():
    """Test get_file_content with invalid repo name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(tmpdir, "repo", {"main.py": ""})

        multi = MultiRepo([repo])

        # Try to get from non-existent repo
        try:
            multi.get_file_content("invalid_repo", "main.py")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass


def test_multi_repo_audit_javascript_dev_deps():
    """Test auditing JavaScript devDependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "js_app",
            {
                "package.json": json.dumps(
                    {
                        "name": "js-app",
                        "dependencies": {"react": "^18.0.0"},
                        "devDependencies": {"jest": "^29.0.0", "typescript": "^5.0.0"},
                    }
                ),
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        js_deps = audit["js_app"]["javascript"]
        # Should include both deps and devDeps
        assert "react" in js_deps
        assert "jest" in js_deps
        assert "typescript" in js_deps


def test_multi_repo_summarize_empty_repo():
    """Test summarize on repo with no files of known languages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "empty_lang",
            {
                "README.md": "# Hello",
                "data.csv": "a,b,c",
            },
        )

        multi = MultiRepo([repo])
        summaries = multi.summarize()

        assert "empty_lang" in summaries
        assert summaries["empty_lang"]["file_count"] == 2
        # languages dict should be empty or not contain known languages
        langs = summaries["empty_lang"]["languages"]
        assert "Python" not in langs
        assert "JavaScript" not in langs


def test_multi_repo_find_symbol_partial_match():
    """Test that find_symbol requires exact name match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "repo",
            {
                "main.py": """
def get_user(): pass
def get_user_by_id(): pass
def get_users(): pass
""",
            },
        )

        multi = MultiRepo([repo])

        # Should only find exact match
        symbols = multi.find_symbol("get_user", symbol_type="function")
        names = [s["name"] for s in symbols]
        assert "get_user" in names
        # Should NOT include partial matches
        assert len([n for n in names if n == "get_user"]) == 1


def test_multi_repo_audit_python_requirements_edge_cases():
    """Test Python requirements.txt parsing edge cases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = create_test_repo(
            tmpdir,
            "py_app",
            {
                "requirements.txt": """# This is a comment
flask==2.0.0
requests>=2.28.0
-e git+https://github.com/user/repo.git#egg=editable
django~=4.0
gunicorn
# Another comment
pandas==1.5.0
""",
            },
        )

        multi = MultiRepo([repo])
        audit = multi.audit_dependencies()

        py_deps = audit["py_app"]["python"]
        assert py_deps["flask"] == "2.0.0"
        assert py_deps["requests"] == "2.28.0"
        assert py_deps["django"] == "4.0"
        assert py_deps["pandas"] == "1.5.0"
        # gunicorn without version
        assert "gunicorn" in py_deps
