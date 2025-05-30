"""PR Reviewer implementation with GitHub API integration and LLM analysis."""

import asyncio
import re
import subprocess
import tempfile
from typing import Any, Dict, List

import requests

from kit import Repository

from .cache import RepoCache
from .config import LLMProvider, ReviewConfig
from .cost_tracker import CostTracker
from .file_prioritizer import FilePrioritizer
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
                "User-Agent": "kit-pr-reviewer/0.1.0",
            }
        )
        self._llm_client = None
        self.repo_cache = RepoCache(config)
        self.cost_tracker = CostTracker(config.custom_pricing)

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
        url_pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
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
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = self.github_session.headers.copy()
        headers["Accept"] = "application/vnd.github.v3.diff"

        response = self.github_session.get(url, headers=headers)
        response.raise_for_status()

        return response.text

    def get_repo_for_analysis(self, owner: str, repo: str, pr_details: Dict[str, Any]) -> str:
        """Get repository for analysis, using cache if available."""
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

        owner, repo_name = pr_details["head"]["repo"]["owner"]["login"], pr_details["head"]["repo"]["name"]
        pr_number = pr_details["number"]
        try:
            pr_diff = self.get_pr_diff(owner, repo_name, pr_number)
        except Exception as e:
            pr_diff = f"Error retrieving diff: {e}"

        # Prioritize files for analysis (smart prioritization for Kit reviewer)
        priority_files, skipped_count = FilePrioritizer.smart_priority(files, max_files=10)

        # Instead of full file contents, get targeted symbol analysis for each file
        file_analysis = {}

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

**Diff:**
```diff
{pr_diff}
```

**Symbol Analysis:**"""

        for file_path, analysis in file_analysis.items():
            analysis_prompt += f"""
{file_path} ({analysis["changes"]}) - {len(analysis["symbols"])} symbols
{chr(10).join([f"- {name}: used in {count} places" for name, count in analysis["symbol_usages"].items()]) if analysis["symbol_usages"] else "- No widespread usage"}"""

        analysis_prompt += f"""

**Review Format:**

## Priority Issues
- [High/Medium/Low priority] findings with [file.py:123](https://github.com/{owner}/{repo_name}/blob/{pr_details["head"]["sha"]}/file.py#L123) links

## Summary
- What this PR does
- Key architectural changes (if any)

## Recommendations
- Security, performance, or logic issues with specific fixes
- Missing error handling or edge cases
- Cross-codebase impact concerns

**Guidelines:** Be specific, actionable, and professional. Reference actual diff content. Focus on issues worth fixing."""

        # Use LLM to analyze with enhanced context
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            return await self._analyze_with_anthropic_enhanced(analysis_prompt)
        else:
            return await self._analyze_with_openai_enhanced(analysis_prompt)

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

            return response.content[0].text

        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_openai_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using OpenAI GPT with enhanced kit context."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        if not self._llm_client:
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

            return response.choices[0].message.content

        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    def review_pr(self, pr_input: str) -> str:
        """Review a PR with intelligent analysis."""
        try:
            # Parse PR input
            owner, repo, pr_number = self.parse_pr_url(pr_input)
            print(f"🛠️ Reviewing PR #{pr_number} in {owner}/{repo} [STANDARD MODE - {self.config.llm.model}]")

            # Get PR details
            pr_details = self.get_pr_details(owner, repo, pr_number)
            print(f"PR Title: {pr_details['title']}")
            print(f"PR Author: {pr_details['user']['login']}")
            print(f"Base: {pr_details['base']['ref']} -> Head: {pr_details['head']['ref']}")

            # Get changed files
            files = self.get_pr_files(owner, repo, pr_number)
            print(f"Changed files: {len(files)}")

            # For more comprehensive analysis, clone the repo
            if len(files) > 0 and self.config.analysis_depth.value != "quick" and self.config.clone_for_analysis:
                print("Cloning repository for analysis...")
                with tempfile.TemporaryDirectory():
                    try:
                        repo_path = self.get_repo_for_analysis(owner, repo, pr_details)
                        print(f"Repository cloned to: {repo_path}")

                        # Run async analysis
                        analysis = asyncio.run(self.analyze_pr_with_kit(repo_path, pr_details, files))

                        # Validate review quality
                        try:
                            pr_diff = self.get_pr_diff(owner, repo, pr_number)
                            changed_files = [f["filename"] for f in files]
                            validation = validate_review_quality(analysis, pr_diff, changed_files)

                            print(f"📊 Review Quality Score: {validation.score:.2f}/1.0")
                            if validation.issues:
                                print(f"⚠️  Quality Issues: {', '.join(validation.issues)}")
                            print(f"📈 Metrics: {validation.metrics}")

                        except Exception as e:
                            print(f"⚠️  Could not validate review quality: {e}")

                        review_comment = self._generate_intelligent_comment(pr_details, files, analysis)

                    except subprocess.CalledProcessError as e:
                        print(f"Failed to clone repository: {e}")
                        # Fall back to basic analysis without cloning
                        basic_analysis = f"Repository analysis failed (clone error). Reviewing based on GitHub API data only.\n\nFiles changed: {len(files)} files with {sum(f['additions'] for f in files)} additions and {sum(f['deletions'] for f in files)} deletions."
                        review_comment = self._generate_intelligent_comment(pr_details, files, basic_analysis)
                    except Exception as e:
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
                print(f"Posted comment: {comment_result['html_url']}")

            # Display cost summary
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
