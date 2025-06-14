"""Unit tests for incremental analysis system."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from kit.incremental_analyzer import FileAnalysisCache, IncrementalAnalyzer


class TestFileAnalysisCache:
    """Test the FileAnalysisCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            cache = FileAnalysisCache(repo_path)

            assert cache.repo_path == repo_path
            assert cache.cache_dir.exists()
            assert cache.metadata_file.name == "analysis_metadata.json"
            assert cache.symbols_cache_file.name == "symbols_cache.json"

    def test_file_metadata_generation(self):
        """Test file metadata generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)
            metadata = cache._get_file_metadata(test_file)

            assert "mtime" in metadata
            assert "size" in metadata
            assert "hash" in metadata
            assert "last_analyzed" in metadata
            assert metadata["size"] == len("def hello(): pass")

    def test_file_change_detection(self):
        """Test file change detection logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)

            # First check - file never analyzed
            assert cache.is_file_changed(test_file) is True

            # Cache some symbols
            cache.cache_symbols(test_file, [{"name": "hello", "type": "function"}])

            # Second check - file unchanged
            assert cache.is_file_changed(test_file) is False

            # Modify file
            time.sleep(0.01)  # Ensure mtime changes
            test_file.write_text("def hello(): pass\ndef world(): pass")

            # Third check - file changed
            assert cache.is_file_changed(test_file) is True

    def test_symbol_caching_and_retrieval(self):
        """Test symbol caching and retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)
            symbols = [{"name": "hello", "type": "function", "line": 1}]

            # Cache symbols
            cache.cache_symbols(test_file, symbols)

            # Retrieve cached symbols
            cached_symbols = cache.get_cached_symbols(test_file)
            assert cached_symbols == symbols

    def test_cache_persistence(self):
        """Test that cache persists to disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            # Create cache and add data
            cache1 = FileAnalysisCache(repo_path)
            symbols = [{"name": "hello", "type": "function"}]
            cache1.cache_symbols(test_file, symbols)
            cache1._save_cache()

            # Create new cache instance (should load from disk)
            cache2 = FileAnalysisCache(repo_path)
            cached_symbols = cache2.get_cached_symbols(test_file)
            assert cached_symbols == symbols

    def test_stale_entry_cleanup(self):
        """Test cleanup of stale cache entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)
            cache.cache_symbols(test_file, [{"name": "hello", "type": "function"}])

            # Remove the file
            test_file.unlink()

            # Cleanup should remove the stale entry
            removed_count = cache.cleanup_stale_entries()
            assert removed_count == 1
            assert len(cache._file_metadata) == 0
            assert len(cache._symbols_cache) == 0

    def test_cache_stats(self):
        """Test cache statistics generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)
            cache.cache_symbols(test_file, [{"name": "hello", "type": "function"}])

            stats = cache.get_cache_stats()
            assert stats["cached_files"] == 1
            assert stats["total_symbols"] == 1
            assert "cache_size_bytes" in stats
            assert "cache_size_mb" in stats

    def test_cache_invalidation(self):
        """Test cache invalidation for specific files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            cache = FileAnalysisCache(repo_path)
            cache.cache_symbols(test_file, [{"name": "hello", "type": "function"}])

            # Verify cached
            assert cache.get_cached_symbols(test_file) is not None

            # Invalidate
            cache.invalidate_file(test_file)

            # Should be gone
            rel_path = str(test_file.relative_to(repo_path))
            assert rel_path not in cache._file_metadata
            assert rel_path not in cache._symbols_cache


class TestIncrementalAnalyzer:
    """Test the IncrementalAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            analyzer = IncrementalAnalyzer(repo_path)

            assert analyzer.repo_path == repo_path
            assert analyzer.cache is not None
            assert analyzer._stats["files_analyzed"] == 0

    def test_single_file_analysis(self):
        """Test analysis of a single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello():\n    pass\n\nclass World:\n    pass")

            analyzer = IncrementalAnalyzer(repo_path)
            symbols = analyzer.analyze_file(test_file)

            # Should find function and class
            assert len(symbols) >= 2
            symbol_names = {s["name"] for s in symbols}
            assert "hello" in symbol_names
            assert "World" in symbol_names

            # Check stats
            stats = analyzer.get_analysis_stats()
            assert stats["files_analyzed"] == 1
            assert stats["cache_misses"] == 1

    def test_cache_hit_on_second_analysis(self):
        """Test that second analysis of same file hits cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)

            # First analysis
            symbols1 = analyzer.analyze_file(test_file)
            stats1 = analyzer.get_analysis_stats()

            # Second analysis (should hit cache)
            symbols2 = analyzer.analyze_file(test_file)
            stats2 = analyzer.get_analysis_stats()

            assert symbols1 == symbols2
            assert stats2["cache_hits"] > stats1["cache_hits"]

    def test_changed_file_reanalysis(self):
        """Test that changed files are re-analyzed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)

            # First analysis
            symbols1 = analyzer.analyze_file(test_file)

            # Modify file
            time.sleep(0.01)  # Ensure mtime changes
            test_file.write_text("def hello(): pass\ndef world(): pass")

            # Second analysis (should re-analyze)
            symbols2 = analyzer.analyze_file(test_file)

            assert len(symbols2) > len(symbols1)

    def test_analyze_changed_files_batch(self):
        """Test batch analysis of changed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create multiple files
            files = []
            for i in range(3):
                test_file = repo_path / f"test{i}.py"
                test_file.write_text(f"def func{i}(): pass")
                files.append(test_file)

            analyzer = IncrementalAnalyzer(repo_path)

            # First batch analysis
            results1 = analyzer.analyze_changed_files(files)
            assert len(results1) == 3

            # Second batch analysis (should hit cache)
            results2 = analyzer.analyze_changed_files(files)
            assert len(results2) == 3

            # Verify cache hits increased
            stats = analyzer.get_analysis_stats()
            assert stats["cache_hits"] > 0

    def test_unsupported_file_types(self):
        """Test handling of unsupported file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.txt"
            test_file.write_text("This is not code")

            analyzer = IncrementalAnalyzer(repo_path)
            symbols = analyzer.analyze_file(test_file)

            assert symbols == []

    def test_file_read_errors(self):
        """Test handling of file read errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)

            # Mock file read to raise exception
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                symbols = analyzer.analyze_file(test_file)
                assert symbols == []

    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)
            analyzer.analyze_file(test_file)

            # Remove file and cleanup
            test_file.unlink()
            analyzer.cleanup_cache()

            # Cache should be cleaned
            analyzer.get_analysis_stats()
            cache_stats = analyzer.cache.get_cache_stats()
            assert cache_stats["cached_files"] == 0

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)
            analyzer.analyze_file(test_file)

            # Clear cache
            analyzer.clear_cache()

            # Stats should be reset
            stats = analyzer.get_analysis_stats()
            assert stats["files_analyzed"] == 0
            assert stats["cache_hits"] == 0

    def test_finalization(self):
        """Test analyzer finalization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / "test.py"
            test_file.write_text("def hello(): pass")

            analyzer = IncrementalAnalyzer(repo_path)
            analyzer.analyze_file(test_file)

            # Should not raise exception
            analyzer.finalize()

    @pytest.mark.parametrize(
        "file_ext,expected_symbols",
        [
            (".py", True),
            (".js", True),
            (".ts", True),
            (".go", True),
            (".rs", True),
            (".txt", False),
            (".md", False),
        ],
    )
    def test_file_type_support(self, file_ext, expected_symbols):
        """Test support for different file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            test_file = repo_path / f"test{file_ext}"

            if file_ext == ".py":
                content = "def hello(): pass"
            elif file_ext == ".js":
                content = "function hello() {}"
            elif file_ext == ".ts":
                content = "function hello(): void {}"
            elif file_ext == ".go":
                content = "func hello() {}"
            elif file_ext == ".rs":
                content = "fn hello() {}"
            else:
                content = "This is not code"

            test_file.write_text(content)

            analyzer = IncrementalAnalyzer(repo_path)
            symbols = analyzer.analyze_file(test_file)

            if expected_symbols:
                assert len(symbols) > 0
            else:
                assert len(symbols) == 0


class TestRepositoryIntegration:
    """Test integration with Repository class."""

    def test_incremental_analyzer_property(self):
        """Test incremental analyzer property access."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from kit.repository import Repository

            repo = Repository(temp_dir)
            analyzer = repo.incremental_analyzer

            assert analyzer is not None
            assert analyzer.repo_path == repo.local_path

    def test_extract_symbols_incremental(self):
        """Test incremental symbol extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from kit.repository import Repository

            # Create test file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass\nclass World: pass")

            repo = Repository(temp_dir)
            symbols = repo.extract_symbols_incremental()

            assert len(symbols) >= 2
            symbol_names = {s["name"] for s in symbols}
            assert "hello" in symbol_names
            assert "World" in symbol_names

    def test_incremental_stats(self):
        """Test incremental statistics retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from kit.repository import Repository

            # Create test file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            repo = Repository(temp_dir)

            # Before any analysis
            stats = repo.get_incremental_stats()
            assert stats["status"] == "not_initialized"

            # After analysis
            repo.extract_symbols_incremental()
            stats = repo.get_incremental_stats()
            assert "cache_hit_rate" in stats

    def test_cache_management_methods(self):
        """Test cache management methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from kit.repository import Repository

            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello(): pass")

            repo = Repository(temp_dir)
            repo.extract_symbols_incremental()

            # Test cleanup
            repo.cleanup_incremental_cache()

            # Test clearing
            repo.clear_incremental_cache()

            # Test finalization
            repo.finalize_analysis()


if __name__ == "__main__":
    pytest.main([__file__])
