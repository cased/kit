import os
import tempfile
import unittest
from pathlib import Path

from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


class ResourceLoadingTest(unittest.TestCase):
    """Tests that verify symbol extraction works outside the kit repository directory."""

    def test_extraction_from_different_working_directory(self):
        """Verify that symbol extraction works when run from a different working directory."""
        # Save current working directory
        original_cwd = os.getcwd()

        try:
            # Create and change to a temporary directory completely outside the repo
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Confirm we're outside the kit repository
                kit_repo_path = Path(original_cwd)
                current_path = Path(os.getcwd())
                self.assertNotEqual(kit_repo_path, current_path)
                self.assertFalse(current_path.is_relative_to(kit_repo_path))

                # Now try to extract symbols - this would fail if the code relies on repo-relative paths
                python_code = "def test_function():\n    pass\n\nclass TestClass:\n    def method(self):\n        pass"
                symbols = TreeSitterSymbolExtractor.extract_symbols(".py", python_code)

                # Verify extraction worked
                self.assertGreater(len(symbols), 0, "Should extract at least one symbol")
                symbol_names = {s["name"] for s in symbols}
                self.assertIn("test_function", symbol_names)
                self.assertIn("TestClass", symbol_names)

                # Optional: Test other languages too
                js_code = "function foo() {}\nclass Bar {}"
                js_symbols = TreeSitterSymbolExtractor.extract_symbols(".js", js_code)
                self.assertGreater(len(js_symbols), 0, "Should extract JavaScript symbols")

        finally:
            # Restore original working directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
