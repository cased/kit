import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from kit.tree_sitter_symbol_extractor import LanguagePlugin, TreeSitterSymbolExtractor


class TestLanguagePlugin:
    """Tests for the LanguagePlugin class."""

    def test_language_plugin_initialization(self):
        """Test that LanguagePlugin initializes correctly."""
        plugin = LanguagePlugin(
            name="test_lang",
            extensions=[".test", ".tst"],
            query_files=["base.scm", "advanced.scm"],
            query_dirs=["/path/to/queries"],
        )

        assert plugin.name == "test_lang"
        assert plugin.extensions == [".test", ".tst"]
        assert plugin.query_files == ["base.scm", "advanced.scm"]
        assert plugin.query_dirs == ["/path/to/queries"]

    def test_language_plugin_default_query_dirs(self):
        """Test that query_dirs defaults to empty list."""
        plugin = LanguagePlugin(name="test_lang", extensions=[".test"], query_files=["base.scm"])

        assert plugin.query_dirs == []


class TestBackwardCompatibility:
    """Tests to ensure existing functionality continues to work."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_existing_languages_still_supported(self):
        """Test that all existing languages are still supported."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()

        # Verify core languages are present
        expected_languages = {"python", "javascript", "go", "rust", "hcl", "typescript", "tsx", "c", "ruby", "java"}

        for lang in expected_languages:
            assert lang in supported, f"Language {lang} should be supported"

    def test_existing_extensions_mapped_correctly(self):
        """Test that file extensions map to correct languages."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()

        # Test specific mappings
        assert ".py" in supported["python"]
        assert ".js" in supported["javascript"]
        assert ".go" in supported["go"]
        assert ".rs" in supported["rust"]
        assert ".tf" in supported["hcl"]
        assert ".hcl" in supported["hcl"]
        assert ".ts" in supported["typescript"]
        assert ".tsx" in supported["tsx"]
        assert ".c" in supported["c"]
        assert ".rb" in supported["ruby"]
        assert ".java" in supported["java"]

    @patch("kit.tree_sitter_symbol_extractor.get_parser")
    @patch("kit.tree_sitter_symbol_extractor.get_language")
    @patch("kit.tree_sitter_symbol_extractor.files")
    def test_backward_compatible_query_loading(self, mock_files, mock_get_language, mock_get_parser):
        """Test that existing tags.scm loading still works."""
        # Mock file system
        mock_package = MagicMock()
        mock_tags_file = MagicMock()
        mock_tags_file.read_text.return_value = "(function_definition) @definition.function"
        mock_package.joinpath.return_value = mock_tags_file
        mock_files.return_value.joinpath.return_value = mock_package

        # Mock language and parser
        mock_language = MagicMock()
        mock_query = MagicMock()
        mock_language.query.return_value = mock_query
        mock_get_language.return_value = mock_language

        # Test query loading
        query = TreeSitterSymbolExtractor.get_query(".py")

        assert query == mock_query
        mock_language.query.assert_called_once()
        mock_files.assert_called_with("kit.queries")


class TestLanguageExtension:
    """Tests for extending existing languages with additional queries."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_extend_language_with_absolute_path(self):
        """Test extending a language with absolute path to query file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("(test_pattern) @definition.test")
            query_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("python", query_file)

            # Verify extension was added
            assert "python" in TreeSitterSymbolExtractor._language_extensions
            assert query_file in TreeSitterSymbolExtractor._language_extensions["python"]
        finally:
            Path(query_file).unlink()

    def test_extend_language_multiple_files(self):
        """Test extending a language with multiple query files."""
        files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
                    f.write(f"(pattern_{i}) @definition.test_{i}")
                    files.append(f.name)
                    TreeSitterSymbolExtractor.extend_language("python", f.name)

            # Verify all extensions were added
            extensions = TreeSitterSymbolExtractor._language_extensions["python"]
            assert len(extensions) == 3
            for file_path in files:
                assert file_path in extensions
        finally:
            for file_path in files:
                Path(file_path).unlink()

    def test_extend_nonexistent_language(self):
        """Test extending a language that doesn't exist creates extension list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("(pattern) @definition.test")
            query_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("nonexistent", query_file)

            # Should create new extension list
            assert "nonexistent" in TreeSitterSymbolExtractor._language_extensions
            assert query_file in TreeSitterSymbolExtractor._language_extensions["nonexistent"]
        finally:
            Path(query_file).unlink()

    def test_extend_language_clears_cache(self):
        """Test that extending a language clears cached queries."""
        # Pre-populate cache
        TreeSitterSymbolExtractor._queries[".py"] = MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("(pattern) @definition.test")
            query_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("python", query_file)

            # Cache should be cleared
            assert ".py" not in TreeSitterSymbolExtractor._queries
        finally:
            Path(query_file).unlink()


class TestNewLanguageRegistration:
    """Tests for registering completely new languages."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_register_new_language(self):
        """Test registering a new language."""
        TreeSitterSymbolExtractor.register_language(
            name="kotlin", extensions=[".kt", ".kts"], query_files=["kotlin.scm"], query_dirs=["/custom/queries"]
        )

        # Verify registration
        assert "kotlin" in TreeSitterSymbolExtractor._custom_languages
        plugin = TreeSitterSymbolExtractor._custom_languages["kotlin"]
        assert plugin.name == "kotlin"
        assert plugin.extensions == [".kt", ".kts"]
        assert plugin.query_files == ["kotlin.scm"]
        assert plugin.query_dirs == ["/custom/queries"]

    def test_register_language_updates_mappings(self):
        """Test that registering a language updates extension mappings."""
        from kit.tree_sitter_symbol_extractor import LANGUAGES

        original_kt_mapping = LANGUAGES.get(".kt")

        TreeSitterSymbolExtractor.register_language(
            name="kotlin", extensions=[".kt", ".kts"], query_files=["kotlin.scm"]
        )

        # Verify mappings updated
        assert LANGUAGES[".kt"] == "kotlin"
        assert LANGUAGES[".kts"] == "kotlin"
        assert ".kt" in TreeSitterSymbolExtractor.LANGUAGES
        assert ".kts" in TreeSitterSymbolExtractor.LANGUAGES

        # Clean up
        if original_kt_mapping is None:
            LANGUAGES.pop(".kt", None)
        else:
            LANGUAGES[".kt"] = original_kt_mapping

    def test_register_language_clears_cache(self):
        """Test that registering a language clears relevant caches."""
        # Pre-populate caches
        TreeSitterSymbolExtractor._parsers[".kt"] = MagicMock()
        TreeSitterSymbolExtractor._queries[".kt"] = MagicMock()

        TreeSitterSymbolExtractor.register_language(name="kotlin", extensions=[".kt"], query_files=["kotlin.scm"])

        # Caches should be cleared
        assert ".kt" not in TreeSitterSymbolExtractor._parsers
        assert ".kt" not in TreeSitterSymbolExtractor._queries

    def test_register_language_overwrites_existing(self):
        """Test that registering overwrites existing custom language."""
        # Register initial language
        TreeSitterSymbolExtractor.register_language(name="kotlin", extensions=[".kt"], query_files=["old.scm"])

        # Register updated language
        TreeSitterSymbolExtractor.register_language(
            name="kotlin", extensions=[".kt", ".kts"], query_files=["new.scm"], query_dirs=["/new/path"]
        )

        # Verify overwrite
        plugin = TreeSitterSymbolExtractor._custom_languages["kotlin"]
        assert plugin.extensions == [".kt", ".kts"]
        assert plugin.query_files == ["new.scm"]
        assert plugin.query_dirs == ["/new/path"]


class TestQueryLoading:
    """Tests for the query loading system."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    @patch("kit.tree_sitter_symbol_extractor.files")
    def test_load_builtin_queries_with_extensions(self, mock_files):
        """Test loading built-in queries with extensions."""
        # Mock built-in tags.scm
        mock_package = MagicMock()
        mock_tags_file = MagicMock()
        mock_tags_file.read_text.return_value = "base_query"
        mock_package.joinpath.return_value = mock_tags_file
        mock_files.return_value.joinpath.return_value = mock_package

        # Add extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("extension_query")
            extension_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("python", extension_file)

            # Load combined queries
            combined = TreeSitterSymbolExtractor._load_query_files("python")

            assert "base_query" in combined
            assert "extension_query" in combined
        finally:
            Path(extension_file).unlink()

    def test_load_custom_language_queries(self):
        """Test loading queries for custom languages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create query files
            query1_path = Path(temp_dir) / "base.scm"
            query2_path = Path(temp_dir) / "advanced.scm"

            query1_path.write_text("base_patterns")
            query2_path.write_text("advanced_patterns")

            # Register custom language
            TreeSitterSymbolExtractor.register_language(
                name="custom", extensions=[".custom"], query_files=["base.scm", "advanced.scm"], query_dirs=[temp_dir]
            )

            # Load queries
            combined = TreeSitterSymbolExtractor._load_query_files("custom")

            assert "base_patterns" in combined
            assert "advanced_patterns" in combined

    def test_load_queries_with_absolute_paths(self):
        """Test loading queries with absolute file paths."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("absolute_path_query")
            abs_query_file = f.name

        try:
            TreeSitterSymbolExtractor.register_language(
                name="test_lang", extensions=[".test"], query_files=[abs_query_file]
            )

            combined = TreeSitterSymbolExtractor._load_query_files("test_lang")
            assert "absolute_path_query" in combined
        finally:
            Path(abs_query_file).unlink()

    def test_load_queries_priority_order(self):
        """Test that queries are loaded in correct priority order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create query file
            query_path = Path(temp_dir) / "test.scm"
            query_path.write_text("custom_query")

            # Register language with multiple directories
            TreeSitterSymbolExtractor.register_language(
                name="test_lang", extensions=[".test"], query_files=["test.scm"], query_dirs=[temp_dir, "/nonexistent"]
            )

            combined = TreeSitterSymbolExtractor._load_query_files("test_lang")
            assert "custom_query" in combined

    def test_load_queries_handles_missing_files(self):
        """Test that missing query files are handled gracefully."""
        TreeSitterSymbolExtractor.register_language(
            name="test_lang", extensions=[".test"], query_files=["nonexistent.scm"]
        )

        # Should not raise exception
        combined = TreeSitterSymbolExtractor._load_query_files("test_lang")
        assert combined == ""  # Empty string for no content

    @patch("kit.tree_sitter_symbol_extractor.files")
    def test_tsx_fallback_to_typescript(self, mock_files):
        """Test that TSX falls back to TypeScript queries."""
        # Mock TSX directory not existing
        mock_tsx_package = MagicMock()
        mock_tsx_tags = MagicMock()
        mock_tsx_tags.read_text.side_effect = FileNotFoundError("Not found")
        mock_tsx_package.joinpath.return_value = mock_tsx_tags

        # Mock TypeScript fallback
        mock_ts_package = MagicMock()
        mock_ts_tags = MagicMock()
        mock_ts_tags.read_text.return_value = "typescript_fallback"
        mock_ts_package.joinpath.return_value = mock_ts_tags

        def mock_joinpath(path):
            if path == "tsx":
                return mock_tsx_package
            elif path == "typescript":
                return mock_ts_package
            return MagicMock()

        mock_files.return_value.joinpath.side_effect = mock_joinpath

        combined = TreeSitterSymbolExtractor._load_query_files("tsx")
        assert "typescript_fallback" in combined


class TestQueryCompilation:
    """Tests for query compilation and caching."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    @patch("kit.tree_sitter_symbol_extractor.get_language")
    @patch("kit.tree_sitter_symbol_extractor.TreeSitterSymbolExtractor._load_query_files")
    def test_query_compilation_success(self, mock_load_files, mock_get_language):
        """Test successful query compilation."""
        mock_load_files.return_value = "(function_definition) @definition.function"

        mock_language = MagicMock()
        mock_query = MagicMock()
        mock_language.query.return_value = mock_query
        mock_get_language.return_value = mock_language

        query = TreeSitterSymbolExtractor.get_query(".py")

        assert query == mock_query
        assert ".py" in TreeSitterSymbolExtractor._queries  # Should be cached

    @patch("kit.tree_sitter_symbol_extractor.get_language")
    @patch("kit.tree_sitter_symbol_extractor.TreeSitterSymbolExtractor._load_query_files")
    def test_query_compilation_failure(self, mock_load_files, mock_get_language):
        """Test query compilation failure handling."""
        mock_load_files.return_value = "invalid query syntax"

        mock_language = MagicMock()
        mock_language.query.side_effect = Exception("Query compilation failed")
        mock_get_language.return_value = mock_language

        query = TreeSitterSymbolExtractor.get_query(".py")

        assert query is None
        assert ".py" not in TreeSitterSymbolExtractor._queries  # Should not cache failed queries

    @patch("kit.tree_sitter_symbol_extractor.get_language")
    @patch("kit.tree_sitter_symbol_extractor.TreeSitterSymbolExtractor._load_query_files")
    def test_empty_query_content_handling(self, mock_load_files, mock_get_language):
        """Test handling of empty query content."""
        mock_load_files.return_value = ""  # Empty content

        query = TreeSitterSymbolExtractor.get_query(".py")

        assert query is None
        mock_get_language.assert_not_called()  # Should not try to compile empty query

    def test_query_caching(self):
        """Test that queries are properly cached."""
        mock_query = MagicMock()
        TreeSitterSymbolExtractor._queries[".py"] = mock_query

        # Should return cached query
        query = TreeSitterSymbolExtractor.get_query(".py")
        assert query == mock_query

    def test_unsupported_extension(self):
        """Test handling of unsupported file extensions."""
        query = TreeSitterSymbolExtractor.get_query(".unknown")
        assert query is None


class TestIntrospection:
    """Tests for introspection and debugging methods."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_list_supported_languages_builtin(self):
        """Test listing built-in supported languages."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()

        assert isinstance(supported, dict)
        assert "python" in supported
        assert ".py" in supported["python"]
        assert "javascript" in supported
        assert ".js" in supported["javascript"]

    def test_list_supported_languages_with_custom(self):
        """Test listing languages including custom ones."""
        TreeSitterSymbolExtractor.register_language(
            name="kotlin", extensions=[".kt", ".kts"], query_files=["kotlin.scm"]
        )

        supported = TreeSitterSymbolExtractor.list_supported_languages()

        assert "kotlin" in supported
        assert ".kt" in supported["kotlin"]
        assert ".kts" in supported["kotlin"]

    def test_list_supported_languages_grouped_correctly(self):
        """Test that extensions are grouped by language correctly."""
        supported = TreeSitterSymbolExtractor.list_supported_languages()

        # HCL should have both .hcl and .tf
        assert "hcl" in supported
        hcl_extensions = supported["hcl"]
        assert ".hcl" in hcl_extensions
        assert ".tf" in hcl_extensions


class TestPluginReset:
    """Tests for plugin reset functionality."""

    def test_reset_plugins_clears_custom_languages(self):
        """Test that reset clears custom languages."""
        TreeSitterSymbolExtractor.register_language(name="test_lang", extensions=[".test"], query_files=["test.scm"])

        assert "test_lang" in TreeSitterSymbolExtractor._custom_languages

        TreeSitterSymbolExtractor.reset_plugins()

        assert len(TreeSitterSymbolExtractor._custom_languages) == 0

    def test_reset_plugins_clears_extensions(self):
        """Test that reset clears language extensions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("test extension")
            query_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("python", query_file)
            assert "python" in TreeSitterSymbolExtractor._language_extensions

            TreeSitterSymbolExtractor.reset_plugins()

            assert len(TreeSitterSymbolExtractor._language_extensions) == 0
        finally:
            Path(query_file).unlink()

    def test_reset_plugins_clears_caches(self):
        """Test that reset clears query and parser caches."""
        # Populate caches
        TreeSitterSymbolExtractor._queries[".py"] = MagicMock()
        TreeSitterSymbolExtractor._parsers[".py"] = MagicMock()

        TreeSitterSymbolExtractor.reset_plugins()

        assert len(TreeSitterSymbolExtractor._queries) == 0
        assert len(TreeSitterSymbolExtractor._parsers) == 0

    def test_reset_plugins_restores_original_mappings(self):
        """Test that reset restores original language mappings."""
        from kit.tree_sitter_symbol_extractor import LANGUAGES

        original_py_mapping = LANGUAGES[".py"]

        # Register custom language that overwrites .py
        TreeSitterSymbolExtractor.register_language(
            name="custom_python", extensions=[".py"], query_files=["custom.scm"]
        )

        assert LANGUAGES[".py"] == "custom_python"

        TreeSitterSymbolExtractor.reset_plugins()

        assert LANGUAGES[".py"] == original_py_mapping


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_extend_language_with_nonexistent_file(self):
        """Test extending language with non-existent file."""
        # Should not raise exception
        TreeSitterSymbolExtractor.extend_language("python", "/nonexistent/file.scm")

        # Extension should still be registered (will fail at load time)
        assert "python" in TreeSitterSymbolExtractor._language_extensions
        assert "/nonexistent/file.scm" in TreeSitterSymbolExtractor._language_extensions["python"]

    def test_register_language_with_empty_extensions(self):
        """Test registering language with empty extensions list."""
        TreeSitterSymbolExtractor.register_language(name="test_lang", extensions=[], query_files=["test.scm"])

        assert "test_lang" in TreeSitterSymbolExtractor._custom_languages
        plugin = TreeSitterSymbolExtractor._custom_languages["test_lang"]
        assert plugin.extensions == []

    def test_register_language_with_empty_query_files(self):
        """Test registering language with empty query files list."""
        TreeSitterSymbolExtractor.register_language(name="test_lang", extensions=[".test"], query_files=[])

        assert "test_lang" in TreeSitterSymbolExtractor._custom_languages
        plugin = TreeSitterSymbolExtractor._custom_languages["test_lang"]
        assert plugin.query_files == []

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_load_queries_permission_error(self, mock_open):
        """Test handling of permission errors when loading queries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            query_file = f.name

        try:
            TreeSitterSymbolExtractor.register_language(
                name="test_lang", extensions=[".test"], query_files=[query_file]
            )

            # Should handle permission error gracefully
            combined = TreeSitterSymbolExtractor._load_query_files("test_lang")
            assert combined == ""  # Empty due to error
        finally:
            Path(query_file).unlink()

    def test_multiple_reset_calls(self):
        """Test that multiple reset calls don't cause issues."""
        TreeSitterSymbolExtractor.reset_plugins()
        TreeSitterSymbolExtractor.reset_plugins()
        TreeSitterSymbolExtractor.reset_plugins()

        # Should not raise any exceptions
        supported = TreeSitterSymbolExtractor.list_supported_languages()
        assert len(supported) > 0


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_mixed_builtin_and_custom_languages(self):
        """Test scenario with both built-in and custom languages."""
        # Register custom language
        TreeSitterSymbolExtractor.register_language(name="kotlin", extensions=[".kt"], query_files=["kotlin.scm"])

        # Extend built-in language
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
            f.write("extension query")
            extension_file = f.name

        try:
            TreeSitterSymbolExtractor.extend_language("python", extension_file)

            supported = TreeSitterSymbolExtractor.list_supported_languages()

            # Should have both built-in and custom
            assert "python" in supported
            assert "kotlin" in supported
            assert ".py" in supported["python"]
            assert ".kt" in supported["kotlin"]

            # Check internal state
            assert "kotlin" in TreeSitterSymbolExtractor._custom_languages
            assert "python" in TreeSitterSymbolExtractor._language_extensions
        finally:
            Path(extension_file).unlink()

    def test_override_builtin_language(self):
        """Test overriding a built-in language with custom registration."""
        # Override Python with custom implementation
        TreeSitterSymbolExtractor.register_language(
            name="custom_python", extensions=[".py"], query_files=["custom_python.scm"]
        )

        from kit.tree_sitter_symbol_extractor import LANGUAGES

        assert LANGUAGES[".py"] == "custom_python"

        supported = TreeSitterSymbolExtractor.list_supported_languages()
        assert "custom_python" in supported
        assert ".py" in supported["custom_python"]

    def test_complex_query_directory_hierarchy(self):
        """Test complex scenario with multiple query directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested directory structure
            base_dir = Path(temp_dir) / "base"
            project_dir = Path(temp_dir) / "project"

            base_dir.mkdir()
            project_dir.mkdir()

            # Create query files
            (base_dir / "base.scm").write_text("base_query")
            (project_dir / "project.scm").write_text("project_query")

            TreeSitterSymbolExtractor.register_language(
                name="complex_lang",
                extensions=[".complex"],
                query_files=["base.scm", "project.scm"],
                query_dirs=[str(base_dir), str(project_dir)],
            )

            combined = TreeSitterSymbolExtractor._load_query_files("complex_lang")

            assert "base_query" in combined
            assert "project_query" in combined


class TestConcurrency:
    """Tests for thread safety and concurrent access."""

    def setup_method(self):
        """Reset plugins before each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def teardown_method(self):
        """Clean up after each test."""
        TreeSitterSymbolExtractor.reset_plugins()

    def test_concurrent_language_registration(self):
        """Test that concurrent language registration is safe."""
        import threading
        import time

        def register_language(lang_name: str):
            TreeSitterSymbolExtractor.register_language(
                name=f"lang_{lang_name}", extensions=[f".{lang_name}"], query_files=[f"{lang_name}.scm"]
            )
            time.sleep(0.01)  # Small delay to increase chance of race conditions

        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_language, args=(str(i),))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All languages should be registered
        assert len(TreeSitterSymbolExtractor._custom_languages) == 10
        for i in range(10):
            assert f"lang_{i}" in TreeSitterSymbolExtractor._custom_languages

    def test_concurrent_extension_and_query_access(self):
        """Test concurrent extension and query access."""
        import threading

        def extend_language():
            with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
                f.write("test query")
                TreeSitterSymbolExtractor.extend_language("python", f.name)
                Path(f.name).unlink()

        def access_query():
            # This might return None due to missing dependencies, but shouldn't crash
            TreeSitterSymbolExtractor.get_query(".py")

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=extend_language))
            threads.append(threading.Thread(target=access_query))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not crash and should have extensions registered
        assert "python" in TreeSitterSymbolExtractor._language_extensions
