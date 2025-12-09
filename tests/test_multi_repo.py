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
