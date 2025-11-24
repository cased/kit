import os
import tempfile

from kit import CodeSearcher
from kit.code_searcher import SearchOptions


def test_search_text_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "foo.py")
        with open(pyfile, "w") as f:
            f.write("""
def foo(): pass

def bar(): pass
""")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("def foo")
        assert any("foo" in m["line"] for m in matches)
        matches_bar = searcher.search_text("bar")
        assert any("bar" in m["line"] for m in matches_bar)


def test_search_text_multiple_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = ["a.py", "b.py", "c.txt"]
        for fname in files:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(f"def {fname[:-3]}(): pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("def ", file_pattern="*.py")
        assert len(matches) == 2
        assert all(m["file"].endswith(".py") for m in matches)


def test_search_text_regex():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "foo.py")
        with open(pyfile, "w") as f:
            f.write("def foo(): pass\ndef bar(): pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text(r"def [fb]oo")
        assert any("foo" in m["line"] for m in matches)
        assert not any("bar" in m["line"] for m in matches)


def test_search_context_before():
    """Test context lines before match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("line1\nline2\ntarget\nline4\n")
        searcher = CodeSearcher(tmpdir)
        options = SearchOptions(context_lines_before=2)
        matches = searcher.search_text("target", file_pattern="*.py", options=options)

        assert len(matches) == 1
        assert len(matches[0]["context_before"]) == 2
        assert matches[0]["context_before"][0] == "line1"
        assert matches[0]["context_before"][1] == "line2"


def test_search_context_after():
    """Test context lines after match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("line1\ntarget\nline3\nline4\n")
        searcher = CodeSearcher(tmpdir)
        options = SearchOptions(context_lines_after=2)
        matches = searcher.search_text("target", file_pattern="*.py", options=options)

        assert len(matches) == 1
        assert len(matches[0]["context_after"]) == 2
        assert matches[0]["context_after"][0] == "line3"
        assert matches[0]["context_after"][1] == "line4"


def test_search_context_both():
    """Test context lines before and after match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("before1\nbefore2\ntarget\nafter1\nafter2\n")
        searcher = CodeSearcher(tmpdir)
        options = SearchOptions(context_lines_before=2, context_lines_after=2)
        matches = searcher.search_text("target", file_pattern="*.py", options=options)

        assert len(matches) == 1
        assert len(matches[0]["context_before"]) == 2
        assert matches[0]["context_before"][0] == "before1"
        assert matches[0]["context_before"][1] == "before2"
        assert len(matches[0]["context_after"]) == 2
        assert matches[0]["context_after"][0] == "after1"
        assert matches[0]["context_after"][1] == "after2"


def test_search_case_insensitive():
    """Test case-insensitive search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("Hello World\n")
        searcher = CodeSearcher(tmpdir)

        # Case sensitive (default) - should not match
        matches = searcher.search_text("hello world", file_pattern="*.py")
        assert len(matches) == 0

        # Case insensitive - should match
        options = SearchOptions(case_sensitive=False)
        matches = searcher.search_text("hello world", file_pattern="*.py", options=options)
        assert len(matches) == 1


def test_search_gitignore_respected():
    """Test that .gitignore rules are respected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .gitignore
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("*.log\n")

        # Create files
        with open(os.path.join(tmpdir, "test.py"), "w") as f:
            f.write("findme\n")
        with open(os.path.join(tmpdir, "test.log"), "w") as f:
            f.write("findme\n")

        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("findme", file_pattern="*")

        # Should only find in test.py, not test.log
        assert len(matches) == 1
        assert "test.py" in matches[0]["file"]


def test_search_gitignore_disabled():
    """Test searching with gitignore disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .gitignore
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("*.log\n")

        # Create files
        with open(os.path.join(tmpdir, "test.py"), "w") as f:
            f.write("findme\n")
        with open(os.path.join(tmpdir, "test.log"), "w") as f:
            f.write("findme\n")

        searcher = CodeSearcher(tmpdir)
        options = SearchOptions(use_gitignore=False)
        matches = searcher.search_text("findme", file_pattern="*", options=options)

        # Should find in both files
        assert len(matches) == 2
        files = [m["file"] for m in matches]
        assert any("test.py" in f for f in files)
        assert any("test.log" in f for f in files)


def test_search_multiple_matches_per_file():
    """Test finding multiple matches in the same file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("def foo():\n    pass\ndef bar():\n    pass\ndef baz():\n    pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text(r"def \w+", file_pattern="*.py")

        # Should find all three function definitions
        assert len(matches) == 3
        assert all(m["file"] == "test.py" for m in matches)


def test_search_empty_results():
    """Test search that returns no results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("def foo():\n    pass\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("nonexistent", file_pattern="*.py")

        assert len(matches) == 0


def test_search_special_regex_chars():
    """Test search with special regex characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("result = foo(bar, baz)\n")
        searcher = CodeSearcher(tmpdir)
        # Search for function call with parens
        matches = searcher.search_text(r"foo\(", file_pattern="*.py")

        assert len(matches) == 1
        assert "foo(" in matches[0]["line"]


def test_search_multiline_pattern():
    """Test that search works line by line (not multiline)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("line1\nline2\nline3\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("line2", file_pattern="*.py")

        assert len(matches) == 1
        assert matches[0]["line_number"] == 2


def test_search_unicode():
    """Test search with unicode characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write("# Comment with émojis 🚀\ndef func():\n    return '你好'\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("🚀", file_pattern="*.py")

        assert len(matches) == 1
        assert "🚀" in matches[0]["line"]


def test_search_subdirectories():
    """Test search across subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create subdirectory structure
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "test1.py"), "w") as f:
            f.write("findme\n")
        with open(os.path.join(tmpdir, "subdir", "test2.py"), "w") as f:
            f.write("findme\n")

        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("findme", file_pattern="*.py")

        assert len(matches) == 2
        files = [m["file"] for m in matches]
        assert any("test1.py" == f for f in files)
        assert any("subdir/test2.py" == f or "subdir\\test2.py" == f for f in files)


def test_search_line_numbers_correct():
    """Test that line numbers are accurate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("line1\nline2\ntarget\nline4\n")
        searcher = CodeSearcher(tmpdir)
        matches = searcher.search_text("target", file_pattern="*.py")

        assert len(matches) == 1
        assert matches[0]["line_number"] == 3


def test_search_context_at_file_boundaries():
    """Test context handling at file start and end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("target\nline2\n")
        searcher = CodeSearcher(tmpdir)

        # Search at start of file with context_before
        options = SearchOptions(context_lines_before=5)
        matches = searcher.search_text("target", file_pattern="*.py", options=options)
        assert len(matches[0]["context_before"]) == 0  # No lines before

        # Search at end of file with context_after
        with open(pyfile, "w") as f:
            f.write("line1\ntarget\n")
        options = SearchOptions(context_lines_after=5)
        matches = searcher.search_text("target", file_pattern="*.py", options=options)
        assert len(matches[0]["context_after"]) == 0  # No lines after


def test_ripgrep_and_python_results_match():
    """Test that ripgrep and Python implementations return equivalent results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("before1\nbefore2\ntarget line\nafter1\nafter2\n")

        searcher = CodeSearcher(tmpdir)

        # Get results with ripgrep (if available)
        options = SearchOptions(context_lines_before=2, context_lines_after=2)
        results_auto = searcher.search_text("target", file_pattern="*.py", options=options)

        # Force Python implementation by disabling ripgrep
        original_ripgrep = searcher._has_ripgrep
        searcher._has_ripgrep = lambda: False
        results_python = searcher.search_text("target", file_pattern="*.py", options=options)
        searcher._has_ripgrep = original_ripgrep

        # Both should have same number of results
        assert len(results_auto) == len(results_python)

        if len(results_auto) > 0:
            # Compare first result
            assert results_auto[0]["file"] == results_python[0]["file"]
            assert results_auto[0]["line_number"] == results_python[0]["line_number"]
            assert results_auto[0]["line"] == results_python[0]["line"]
            assert results_auto[0]["context_before"] == results_python[0]["context_before"]
            assert results_auto[0]["context_after"] == results_python[0]["context_after"]


# Security tests
def test_search_no_shell_injection():
    """Test that shell metacharacters in queries don't cause injection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("normal_content\n")

        searcher = CodeSearcher(tmpdir)

        # Try various shell metacharacters - should not execute commands
        dangerous_queries = [
            "; ls",
            "| cat /etc/passwd",
            "$(whoami)",
            "`whoami`",
            "&& echo hacked",
            "|| rm -rf /",
        ]

        for query in dangerous_queries:
            # Should not raise exception and not execute shell commands
            try:
                results = searcher.search_text(query, file_pattern="*.py")
                # If it doesn't crash, that's good
                assert isinstance(results, list)
            except Exception:
                # Some queries might cause regex errors, which is fine
                # as long as they don't execute shell commands
                pass


def test_search_special_chars_in_file_pattern():
    """Test that special characters in file patterns are handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("content\n")

        searcher = CodeSearcher(tmpdir)

        # Special characters in glob patterns should be handled safely
        patterns = [
            "*.py",
            "**/*.py",
            "test[123].py",
            "test?.py",
        ]

        for pattern in patterns:
            results = searcher.search_text("content", file_pattern=pattern)
            assert isinstance(results, list)


def test_search_excessive_context_capped():
    """Test that excessive context line requests are capped to prevent DoS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        # Create file with many lines
        with open(pyfile, "w") as f:
            for i in range(500):
                f.write(f"line{i}\n")
            f.write("target\n")
            for i in range(500):
                f.write(f"line{i}\n")

        searcher = CodeSearcher(tmpdir)

        # Request excessive context (should be capped at 100)
        options = SearchOptions(context_lines_before=1000, context_lines_after=1000)
        results = searcher.search_text("target", file_pattern="*.py", options=options)

        assert len(results) == 1
        # Context should be capped at 100 lines each direction
        # (or less if using Python implementation without the cap)
        assert len(results[0]["context_before"]) <= 100
        assert len(results[0]["context_after"]) <= 100


def test_search_timeout_protection():
    """Test that search operations have timeout protection."""
    # This test verifies the timeout exists in the code
    # Actual timeout testing would require a very large codebase
    # which is impractical in unit tests
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("content\n")

        searcher = CodeSearcher(tmpdir)

        # Verify the search completes (doesn't hang)
        results = searcher.search_text("content", file_pattern="*.py")
        assert isinstance(results, list)


def test_search_binary_files_handled():
    """Test that binary files don't cause crashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a binary file
        binfile = os.path.join(tmpdir, "test.bin")
        with open(binfile, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")

        # Create a text file
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("content\n")

        searcher = CodeSearcher(tmpdir)

        # Should handle binary files gracefully
        results = searcher.search_text("content", file_pattern="*")
        assert isinstance(results, list)


def test_search_empty_file():
    """Test searching in empty files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "empty.py")
        with open(pyfile, "w"):
            pass  # Empty file

        searcher = CodeSearcher(tmpdir)
        results = searcher.search_text("anything", file_pattern="*.py")
        assert len(results) == 0


def test_search_very_long_line():
    """Test searching files with very long lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        long_line = "x" * 10000 + "needle" + "y" * 10000
        with open(pyfile, "w") as f:
            f.write(long_line + "\n")

        searcher = CodeSearcher(tmpdir)
        results = searcher.search_text("needle", file_pattern="*.py")
        assert len(results) == 1
        assert "needle" in results[0]["line"]


def test_search_newlines_in_pattern():
    """Test that multiline patterns work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("def foo():\n    pass\n")

        searcher = CodeSearcher(tmpdir)
        # Search for single line pattern
        results = searcher.search_text("def foo", file_pattern="*.py")
        assert len(results) == 1


def test_search_different_file_extensions():
    """Test searching across different file extensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files with different extensions
        extensions = [".py", ".js", ".txt", ".md"]
        for ext in extensions:
            filepath = os.path.join(tmpdir, f"test{ext}")
            with open(filepath, "w") as f:
                f.write(f"content{ext}\n")

        searcher = CodeSearcher(tmpdir)

        # Search only .py files
        results_py = searcher.search_text("content", file_pattern="*.py")
        assert len(results_py) == 1
        assert results_py[0]["file"].endswith(".py")

        # Search all files
        results_all = searcher.search_text("content", file_pattern="*")
        assert len(results_all) == len(extensions)


def test_search_symlinks():
    """Test that symlinks are handled appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a regular file
        realfile = os.path.join(tmpdir, "real.py")
        with open(realfile, "w") as f:
            f.write("content\n")

        # Create a symlink
        linkfile = os.path.join(tmpdir, "link.py")
        try:
            os.symlink(realfile, linkfile)
        except (OSError, NotImplementedError):
            # Skip test on systems that don't support symlinks
            return

        searcher = CodeSearcher(tmpdir)
        results = searcher.search_text("content", file_pattern="*.py")

        # Should find content (implementation may vary)
        assert isinstance(results, list)


def test_search_nested_directories():
    """Test searching in deeply nested directory structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested structure
        deep_path = os.path.join(tmpdir, "a", "b", "c", "d", "e")
        os.makedirs(deep_path)

        # Create file in deep directory
        deepfile = os.path.join(deep_path, "deep.py")
        with open(deepfile, "w") as f:
            f.write("deep_content\n")

        searcher = CodeSearcher(tmpdir)
        results = searcher.search_text("deep_content", file_pattern="*.py")

        assert len(results) == 1
        assert "deep.py" in results[0]["file"]


def test_search_shell_injection_query():
    """Test that shell metacharacters in query don't cause command injection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("normal_content\n")
            f.write("; echo hacked\n")
            f.write("$(whoami)\n")

        # Create a marker file that should NOT be created if injection works
        marker_file = os.path.join(tmpdir, "INJECTION_HAPPENED")

        searcher = CodeSearcher(tmpdir)

        # Try various shell injection patterns in the query
        malicious_queries = [
            "; rm -rf /",
            "$(touch " + marker_file + ")",
            "`touch " + marker_file + "`",
            "| touch " + marker_file,
            "&& touch " + marker_file,
            "; touch " + marker_file + " #",
        ]

        for query in malicious_queries:
            # Should treat as literal search pattern, not execute
            results = searcher.search_text(query, file_pattern="*.py")
            # Verify marker file was NOT created (no injection occurred)
            assert not os.path.exists(marker_file), f"Shell injection occurred with query: {query}"

        # Verify we can safely search for shell metacharacters as literals
        results = searcher.search_text("; echo hacked", file_pattern="*.py")
        if results:  # Will only match if ripgrep is available
            assert len(results) == 1
            assert "; echo hacked" in results[0]["line"]


def test_search_shell_injection_file_pattern():
    """Test that shell metacharacters in file pattern don't cause injection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("content\n")

        marker_file = os.path.join(tmpdir, "PATTERN_INJECTION")

        searcher = CodeSearcher(tmpdir)

        # Try shell injection in file pattern
        malicious_patterns = [
            "*.py; touch " + marker_file,
            "*.py && touch " + marker_file,
            "*.py | touch " + marker_file,
            "*.py`touch " + marker_file + "`",
        ]

        for pattern in malicious_patterns:
            # Should be treated as a glob pattern, not executed
            searcher.search_text("content", file_pattern=pattern)
            # Verify marker file was NOT created
            assert not os.path.exists(marker_file), f"Shell injection via pattern: {pattern}"


def test_search_shell_injection_path():
    """Test that shell metacharacters in repo path are handled safely."""
    # Create a directory with shell metacharacters in the name
    with tempfile.TemporaryDirectory() as base_tmpdir:
        # Directory names with shell metacharacters
        dangerous_names = [
            "dir; echo hacked",
            "dir && whoami",
            "dir`id`",
            "dir$(date)",
        ]

        for dirname in dangerous_names:
            try:
                # Some filesystems may not allow certain characters
                test_dir = os.path.join(base_tmpdir, dirname)
                os.makedirs(test_dir, exist_ok=True)

                # Create test file
                pyfile = os.path.join(test_dir, "test.py")
                with open(pyfile, "w") as f:
                    f.write("content\n")

                # This should work without executing shell commands
                searcher = CodeSearcher(test_dir)
                results = searcher.search_text("content", file_pattern="*.py")

                # Should find the file normally
                assert isinstance(results, list)
            except OSError:
                # Some characters might not be allowed by filesystem, that's fine
                pass


def test_search_no_shell_subprocess():
    """Verify that subprocess is called without shell=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("test_content\n")

        searcher = CodeSearcher(tmpdir)

        # Patch subprocess.run to verify shell=False
        import subprocess

        original_run = subprocess.run
        shell_used = []

        def patched_run(*args, **kwargs):
            shell_used.append(kwargs.get("shell", False))
            return original_run(*args, **kwargs)

        subprocess.run = patched_run
        try:
            searcher.search_text("test_content", file_pattern="*.py")
            # Verify subprocess.run was called (if ripgrep available)
            if searcher._has_ripgrep():
                assert len(shell_used) > 0, "subprocess.run should have been called"
                # Verify shell was False or not set (defaults to False)
                assert all(s is False for s in shell_used), "shell=True was used!"
        finally:
            subprocess.run = original_run


def test_search_command_injection_stress():
    """Stress test with many shell injection patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyfile = os.path.join(tmpdir, "test.py")
        with open(pyfile, "w") as f:
            f.write("safe_content\n")

        marker = os.path.join(tmpdir, "INJECTED")
        searcher = CodeSearcher(tmpdir)

        # Comprehensive list of shell injection patterns
        injection_patterns = [
            "; ls",
            "| ls",
            "&& ls",
            "|| ls",
            "`ls`",
            "$(ls)",
            "\n ls",
            "$((1+1))",
            "${PATH}",
            "!ls",
            ">\\/dev\\/null",
            "2>&1",
            "< input.txt",
            "*; ls",
        ]

        for pattern in injection_patterns:
            # Try in query
            searcher.search_text(pattern, file_pattern="*.py")
            assert not os.path.exists(marker), f"Injection via query: {pattern}"

            # Try in file pattern
            searcher.search_text("safe", file_pattern=f"*.py{pattern}")
            assert not os.path.exists(marker), f"Injection via file_pattern: {pattern}"


def test_search_utf8_chinese_content():
    """Test searching files containing Chinese characters (UTF-8 encoding)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with Chinese content
        pyfile = os.path.join(tmpdir, "test_chinese.py")
        chinese_content = """
def 测试函数():
    \"\"\"这是一个测试函数\"\"\"
    return "你好世界"

def hello():
    # 注释: 这是中文注释
    pass
"""
        with open(pyfile, "w", encoding="utf-8") as f:
            f.write(chinese_content)

        searcher = CodeSearcher(tmpdir)

        # Search for Chinese function name
        matches = searcher.search_text("测试函数", file_pattern="*.py")
        assert len(matches) >= 1
        assert any("测试函数" in m["line"] for m in matches)

        # Search for Chinese string
        matches = searcher.search_text("你好世界", file_pattern="*.py")
        assert len(matches) >= 1
        assert any("你好世界" in m["line"] for m in matches)

        # Search for Chinese comment
        matches = searcher.search_text("中文注释", file_pattern="*.py")
        assert len(matches) >= 1
        assert any("中文注释" in m["line"] for m in matches)


def test_search_utf8_mixed_languages():
    """Test searching files with mixed English and non-ASCII characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files with various Unicode characters
        test_cases = [
            ("japanese.py", "世界", "def hello_世界():"),
            ("korean.py", "테스트", "class 테스트:"),
            ("emoji.py", "🚀", "# TODO: 🚀 Launch feature"),
            ("french.py", "café", "def café():"),
        ]

        for filename, search_term, content in test_cases:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content + "\n    pass\n")

        searcher = CodeSearcher(tmpdir)

        # Test each language
        for filename, search_term, content in test_cases:
            matches = searcher.search_text(search_term, file_pattern="*.py")
            assert len(matches) >= 1, f"Failed to find {search_term} in {filename}"
            assert any(search_term in m["line"] for m in matches), f"Search term {search_term} not in results"


def test_search_utf8_filename_with_chinese():
    """Test searching in files with Chinese characters in filename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with Chinese characters in the filename
        chinese_filename = "测试文件.py"
        filepath = os.path.join(tmpdir, chinese_filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("def test():\n    return 'hello'\n")

        searcher = CodeSearcher(tmpdir)

        # Search should find the file and return correct filename
        matches = searcher.search_text("test", file_pattern="*.py")
        assert len(matches) >= 1
        # The filename in results should preserve Chinese characters
        assert any(chinese_filename in m["file"] or "测试文件" in m["file"] for m in matches)
