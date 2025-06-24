"""PR Reviewer implementation with GitHub API integration and LLM analysis."""

import asyncio
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import requests

from kit import Repository

from .cache import RepoCache
from .config import LLMProvider, ReviewConfig
from .cost_tracker import CostTracker
from .diff_parser import DiffParser, FileDiff
from .file_prioritizer import FilePrioritizer
from .priority_filter import filter_review_by_priority
from .validator import validate_review_quality


class PRReviewer:
    """PR reviewer that uses kit's Repository class and LLM analysis for intelligent code reviews."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.github_session = requests.Session()
        self.github_session.headers.update(
            {
                "Authorization": f"token {config.github.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "kit-review/0.6.1",
            }
        )
        self._llm_client: Optional[Any] = None  # Will be Anthropic or OpenAI client
        # Pass quiet mode to repo cache
        quiet = self.config.quiet
        self.repo_cache = RepoCache(config, quiet=quiet)
        self.cost_tracker = CostTracker(config.custom_pricing)

        # Diff caching (initialized to None, filled lazily)
        self._cached_diff_key: Optional[tuple[str, str, int]] = None
        self._cached_diff_text: Optional[str] = None
        self._cached_parsed_diff: Optional[Dict[str, FileDiff]] = None
        self._cached_parsed_key: Optional[tuple[str, str, int]] = None

    def parse_pr_url(self, pr_input: str) -> tuple[str, str, int]:
        """Parse PR URL or number to extract owner, repo, and PR number.

        Args:
            pr_input: GitHub PR URL or just PR number (if in repo directory)

        Returns:
            tuple of (owner, repo, pr_number)
        """
        # If it's just a number, we'll need to detect repo from current directory
        if pr_input.isdigit():
            raise NotImplementedError(
                "PR number without repository URL is not yet supported. "
                "Please provide the full GitHub PR URL: https://github.com/owner/repo/pull/123"
            )

        # Parse GitHub URL
        # https://github.com/owner/repo/pull/123
        url_pattern = r"https://(?:\w+\.)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(url_pattern, pr_input)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_input}")

        owner, repo, pr_number = match.groups()
        return owner, repo, int(pr_number)

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get PR details from GitHub API."""
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        response = self.github_session.get(url)
        response.raise_for_status()

        return response.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[Dict[str, Any]]:
        """Get list of files changed in the PR."""
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"

        response = self.github_session.get(url)
        response.raise_for_status()

        return response.json()

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the full diff for the PR."""
        key = (owner, repo, pr_number)

        # Return cached diff text if we already fetched it
        if getattr(self, "_cached_diff_key", None) == key and hasattr(self, "_cached_diff_text"):
            # mypy: we know _cached_diff_text is not None because key matched and attribute exists
            assert self._cached_diff_text is not None
            return self._cached_diff_text

        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = dict(self.github_session.headers)
        headers["Accept"] = "application/vnd.github.v3.diff"

        response = self.github_session.get(url, headers=headers)
        response.raise_for_status()

        # Cache the result
        self._cached_diff_key = key
        self._cached_diff_text = response.text

        # Invalidate parsed cache (if any) because diff may have changed
        if hasattr(self, "_cached_parsed_diff"):
            delattr(self, "_cached_parsed_diff")

        return response.text

    def get_repo_for_analysis(self, owner: str, repo: str, pr_details: Dict[str, Any]) -> str:
        """Get repository for analysis, using cache if available."""
        # If a repo_path is configured, use the existing repository
        if self.config.repo_path:
            from pathlib import Path

            repo_path = Path(self.config.repo_path).expanduser().resolve()
            if not repo_path.exists():
                raise ValueError(f"Specified repository path does not exist: {repo_path}")
            if not (repo_path / ".git").exists():
                raise ValueError(f"Specified path is not a git repository: {repo_path}")
            return str(repo_path)

        # Default behavior: use cache
        head_sha = pr_details["head"]["sha"]
        return self.repo_cache.get_repo_path(owner, repo, head_sha)

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, comment: str) -> Dict[str, Any]:
        """Post a comment on the PR."""
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"

        data = {"body": comment}
        response = self.github_session.post(url, json=data)
        response.raise_for_status()

        return response.json()

    async def analyze_pr_with_kit(self, repo_path: str, pr_details: Dict[str, Any], files: List[Dict[str, Any]]) -> str:
        """Analyze PR using kit Repository class and LLM analysis with full kit capabilities."""
        # Create kit Repository instance
        repo = Repository(repo_path)

        owner, repo_name = pr_details["base"]["repo"]["owner"]["login"], pr_details["base"]["repo"]["name"]
        pr_number = pr_details["number"]
        try:
            pr_diff = self.get_pr_diff(owner, repo_name, pr_number)  # cached
            diff_files = self.get_parsed_diff(owner, repo_name, pr_number)
        except Exception as e:
            pr_diff = f"Error retrieving diff: {e}"
            diff_files = {}

        # Parse diff for accurate line number mapping
        line_number_context = DiffParser.generate_line_number_context(
            diff_files, owner, repo_name, pr_details["head"]["sha"]
        )

        # Prioritize files for analysis (smart prioritization for Kit reviewer)
        priority_files, skipped_count = FilePrioritizer.smart_priority(files, max_files=10)

        # Instead of full file contents, get targeted symbol analysis for each file
        file_analysis: Dict[str, Dict[str, Any]] = {}

        for file_info in priority_files:
            file_path = file_info["filename"]
            try:
                # Add kit's repository intelligence WITHOUT full file content
                kit_context = {}
                try:
                    # Try to get symbols from kit (may fail for new files)
                    file_symbols = repo.extract_symbols(file_path)
                    kit_context["symbols"] = file_symbols
                except Exception:
                    kit_context["symbols"] = []

                # Find usages of symbols defined in this file
                symbol_usages = {}
                for symbol in kit_context["symbols"][:5]:  # Limit to first 5 symbols
                    try:
                        usages = repo.find_symbol_usages(symbol["name"])
                        if len(usages) > 1:  # More than just the definition
                            symbol_usages[symbol["name"]] = len(usages) - 1
                    except Exception:
                        continue

                file_analysis[file_path] = {
                    "symbols": kit_context["symbols"],
                    "symbol_usages": symbol_usages,
                    "changes": f"+{file_info['additions']} -{file_info['deletions']}",
                }

            except Exception:
                file_analysis[file_path] = {
                    "symbols": [],
                    "symbol_usages": {},
                    "changes": f"+{file_info['additions']} -{file_info['deletions']}",
                }

        # Get dependency analysis for the repository
        try:
            dependency_analyzer = repo.get_dependency_analyzer()
            dependency_context = dependency_analyzer.generate_llm_context()
        except Exception as e:
            dependency_context = f"Dependency analysis unavailable: {e}"

        # Get overall repository context (but more efficiently)
        try:
            # Get just a summary of file tree instead of full tree
            file_tree = repo.get_file_tree()
            total_files = len([f for f in file_tree if not f.get("is_dir", True)])
            total_dirs = len([f for f in file_tree if f.get("is_dir", False)])
            repo_summary = f"{total_files} files in {total_dirs} directories"
        except Exception:
            repo_summary = "Repository structure unavailable"

        # Generate analysis summary for transparency
        analysis_summary = FilePrioritizer.get_analysis_summary(files, priority_files)

        # Create enhanced analysis prompt with kit's rich context
        pr_status = (
            "WIP"
            if "WIP" in pr_details["title"].upper() or "WORK IN PROGRESS" in pr_details["title"].upper()
            else "Ready for Review"
        )

        analysis_prompt = f"""You are an expert code reviewer. Analyze this GitHub PR using the provided repository intelligence.

**PR Information:**
- Title: {pr_details["title"]}
- Author: {pr_details["user"]["login"]}
- Files: {len(files)} changed
- Status: {pr_status}

**Repository Context:**
- Structure: {repo_summary}
- Dependencies: {dependency_context}

{analysis_summary}

{line_number_context}"""

        # Add custom context from profile if available
        if self.config.profile_context:
            analysis_prompt += f"""

**Custom Review Guidelines:**
{self.config.profile_context}"""

        analysis_prompt += f"""

**Diff:**
```diff
{pr_diff}
```

**Symbol Analysis:**"""

        for file_path, file_data in file_analysis.items():
            analysis_prompt += f"""
{file_path} ({file_data["changes"]}) - {len(file_data["symbols"])} symbols
{chr(10).join([f"- {name}: used in {count} places" for name, count in file_data["symbol_usages"].items()]) if file_data["symbol_usages"] else "- No widespread usage"}"""

        analysis_prompt += """

**Review Format:**

## Priority Issues
- [High/Medium/Low priority] findings with [file.py:123](https://github.com/{owner}/{repo_name}/blob/{pr_details["head"]["sha"]}/file.py#L123) links

## Summary
- What this PR does
- Key architectural changes (if any)

## Recommendations
- Security, performance, or logic issues with specific fixes; missing error handling or edge cases; cross-codebase impact concerns

**Guidelines:** Be specific, actionable, and professional. Reference actual diff content. Focus on issues worth fixing. Use measured technical language - distinguish between defensive code (with safeguards) and actual vulnerabilities."""

        # Use LLM to analyze with enhanced context
        analysis: str
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            analysis = await self._analyze_with_anthropic_enhanced(analysis_prompt)
        elif self.config.llm.provider == LLMProvider.GOOGLE:
            analysis = await self._analyze_with_google_enhanced(analysis_prompt)
        elif self.config.llm.provider == LLMProvider.OLLAMA:
            analysis = await self._analyze_with_ollama_enhanced(analysis_prompt)
        else:
            analysis = await self._analyze_with_openai_enhanced(analysis_prompt)

        # Apply priority filtering if requested
        priority_filter = self.config.priority_filter
        filtered_analysis = filter_review_by_priority(analysis, priority_filter, self.config.max_review_size_mb)

        return filtered_analysis

    async def _analyze_with_anthropic_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Anthropic Claude with enhanced kit context."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        if not self._llm_client:
            self._llm_client = anthropic.Anthropic(api_key=self.config.llm.api_key)

        try:
            response = self._llm_client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                messages=[{"role": "user", "content": enhanced_prompt}],
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

            return text_content if text_content else "No text content in response"

        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_google_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Google Gemini with enhanced kit context."""
        try:
            import google.genai as genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed. Run: pip install google-genai")

        if not self._llm_client:
            self._llm_client = genai.Client(api_key=self.config.llm.api_key)

        try:
            # Use the correct API format for the new google-genai SDK
            response = self._llm_client.models.generate_content(
                model=self.config.llm.model,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    temperature=self.config.llm.temperature,
                    max_output_tokens=self.config.llm.max_tokens,
                ),
            )

            # Track cost using accurate token counts from the response
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)

                self.cost_tracker.track_llm_usage(
                    self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
                )
            else:
                # Fallback: Use count_tokens API for input estimation if usage_metadata unavailable
                try:
                    token_count_response = self._llm_client.models.count_tokens(
                        model=self.config.llm.model, contents=enhanced_prompt
                    )
                    input_tokens = getattr(token_count_response, "total_tokens", 0)
                    # Estimate output tokens based on response length (rough fallback)
                    estimated_output_tokens = len(str(response.text)) // 4 if response.text else 0

                    self.cost_tracker.track_llm_usage(
                        self.config.llm.provider, self.config.llm.model, input_tokens, estimated_output_tokens
                    )
                except Exception:
                    # If all else fails, estimate tokens based on character count
                    estimated_input_tokens = len(enhanced_prompt) // 4
                    estimated_output_tokens = len(str(response.text)) // 4 if response.text else 0

                    self.cost_tracker.track_llm_usage(
                        self.config.llm.provider, self.config.llm.model, estimated_input_tokens, estimated_output_tokens
                    )

            # Ensure we always return a string
            result_text = response.text
            return result_text if result_text is not None else "No response content from Google Gemini"

        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_openai_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using OpenAI GPT with enhanced kit context."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        if not self._llm_client:
            # Support custom OpenAI compatible providers via api_base_url
            if self.config.llm.api_base_url:
                self._llm_client = openai.OpenAI(api_key=self.config.llm.api_key, base_url=self.config.llm.api_base_url)
            else:
                self._llm_client = openai.OpenAI(api_key=self.config.llm.api_key)

        try:
            response = self._llm_client.chat.completions.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                messages=[{"role": "user", "content": enhanced_prompt}],
            )

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_openai_usage(response)
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
            )

            content = response.choices[0].message.content
            return content if content is not None else "No response content"

        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_ollama_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Ollama with enhanced kit context."""
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
                enhanced_prompt,
                temperature=self.config.llm.temperature,
                num_predict=self.config.llm.max_tokens,
            )

            # Strip thinking tokens from reasoning models like DeepSeek R1
            cleaned_response = _strip_thinking_tokens(response)

            # Ollama is free, so no cost tracking needed, but we can track usage
            # For consistency, we'll estimate tokens (very rough)
            estimated_input_tokens = len(enhanced_prompt) // 4
            estimated_output_tokens = len(cleaned_response) // 4
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, estimated_input_tokens, estimated_output_tokens
            )

            return cleaned_response if cleaned_response else "No response content from Ollama"

        except Exception as e:
            return f"Error during enhanced Ollama analysis: {e}"

    def review_pr(self, pr_input: str) -> str:
        """Review a PR with intelligent analysis."""
        try:
            # Check if quiet mode is enabled (for plain output)
            quiet = self.config.quiet

            # Parse PR input
            owner, repo, pr_number = self.parse_pr_url(pr_input)
            if not quiet:
                print(
                    f"🛠️ Reviewing PR #{pr_number} in {owner}/{repo} "
                    f"[STANDARD MODE - {self.config.llm.model} | max_tokens={self.config.llm.max_tokens}]"
                )

            # Get PR details
            pr_details = self.get_pr_details(owner, repo, pr_number)
            if not quiet:
                print(f"PR Title: {pr_details['title']}")
                print(f"PR Author: {pr_details['user']['login']}")
                print(f"Base: {pr_details['base']['ref']} -> Head: {pr_details['head']['ref']}")

            # Get changed files
            files = self.get_pr_files(owner, repo, pr_number)
            if not quiet:
                print(f"Changed files: {len(files)}")

            # For more comprehensive analysis, clone the repo
            if len(files) > 0 and self.config.analysis_depth.value != "quick" and self.config.clone_for_analysis:
                # Check if using existing repository
                if self.config.repo_path:
                    # Show warning when using existing repository
                    if not quiet:
                        print("⚠️ WARNING: Using existing repository - results may not reflect the main branch")
                        print(f"Using existing repository at: {self.config.repo_path}")

                    try:
                        repo_path = self.get_repo_for_analysis(owner, repo, pr_details)

                        # Run async analysis
                        if not quiet:
                            print("Running analysis...")
                        analysis = asyncio.run(self.analyze_pr_with_kit(repo_path, pr_details, files))

                        # Validate review quality
                        try:
                            pr_diff = self.get_pr_diff(owner, repo, pr_number)  # cached
                            changed_files = [f["filename"] for f in files]
                            validation = validate_review_quality(analysis, pr_diff, changed_files)

                            if not quiet:
                                print(f"📊 Review Quality Score: {validation.score:.2f}/1.0")
                                if validation.issues:
                                    print(f"⚠️  Quality Issues: {', '.join(validation.issues)}")
                                print(f"📈 Metrics: {validation.metrics}")

                            # Auto-fix wrong line numbers if any
                            if validation.metrics.get("line_reference_errors", 0) > 0:
                                from .line_ref_fixer import LineRefFixer

                                analysis, fixes = LineRefFixer.fix_comment(analysis, pr_diff)
                                if fixes and not quiet:
                                    print(
                                        f"🔧 Auto-fixed {len(fixes) // (2 if any(f[1] != f[2] for f in fixes) else 1)} line reference(s)"
                                    )

                        except Exception as e:
                            if not quiet:
                                print(f"⚠️  Could not validate review quality: {e}")

                        review_comment = self._generate_intelligent_comment(pr_details, files, analysis)

                    except Exception as e:
                        if not quiet:
                            print(f"Analysis failed: {e}")
                        # Fall back to basic analysis
                        basic_analysis = f"Analysis failed ({e!s}). Reviewing based on GitHub API data only.\n\nFiles changed: {len(files)} files with {sum(f['additions'] for f in files)} additions and {sum(f['deletions'] for f in files)} deletions."
                        review_comment = self._generate_intelligent_comment(pr_details, files, basic_analysis)
                else:
                    # Standard cloning behavior
                    if not quiet:
                        print("Preparing repository for analysis...")
                    with tempfile.TemporaryDirectory():
                        try:
                            repo_path = self.get_repo_for_analysis(owner, repo, pr_details)
                            if not quiet:
                                print(f"Using repository at: {repo_path}")

                            # Run async analysis
                            if not quiet:
                                print("Running analysis...")
                            analysis = asyncio.run(self.analyze_pr_with_kit(repo_path, pr_details, files))

                            # Validate review quality
                            try:
                                pr_diff = self.get_pr_diff(owner, repo, pr_number)  # cached
                                changed_files = [f["filename"] for f in files]
                                validation = validate_review_quality(analysis, pr_diff, changed_files)

                                if not quiet:
                                    print(f"📊 Review Quality Score: {validation.score:.2f}/1.0")
                                    if validation.issues:
                                        print(f"⚠️  Quality Issues: {', '.join(validation.issues)}")
                                    print(f"📈 Metrics: {validation.metrics}")

                                # Auto-fix wrong line numbers if any
                                if validation.metrics.get("line_reference_errors", 0) > 0:
                                    from .line_ref_fixer import LineRefFixer

                                    analysis, fixes = LineRefFixer.fix_comment(analysis, pr_diff)
                                    if fixes and not quiet:
                                        print(
                                            f"🔧 Auto-fixed {len(fixes) // (2 if any(f[1] != f[2] for f in fixes) else 1)} line reference(s)"
                                        )

                            except Exception as e:
                                if not quiet:
                                    print(f"⚠️  Could not validate review quality: {e}")

                            review_comment = self._generate_intelligent_comment(pr_details, files, analysis)

                        except subprocess.CalledProcessError as e:
                            if not quiet:
                                print(f"Failed to clone repository: {e}")
                            # Fall back to basic analysis without cloning
                            basic_analysis = f"Repository analysis failed (clone error). Reviewing based on GitHub API data only.\n\nFiles changed: {len(files)} files with {sum(f['additions'] for f in files)} additions and {sum(f['deletions'] for f in files)} deletions."
                            review_comment = self._generate_intelligent_comment(pr_details, files, basic_analysis)
                        except Exception as e:
                            if not quiet:
                                print(f"Analysis failed: {e}")
                            # Fall back to basic analysis without cloning
                            basic_analysis = f"Analysis failed ({e!s}). Reviewing based on GitHub API data only.\n\nFiles changed: {len(files)} files with {sum(f['additions'] for f in files)} additions and {sum(f['deletions'] for f in files)} deletions."
                            review_comment = self._generate_intelligent_comment(pr_details, files, basic_analysis)
            else:
                # Basic analysis for quick mode or no files
                basic_analysis = f"Quick analysis mode.\n\nFiles changed: {len(files)} files with {sum(f['additions'] for f in files)} additions and {sum(f['deletions'] for f in files)} deletions."
                review_comment = self._generate_intelligent_comment(pr_details, files, basic_analysis)

            # Post comment if configured to do so
            if self.config.post_as_comment:
                comment_result = self.post_pr_comment(owner, repo, pr_number, review_comment)
                if not quiet:
                    print(f"Posted comment: {comment_result['html_url']}")

            # Display cost summary
            if not quiet:
                print(self.cost_tracker.get_cost_summary())

            return review_comment

        except requests.RequestException as e:
            raise RuntimeError(f"GitHub API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Review failed: {e}")

    def _generate_intelligent_comment(
        self, pr_details: Dict[str, Any], files: list[Dict[str, Any]], analysis: str
    ) -> str:
        """Generate an intelligent review comment using LLM analysis."""
        comment = f"""## 🛠️ Kit AI Code Review

{analysis}

---
*Generated by [cased kit](https://github.com/cased/kit) v{self._get_kit_version()} • Mode: kit • Model: {self.config.llm.model}*
"""
        return comment

    def _get_kit_version(self) -> str:
        """Get kit version for review attribution."""
        try:
            import kit

            return getattr(kit, "__version__", "dev")
        except Exception:
            return "dev"

    def get_parsed_diff(self, owner: str, repo: str, pr_number: int) -> Dict[str, FileDiff]:
        """Return a cached parsed diff so we don't re-parse the same content multiple times."""

        key = (owner, repo, pr_number)

        # Return cached parsed diff if key matches
        if self._cached_parsed_key == key and self._cached_parsed_diff is not None:
            return self._cached_parsed_diff

        diff_text = self.get_pr_diff(owner, repo, pr_number)
        parsed: Dict[str, FileDiff] = DiffParser.parse_diff(diff_text)
        self._cached_parsed_key = key
        self._cached_parsed_diff = parsed
        return parsed


def _strip_thinking_tokens(response: str) -> str:
    """
    Strip thinking tokens from LLM responses.

    Reasoning models like DeepSeek R1 include <think>...</think> tags
    that show internal reasoning but aren't meant for end users.
    """
    if not response:
        return response

    import re

    # Common thinking token patterns used by reasoning models
    patterns = [
        r"<think>.*?</think>",  # DeepSeek R1, others
        r"<thinking>.*?</thinking>",  # Alternative format
        r"<thought>.*?</thought>",  # Another variant
        r"<reason>.*?</reason>",  # Reasoning blocks
    ]

    cleaned = response
    for pattern in patterns:
        # Use DOTALL flag to match across newlines
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # Clean up extra whitespace left by removal
    cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned)  # Multiple blank lines
    cleaned = cleaned.strip()

    return cleaned
