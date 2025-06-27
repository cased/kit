"""Tests for the dependencies CLI command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kit.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_output_file():
    """Create a temporary output file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_repository():
    """Create a mock repository with dependency analyzer."""
    repo = MagicMock()
    analyzer = MagicMock()

    # Mock dependency graph
    mock_graph = {
        "kit.repository": {
            "type": "internal",
            "path": "/src/kit/repository.py",
            "dependencies": ["kit.utils", "pathlib"],
        },
        "kit.utils": {"type": "internal", "path": "/src/kit/utils.py", "dependencies": ["os", "sys"]},
        "aws_instance.web": {"type": "resource", "path": "/infrastructure/main.tf", "dependencies": ["aws_vpc.main"]},
        "aws_vpc.main": {"type": "resource", "path": "/infrastructure/vpc.tf", "dependencies": []},
        "pathlib": {"type": "external", "dependencies": []},
        "os": {"type": "external", "dependencies": []},
        "sys": {"type": "external", "dependencies": []},
    }

    analyzer.build_dependency_graph.return_value = mock_graph
    analyzer.find_cycles.return_value = []
    analyzer.export_dependency_graph.return_value = '{"mock": "data"}'
    analyzer.get_module_dependencies.return_value = ["kit.utils", "pathlib"]
    analyzer.get_dependents.return_value = []
    analyzer.get_resource_dependencies.return_value = ["aws_vpc.main"]
    analyzer.generate_llm_context.return_value = "Mock LLM context"
    analyzer.visualize_dependencies.return_value = "/path/to/viz.png"

    repo.get_dependency_analyzer.return_value = analyzer
    return repo, analyzer


class TestDependenciesCommand:
    """Test cases for the dependencies CLI command."""

    def test_missing_language_parameter(self, runner):
        """Test that missing --language parameter shows error."""
        result = runner.invoke(app, ["dependencies", "."])
        assert result.exit_code != 0
        # Be flexible about colorized output and message variants
        output_lower = result.output.lower()
        assert "missing" in output_lower and "language" in output_lower

    def test_invalid_language(self, runner):
        """Test error handling for invalid language."""
        with patch("kit.Repository"):
            result = runner.invoke(app, ["dependencies", ".", "--language", "invalid"])
            assert result.exit_code == 1
            assert "Unsupported language: invalid" in result.output
            assert "python, terraform" in result.output

    @patch("kit.Repository")
    def test_basic_python_analysis(self, mock_repo_class, runner, mock_repository):
        """Test basic Python dependency analysis."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python"])

        assert result.exit_code == 0
        assert "Analyzing python dependencies" in result.output
        assert "Found 7 components in the dependency graph" in result.output
        assert "2 internal, 5 external dependencies" in result.output

        # Verify calls
        mock_repo_class.assert_called_once_with(".", ref=None)
        repo.get_dependency_analyzer.assert_called_once_with("python")
        analyzer.build_dependency_graph.assert_called_once()
        analyzer.export_dependency_graph.assert_called_once_with(output_format="json", output_path=None)

    @patch("kit.Repository")
    def test_basic_terraform_analysis(self, mock_repo_class, runner, mock_repository):
        """Test basic Terraform dependency analysis."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "terraform"])

        assert result.exit_code == 0
        assert "Analyzing terraform dependencies" in result.output
        repo.get_dependency_analyzer.assert_called_once_with("terraform")

    @patch("kit.Repository")
    def test_cycles_detection_with_cycles(self, mock_repo_class, runner, mock_repository):
        """Test cycle detection when cycles exist."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        # Mock cycles
        analyzer.find_cycles.return_value = [
            ["kit.module_a", "kit.module_b", "kit.module_c"],
            ["kit.utils", "kit.helpers"],
        ]

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--cycles"])

        assert result.exit_code == 0
        assert "Found 2 circular dependencies" in result.output
        assert "kit.module_a → kit.module_b → kit.module_c → kit.module_a" in result.output
        assert "kit.utils → kit.helpers → kit.utils" in result.output

    @patch("kit.Repository")
    def test_cycles_detection_no_cycles(self, mock_repo_class, runner, mock_repository):
        """Test cycle detection when no cycles exist."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--cycles"])

        assert result.exit_code == 0
        assert "No circular dependencies found!" in result.output

    @patch("kit.Repository")
    def test_cycles_output_to_file(self, mock_repo_class, runner, mock_repository, temp_output_file):
        """Test cycles detection with file output."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        analyzer.find_cycles.return_value = [["module_a", "module_b"]]

        result = runner.invoke(
            app, ["dependencies", ".", "--language", "python", "--cycles", "--output", temp_output_file]
        )

        assert result.exit_code == 0
        assert f"Cycles data written to {temp_output_file}" in result.output

        # Check file content
        with open(temp_output_file) as f:
            data = json.load(f)
        assert data["cycles_count"] == 1
        assert len(data["cycles"]) == 1
        assert data["cycles"][0]["components"] == ["module_a", "module_b"]

    @patch("kit.Repository")
    def test_module_analysis_python(self, mock_repo_class, runner, mock_repository):
        """Test module-specific analysis for Python."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--module", "kit.repository"])

        assert result.exit_code == 0
        assert "Analyzing dependencies for: kit.repository" in result.output
        assert "Direct dependencies (2):" in result.output
        assert "kit.utils (internal)" in result.output
        assert "pathlib (external)" in result.output

        analyzer.get_module_dependencies.assert_called_with("kit.repository", include_indirect=False)
        analyzer.get_dependents.assert_called_with("kit.repository", include_indirect=False)

    @patch("kit.Repository")
    def test_module_analysis_with_indirect(self, mock_repo_class, runner, mock_repository):
        """Test module analysis with indirect dependencies."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(
            app, ["dependencies", ".", "--language", "python", "--module", "kit.repository", "--include-indirect"]
        )

        assert result.exit_code == 0
        assert "All dependencies (2):" in result.output

        analyzer.get_module_dependencies.assert_called_with("kit.repository", include_indirect=True)
        analyzer.get_dependents.assert_called_with("kit.repository", include_indirect=True)

    @patch("kit.Repository")
    def test_module_analysis_terraform(self, mock_repo_class, runner, mock_repository):
        """Test module-specific analysis for Terraform."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "terraform", "--module", "aws_instance.web"])

        assert result.exit_code == 0
        assert "Analyzing dependencies for: aws_instance.web" in result.output

        analyzer.get_resource_dependencies.assert_called_with("aws_instance.web", include_indirect=False)

    @patch("kit.Repository")
    def test_module_not_found(self, mock_repo_class, runner, mock_repository):
        """Test error when module is not found."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--module", "nonexistent.module"])

        assert result.exit_code == 1
        assert "Module/resource 'nonexistent.module' not found in dependency graph" in result.output

    @patch("kit.Repository")
    def test_llm_context_generation(self, mock_repo_class, runner, mock_repository):
        """Test LLM context generation."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--llm-context"])

        assert result.exit_code == 0
        assert "Generating LLM-friendly context" in result.output
        assert "LLM CONTEXT" in result.output
        assert "Mock LLM context" in result.output

        analyzer.generate_llm_context.assert_called_once_with(output_format="text")

    @patch("kit.Repository")
    def test_llm_context_markdown_output(self, mock_repo_class, runner, mock_repository, temp_output_file):
        """Test LLM context generation with markdown output."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        md_file = temp_output_file.replace(".json", ".md")

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--llm-context", "--output", md_file])

        assert result.exit_code == 0
        assert f"LLM context written to {md_file}" in result.output

        analyzer.generate_llm_context.assert_called_once_with(output_format="markdown")

    @patch("kit.Repository")
    def test_different_output_formats(self, mock_repo_class, runner, mock_repository, temp_output_file):
        """Test different output formats."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        formats = ["json", "dot", "graphml", "adjacency"]

        for fmt in formats:
            result = runner.invoke(
                app, ["dependencies", ".", "--language", "python", "--format", fmt, "--output", temp_output_file]
            )

            assert result.exit_code == 0
            assert f"Dependency graph exported to {temp_output_file} ({fmt} format)" in result.output

            analyzer.export_dependency_graph.assert_called_with(output_format=fmt, output_path=temp_output_file)

    @patch("kit.Repository")
    def test_visualization_flag(self, mock_repo_class, runner, mock_repository):
        """Test visualization flag."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--visualize"])

        assert result.exit_code == 0
        assert "Generating visualization (png)" in result.output
        assert "Visualization saved to" in result.output

        analyzer.visualize_dependencies.assert_called_once()

    @patch("kit.Repository")
    def test_visualization_different_formats(self, mock_repo_class, runner, mock_repository):
        """Test visualization with different formats."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        formats = ["png", "svg", "pdf"]

        for fmt in formats:
            result = runner.invoke(
                app, ["dependencies", ".", "--language", "python", "--visualize", "--viz-format", fmt]
            )

            assert result.exit_code == 0
            assert f"Generating visualization ({fmt})" in result.output

    @patch("kit.Repository")
    def test_visualization_failure(self, mock_repo_class, runner, mock_repository):
        """Test visualization failure handling."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        analyzer.visualize_dependencies.side_effect = Exception("Graphviz not found")

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--visualize"])

        assert result.exit_code == 0  # Should not fail completely
        assert "Visualization failed: Graphviz not found" in result.output
        assert "Make sure Graphviz is installed" in result.output

    @patch("kit.Repository")
    def test_git_ref_parameter(self, mock_repo_class, runner, mock_repository):
        """Test git ref parameter."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--ref", "v1.0.0"])

        assert result.exit_code == 0
        mock_repo_class.assert_called_once_with(".", ref="v1.0.0")

    @patch("kit.Repository")
    def test_repository_creation_error(self, mock_repo_class, runner):
        """Test error handling when repository creation fails."""
        mock_repo_class.side_effect = Exception("Invalid repository path")

        result = runner.invoke(app, ["dependencies", "/invalid/path", "--language", "python"])

        assert result.exit_code == 1
        assert "Dependency analysis failed: Invalid repository path" in result.output

    @patch("kit.Repository")
    def test_analyzer_error(self, mock_repo_class, runner, mock_repository):
        """Test error handling when analyzer fails."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        analyzer.build_dependency_graph.side_effect = Exception("Analysis failed")

        result = runner.invoke(app, ["dependencies", ".", "--language", "python"])

        assert result.exit_code == 1
        assert "Dependency analysis failed: Analysis failed" in result.output

    @patch("kit.Repository")
    def test_file_output_basic(self, mock_repo_class, runner, mock_repository, temp_output_file):
        """Test basic file output."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "python", "--output", temp_output_file])

        assert result.exit_code == 0
        assert f"Dependency graph exported to {temp_output_file}" in result.output

        analyzer.export_dependency_graph.assert_called_with(output_format="json", output_path=temp_output_file)

    @patch("kit.Repository")
    def test_module_output_to_file(self, mock_repo_class, runner, mock_repository, temp_output_file):
        """Test module analysis with file output."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(
            app,
            ["dependencies", ".", "--language", "python", "--module", "kit.repository", "--output", temp_output_file],
        )

        assert result.exit_code == 0
        assert f"Module analysis written to {temp_output_file}" in result.output

        # Check file content
        with open(temp_output_file) as f:
            data = json.load(f)
        assert data["module"] == "kit.repository"
        assert data["language"] == "python"
        assert "dependencies" in data
        assert "dependents" in data

    @patch("kit.Repository")
    def test_cycles_warning_in_normal_mode(self, mock_repo_class, runner, mock_repository):
        """Test that cycles warning appears in normal dependency analysis."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        analyzer.find_cycles.return_value = [["module_a", "module_b"]]

        result = runner.invoke(app, ["dependencies", ".", "--language", "python"])

        assert result.exit_code == 0
        assert "Warning: 1 circular dependencies detected" in result.output
        assert "Run with --cycles to see details" in result.output

    @patch("kit.Repository")
    def test_case_insensitive_language(self, mock_repo_class, runner, mock_repository):
        """Test that language parameter is case insensitive."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        result = runner.invoke(app, ["dependencies", ".", "--language", "PYTHON"])

        assert result.exit_code == 0
        repo.get_dependency_analyzer.assert_called_once_with("python")

    @patch("kit.Repository")
    def test_short_option_flags(self, mock_repo_class, runner, mock_repository):
        """Test short option flags work correctly."""
        repo, analyzer = mock_repository
        mock_repo_class.return_value = repo

        # Test without conflicting flags (cycles and module are mutually exclusive)
        result = runner.invoke(app, ["dependencies", ".", "-l", "python", "-v", "-m", "kit.repository", "-i"])

        assert result.exit_code == 0
        assert "Generating visualization" in result.output
        assert "Analyzing dependencies for: kit.repository" in result.output

        analyzer.get_module_dependencies.assert_called_with("kit.repository", include_indirect=True)


class TestDependenciesIntegration:
    """Integration tests that test against real repositories."""

    def test_help_output(self, runner):
        """Test that help output includes the new command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "dependencies" in result.output
        # Test for the command being listed, the exact help text might be formatted differently
        assert "dependencies" in result.output.lower()

    def test_dependencies_help(self, runner):
        """Test dependencies command help."""
        result = runner.invoke(app, ["dependencies", "--help"])
        assert result.exit_code == 0

        # Normalize output to lowercase for case-insensitive matching and strip ANSI codes
        import re

        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        clean_output = ansi_escape.sub("", result.output).lower()

        # Check essential help content
        assert "analyze and visualize code dependencies" in clean_output
        assert "python" in clean_output and "terraform" in clean_output

        # Check key options (no strict '--' required due to formatting differences)
        for keyword in ["language", "cycles", "visualize", "llm", "module"]:
            assert keyword in clean_output


if __name__ == "__main__":
    pytest.main([__file__])
