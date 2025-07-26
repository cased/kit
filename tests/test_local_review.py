"""Tests for local diff review functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kit.pr_review.config import ReviewConfig
from kit.pr_review.local_reviewer import LocalChange, LocalDiffReviewer


@pytest.fixture
def mock_config():
    """Create a mock ReviewConfig for testing."""
    config = MagicMock(spec=ReviewConfig)
    config.max_files = 10
    config.quiet = True
    config.save_reviews = False
    config.priority_filter = None
    config.llm_provider = "anthropic"
    config.llm_model = "claude-3-haiku-20240307"
    config.llm_api_key = "test-key"
    config.llm_api_base_url = None
    config.llm_temperature = 0.1
    config.llm_max_tokens = 1000
    config.custom_pricing = None
    return config


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        os.chdir(repo_path)
        os.system("git init --quiet")
        os.system('git config user.name "Test User"')
        os.system('git config user.email "test@example.com"')

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repository\n")
        os.system("git add README.md")
        os.system('git commit -m "Initial commit" --quiet')

        yield repo_path


class TestLocalDiffReviewer:
    """Test LocalDiffReviewer class."""

    def test_init(self, mock_config, temp_git_repo):
        """Test LocalDiffReviewer initialization."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)
        assert reviewer.config == mock_config
        assert reviewer.repo_path == temp_git_repo
        assert reviewer.cost_tracker is not None
        assert reviewer._llm_client is None

    def test_parse_diff_spec(self, mock_config, temp_git_repo):
        """Test diff specification parsing."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Test branch comparison
        base, head = reviewer._parse_diff_spec("main..feature")
        assert base == "main"
        assert head == "feature"

        # Test staged changes
        base, head = reviewer._parse_diff_spec("--staged")
        assert base == "HEAD"
        assert head == "staged"

        # Test single ref
        base, head = reviewer._parse_diff_spec("HEAD~3")
        assert base == "HEAD~3"
        assert head == "HEAD"

    def test_get_commit_info(self, mock_config, temp_git_repo):
        """Test getting commit information."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Test HEAD commit info
        info = reviewer._get_commit_info("HEAD")
        assert info["author"] == "Test User"
        assert info["subject"] == "Initial commit"
        assert info["hash"] != ""

        # Test staged info
        info = reviewer._get_commit_info("staged")
        assert info["hash"] == "staged"
        assert info["subject"] == "Staged changes"

    def test_get_diff(self, mock_config, temp_git_repo):
        """Test getting diff between refs."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Make a change
        (temp_git_repo / "test.py").write_text("def hello():\n    print('Hello')\n")
        os.system("git add test.py")
        os.system('git commit -m "Add test.py" --quiet')

        # Get diff
        diff = reviewer._get_diff("HEAD~1", "HEAD")
        assert "test.py" in diff
        assert "+def hello():" in diff
        assert "+    print('Hello')" in diff

    def test_get_changed_files(self, mock_config, temp_git_repo):
        """Test getting list of changed files."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Make changes
        (temp_git_repo / "new_file.txt").write_text("New content")
        (temp_git_repo / "README.md").write_text("# Updated README\n")
        os.system("git add .")
        os.system('git commit -m "Update files" --quiet')

        # Get changed files
        files = reviewer._get_changed_files("HEAD~1", "HEAD")
        assert len(files) == 2

        # Check file info
        filenames = [f["filename"] for f in files]
        assert "README.md" in filenames
        assert "new_file.txt" in filenames

        # Find the new_file.txt entry
        new_file = next(f for f in files if f["filename"] == "new_file.txt")
        assert new_file["status"] == "added"
        assert new_file["additions"] > 0

    def test_prepare_local_change(self, mock_config, temp_git_repo):
        """Test preparing LocalChange object."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Make a change
        (temp_git_repo / "feature.py").write_text("# Feature implementation\n")
        os.system("git add feature.py")
        os.system('git commit -m "Add feature" --quiet')

        # Prepare change
        change = reviewer._prepare_local_change("HEAD~1..HEAD")
        assert isinstance(change, LocalChange)
        assert change.base_ref == "HEAD~1"
        assert change.head_ref == "HEAD"
        assert change.title == "Add feature"
        assert change.author == "Test User"
        assert len(change.files) == 1
        assert "feature.py" in change.diff

    @pytest.mark.asyncio
    async def test_analyze_with_kit(self, mock_config, temp_git_repo):
        """Test repository analysis with kit."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Create a Python file for analysis
        (temp_git_repo / "module.py").write_text("""
def calculate_sum(a, b):
    '''Calculate sum of two numbers.'''
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")
        os.system("git add module.py")
        os.system('git commit -m "Add module" --quiet')

        # Prepare change
        change = reviewer._prepare_local_change("HEAD~1..HEAD")

        # Mock Repository methods
        with patch("kit.pr_review.local_reviewer.Repository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock extract_symbols to return test data
            mock_repo.extract_symbols.return_value = [
                {"name": "calculate_sum", "type": "function", "file_path": "module.py", "line_number": 2},
                {"name": "Calculator", "type": "class", "file_path": "module.py", "line_number": 6},
            ]

            # Mock get_symbol_usages
            mock_repo.get_symbol_usages.return_value = []

            # Mock get_file_tree
            mock_repo.get_file_tree.return_value = [
                {"path": "README.md", "type": "file"},
                {"path": "module.py", "type": "file"},
            ]

            # Run analysis
            analysis = await reviewer._analyze_with_kit(change)

            assert "symbols" in analysis
            assert len(analysis["symbols"]) == 2
            assert analysis["symbols"][0]["name"] == "calculate_sum"
            assert analysis["changed_files"] == 1

    def test_generate_review_prompt(self, mock_config, temp_git_repo):
        """Test review prompt generation."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Create test change
        change = LocalChange(
            base_ref="main",
            head_ref="feature",
            title="Add new feature",
            description="This adds a new feature",
            author="Test User",
            repo_path=temp_git_repo,
            diff="diff --git a/test.py b/test.py\n+def test():\n+    pass\n",
            files=[{"filename": "test.py", "status": "added", "additions": 2, "deletions": 0}],
        )

        # Create mock analysis
        analysis = {
            "symbols": [{"name": "test", "type": "function", "file": "test.py", "line": 1, "usage_count": 0}],
            "structure": [],
            "total_files": 2,
            "changed_files": 1,
        }

        # Generate prompt
        prompt = reviewer._generate_review_prompt(change, analysis)

        assert "local git diff" in prompt
        assert "Base: main" in prompt
        assert "Head: feature" in prompt
        assert "Author: Test User" in prompt
        assert "test.py" in prompt
        assert "function test" in prompt

    @pytest.mark.asyncio
    async def test_llm_review_anthropic(self, mock_config, temp_git_repo):
        """Test LLM review with Anthropic."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Mock the _analyze_with_anthropic_enhanced method directly
        with patch.object(reviewer, "_analyze_with_anthropic_enhanced") as mock_analyze:
            mock_analyze.return_value = "Test review content"

            # Get review
            prompt = "Test prompt"
            review, usage = await reviewer._get_llm_review(prompt)

            assert review == "Test review content"
            assert mock_analyze.called

    def test_format_review_output(self, mock_config, temp_git_repo):
        """Test review output formatting."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        change = LocalChange(
            base_ref="main",
            head_ref="feature",
            title="Test",
            description="",
            author="Test User",
            repo_path=temp_git_repo,
            diff="",
            files=[],
        )

        review_text = "## HIGH Priority\n- Issue 1\n\n## LOW Priority\n- Issue 2"
        cost = 0.0123

        formatted = reviewer._format_review_output(review_text, change, cost)

        assert "Kit Local Diff Review" in formatted
        assert "**Repository**:" in formatted  # Match markdown format
        assert "**Diff**: main..feature" in formatted  # Match markdown format
        assert "**Author**: Test User" in formatted  # Match markdown format
        assert "HIGH Priority" in formatted
        assert "Cost: $0.0123" in formatted

    def test_review_integration(self, mock_config, temp_git_repo):
        """Test full review integration."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Make a change
        (temp_git_repo / "example.py").write_text("print('Hello, World!')\n")
        os.system("git add example.py")
        os.system('git commit -m "Add example" --quiet')

        # Mock asyncio.run to return expected values
        def mock_async_run(coro):
            # Check what coroutine is being run
            if coro.__name__ == "_get_llm_review":
                return ("## Review\nLooks good!", {})
            elif coro.__name__ == "_analyze_with_kit":
                return {"symbols": [], "structure": [], "total_files": 1, "changed_files": 1}
            else:
                # For other coroutines, try to run them
                import asyncio

                return asyncio.get_event_loop().run_until_complete(coro)

        with patch("kit.pr_review.local_reviewer.asyncio.run", side_effect=mock_async_run):
            with patch("kit.pr_review.local_reviewer.Repository"):
                # Run review
                result = reviewer.review("HEAD~1..HEAD")

                assert "Kit Local Diff Review" in result
                assert "Looks good!" in result

    def test_error_handling(self, mock_config):
        """Test error handling."""
        # Test with non-git directory
        with tempfile.TemporaryDirectory() as tmpdir:
            reviewer = LocalDiffReviewer(mock_config, Path(tmpdir))

            with pytest.raises(RuntimeError, match="Not in a git repository"):
                reviewer.review("HEAD~1..HEAD")

    def test_staged_changes(self, mock_config, temp_git_repo):
        """Test reviewing staged changes."""
        reviewer = LocalDiffReviewer(mock_config, temp_git_repo)

        # Stage a change
        (temp_git_repo / "staged.txt").write_text("Staged content\n")
        os.system("git add staged.txt")

        # Get staged diff
        diff = reviewer._get_diff("HEAD", "staged")
        assert "staged.txt" in diff
        assert "+Staged content" in diff

        # Get staged files
        files = reviewer._get_changed_files("HEAD", "staged")
        assert len(files) == 1
        assert files[0]["filename"] == "staged.txt"
        assert files[0]["status"] == "added"
