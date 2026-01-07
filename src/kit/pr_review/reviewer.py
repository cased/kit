"""PR Reviewer implementation with GitHub API integration and LLM analysis."""

import asyncio
import subprocess
import tempfile
from typing import Any, Dict, List

import requests

from kit import Repository
from kit.llm_client_factory import create_client_from_review_config

from .base_reviewer import BaseReviewer
from .config import LLMProvider, ReviewConfig
from .diff_parser import DiffParser, FileDiff
from .file_prioritizer import FilePrioritizer
from .priority_filter import filter_review_by_priority
from .validator import validate_review_quality


class PRReviewer(BaseReviewer):
    """PR reviewer that uses kit's Repository class and LLM analysis for intelligent code reviews."""

    def __init__(self, config: ReviewConfig):
        super().__init__(config)  # Uses default kit-review/{version}

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
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            response = self._llm_client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
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
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed. Run: pip install google-genai")

        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            # Use the correct API format for the new google-genai SDK
            response = self._llm_client.models.generate_content(
                model=self.config.llm.model,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
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
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            # GPT-5 models use max_completion_tokens instead of max_tokens
            completion_params: Dict[str, Any] = {
                "model": self.config.llm.model,
                "messages": [{"role": "user", "content": enhanced_prompt}],
            }
            if "gpt-5" in self.config.llm.model.lower():
                completion_params["max_completion_tokens"] = self.config.llm.max_tokens
            else:
                completion_params["max_tokens"] = self.config.llm.max_tokens

            response = self._llm_client.chat.completions.create(**completion_params)

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
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            response = await asyncio.to_thread(
                self._llm_client.generate,
                enhanced_prompt,
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

                                # Use cached parsed diff to avoid re-parsing
                                cached_parsed = self.get_parsed_diff(owner, repo, pr_number)
                                analysis, fixes = LineRefFixer.fix_comment(analysis, pr_diff, parsed_diff=cached_parsed)
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

                                    # Use cached parsed diff to avoid re-parsing
                                    cached_parsed = self.get_parsed_diff(owner, repo, pr_number)
                                    analysis, fixes = LineRefFixer.fix_comment(
                                        analysis, pr_diff, parsed_diff=cached_parsed
                                    )
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

    def review_local_diff(self, diff_spec: str, repo_path: str = ".") -> str:
        """Review local branch changes using git diff."""
        try:
            # Validate we're in a git repository
            from pathlib import Path

            git_dir = Path(repo_path) / ".git"
            if not git_dir.exists():
                raise RuntimeError("Not a git repository. Local diff review requires a git repository.")

            # Check if quiet mode is enabled (for plain output)
            quiet: bool = self.config.quiet

            if not quiet:
                print(f"🛠️ Reviewing local changes: {diff_spec} [STANDARD MODE - {self.config.llm.model}]")

            # Use LocalDiffProvider for git operations
            from kit.pr_review.local_diff_provider import LocalDiffProvider

            diff_provider = LocalDiffProvider(repo_path)
            diff_content: str = diff_provider.get_diff(diff_spec)

            if not diff_content.strip():
                return "No changes found in the specified diff range."

            changed_files: List[str] = diff_provider.get_changed_files(diff_spec)

            if not quiet:
                print(f"Changed files: {len(changed_files)}")
                for file in changed_files[:5]:  # Show first 5 files
                    print(f"  {file}")
                if len(changed_files) > 5:
                    print(f"  ... and {len(changed_files) - 5} more")

            # Parse the diff to get file change information
            from .diff_parser import DiffParser

            parsed_diff: Dict[str, FileDiff] = DiffParser.parse_diff(diff_content)

            # Create mock data for analysis
            mock_files: List[Dict[str, Any]] = diff_provider.get_mock_files(diff_spec, changed_files)
            mock_pr_details: Dict[str, Any] = diff_provider.get_mock_pr_details(diff_spec)

            if not quiet:
                print(f"Title: {mock_pr_details['title']}")
                print(f"Base: {mock_pr_details['base']['ref']} -> Head: {mock_pr_details['head']['ref']}")

            # Perform repository analysis if enabled
            if len(mock_files) > 0 and self.config.analysis_depth.value != "quick" and self.config.clone_for_analysis:
                # Use the specified repo path or current directory
                analysis_repo_path: str = repo_path

                if not quiet:
                    print("Running analysis...")

                try:
                    analysis: str = asyncio.run(
                        self.analyze_local_diff_with_kit(
                            analysis_repo_path, mock_pr_details, mock_files, diff_content, parsed_diff
                        )
                    )

                    # Validate review quality
                    try:
                        changed_files_list: List[str] = [str(f.get("filename", "")) for f in mock_files]
                        from .validator import validate_review_quality

                        validation = validate_review_quality(analysis, diff_content, changed_files_list)

                        if not quiet:
                            print(f"📊 Review Quality Score: {validation.score:.2f}/1.0")
                            if validation.issues:
                                print(f"⚠️  Quality Issues: {', '.join(validation.issues)}")
                            print(f"📈 Metrics: {validation.metrics}")

                        # Auto-fix wrong line numbers if any
                        if validation.metrics.get("line_reference_errors", 0) > 0:
                            from .line_ref_fixer import LineRefFixer

                            # Reuse already-parsed diff to avoid re-parsing
                            analysis, fixes = LineRefFixer.fix_comment(analysis, diff_content, parsed_diff=parsed_diff)
                            if fixes and not quiet:
                                is_different = [f[1] != f[2] for f in fixes]
                                divisor = 2 if any(is_different) else 1
                                print(f"🔧 Auto-fixed {len(fixes) // divisor} line reference(s)")

                    except Exception as e:
                        if not quiet:
                            print(f"⚠️  Could not validate review quality: {e}")

                    review_comment = self._generate_local_diff_comment(mock_pr_details, mock_files, analysis, diff_spec)

                except Exception as e:
                    if not quiet:
                        print(f"Analysis failed: {e}")
                    # Fall back to basic analysis
                    basic_analysis = f"Analysis failed ({e!s}). Reviewing based on git diff only.\n\nFiles changed: {len(mock_files)} files with {sum(f['additions'] for f in mock_files)} additions and {sum(f['deletions'] for f in mock_files)} deletions."
                    review_comment = self._generate_local_diff_comment(
                        mock_pr_details, mock_files, basic_analysis, diff_spec
                    )
            else:
                # Basic analysis for quick mode or no files
                basic_analysis = f"Quick analysis mode.\n\nFiles changed: {len(mock_files)} files with {sum(f['additions'] for f in mock_files)} additions and {sum(f['deletions'] for f in mock_files)} deletions."
                review_comment = self._generate_local_diff_comment(
                    mock_pr_details, mock_files, basic_analysis, diff_spec
                )

            # Display cost summary
            if not quiet:
                print(self.cost_tracker.get_cost_summary())

            return review_comment

        except Exception as e:
            raise RuntimeError(f"Local diff review failed: {e}")

    async def analyze_local_diff_with_kit(
        self,
        repo_path: str,
        mock_pr_details: Dict[str, Any],
        files: List[Dict[str, Any]],
        diff_content: str,
        parsed_diff: Dict[str, Any],
    ) -> str:
        """Analyze local diff using kit Repository class and LLM analysis."""
        from kit import Repository

        # Create kit Repository instance
        repo = Repository(repo_path)

        # Generate line number context from parsed diff
        from .diff_parser import DiffParser

        line_number_context = DiffParser.generate_line_number_context(parsed_diff)

        # Prioritize files for analysis
        from .file_prioritizer import FilePrioritizer

        priority_files, skipped_count = FilePrioritizer.smart_priority(files, max_files=10)

        # Get symbol analysis for each file
        file_analysis: Dict[str, Dict[str, Any]] = {}

        for file_data in priority_files:
            file_path = file_data["filename"]
            try:
                # Get symbols from the file
                file_symbols = repo.extract_symbols(file_path)

                # Get symbol usage counts
                symbol_usages = {}
                for symbol in file_symbols[:5]:  # Limit to top 5 symbols
                    try:
                        usages = repo.find_symbol_usages(symbol["name"])
                        symbol_usages[symbol["name"]] = len(usages)
                    except Exception:
                        symbol_usages[symbol["name"]] = 0

                file_analysis[file_path] = {
                    "changes": f"{file_data['additions']}+, {file_data['deletions']}-",
                    "symbols": file_symbols[:5],
                    "symbol_usages": symbol_usages,
                }

            except Exception:
                file_analysis[file_path] = {
                    "changes": f"{file_data['additions']}+, {file_data['deletions']}-",
                    "symbols": [],
                    "symbol_usages": {},
                }

        # Get dependency analysis for the repository
        try:
            dependency_analyzer = repo.get_dependency_analyzer()
            dependency_context = dependency_analyzer.generate_llm_context()
        except Exception as e:
            dependency_context = f"Dependency analysis unavailable: {e}"

        # Get repository context
        try:
            file_tree = repo.get_file_tree()
            total_files = len([f for f in file_tree if not f.get("is_dir", True)])
            total_dirs = len([f for f in file_tree if f.get("is_dir", False)])
            repo_summary = f"{total_files} files in {total_dirs} directories"
        except Exception:
            repo_summary = "Repository structure unavailable"

        # Generate analysis summary
        analysis_summary = FilePrioritizer.get_analysis_summary(files, priority_files)

        # Create enhanced analysis prompt
        analysis_prompt = f"""You are an expert code reviewer. Analyze this local git diff using the provided repository intelligence.

**Local Changes Information:**
- Diff: {mock_pr_details["base"]["ref"]}..{mock_pr_details["head"]["ref"]}
- Title: {mock_pr_details["title"]}
- Files: {len(files)} changed

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
{diff_content}
```

**Symbol Analysis:**"""

        for file_path, file_data in file_analysis.items():
            analysis_prompt += f"""
{file_path} ({file_data["changes"]}) - {len(file_data["symbols"])} symbols
{chr(10).join([f"- {name}: used in {count} places" for name, count in file_data["symbol_usages"].items()]) if file_data["symbol_usages"] else "- No widespread usage"}"""

        analysis_prompt += """

**Review Format:**

## Priority Issues
- [High/Medium/Low priority] findings with file:line references

## Summary
- What these changes do
- Key architectural changes (if any)

## Recommendations
- Security, performance, or logic issues with specific fixes; missing error handling or edge cases; cross-codebase impact concerns

**Guidelines:** Be specific, actionable, and professional. Reference actual diff content. Focus on issues worth fixing. Use measured technical language - distinguish between defensive code (with safeguards) and actual vulnerabilities."""

        # Use LLM to analyze with enhanced context
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            analysis = await self._analyze_with_anthropic_enhanced(analysis_prompt)
        elif self.config.llm.provider == LLMProvider.GOOGLE:
            analysis = await self._analyze_with_google_enhanced(analysis_prompt)
        elif self.config.llm.provider == LLMProvider.OLLAMA:
            analysis = await self._analyze_with_ollama_enhanced(analysis_prompt)
        else:
            analysis = await self._analyze_with_openai_enhanced(analysis_prompt)

        # Apply priority filtering if requested
        from .priority_filter import filter_review_by_priority

        priority_filter = self.config.priority_filter
        filtered_analysis = filter_review_by_priority(analysis, priority_filter, self.config.max_review_size_mb)

        return filtered_analysis

    def _generate_local_diff_comment(
        self, mock_pr_details: Dict[str, Any], files: List[Dict[str, Any]], analysis: str, diff_spec: str
    ) -> str:
        """Generate an intelligent review comment for local diff analysis."""
        # Strip any existing footers from the analysis to prevent duplicates
        analysis_lines = analysis.strip().split("\n")
        if analysis_lines and "Generated by" in analysis_lines[-1]:
            # Remove the last two lines (footer separator and attribution)
            analysis = "\n".join(analysis_lines[:-2]).strip()

        comment = f"""## 🛠️ Kit AI Code Review - Local Changes

**Diff:** `{diff_spec}`

{analysis}

---
*Generated by [cased kit](https://github.com/cased/kit) v{self._get_kit_version()} • Mode: local-diff • Model: {self.config.llm.model}*
"""
        return comment


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
