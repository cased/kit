import os
import unittest
from pathlib import Path


class ResourceLoadingTest(unittest.TestCase):
    """Tests that verify symbol extraction works outside the kit repository directory."""

    def test_extraction_from_different_working_directory(self):
        """Verify that symbol extraction works when run from a different working directory."""
        # Save current working directory
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # Handle case where current directory doesn't exist (e.g., in CI)
            original_cwd = "/tmp"

        try:
            # Change to a different directory
            os.chdir("/tmp")
            current_path = Path(os.getcwd())
            assert current_path.name == "tmp"

            # Test that we can still extract symbols from the test directory
            test_file = Path(__file__).parent / "sample_code" / "python_sample.py"
            assert test_file.exists()

            # Extract symbols from the test file
            from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

            extractor = TreeSitterSymbolExtractor()
            with open(test_file, "r") as f:
                source_code = f.read()
            symbols = extractor.extract_symbols(".py", source_code)

            # Should find some symbols
            assert len(symbols) > 0
            # Check for symbols that are actually in the sample file
            symbol_names = [s["name"] for s in symbols]
            assert any(name in symbol_names for name in ["greet", "Greeter"])

        finally:
            try:
                os.chdir(original_cwd)
            except FileNotFoundError:
                # If original_cwd doesn't exist, just stay in current directory
                pass


if __name__ == "__main__":
    unittest.main()
