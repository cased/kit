"""Commit message generator implementation with repository intelligence and LLM analysis."""

import asyncio
import subprocess
from typing import Any, Dict, List

from kit import Repository

from .config import LLMProvider, ReviewConfig
from .cost_tracker import CostTracker


class CommitMessageGenerator:
    """Generate intelligent commit messages using repository context and LLM analysis."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.cost_tracker = CostTracker(config.custom_pricing)
        self._llm_client: Any = None

    def get_staged_diff(self) -> str:
        """Get the diff of staged changes."""
        try:
            result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get staged diff: {e}")

    def get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
            )
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get staged files: {e}")

    def check_staged_changes(self) -> bool:
        """Check if there are any staged changes."""
        staged_files = self.get_staged_files()
        return len(staged_files) > 0

    async def analyze_changes_for_commit(self, repo_path: str) -> str:
        """Analyze staged changes using repository intelligence to generate commit message."""
        repo = Repository(repo_path)

        # Get staged changes
        diff = self.get_staged_diff()
        staged_files = self.get_staged_files()

        if not diff.strip():
            return "No staged changes to commit"

        # Analyze changed files with repository context
        file_analysis: Dict[str, Dict[str, Any]] = {}
        change_types = set()

        for file_path in staged_files:
            try:
                # Get symbols from the file
                file_symbols = repo.extract_symbols(file_path)

                # Determine change type based on file extension and content
                if file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs")):
                    change_types.add("code")
                elif file_path.endswith((".md", ".txt", ".rst")):
                    change_types.add("docs")
                elif file_path.endswith((".yaml", ".yml", ".json", ".toml", ".ini")):
                    change_types.add("config")
                elif file_path.endswith((".test.py", ".spec.js", ".test.ts")):
                    change_types.add("test")

                file_analysis[file_path] = {
                    "symbols": file_symbols[:3],  # Top 3 symbols
                    "symbol_count": len(file_symbols),
                }

            except Exception:
                file_analysis[file_path] = {"symbols": [], "symbol_count": 0}

        # Create commit message generation prompt
        commit_prompt = f"""You are an expert developer writing a concise, clear commit message.

**Changes Overview:**
- Files changed: {len(staged_files)}
- Change types: {", ".join(change_types) if change_types else "general"}

**File Analysis:**"""

        # Limit to 5 files and ensure proper typing
        file_items = list(file_analysis.items())[:5]
        for file_path, analysis in file_items:
            commit_prompt += f"""
- {file_path}: {analysis["symbol_count"]} symbols"""
            if analysis["symbols"]:
                symbol_names = [s["name"] for s in analysis["symbols"]]
                commit_prompt += f" ({', '.join(symbol_names)})"

        commit_prompt += f"""

**Diff (first 2000 chars):**
```diff
{diff[:2000]}{"..." if len(diff) > 2000 else ""}
```

**Generate a commit message following these guidelines:**
1. First line: concise summary (50 chars max, no period)
2. If needed, add a blank line then detailed explanation
3. Use imperative mood ("Add feature" not "Added feature")
4. Focus on WHY and WHAT, not HOW
5. Use conventional commit prefixes when appropriate (feat:, fix:, docs:, refactor:, test:)

**Examples of good commit messages:**
- feat: add user authentication with JWT tokens
- fix: resolve memory leak in data processing pipeline
- docs: update API documentation for v2 endpoints
- refactor: extract validation logic into separate module
- test: add integration tests for payment flow

Generate only the commit message, nothing else."""

        # Use LLM to generate commit message
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            message = await self._generate_with_anthropic(commit_prompt)
        elif self.config.llm.provider == LLMProvider.GOOGLE:
            message = await self._generate_with_google(commit_prompt)
        elif self.config.llm.provider == LLMProvider.OLLAMA:
            message = await self._generate_with_ollama(commit_prompt)
        else:
            message = await self._generate_with_openai(commit_prompt)

        return message.strip()

    async def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate commit message using Anthropic Claude."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        if not self._llm_client:
            self._llm_client = anthropic.Anthropic(api_key=self.config.llm.api_key)

        try:
            response = self._llm_client.messages.create(
                model=self.config.llm.model,
                max_tokens=200,  # Short for commit messages
                temperature=0.3,  # Slightly creative but consistent
                messages=[{"role": "user", "content": prompt}],
            )

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_anthropic_usage(response)
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
            )

            # Extract text from the response content
            text_content = ""
            for content_block in response.content:
                if hasattr(content_block, "text"):
                    text_content += content_block.text

            return text_content if text_content else "Update files"

        except Exception as e:
            return f"Update files (error: {e})"

    async def _generate_with_google(self, prompt: str) -> str:
        """Generate commit message using Google Gemini."""
        try:
            import google.genai as genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed. Run: pip install google-genai")

        if not self._llm_client:
            self._llm_client = genai.Client(api_key=self.config.llm.api_key)

        try:
            response = self._llm_client.models.generate_content(
                model=self.config.llm.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )

            # Track cost
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
                self.cost_tracker.track_llm_usage(
                    self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
                )

            result_text = response.text
            return result_text if result_text is not None else "Update files"

        except Exception as e:
            return f"Update files (error: {e})"

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate commit message using OpenAI GPT."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        if not self._llm_client:
            if self.config.llm.api_base_url:
                self._llm_client = openai.OpenAI(api_key=self.config.llm.api_key, base_url=self.config.llm.api_base_url)
            else:
                self._llm_client = openai.OpenAI(api_key=self.config.llm.api_key)

        try:
            response = self._llm_client.chat.completions.create(
                model=self.config.llm.model,
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_openai_usage(response)
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
            )

            content = response.choices[0].message.content
            return content if content is not None else "Update files"

        except Exception as e:
            return f"Update files (error: {e})"

    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate commit message using Ollama."""
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests package not installed. Run: pip install requests")

        if not self._llm_client:
            # Create Ollama client
            class OllamaClient:
                def __init__(self, base_url: str, model: str):
                    self.base_url = base_url
                    self.model = model
                    self.session = requests.Session()

                def generate(self, prompt: str, **kwargs) -> str:
                    """Generate text using Ollama's API."""
                    url = f"{self.base_url}/api/generate"
                    data = {"model": self.model, "prompt": prompt, "stream": False, **kwargs}
                    response = self.session.post(url, json=data)
                    response.raise_for_status()
                    return response.json().get("response", "")

            self._llm_client = OllamaClient(
                self.config.llm.api_base_url or "http://localhost:11434", self.config.llm.model
            )

        try:
            response = await asyncio.to_thread(
                self._llm_client.generate,
                prompt,
                temperature=0.3,
                num_predict=200,
            )

            # Track usage (free but good for statistics)
            estimated_input_tokens = len(prompt) // 4
            estimated_output_tokens = len(response) // 4
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, estimated_input_tokens, estimated_output_tokens
            )

            return response if response else "Update files"

        except Exception as e:
            return f"Update files (error: {e})"

    def commit_with_message(self, message: str) -> None:
        """Execute git commit with the generated message."""
        try:
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit: {e.stderr}")

    def generate_and_commit(self, repo_path: str = ".") -> str:
        """Generate commit message and commit changes in one step."""
        try:
            # Check for staged changes
            if not self.check_staged_changes():
                return "❌ No staged changes to commit. Use 'git add <files>' to stage changes."

            quiet = getattr(self.config, "quiet", False)

            if not quiet:
                print("🔍 Analyzing staged changes...")

            # Generate commit message
            message = asyncio.run(self.analyze_changes_for_commit(repo_path))

            if not quiet:
                print(f"💭 Generated message: {message}")
                print("📝 Committing changes...")

            # Commit with generated message
            self.commit_with_message(message)

            # Show cost if not quiet
            if not quiet:
                total_cost = self.cost_tracker.get_total_cost()
                if total_cost > 0:
                    print(f"💰 Cost: ${total_cost:.4f}")

            return f"✅ Committed with message: {message}"

        except Exception as e:
            return f"❌ Commit failed: {e}"
