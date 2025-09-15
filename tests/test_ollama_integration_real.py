"""Integration tests for Ollama that make real API calls."""

import os
import subprocess
import time

import pytest
import requests

from kit import Repository
from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from kit.pr_review.cost_tracker import CostTracker
from kit.pr_review.reviewer import PRReviewer
from kit.summaries import OllamaConfig


def is_ci_environment():
    """Check if we're running in a CI environment."""
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "BUILDKITE",
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


def is_ollama_available():
    """Check if Ollama is installed and running."""
    try:
        # Check if ollama command exists
        subprocess.run(["which", "ollama"], check=True, capture_output=True)

        # Check if service is running by making a simple API call
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except (subprocess.CalledProcessError, requests.RequestException, FileNotFoundError):
        return False


def has_qwen_model():
    """Check if qwen2.5-coder:latest model is available."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        return "qwen2.5-coder:latest" in result.stdout
    except subprocess.CalledProcessError:
        return False


@pytest.fixture
def skip_if_no_ollama():
    """Skip test if Ollama is not available."""
    if is_ci_environment():
        pytest.skip("Skipping Ollama tests in CI environment (Ollama not available)")

    if not is_ollama_available():
        pytest.skip("Ollama not available - install with: curl -fsSL https://ollama.ai/install.sh | sh")

    if not has_qwen_model():
        pytest.skip("qwen2.5-coder:latest not available - install with: ollama pull qwen2.5-coder:latest")


class TestOllamaIntegration:
    """Integration tests for Ollama that make real API calls."""

    @pytest.fixture
    def ollama_config(self):
        """Create Ollama configuration for testing."""
        return OllamaConfig(model="qwen2.5-coder:latest", base_url="http://localhost:11434", max_tokens=500)

    @pytest.fixture
    def test_repo(self, tmp_path):
        """Create a temporary repository for testing."""
        # Create a simple Python file to summarize
        test_file = tmp_path / "test_module.py"
        test_file.write_text('''
"""Test module for Ollama integration."""

def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    """Utility class for mathematical operations."""

    @staticmethod
    def is_prime(n):
        """Check if a number is prime."""
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True
''')

        return Repository(str(tmp_path))

    @pytest.mark.integration
    @pytest.mark.skipif(is_ci_environment(), reason="Skip Ollama tests in CI")
    def test_ollama_file_summarization_real(self, skip_if_no_ollama, ollama_config, test_repo):
        """Test real file summarization with Ollama."""
        summarizer = test_repo.get_summarizer(config=ollama_config)

        # Test file summarization
        summary = summarizer.summarize_file("test_module.py")

        # Verify we got a real response
        assert summary is not None
        assert len(summary) > 50  # Should be a substantial summary
        assert "fibonacci" in summary.lower() or "math" in summary.lower()

        print(f"✅ Ollama file summary ({len(summary)} chars): {summary[:100]}...")
        print("💰 Cost: $0.00")

    @pytest.mark.integration
    @pytest.mark.skipif(is_ci_environment(), reason="Skip Ollama tests in CI")
    def test_ollama_function_summarization_real(self, skip_if_no_ollama, ollama_config, test_repo):
        """Test real function summarization with Ollama."""
        summarizer = test_repo.get_summarizer(config=ollama_config)

        # Test function summarization
        summary = summarizer.summarize_function("test_module.py", "calculate_fibonacci")

        # Verify we got a real response about the function
        assert summary is not None
        assert len(summary) > 20
        assert "fibonacci" in summary.lower()

        print(f"✅ Ollama function summary: {summary}")
        print("💰 Cost: $0.00")

    @pytest.mark.integration
    @pytest.mark.skipif(is_ci_environment(), reason="Skip Ollama tests in CI")
    def test_ollama_class_summarization_real(self, skip_if_no_ollama, ollama_config, test_repo):
        """Test real class summarization with Ollama."""
        summarizer = test_repo.get_summarizer(config=ollama_config)

        # Test class summarization
        summary = summarizer.summarize_class("test_module.py", "MathUtils")

        # Verify we got a real response about the class
        assert summary is not None
        assert len(summary) > 20
        assert "math" in summary.lower() or "utility" in summary.lower()

        print(f"✅ Ollama class summary: {summary}")
        print("💰 Cost: $0.00")

    @pytest.mark.integration
    @pytest.mark.expensive
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive Ollama tests in CI")
    def test_ollama_pr_review_simulation(self, skip_if_no_ollama):
        """Test Ollama integration with PR review workflow (simulation)."""
        # Create a review config with Ollama
        review_config = ReviewConfig(
            github=GitHubConfig(token="test_token"),  # Won't be used in simulation
            llm=LLMConfig(
                provider=LLMProvider.OLLAMA,
                model="qwen2.5-coder:latest",
                api_key="ollama",
                api_base_url="http://localhost:11434",
                max_tokens=1000,
            ),
        )

        # Test cost tracking
        tracker = CostTracker()
        tracker.track_llm_usage(LLMProvider.OLLAMA, "qwen2.5-coder:latest", 1500, 800)

        assert tracker.get_total_cost() == 0.0

        # Test that reviewer can be instantiated
        reviewer = PRReviewer(review_config)
        assert reviewer.config.llm.provider == LLMProvider.OLLAMA

        print("✅ Ollama PR reviewer configured")
        print(f"   Model: {review_config.llm.model}")
        print(f"   Provider: {review_config.llm.provider.value}")
        print("   Cost: $0.00")

    @pytest.mark.integration
    @pytest.mark.expensive
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive Ollama tests in CI")
    def test_ollama_api_direct(self, skip_if_no_ollama):
        """Test direct Ollama API communication."""
        # Test the actual HTTP API that our OllamaClient uses
        try:
            import requests

            url = "http://localhost:11434/api/generate"
            data = {
                "model": "qwen2.5-coder:latest",
                "prompt": "What is a Python function? Answer in one sentence.",
                "stream": False,
            }

            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            assert "response" in result
            assert len(result["response"]) > 10

            print("✅ Direct Ollama API test successful")
            print(f"   Response: {result['response'][:100]}...")
            print("   💰 Cost: $0.00")

        except Exception as e:
            pytest.fail(f"Direct Ollama API test failed: {e}")

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.skipif(is_ci_environment(), reason="Skip performance tests in CI")
    def test_ollama_performance_comparison(self, skip_if_no_ollama, ollama_config, test_repo):
        """Test Ollama performance and compare with expectations."""
        summarizer = test_repo.get_summarizer(config=ollama_config)

        # Time the summarization
        start_time = time.time()

        summary = summarizer.summarize_file("test_module.py")

        end_time = time.time()
        duration = end_time - start_time

        # Verify reasonable performance (should be under 30 seconds for small file)
        assert duration < 30, f"Ollama took too long: {duration}s"
        assert len(summary) > 30, "Summary too short"

        print("✅ Ollama performance test")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Summary length: {len(summary)} chars")
        print("   Cost: $0.00")


class TestOllamaErrorHandling:
    """Test Ollama error handling scenarios."""

    @pytest.mark.integration
    @pytest.mark.skipif(is_ci_environment(), reason="Skip Ollama tests in CI")
    def test_ollama_service_down(self, tmp_path):
        """Test behavior when Ollama service is down."""
        # Create config pointing to non-existent service
        config = OllamaConfig(
            model="qwen2.5-coder:latest",
            base_url="http://localhost:9999",  # Wrong port
            max_tokens=100,
        )

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): return 'world'")

        repo = Repository(str(tmp_path))
        summarizer = repo.get_summarizer(config=config)

        # Should handle connection error gracefully
        summary = summarizer.summarize_file("test.py")

        # Should return error message, not crash
        assert "error" in summary.lower() or "failed" in summary.lower()

        print("✅ Ollama error handling test passed")
        print(f"   Error summary: {summary}")

    @pytest.mark.integration
    @pytest.mark.skipif(is_ci_environment(), reason="Skip Ollama tests in CI")
    def test_ollama_invalid_model(self, skip_if_no_ollama, tmp_path):
        """Test behavior with invalid model name."""
        # Create config with non-existent model
        config = OllamaConfig(model="nonexistent-model:latest", base_url="http://localhost:11434", max_tokens=100)

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): return 'world'")

        repo = Repository(str(tmp_path))
        summarizer = repo.get_summarizer(config=config)

        # Should handle model error gracefully
        summary = summarizer.summarize_file("test.py")

        # Should return error message, not crash
        assert "error" in summary.lower() or "failed" in summary.lower()

        print("✅ Ollama invalid model test passed")
        print(f"   Error summary: {summary}")


# Utility functions for integration testing
def setup_ollama_for_testing():
    """Helper function to set up Ollama for testing."""
    print("🦙 Setting up Ollama for integration testing...")

    if not is_ollama_available():
        print("❌ Ollama not available")
        print("   Install: curl -fsSL https://ollama.ai/install.sh | sh")
        return False

    if not has_qwen_model():
        print("📥 Pulling qwen2.5-coder:latest...")
        try:
            subprocess.run(["ollama", "pull", "qwen2.5-coder:latest"], check=True)
            print("✅ Model pulled successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to pull model")
            return False

    print("✅ Ollama ready for testing")
    return True


if __name__ == "__main__":
    # Allow running this file directly to set up Ollama
    setup_ollama_for_testing()
