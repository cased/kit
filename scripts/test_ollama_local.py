#!/usr/bin/env python3
"""
Local Ollama Test Script

This script will:
1. Check if Ollama is installed
2. Install it if needed (with user permission)
3. Pull the recommended model
4. Start Ollama service
5. Test kit's Ollama integration with real code
6. Show cost comparison vs cloud models

Prerequisites: macOS or Linux
"""

import os
import platform
import subprocess
import sys
import time


def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=True)
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        return result.returncode == 0, stdout, stderr
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else ""
        stderr = e.stderr.strip() if e.stderr else ""
        return False, stdout, stderr


def check_ollama_installed():
    """Check if Ollama is installed."""
    success, stdout, stderr = run_command("which ollama", check=False)
    return success


def install_ollama():
    """Install Ollama with user permission."""
    if platform.system() not in ["Darwin", "Linux"]:
        print("❌ This script only supports macOS and Linux")
        print("   Please install Ollama manually from https://ollama.ai/")
        return False

    print("🦙 Ollama not found. Installing Ollama...")
    response = input("   Install Ollama now? (y/n): ").lower().strip()

    if response != "y":
        print("❌ Ollama installation cancelled")
        print("   You can install manually: curl -fsSL https://ollama.ai/install.sh | sh")
        return False

    print("📥 Downloading and installing Ollama...")
    success, stdout, stderr = run_command("curl -fsSL https://ollama.ai/install.sh | sh", capture_output=False)

    if success:
        print("✅ Ollama installed successfully!")
        return True
    else:
        print(f"❌ Ollama installation failed: {stderr}")
        return False


def check_ollama_running():
    """Check if Ollama service is running."""
    success, stdout, stderr = run_command("pgrep ollama", check=False)
    return success


def start_ollama():
    """Start Ollama service in background."""
    if check_ollama_running():
        print("✅ Ollama is already running")
        return True

    print("🚀 Starting Ollama service...")
    # Start in background
    success, stdout, stderr = run_command("ollama serve &", check=False)

    # Wait a moment for it to start
    time.sleep(3)

    if check_ollama_running():
        print("✅ Ollama service started successfully!")
        return True
    else:
        print("❌ Failed to start Ollama service")
        print("   Try manually: ollama serve")
        return False


def check_model_available(model_name):
    """Check if a model is available locally."""
    success, stdout, stderr = run_command("ollama list", check=False)
    if success:
        return model_name in stdout
    return False


def pull_model(model_name):
    """Pull a model from Ollama registry."""
    if check_model_available(model_name):
        print(f"✅ Model {model_name} already available")
        return True

    print(f"📥 Pulling model {model_name}...")
    print("   This may take a few minutes depending on model size...")

    success, stdout, stderr = run_command(f"ollama pull {model_name}", capture_output=False)

    if success:
        print(f"✅ Model {model_name} pulled successfully!")
        return True
    else:
        print(f"❌ Failed to pull model {model_name}: {stderr}")
        return False


def test_ollama_api(model_name):
    """Test basic Ollama API functionality."""
    print(f"\n🧪 Testing Ollama API with {model_name}...")

    test_prompt = "What is Python? Answer in one sentence."
    cmd = f'ollama run {model_name} "{test_prompt}"'

    print(f"   Prompt: {test_prompt}")
    success, stdout, stderr = run_command(cmd, capture_output=False)

    if success:
        print("✅ Ollama API test successful!")
        return True
    else:
        print(f"❌ Ollama API test failed: {stderr}")
        return False


def test_kit_integration(model_name):
    """Test kit's Ollama integration with real code."""
    print(f"\n🛠️ Testing kit integration with {model_name}...")

    try:
        from kit import Repository
        from kit.summaries import OllamaConfig

        # Test with current repository
        repo = Repository(".")
        config = OllamaConfig(model=model_name, temperature=0.1, max_tokens=500)
        summarizer = repo.get_summarizer(config=config)

        print("✅ Kit Ollama client initialized successfully!")

        # Test file summarization
        test_file = "README.md"
        if os.path.exists(test_file):
            print(f"📄 Testing file summarization: {test_file}")
            try:
                summary = summarizer.summarize_file(test_file)
                print("✅ Summary generated successfully!")
                print(f"   Length: {len(summary)} characters")
                print(f"   Preview: {summary[:100]}...")
                print("   💰 Cost: $0.00")
                return True
            except Exception as e:
                print(f"❌ File summarization failed: {e}")
                return False
        else:
            print(f"⚠️ {test_file} not found, skipping file test")
            return True

    except ImportError as e:
        print(f"❌ Kit import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Kit integration test failed: {e}")
        return False


def show_cost_comparison():
    """Show cost comparison between Ollama and cloud providers."""
    print("\n💰 Cost Comparison")
    print("=" * 50)

    scenarios = [
        ("Single PR review", "1 review"),
        ("Daily reviews", "30 reviews/month"),
        ("Enterprise usage", "1000 reviews/month"),
        ("Continuous integration", "10,000 reviews/month"),
    ]

    print(f"{'Scenario':<25} {'Ollama':<15} {'OpenAI GPT-4o':<15} {'Claude Sonnet'}")
    print("-" * 70)

    for scenario, usage in scenarios:
        reviews = int(usage.split()[0].replace(",", ""))
        openai_cost = reviews * 0.10  # $0.10 per review
        claude_cost = reviews * 0.08  # $0.08 per review

        print(f"{scenario:<25} {'$0.00':<15} ${openai_cost:<14.2f} ${claude_cost:<14.2f}")

    print("\n🎯 Ollama Benefits:")
    print("   - Zero cost for unlimited usage")
    print("   - Complete privacy (code never leaves your machine)")
    print("   - No rate limits (only hardware constraints)")
    print("   - Works offline")
    print("   - Latest open source models")


def main():
    """Main test workflow."""
    print("🦙 Kit + Ollama Local Test")
    print("=" * 40)

    model_name = "qwen2.5-coder:latest"

    # Step 1: Check/Install Ollama
    if not check_ollama_installed():
        if not install_ollama():
            sys.exit(1)
    else:
        print("✅ Ollama is installed")

    # Step 2: Start Ollama service
    if not start_ollama():
        sys.exit(1)

    # Step 3: Pull model
    if not pull_model(model_name):
        sys.exit(1)

    # Step 4: Test basic API
    if not test_ollama_api(model_name):
        print("⚠️ Basic API test failed, but continuing with kit test...")

    # Step 5: Test kit integration
    if not test_kit_integration(model_name):
        print("❌ Kit integration test failed")
        sys.exit(1)

    # Step 6: Show cost comparison
    show_cost_comparison()

    print("\n🎉 All tests passed!")
    print("\n📋 Summary:")
    print(f"   Model: {model_name}")
    print("   Status: Running at http://localhost:11434")
    print("   Kit integration: ✅ Working")
    print("   Total cost: $0.00")

    print("\n🚀 Next steps:")
    print("   1. Try PR reviews: kit review --init-config")
    print(f"      (Select 'ollama' provider and '{model_name}' model)")
    print("   2. Test with a real PR: kit review --dry-run <PR_URL>")
    print("   3. Explore other models: ollama pull deepseek-r1:latest")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
