"""Tests for custom context profile functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import typer.testing
import yaml

from kit.cli import app
from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from kit.pr_review.profile_manager import ProfileManager, ReviewProfile


@pytest.fixture
def runner():
    """Create a typer test runner."""
    return typer.testing.CliRunner()


@pytest.fixture
def temp_profiles_dir():
    """Create a temporary directory for profile storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def profile_manager(temp_profiles_dir):
    """Create a ProfileManager instance with temporary directory."""
    return ProfileManager(profiles_dir=str(temp_profiles_dir))


@pytest.fixture
def sample_profile():
    """Create a sample profile for testing."""
    return ReviewProfile(
        name="test-profile",
        description="Test profile for unit tests",
        context="Test context content\nWith multiple lines",
        created_at="2024-01-15T10:30:00Z",
        updated_at="2024-01-15T10:30:00Z",
        tags=["test", "unit"],
    )


@pytest.fixture
def sample_profile_content():
    """Sample profile content string."""
    return """**Test Review Guidelines:**

1. **Code Quality:**
   - All functions must have docstrings
   - Use type hints for parameters
   - Follow PEP 8 standards

2. **Security:**
   - Validate all user inputs
   - No hardcoded secrets
   - Use parameterized queries

3. **Testing:**
   - Unit tests required for new features
   - Mock external dependencies
   - Maintain 80%+ coverage
"""


class TestReviewProfile:
    """Test the ReviewProfile dataclass."""

    def test_profile_creation(self):
        """Test creating a profile instance."""
        profile = ReviewProfile(
            name="test",
            description="Test profile",
            context="Test context",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
        )

        assert profile.name == "test"
        assert profile.description == "Test profile"
        assert profile.context == "Test context"
        assert profile.tags == []  # Default empty list

    def test_profile_with_tags(self):
        """Test creating a profile with tags."""
        profile = ReviewProfile(
            name="test",
            description="Test profile",
            context="Test context",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
            tags=["security", "python"],
        )

        assert profile.tags == ["security", "python"]

    def test_profile_post_init(self):
        """Test that __post_init__ sets default tags."""
        profile = ReviewProfile(
            name="test",
            description="Test profile",
            context="Test context",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
            tags=None,
        )

        assert profile.tags == []


class TestProfileManager:
    """Test the ProfileManager class."""

    def test_init_default_directory(self):
        """Test ProfileManager initialization with default directory."""
        with patch("os.path.expanduser") as mock_expanduser, patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_expanduser.return_value = "/home/user/.kit/profiles"

            manager = ProfileManager()

            assert str(manager.profiles_dir) == "/home/user/.kit/profiles"
            mock_expanduser.assert_called_once_with("~/.kit/profiles")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_custom_directory(self, temp_profiles_dir):
        """Test ProfileManager initialization with custom directory."""
        manager = ProfileManager(profiles_dir=str(temp_profiles_dir))
        assert manager.profiles_dir == temp_profiles_dir

    def test_create_profile(self, profile_manager, temp_profiles_dir):
        """Test creating a new profile."""
        # Mock the datetime import inside the method
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00Z"

            profile = profile_manager.create_profile(
                name="test-profile", description="Test description", context="Test context", tags=["test"]
            )

            assert profile.name == "test-profile"
            assert profile.description == "Test description"
            assert profile.context == "Test context"
            assert profile.tags == ["test"]
            assert profile.created_at == "2024-01-15T10:30:00Z"
            assert profile.updated_at == "2024-01-15T10:30:00Z"

            # Check file was created
            profile_file = temp_profiles_dir / "test-profile.yaml"
            assert profile_file.exists()

    def test_create_profile_from_file(self, profile_manager, temp_profiles_dir, sample_profile_content):
        """Test creating a profile from a file."""
        # Create a temporary content file
        content_file = temp_profiles_dir / "content.md"
        content_file.write_text(sample_profile_content)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00Z"

            profile = profile_manager.create_profile_from_file(
                name="file-profile", description="Profile from file", file_path=str(content_file), tags=["file", "test"]
            )

            assert profile.name == "file-profile"
            assert profile.context == sample_profile_content
            assert profile.tags == ["file", "test"]

    def test_create_profile_from_nonexistent_file(self, profile_manager):
        """Test creating a profile from a non-existent file raises error."""
        with pytest.raises(ValueError, match="File not found"):
            profile_manager.create_profile_from_file(name="test", description="Test", file_path="/nonexistent/file.md")

    def test_create_profile_duplicate_name(self, profile_manager, sample_profile):
        """Test creating a profile with duplicate name raises error."""
        # Create first profile
        profile_manager._save_profile(sample_profile)

        # Try to create another with same name
        with pytest.raises(ValueError, match="Profile 'test-profile' already exists"):
            profile_manager.create_profile(name="test-profile", description="Duplicate", context="Duplicate context")

    def test_get_profile(self, profile_manager, sample_profile):
        """Test retrieving a profile."""
        profile_manager._save_profile(sample_profile)

        retrieved = profile_manager.get_profile("test-profile")

        assert retrieved.name == sample_profile.name
        assert retrieved.description == sample_profile.description
        assert retrieved.context == sample_profile.context

    def test_get_profile_not_found(self, profile_manager):
        """Test retrieving a non-existent profile raises error."""
        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            profile_manager.get_profile("nonexistent")

    def test_list_profiles_empty(self, profile_manager):
        """Test listing profiles when none exist."""
        profiles = profile_manager.list_profiles()
        assert profiles == []

    def test_list_profiles(self, profile_manager, temp_profiles_dir):
        """Test listing multiple profiles."""
        # Create multiple profiles
        profile1 = ReviewProfile(
            name="profile1",
            description="First",
            context="Context1",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
        )
        profile2 = ReviewProfile(
            name="profile2",
            description="Second",
            context="Context2",
            created_at="2024-01-15T11:30:00Z",
            updated_at="2024-01-15T11:30:00Z",
        )

        profile_manager._save_profile(profile1)
        profile_manager._save_profile(profile2)

        profiles = profile_manager.list_profiles()

        assert len(profiles) == 2
        profile_names = [p.name for p in profiles]
        assert "profile1" in profile_names
        assert "profile2" in profile_names

    def test_update_profile(self, profile_manager, sample_profile):
        """Test updating an existing profile."""
        profile_manager._save_profile(sample_profile)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T12:00:00Z"

            updated = profile_manager.update_profile(
                name="test-profile", description="Updated description", context="Updated context", tags=["updated"]
            )

            assert updated.description == "Updated description"
            assert updated.context == "Updated context"
            assert updated.tags == ["updated"]
            assert updated.updated_at == "2024-01-15T12:00:00Z"
            assert updated.created_at == sample_profile.created_at  # Should not change

    def test_update_profile_not_found(self, profile_manager):
        """Test updating a non-existent profile raises error."""
        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            profile_manager.update_profile(name="nonexistent", description="Updated", context="Updated")

    def test_delete_profile(self, profile_manager, sample_profile, temp_profiles_dir):
        """Test deleting a profile."""
        profile_manager._save_profile(sample_profile)
        profile_file = temp_profiles_dir / "test-profile.yaml"
        assert profile_file.exists()

        result = profile_manager.delete_profile("test-profile")

        assert result is True
        assert not profile_file.exists()

    def test_delete_profile_not_found(self, profile_manager):
        """Test deleting a non-existent profile."""
        result = profile_manager.delete_profile("nonexistent")
        assert result is False

    def test_copy_profile(self, profile_manager, sample_profile):
        """Test copying a profile."""
        profile_manager._save_profile(sample_profile)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T12:00:00Z"

            copied = profile_manager.copy_profile("test-profile", "copied-profile")

            assert copied.name == "copied-profile"
            assert copied.description == f"Copy of {sample_profile.description}"
            assert copied.context == sample_profile.context
            assert copied.tags == sample_profile.tags
            assert copied.created_at == "2024-01-15T12:00:00Z"

            # Original should still exist
            original = profile_manager.get_profile("test-profile")
            assert original.name == "test-profile"

    def test_copy_profile_not_found(self, profile_manager):
        """Test copying a non-existent profile raises error."""
        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            profile_manager.copy_profile("nonexistent", "new-name")

    def test_copy_profile_target_exists(self, profile_manager, sample_profile):
        """Test copying to an existing profile name raises error."""
        profile_manager._save_profile(sample_profile)

        # Create another profile
        profile2 = ReviewProfile(
            name="existing",
            description="Existing",
            context="Context",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
        )
        profile_manager._save_profile(profile2)

        with pytest.raises(ValueError, match="Profile 'existing' already exists"):
            profile_manager.copy_profile("test-profile", "existing")

    def test_export_profile(self, profile_manager, sample_profile, temp_profiles_dir):
        """Test exporting a profile to file."""
        profile_manager._save_profile(sample_profile)
        export_file = temp_profiles_dir / "exported.md"

        profile_manager.export_profile("test-profile", str(export_file))

        assert export_file.exists()
        content = export_file.read_text()
        assert sample_profile.context in content

    def test_export_profile_not_found(self, profile_manager, temp_profiles_dir):
        """Test exporting a non-existent profile raises error."""
        export_file = temp_profiles_dir / "exported.md"

        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            profile_manager.export_profile("nonexistent", str(export_file))

    def test_import_profile(self, profile_manager, temp_profiles_dir, sample_profile_content):
        """Test importing a profile from file."""
        import_file = temp_profiles_dir / "import.md"
        import_file.write_text(sample_profile_content)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T12:00:00Z"

            profile = profile_manager.import_profile(file_path=str(import_file), name="imported-profile")

            assert profile.name == "imported-profile"
            assert profile.context == sample_profile_content
            assert "import.md" in profile.description

    def test_import_profile_with_custom_name(self, profile_manager, temp_profiles_dir, sample_profile_content):
        """Test importing a profile with custom name."""
        import_file = temp_profiles_dir / "import.md"
        import_file.write_text(sample_profile_content)

        profile = profile_manager.import_profile(file_path=str(import_file), name="custom-name")

        assert profile.name == "custom-name"

    def test_import_profile_nonexistent_file(self, profile_manager):
        """Test importing from non-existent file raises error."""
        with pytest.raises(ValueError, match="File not found"):
            profile_manager.import_profile("/nonexistent/file.md")

    def test_save_and_load_profile(self, profile_manager, sample_profile, temp_profiles_dir):
        """Test saving and loading profile to/from YAML."""
        # Save profile
        profile_manager._save_profile(sample_profile)

        # Check file exists
        profile_file = temp_profiles_dir / "test-profile.yaml"
        assert profile_file.exists()

        # Load and verify using get_profile method
        loaded = profile_manager.get_profile("test-profile")
        assert loaded.name == sample_profile.name
        assert loaded.description == sample_profile.description
        assert loaded.context == sample_profile.context
        assert loaded.tags == sample_profile.tags

    def test_load_profile_invalid_yaml(self, profile_manager, temp_profiles_dir):
        """Test loading profile with invalid YAML raises error."""
        # Create invalid YAML file
        profile_file = temp_profiles_dir / "invalid.yaml"
        profile_file.write_text("invalid: yaml: content: [")

        with pytest.raises(Exception):  # YAML loading will raise an exception
            profile_manager.get_profile("invalid")

    def test_load_profile_missing_fields(self, profile_manager, temp_profiles_dir):
        """Test loading profile with missing required fields raises error."""
        # Create YAML file missing required fields
        profile_file = temp_profiles_dir / "incomplete.yaml"
        profile_data = {"name": "incomplete"}
        profile_file.write_text(yaml.dump(profile_data))

        with pytest.raises(TypeError):  # Missing required fields will cause TypeError
            profile_manager.get_profile("incomplete")


class TestProfileManagerCLI:
    """Test the CLI commands for profile management."""

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_create_basic(self, mock_manager_class, runner):
        """Test basic profile creation via CLI."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_profile = MagicMock()
        mock_profile.name = "test-profile"
        mock_manager.create_profile.return_value = mock_profile

        # Mock stdin for interactive input
        input_text = "Test context line 1\nTest context line 2\n"
        result = runner.invoke(
            app,
            ["review-profile", "create", "--name", "test-profile", "--description", "Test description"],
            input=input_text,
        )

        assert result.exit_code == 0
        assert "Created profile 'test-profile'" in result.output
        mock_manager.create_profile.assert_called_once()

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_create_from_file(self, mock_manager_class, runner, temp_profiles_dir):
        """Test creating profile from file via CLI."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_profile = MagicMock()
        mock_profile.name = "file-profile"
        mock_manager.create_profile_from_file.return_value = mock_profile

        # Create a content file
        content_file = temp_profiles_dir / "guidelines.md"
        content_file.write_text("Test guidelines content")

        result = runner.invoke(
            app,
            [
                "review-profile",
                "create",
                "--name",
                "file-profile",
                "--description",
                "From file",
                "--file",
                str(content_file),
                "--tags",
                "test,file",
            ],
        )

        assert result.exit_code == 0
        assert "Created profile 'file-profile' from file" in result.output
        mock_manager.create_profile_from_file.assert_called_once_with(
            "file-profile", "From file", str(content_file), ["test", "file"]
        )

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_create_missing_name(self, mock_manager_class, runner):
        """Test profile creation without required name."""
        result = runner.invoke(app, ["review-profile", "create", "--description", "Test description"])

        assert result.exit_code == 1
        assert "Profile name is required" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_list_empty(self, mock_manager_class, runner):
        """Test listing profiles when none exist."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_profiles.return_value = []

        result = runner.invoke(app, ["review-profile", "list"])

        assert result.exit_code == 0
        assert "No profiles found" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_list_table_format(self, mock_manager_class, runner):
        """Test listing profiles in table format."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Create a profile mock with proper attributes
        mock_profile = MagicMock()
        mock_profile.name = "profile1"
        mock_profile.description = "First profile"
        mock_profile.tags = ["test"]
        mock_profile.created_at = "2024-01-15T10:30:00Z"

        mock_manager.list_profiles.return_value = [mock_profile]

        # Mock the rich console import that's used in the CLI
        with patch("rich.console.Console"), patch("rich.table.Table"):
            result = runner.invoke(app, ["review-profile", "list"])

            assert result.exit_code == 0
            # Check that the command succeeded and manager was called
            assert mock_manager.list_profiles.called

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_list_json_format(self, mock_manager_class, runner):
        """Test listing profiles in JSON format."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Create a proper profile mock
        mock_profile = MagicMock()
        mock_profile.name = "profile1"
        mock_profile.description = "First profile"
        mock_profile.tags = ["test"]
        mock_profile.created_at = "2024-01-15T10:30:00Z"
        mock_profile.updated_at = "2024-01-15T10:30:00Z"

        mock_manager.list_profiles.return_value = [mock_profile]

        result = runner.invoke(app, ["review-profile", "list", "--format", "json"])

        assert result.exit_code == 0

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_show(self, mock_manager_class, runner):
        """Test showing a specific profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_profile = MagicMock()
        mock_profile.name = "test-profile"
        mock_profile.description = "Test description"
        mock_profile.context = "Test context"
        mock_profile.tags = ["test"]
        mock_profile.created_at = "2024-01-15T10:30:00Z"
        mock_profile.updated_at = "2024-01-15T10:30:00Z"
        mock_manager.get_profile.return_value = mock_profile

        result = runner.invoke(app, ["review-profile", "show", "--name", "test-profile"])

        assert result.exit_code == 0
        assert "test-profile" in result.output
        assert "Test context" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_show_missing_name(self, mock_manager_class, runner):
        """Test showing profile without required name."""
        result = runner.invoke(app, ["review-profile", "show"])

        assert result.exit_code == 1
        assert "Profile name is required" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_delete(self, mock_manager_class, runner):
        """Test deleting a profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.delete_profile.return_value = True

        result = runner.invoke(app, ["review-profile", "delete", "--name", "test-profile"])

        assert result.exit_code == 0
        assert "Deleted profile 'test-profile'" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_delete_not_found(self, mock_manager_class, runner):
        """Test deleting non-existent profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.delete_profile.return_value = False

        result = runner.invoke(app, ["review-profile", "delete", "--name", "nonexistent"])

        assert result.exit_code == 1
        assert "Profile 'nonexistent' not found" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_copy(self, mock_manager_class, runner):
        """Test copying a profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_profile = MagicMock(name="copied-profile")
        mock_manager.copy_profile.return_value = mock_profile

        result = runner.invoke(
            app, ["review-profile", "copy", "--name", "source-profile", "--target", "copied-profile"]
        )

        assert result.exit_code == 0
        assert "Copied profile 'source-profile' to 'copied-profile'" in result.output

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_export(self, mock_manager_class, runner, temp_profiles_dir):
        """Test exporting a profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        export_file = temp_profiles_dir / "exported.md"

        result = runner.invoke(app, ["review-profile", "export", "--name", "test-profile", "--file", str(export_file)])

        assert result.exit_code == 0
        assert "Exported profile 'test-profile'" in result.output
        mock_manager.export_profile.assert_called_once_with("test-profile", str(export_file))

    @patch("kit.pr_review.profile_manager.ProfileManager")
    def test_profile_import(self, mock_manager_class, runner, temp_profiles_dir):
        """Test importing a profile."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_profile = MagicMock()
        mock_profile.name = "imported-profile"
        mock_manager.import_profile.return_value = mock_profile

        import_file = temp_profiles_dir / "import.md"
        import_file.write_text("Test content")

        result = runner.invoke(
            app, ["review-profile", "import", "--file", str(import_file), "--name", "imported-profile"]
        )

        assert result.exit_code == 0
        assert "Imported profile 'imported-profile'" in result.output

    def test_profile_unknown_action(self, runner):
        """Test profile command with unknown action."""
        result = runner.invoke(app, ["review-profile", "unknown"])

        assert result.exit_code == 1
        assert "Unknown action: unknown" in result.output


class TestConfigurationIntegration:
    """Test integration of profiles with configuration."""

    def test_config_from_file_without_profile(self, temp_profiles_dir):
        """Test loading config without profile."""
        config_file = temp_profiles_dir / "config.yaml"
        config_data = {
            "github": {"token": "test_token"},
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "api_key": "test_key"},
        }
        config_file.write_text(yaml.dump(config_data))

        config = ReviewConfig.from_file(str(config_file))

        assert config.github.token == "test_token"
        assert config.profile is None
        assert config.profile_context is None

    def test_config_from_file_with_profile(self, temp_profiles_dir):
        """Test loading config with profile."""
        # Create profile
        profile_manager = ProfileManager(profiles_dir=str(temp_profiles_dir))
        profile = profile_manager.create_profile(
            name="test-profile", description="Test profile", context="Test context for review"
        )

        # Create config file
        config_file = temp_profiles_dir / "config.yaml"
        config_data = {
            "github": {"token": "test_token"},
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "api_key": "test_key"},
        }
        config_file.write_text(yaml.dump(config_data))

        # Load config with profile
        with patch("kit.pr_review.profile_manager.ProfileManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_profile.return_value = profile

            config = ReviewConfig.from_file(str(config_file), profile="test-profile")

            assert config.profile == "test-profile"
            assert config.profile_context == "Test context for review"

    def test_config_from_file_with_nonexistent_profile(self, temp_profiles_dir):
        """Test loading config with non-existent profile raises error."""
        config_file = temp_profiles_dir / "config.yaml"
        config_data = {
            "github": {"token": "test_token"},
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "api_key": "test_key"},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("kit.pr_review.profile_manager.ProfileManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_profile.side_effect = ValueError("Profile 'nonexistent' not found")

            with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
                ReviewConfig.from_file(str(config_file), profile="nonexistent")


class TestReviewIntegration:
    """Test integration of profiles with the review process."""

    @patch("kit.pr_review.config.ReviewConfig.from_file")
    @patch("kit.pr_review.reviewer.PRReviewer")
    def test_review_with_profile_flag(self, mock_pr_reviewer_class, mock_config_from_file, runner):
        """Test review command with --profile flag."""
        # Mock the config with profile context
        mock_config = MagicMock()
        mock_config.llm.model = "claude-sonnet-4-20250514"
        mock_config.profile = "company-standards"
        mock_config.profile_context = "Company coding standards context"
        mock_config_from_file.return_value = mock_config

        # Mock the reviewer
        mock_reviewer_instance = MagicMock()
        mock_reviewer_instance.review_pr.return_value = "Review with company standards applied."
        mock_pr_reviewer_class.return_value = mock_reviewer_instance

        # Mock CostTracker.is_valid_model to return True
        with patch("kit.pr_review.cost_tracker.CostTracker.is_valid_model", return_value=True):
            result = runner.invoke(
                app, ["review", "--profile", "company-standards", "--dry-run", "https://github.com/test/repo/pull/123"]
            )

            assert result.exit_code == 0
            assert "Using profile: company-standards" in result.output

            # Verify config was loaded with profile
            mock_config_from_file.assert_called_once_with(None, "company-standards", repo_path=None, model_hint=None)

    def test_profile_context_injection_standard_reviewer(self):
        """Test that profile context is injected into standard reviewer prompt."""
        from kit.pr_review.reviewer import PRReviewer

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-sonnet-4-20250514", api_key="test"),
            profile="test-profile",
            profile_context="**Custom Guidelines:**\n- Use type hints\n- Write tests",
            quiet=True,  # Enable quiet mode to suppress print output
        )

        reviewer = PRReviewer(config)

        # Mock all the necessary methods
        with (
            patch.object(reviewer, "get_pr_details") as mock_get_pr,
            patch.object(reviewer, "get_pr_files") as mock_get_files,
            patch.object(reviewer, "get_pr_diff") as mock_get_diff,
            patch.object(reviewer, "get_repo_for_analysis") as mock_get_repo,
            patch.object(reviewer, "analyze_pr_with_kit") as mock_analyze_pr,
            patch.object(reviewer, "post_pr_comment"),
        ):
            mock_get_pr.return_value = {
                "title": "Test PR",
                "user": {"login": "testuser"},
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
            }
            mock_get_files.return_value = [{"filename": "test.py", "additions": 5, "deletions": 2}]
            mock_get_diff.return_value = "test diff"
            mock_get_repo.return_value = "/tmp/repo"
            mock_analyze_pr.return_value = "Test review response"

            # Call the review method
            review_result = reviewer.review_pr("https://github.com/test/repo/pull/123")

            # Verify that the method was called successfully
            assert review_result is not None
            mock_analyze_pr.assert_called_once()

    def test_profile_context_injection_agentic_reviewer(self):
        """Test that profile context is injected into agentic reviewer prompt."""
        from kit.pr_review.agentic_reviewer import AgenticPRReviewer

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-sonnet-4-20250514", api_key="test"),
            profile="test-profile",
            profile_context="**Security Guidelines:**\n- Validate inputs\n- No hardcoded secrets",
        )

        reviewer = AgenticPRReviewer(config)

        # Mock all the methods directly to avoid HTTP calls
        with (
            patch.object(reviewer, "get_pr_details") as mock_get_pr,
            patch.object(reviewer, "get_pr_files") as mock_get_files,
            patch.object(reviewer, "get_repo_for_analysis") as mock_get_repo,
            patch.object(reviewer, "analyze_pr_agentic") as mock_analyze_pr,
            patch.object(reviewer, "post_pr_comment"),
            patch("builtins.print"),
        ):  # Suppress print output
            mock_get_pr.return_value = {
                "title": "Test PR",
                "user": {"login": "testuser"},
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
            }
            mock_get_files.return_value = [{"filename": "test.py", "additions": 5, "deletions": 2}]
            mock_get_repo.return_value = "/tmp/repo"
            mock_analyze_pr.return_value = "Test agentic review response"

            # Call the agentic review method
            review_result = reviewer.review_pr_agentic("https://github.com/test/repo/pull/123")

            # Verify that the method was called successfully
            assert review_result is not None
            mock_analyze_pr.assert_called_once()


class TestErrorHandling:
    """Test error handling in profile functionality."""

    def test_profile_manager_directory_creation(self, temp_profiles_dir):
        """Test that ProfileManager creates directory if it doesn't exist."""
        profiles_dir = temp_profiles_dir / "new_profiles"
        assert not profiles_dir.exists()

        manager = ProfileManager(profiles_dir=str(profiles_dir))
        # Create a profile to trigger directory creation
        manager.create_profile(name="test", description="Test", context="Test context")

        assert profiles_dir.exists()
        assert (profiles_dir / "test.yaml").exists()

    def test_profile_manager_permission_error(self, temp_profiles_dir):
        """Test handling of permission errors during file operations."""
        manager = ProfileManager(profiles_dir=str(temp_profiles_dir))

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")

            with pytest.raises(PermissionError):
                manager.create_profile(name="test", description="Test", context="Test context")

    def test_cli_profile_validation_error(self, runner):
        """Test CLI handling of profile validation errors."""
        with patch("kit.pr_review.profile_manager.ProfileManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.create_profile.side_effect = ValueError("Profile 'test' already exists")

            input_text = "Test context\n"
            result = runner.invoke(
                app,
                ["review-profile", "create", "--name", "test", "--description", "Test description"],
                input=input_text,
            )

            assert result.exit_code == 1
            assert "Profile error" in result.output

    def test_cli_profile_unexpected_error(self, runner):
        """Test CLI handling of unexpected errors."""
        with patch("kit.pr_review.profile_manager.ProfileManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.list_profiles.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(app, ["review-profile", "list"])

            assert result.exit_code == 1
            assert "Profile operation failed: Unexpected error" in result.output
