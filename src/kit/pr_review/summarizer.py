"""PR Summarizer implementation with GitHub API integration and LLM analysis."""

import asyncio
from typing import Any, Dict, List

from kit import Repository
from kit.llm_client_factory import create_client_from_review_config

from .config import LLMProvider, ReviewConfig
from .diff_parser import DiffParser
from .file_prioritizer import FilePrioritizer
from .reviewer import PRReviewer


class PRSummarizer(PRReviewer):
    """PR summarizer that uses kit's Repository class and LLM analysis for intelligent PR summaries.

    Inherits from PRReviewer to reuse all the GitHub API integration, diff parsing,
    and repository analysis capabilities, but provides summarization-focused prompts.
    """

    def __init__(self, config: ReviewConfig):
        super().__init__(config)

    async def analyze_pr_for_summary(
        self, repo_path: str, pr_details: Dict[str, Any], files: List[Dict[str, Any]]
    ) -> str:
        """Analyze PR using kit Repository class and LLM analysis for concise summarization."""
        # Create kit Repository instance
        repo = Repository(repo_path)

        owner, repo_name = pr_details["base"]["repo"]["owner"]["login"], pr_details["base"]["repo"]["name"]
        pr_number = pr_details["number"]

        try:
            pr_diff = self.get_pr_diff(owner, repo_name, pr_number)
            diff_files = self.get_parsed_diff(owner, repo_name, pr_number)
        except Exception as e:
            pr_diff = f"Error retrieving diff: {e}"
            diff_files = {}

        # Parse diff for context
        DiffParser.generate_line_number_context(diff_files, owner, repo_name, pr_details["head"]["sha"])

        # Prioritize files for analysis but keep it lightweight for summaries
        priority_files, skipped_count = FilePrioritizer.smart_priority(files, max_files=15)

        # Get high-level analysis without diving too deep
        file_analysis: Dict[str, Dict[str, Any]] = {}
        key_changes = []

        for file_info in priority_files:
            file_path = file_info["filename"]
            try:
                # Get symbols for understanding what changed
                kit_context = {}
                try:
                    file_symbols = repo.extract_symbols(file_path)
                    kit_context["symbols"] = file_symbols[:3]  # Just top 3 for summary
                except Exception:
                    kit_context["symbols"] = []

                file_analysis[file_path] = {
                    "symbols": kit_context["symbols"],
                    "changes": f"+{file_info['additions']} -{file_info['deletions']}",
                    "status": file_info.get("status", "modified"),
                }

                # Track significant changes
                if file_info["additions"] + file_info["deletions"] > 20:
                    key_changes.append(f"{file_path} ({file_info['additions']}+/{file_info['deletions']}-)")

            except Exception:
                file_analysis[file_path] = {
                    "symbols": [],
                    "changes": f"+{file_info['additions']} -{file_info['deletions']}",
                    "status": file_info.get("status", "modified"),
                }

        # Get lightweight repository context
        try:
            file_tree = repo.get_file_tree()
            total_files = len([f for f in file_tree if not f.get("is_dir", True)])
            repo_summary = f"{total_files} files"
        except Exception:
            repo_summary = "Repository structure unavailable"

        # Generate analysis summary
        analysis_summary = FilePrioritizer.get_analysis_summary(files, priority_files)

        # Create summarization-focused prompt
        pr_status = (
            "WIP"
            if "WIP" in pr_details["title"].upper() or "WORK IN PROGRESS" in pr_details["title"].upper()
            else "Ready for Review"
        )

        summary_prompt = f"""You are an expert code analyst. Provide a concise, clear summary of this GitHub PR.

**PR Information:**
- Title: {pr_details["title"]}
- Author: {pr_details["user"]["login"]}
- Files: {len(files)} changed
- Status: {pr_status}
- Repository: {repo_summary}

{analysis_summary}

**Key Changes:**
{chr(10).join([f"- {change}" for change in key_changes[:5]]) if key_changes else "- No major changes detected"}

**Diff:**
```diff
{pr_diff[:8000]}{"..." if len(pr_diff) > 8000 else ""}
```

**File Analysis:**"""

        for file_path, file_data in list(file_analysis.items())[:8]:  # Limit to 8 files for summary
            summary_prompt += f"""
{file_path} ({file_data["changes"]}, {file_data["status"]})
{chr(10).join([f"- {sym['name']} ({sym['type']})" for sym in file_data["symbols"][:2]]) if file_data["symbols"] else "- No symbols detected"}"""

        summary_prompt += """

**Please provide a summary in this format:**

## What This PR Does
[2-3 sentences describing the main purpose and changes]

## Key Changes
- [Most important changes, max 5 bullet points]

## Impact
- [Areas of codebase affected]
- [Potential risks or benefits, if any]

**Guidelines:** Be concise but informative. Focus on what someone reviewing or merging this PR needs to know. Avoid implementation details unless critical."""

        # Use LLM to analyze with summarization context
        analysis: str
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            analysis = await self._analyze_with_anthropic_summary(summary_prompt)
        elif self.config.llm.provider == LLMProvider.GOOGLE:
            analysis = await self._analyze_with_google_summary(summary_prompt)
        elif self.config.llm.provider == LLMProvider.OLLAMA:
            analysis = await self._analyze_with_ollama_summary(summary_prompt)
        else:
            analysis = await self._analyze_with_openai_summary(summary_prompt)

        return analysis

    async def _analyze_with_anthropic_summary(self, summary_prompt: str) -> str:
        """Analyze using Anthropic Claude with summarization focus."""
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            response = self._llm_client.messages.create(
                model=self.config.llm.model,
                max_tokens=min(self.config.llm.max_tokens, 1000),  # Cap for summaries
                # Lower temperature removed for better model compatibility
                messages=[{"role": "user", "content": summary_prompt}],
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

            return text_content if text_content else "No summary generated"

        except Exception as e:
            return f"Error during summarization: {e}"

    async def _analyze_with_google_summary(self, summary_prompt: str) -> str:
        """Analyze using Google Gemini with summarization focus."""
        try:
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed. Run: pip install google-genai")

        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            response = self._llm_client.models.generate_content(
                model=self.config.llm.model,
                contents=summary_prompt,
                config=types.GenerateContentConfig(
                    # Lower temperature removed for better model compatibility
                    max_output_tokens=min(self.config.llm.max_tokens, 1000),  # Cap for summaries
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
            return result_text if result_text is not None else "No summary generated"

        except Exception as e:
            return f"Error during summarization: {e}"

    async def _analyze_with_openai_summary(self, summary_prompt: str) -> str:
        """Analyze using OpenAI GPT with summarization focus."""
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            # GPT-5 models use max_completion_tokens instead of max_tokens
            max_tokens_value = min(self.config.llm.max_tokens, 1000)  # Cap for summaries
            completion_params: Dict[str, Any] = {
                "model": self.config.llm.model,
                # Lower temperature removed for better model compatibility
                "messages": [{"role": "user", "content": summary_prompt}],
            }
            if "gpt-5" in self.config.llm.model.lower():
                completion_params["max_completion_tokens"] = max_tokens_value
            else:
                completion_params["max_tokens"] = max_tokens_value

            response = self._llm_client.chat.completions.create(**completion_params)

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_openai_usage(response)
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
            )

            content = response.choices[0].message.content
            return content if content is not None else "No summary generated"

        except Exception as e:
            return f"Error during summarization: {e}"

    async def _analyze_with_ollama_summary(self, summary_prompt: str) -> str:
        """Analyze using Ollama with summarization focus."""
        if not self._llm_client:
            self._llm_client = create_client_from_review_config(self.config.llm)

        try:
            response = await asyncio.to_thread(
                self._llm_client.generate,
                summary_prompt,
                # Lower temperature removed for better model compatibility
                num_predict=min(self.config.llm.max_tokens, 1000),  # Cap for summaries
            )

            # Strip thinking tokens (reusing logic from parent class)
            from .reviewer import _strip_thinking_tokens

            cleaned_response = _strip_thinking_tokens(response)

            # Track usage (free but good for statistics)
            estimated_input_tokens = len(summary_prompt) // 4
            estimated_output_tokens = len(cleaned_response) // 4
            self.cost_tracker.track_llm_usage(
                self.config.llm.provider, self.config.llm.model, estimated_input_tokens, estimated_output_tokens
            )

            return cleaned_response if cleaned_response else "No summary generated"

        except Exception as e:
            return f"Error during summarization: {e}"

    def summarize_pr(self, pr_input: str, update_body: bool = False) -> str:
        """Summarize a PR with intelligent analysis."""
        try:
            quiet = self.config.quiet

            # Parse PR input
            owner, repo, pr_number = self.parse_pr_url(pr_input)
            if not quiet:
                print(f"📄 Summarizing PR #{pr_number} in {owner}/{repo} [{self.config.llm.model}]")

            # Get PR details
            pr_details = self.get_pr_details(owner, repo, pr_number)
            if not quiet:
                print(f"PR Title: {pr_details['title']}")
                print(f"PR Author: {pr_details['user']['login']}")

            # Get changed files
            files = self.get_pr_files(owner, repo, pr_number)
            if not quiet:
                print(f"Changed files: {len(files)}")

            # Clone repository for analysis (reusing reviewer logic)
            if len(files) > 0 and self.config.clone_for_analysis:
                # Check if using existing repository
                if self.config.repo_path:
                    # Show warning when using existing repository
                    if not quiet:
                        print("⚠️ WARNING: Using existing repository - results may not reflect the main branch")
                        print(f"Using existing repository at: {self.config.repo_path}")
                else:
                    if not quiet:
                        print("Preparing repository for analysis...")

                repo_path = self.get_repo_for_analysis(owner, repo, pr_details)

                # Run async analysis
                if not quiet:
                    print("Running analysis...")
                summary = asyncio.run(self.analyze_pr_for_summary(repo_path, pr_details, files))
            else:
                # Fallback to basic summary without full repo analysis
                summary = self._generate_basic_summary(pr_details, files)

            if update_body:
                if not quiet:
                    print("Updating PR description with summary...")
                self.update_pr_body(owner, repo, pr_number, summary)

            return summary

        except Exception as e:
            return f"❌ Summarization failed: {e}"

    def _generate_basic_summary(self, pr_details: Dict[str, Any], files: List[Dict[str, Any]]) -> str:
        """Generate a basic summary without full repository analysis."""
        total_additions = sum(f.get("additions", 0) for f in files)
        total_deletions = sum(f.get("deletions", 0) for f in files)

        file_types: Dict[str, int] = {}
        for f in files:
            ext = f["filename"].split(".")[-1] if "." in f["filename"] else "no_ext"
            file_types[ext] = file_types.get(ext, 0) + 1

        return f"""## What This PR Does
{pr_details["title"]}

## Key Changes
- {len(files)} files modified
- +{total_additions} additions, -{total_deletions} deletions
- File types: {", ".join([f"{ext} ({count})" for ext, count in sorted(file_types.items())[:5]])}

## Impact
- Author: {pr_details["user"]["login"]}
- Base branch: {pr_details["base"]["ref"]}
- Head branch: {pr_details["head"]["ref"]}

*Note: This is a basic summary. For detailed analysis, enable repository cloning in config.*"""

    def update_pr_body(self, owner: str, repo: str, pr_number: int, summary: str) -> Dict[str, Any]:
        """Update the PR body to include the AI-generated summary."""
        # Get current PR details to read existing body
        pr_details = self.get_pr_details(owner, repo, pr_number)
        current_body = pr_details.get("body", "") or ""

        # Marker for our AI summary section
        summary_marker_start = "<!-- AI SUMMARY START -->"
        summary_marker_end = "<!-- AI SUMMARY END -->"

        # Check if we already have a summary section
        if summary_marker_start in current_body:
            # Replace existing summary
            start_idx = current_body.find(summary_marker_start)
            end_idx = current_body.find(summary_marker_end)
            if end_idx != -1:
                # Remove old summary section
                end_idx += len(summary_marker_end)
                current_body = current_body[:start_idx] + current_body[end_idx:]
            else:
                # Marker start found but no end marker - remove from start marker onwards
                current_body = current_body[:start_idx]

        # Clean up any trailing whitespace
        current_body = current_body.rstrip()

        # Add our summary section
        summary_section = f"""

{summary_marker_start}
{summary}

*Generated by [kit](https://github.com/cased/kit) v{self._get_kit_version()} • Model: {self.config.llm.model}*
{summary_marker_end}"""

        updated_body = current_body + summary_section

        # Update PR via GitHub API
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        data = {"body": updated_body}

        response = self.github_session.patch(url, json=data)
        response.raise_for_status()

        return response.json()

    def _get_kit_version(self) -> str:
        """Get kit version for summary attribution."""
        try:
            import kit

            return getattr(kit, "__version__", "dev")
        except ImportError:
            return "dev"
