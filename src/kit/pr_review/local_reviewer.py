"""Local diff reviewer for reviewing changes without GitHub PRs."""

import asyncio
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from ..repository import Repository
from .config import LLMProvider, ReviewConfig
from .cost_tracker import CostTracker
from .diff_parser import DiffParser
from .file_prioritizer import FilePrioritizer
from .priority_filter import filter_review_by_priority
from .validator import validate_review_quality


@dataclass
class LocalChange:
    """Represents a local git change."""

    base_ref: str
    head_ref: str
    title: str
    description: str
    author: str
    repo_path: Path
    diff: str
    files: List[Dict[str, Any]]


class LocalDiffReviewer:
    """Reviews local git diffs without requiring a GitHub PR."""

    def __init__(self, config: ReviewConfig, repo_path: Optional[Union[Path, str]] = None):
        self.config = config
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.cost_tracker = CostTracker(config.custom_pricing)
        self._llm_client: Optional[Any] = None
        self._ollama_session: Optional[requests.Session] = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()
        return False

    def cleanup(self):
        """Clean up resources like LLM clients and sessions."""
        # Close Ollama session if exists
        if self._ollama_session:
            try:
                self._ollama_session.close()
            except Exception:
                pass
            self._ollama_session = None

        # Reset LLM client
        self._llm_client = None

    def _validate_git_ref(self, ref: str) -> bool:
        """Validate git ref format to prevent injection attacks."""
        # Special cases
        if ref in ["HEAD", "--staged", "--cached"]:
            return True

        # Block obvious path traversal attempts and shell injection
        # But allow ".." in branch range syntax like "main..feature"
        if ref.startswith("/") or ref.startswith("~") or ref.startswith("-"):
            return False

        # Block path traversal patterns (but allow .. in ranges)
        if "../" in ref or "..\\" in ref:
            return False

        # Block shell metacharacters
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", "\x00"]
        if any(char in ref for char in dangerous_chars):
            return False

        # Handle git range syntax (main..feature, main...feature)
        if ".." in ref:
            # Check if it's a valid range pattern
            if "..." in ref:
                # Three dots: main...feature (symmetric difference)
                parts = ref.split("...", 1)
            else:
                # Two dots: main..feature (range)
                parts = ref.split("..", 1)

            if len(parts) == 2:
                # Validate both parts of the range
                return all(self._validate_single_ref(part) for part in parts)
            else:
                return False

        # Block dots at the beginning or end of ref names
        if ref.startswith(".") or ref.endswith("."):
            return False

        # Block multiple consecutive dots (more than 3)
        if "...." in ref:
            return False

        # Allow HEAD with various notations
        # HEAD~3, HEAD^, HEAD@{1}, HEAD@{upstream}
        if re.match(r"^HEAD[@~^].*$", ref):
            return True

        # Allow commit SHAs (full or abbreviated)
        if re.match(r"^[a-f0-9]{4,40}$", ref):
            return True

        # Allow remote refs like origin/main
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9/_.-]+$", ref):
            return True

        # Allow branch names with restricted dot usage
        # Dots are only allowed in specific patterns:
        # - Version numbers: v1.2.3, 1.2.3
        # - Release candidates: v1.2.3-rc1
        # - Feature branches with dots: feature/name.1
        # But NOT: ../../../etc/passwd or similar path traversal
        if re.match(r"^[a-zA-Z0-9/_-]+$", ref):
            # No dots - safe
            return True
        elif re.match(r"^[a-zA-Z0-9/_-]*\.\d+([a-zA-Z0-9/_-]*\.\d+)*[a-zA-Z0-9/_-]*$", ref):
            # Dots only in version number patterns
            return True
        elif re.match(r"^[a-zA-Z0-9/_-]*\.\d+[a-zA-Z0-9/_-]*$", ref):
            # Single dot with version number
            return True
        elif re.match(r"^v?\d+\.\d+(\.\d+)?(-[a-zA-Z0-9._-]+)?$", ref):
            # Version tags
            return True

        return False

    def _validate_single_ref(self, ref: str) -> bool:
        """Validate a single git ref (without range syntax)."""
        # Block obvious path traversal attempts and shell injection
        if ref.startswith("/") or ref.startswith("~") or ref.startswith("-"):
            return False

        # Block path traversal patterns
        if "../" in ref or "..\\" in ref:
            return False

        # Block shell metacharacters
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", "\x00"]
        if any(char in ref for char in dangerous_chars):
            return False

        # Block dots at the beginning or end of ref names
        if ref.startswith(".") or ref.endswith("."):
            return False

        # Block multiple consecutive dots
        if "..." in ref:
            return False

        # Allow HEAD with various notations
        if re.match(r"^HEAD[@~^].*$", ref):
            return True

        # Allow commit SHAs (full or abbreviated)
        if re.match(r"^[a-f0-9]{4,40}$", ref):
            return True

        # Allow remote refs like origin/main
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9/_.-]+$", ref):
            return True

        # Allow branch names with restricted dot usage
        if re.match(r"^[a-zA-Z0-9/_-]+$", ref):
            # No dots - safe
            return True
        elif re.match(r"^[a-zA-Z0-9/_-]*\.\d+([a-zA-Z0-9/_-]*\.\d+)*[a-zA-Z0-9/_-]*$", ref):
            # Dots only in version number patterns
            return True
        elif re.match(r"^[a-zA-Z0-9/_-]*\.\d+[a-zA-Z0-9/_-]*$", ref):
            # Single dot with version number
            return True
        elif re.match(r"^v?\d+\.\d+(\.\d+)?(-[a-zA-Z0-9._-]+)?$", ref):
            # Version tags
            return True

        return False

    def _run_git_command(self, *args: str) -> Tuple[str, int]:
        """Run a git command and return output and exit code."""
        try:
            # Validate arguments to prevent command injection
            safe_args = []
            for i, arg in enumerate(args):
                if not isinstance(arg, str):
                    raise ValueError(f"Invalid git argument type: {type(arg)}")

                # First argument is the git subcommand - validate it
                if i == 0:
                    allowed_commands = {"diff", "show", "rev-parse", "log", "status", "config"}
                    if arg not in allowed_commands:
                        raise ValueError(f"Disallowed git command: {arg}")
                    safe_args.append(arg)
                # Arguments starting with - are options
                elif arg.startswith("-"):
                    # Whitelist safe options
                    allowed_options = {
                        "-s",
                        "--",
                        "--cached",
                        "--name-status",
                        "--numstat",
                        "--porcelain",
                        "--verify",
                        "--quiet",
                        "--no-pager",
                        "--format",
                        "--pretty",
                        "--git-dir",
                    }
                    # Allow --format= and --pretty= with values
                    if arg.startswith("--format=") or arg.startswith("--pretty="):
                        # These need to be passed as-is since they contain the format string
                        # The format string itself is safe as it's constructed by our code
                        safe_args.append(arg)
                    elif arg in allowed_options:
                        safe_args.append(arg)
                    else:
                        raise ValueError(f"Disallowed git option: {arg}")
                # Git refs need validation (but not after --)
                elif i > 0 and args[0] in {"diff", "show", "rev-parse", "log"}:
                    # Check if we've seen "--" already, which means following args are paths
                    seen_separator = False
                    for j in range(i):
                        if args[j] == "--":
                            seen_separator = True
                            break

                    if seen_separator:
                        # Everything after -- is a file path, not a ref
                        safe_args.append(shlex.quote(arg))
                    else:
                        # For git commands, we need to distinguish between refs and file paths
                        # File paths typically don't contain git ref patterns
                        # and are usually passed after certain options

                        # If this looks like a file path (contains / or . and not a git ref pattern)
                        # and we're in a context where file paths are expected, treat it as a path
                        if (
                            ("/" in arg or "." in arg)
                            and not self._validate_git_ref(arg)
                            and args[0] == "diff"
                            and any(opt in args for opt in ["--cached", "--name-status", "--numstat"])
                        ):
                            # This is likely a file path, not a ref
                            safe_args.append(shlex.quote(arg))
                        else:
                            # For diff ranges like main..feature or main...feature
                            if ".." in arg:
                                # Handle both .. and ... operators
                                if "..." in arg:
                                    parts = arg.split("...", 1)
                                else:
                                    parts = arg.split("..", 1)

                                if len(parts) == 2 and all(self._validate_git_ref(p) for p in parts):
                                    safe_args.append(arg)
                                else:
                                    raise ValueError(f"Invalid git ref range: {arg}")
                            elif self._validate_git_ref(arg):
                                safe_args.append(arg)
                            else:
                                raise ValueError(f"Invalid git ref: {arg}")
                # Other arguments (like format strings) should be quoted
                else:
                    safe_args.append(shlex.quote(arg))

            # Build command with proper quoting
            cmd = ["git", *safe_args]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,  # Prevent hanging on large operations
                shell=False,  # Never use shell=True
            )
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", 128  # Git error code for timeout
        except FileNotFoundError:
            raise RuntimeError("Git is not installed or not in PATH")
        except Exception as e:
            raise RuntimeError(f"Failed to execute git command: {e}")

    def _parse_diff_spec(self, diff_spec: str) -> Tuple[str, str]:
        """Parse diff specification like 'main..feature' or 'HEAD~3'."""
        if diff_spec == "--staged":
            return "HEAD", "staged"
        elif ".." in diff_spec:
            parts = diff_spec.split("..", 1)
            return parts[0], parts[1]
        else:
            # Single ref means compare with HEAD
            return diff_spec, "HEAD"

    def _get_commit_info(self, ref: str) -> Dict[str, str]:
        """Get commit information for a given ref."""
        if ref == "staged":
            return {
                "hash": "staged",
                "author": self._run_git_command("config", "user.name")[0],
                "date": "now",
                "subject": "Staged changes",
                "body": "",
            }

        # Get commit info
        format_str = "%H%n%an%n%ad%n%s%n%b"
        output, code = self._run_git_command("show", "-s", f"--format={format_str}", ref)

        if code != 0:
            raise ValueError(f"Invalid git ref: {ref}")

        lines = output.split("\n")
        return {
            "hash": lines[0] if len(lines) > 0 else "",
            "author": lines[1] if len(lines) > 1 else "",
            "date": lines[2] if len(lines) > 2 else "",
            "subject": lines[3] if len(lines) > 3 else "",
            "body": "\n".join(lines[4:]) if len(lines) > 4 else "",
        }

    def _get_diff(self, base_ref: str, head_ref: str) -> str:
        """Get diff between two refs."""
        # Check if repository is in a clean state first
        status_output, status_code = self._run_git_command("status", "--porcelain")
        if status_code != 0:
            raise ValueError("Unable to check repository status")

        # Check for merge/rebase in progress
        merge_head_exists = (self.repo_path / ".git" / "MERGE_HEAD").exists()
        rebase_dir_exists = (self.repo_path / ".git" / "rebase-merge").exists() or (
            self.repo_path / ".git" / "rebase-apply"
        ).exists()

        if merge_head_exists:
            raise ValueError("Repository is in the middle of a merge. Please complete or abort the merge first.")
        if rebase_dir_exists:
            raise ValueError("Repository is in the middle of a rebase. Please complete or abort the rebase first.")

        if head_ref == "staged":
            # Get staged changes
            diff, code = self._run_git_command("diff", "--cached")
        else:
            diff, code = self._run_git_command("diff", f"{base_ref}..{head_ref}")

        if code != 0:
            # Try to provide more helpful error messages
            if code == 128:
                # Check if refs exist
                base_exists, _ = self._run_git_command("rev-parse", "--verify", base_ref)
                head_exists, _ = self._run_git_command("rev-parse", "--verify", head_ref)
                if _ != 0:
                    raise ValueError(f"Invalid git ref: {base_ref}")
                if head_exists == "" and _ != 0:
                    raise ValueError(f"Invalid git ref: {head_ref}")
            raise ValueError(f"Failed to get diff between {base_ref} and {head_ref}")

        return diff

    def _get_changed_files(self, base_ref: str, head_ref: str) -> List[Dict[str, Any]]:
        """Get list of changed files between two refs."""
        if head_ref == "staged":
            output, code = self._run_git_command("diff", "--cached", "--name-status")
        else:
            output, code = self._run_git_command("diff", "--name-status", f"{base_ref}..{head_ref}")

        if code != 0:
            return []

        files = []
        for line in output.split("\n"):
            if not line:
                continue

            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue

            status_code, filename = parts
            status_map = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed", "C": "copied"}

            status = status_map.get(status_code[0], "modified")

            # Get line stats
            if head_ref == "staged":
                stats_output, _ = self._run_git_command("diff", "--cached", "--numstat", filename)
            else:
                stats_output, _ = self._run_git_command("diff", "--numstat", f"{base_ref}..{head_ref}", "--", filename)

            additions = 0
            deletions = 0
            if stats_output:
                stats_parts = stats_output.split("\t")
                if len(stats_parts) >= 2:
                    try:
                        additions = int(stats_parts[0])
                        deletions = int(stats_parts[1])
                    except ValueError:
                        pass

            files.append(
                {
                    "filename": filename,
                    "status": status,
                    "additions": additions,
                    "deletions": deletions,
                    "changes": additions + deletions,
                }
            )

        return files

    def _prepare_local_change(self, diff_spec: str) -> LocalChange:
        """Prepare LocalChange object from diff specification."""
        base_ref, head_ref = self._parse_diff_spec(diff_spec)

        # Get commit info
        self._get_commit_info(base_ref)
        head_info = self._get_commit_info(head_ref)

        # Get diff and files
        diff = self._get_diff(base_ref, head_ref)
        files = self._get_changed_files(base_ref, head_ref)

        # Construct title and description
        if head_ref == "staged":
            title = "Review staged changes"
            description = "Changes currently staged for commit"
        else:
            title = head_info["subject"]
            description = head_info["body"]

        return LocalChange(
            base_ref=base_ref,
            head_ref=head_ref,
            title=title,
            description=description,
            author=head_info["author"],
            repo_path=self.repo_path,
            diff=diff,
            files=files,
        )

    async def _analyze_with_kit(self, change: LocalChange) -> Dict[str, Any]:
        """Analyze repository using kit's Repository class."""
        repo = Repository(str(self.repo_path))

        # Get all symbols
        all_symbols = repo.extract_symbols()

        # Parse the diff to get changed symbols
        parser = DiffParser()
        parser.parse_diff(change.diff)

        changed_files = {f["filename"] for f in change.files}

        # Find symbols in changed files
        symbols_in_changed_files = []
        for symbol in all_symbols:
            if symbol.get("file_path") in changed_files:
                symbol_name = symbol.get("name", "")
                # Get usages if available
                try:
                    usages = repo.find_symbol_usages(symbol_name) if symbol_name else []
                    usage_count = len(usages)
                except Exception as e:
                    print(f"Error getting symbol usages: {e}")
                    usage_count = 0

                symbols_in_changed_files.append(
                    {
                        "name": symbol_name,
                        "type": symbol.get("type", "unknown"),
                        "file": symbol.get("file_path", ""),
                        "line": symbol.get("line_number", 0),
                        "usage_count": usage_count,
                    }
                )

        # Get repository structure
        structure = repo.get_file_tree()

        return {
            "symbols": symbols_in_changed_files,
            "structure": structure,
            "total_files": len(structure),
            "changed_files": len(changed_files),
        }

    def _generate_review_prompt(self, change: LocalChange, analysis: Dict[str, Any]) -> str:
        """Generate prompt for LLM review."""
        # Prioritize files
        prioritizer = FilePrioritizer()
        selected_files, total_files = prioritizer.smart_priority(change.files, max_files=self.config.max_files)

        # Build context about the change
        context = f"""You are reviewing a local git diff.

Repository: {change.repo_path.name}
Base: {change.base_ref}
Head: {change.head_ref}
Author: {change.author}

Title: {change.title}
Description: {change.description}

Repository contains {analysis["total_files"]} files total.
This change modifies {analysis["changed_files"]} files.

Changed symbols and their usage counts:
"""

        for symbol in analysis["symbols"][:20]:  # Limit to top 20 symbols
            context += f"- {symbol['type']} {symbol['name']} in {symbol['file']}:{symbol['line']} (used {symbol['usage_count']} times)\n"

        # Add the diff
        context += f"\n\nDiff to review ({len(selected_files)} files selected from {len(change.files)} total):\n\n"

        # Parse diff and add file patches
        parser = DiffParser()
        parsed_diff = parser.parse_diff(change.diff)

        selected_filenames = {f["filename"] for f in selected_files}

        for filename, file_diff in parsed_diff.items():
            if filename in selected_filenames:
                context += f"File: {filename}\n"
                context += "=" * 80 + "\n"

                for hunk in file_diff.hunks:
                    context += f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@\n"
                    for line in hunk.lines:
                        # Lines are already formatted with +/- prefixes
                        context += line
                        if not line.endswith("\n"):
                            context += "\n"
                    context += "\n"

        # Add review instructions
        context += """

Please review this code diff and provide feedback organized by priority:
- HIGH priority: Critical issues (bugs, security vulnerabilities, data loss risks)
- MEDIUM priority: Important issues (performance problems, maintainability concerns, best practice violations)
- LOW priority: Minor issues (style improvements, optional optimizations)

For each issue, specify the exact file and line number where applicable.
Format: `filename:line_number`

Focus on practical, actionable feedback. Be concise but specific.
"""

        return context

    async def _get_llm_review(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        """Get review from LLM."""
        # Call the appropriate provider's method
        # llm_provider is already a string (not an enum)
        if self.config.llm_provider == "anthropic":
            response = await self._analyze_with_anthropic_enhanced(prompt)
        elif self.config.llm_provider == "google":
            response = await self._analyze_with_google_enhanced(prompt)
        elif self.config.llm_provider == "ollama":
            response = await self._analyze_with_ollama_enhanced(prompt)
        else:  # OpenAI
            response = await self._analyze_with_openai_enhanced(prompt)

        # Return empty usage dict, as tokens are tracked directly in each provider method
        usage: Dict[str, int] = {}

        return response, usage

    async def _analyze_with_anthropic_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Anthropic with enhanced kit context."""
        try:
            import anthropic
        except ImportError:
            raise ValueError("Anthropic library not installed. Install with: pip install anthropic")

        if not self._llm_client:
            self._llm_client = anthropic.Anthropic(api_key=self.config.llm_api_key)

        try:
            response = self._llm_client.messages.create(
                model=self.config.llm_model,
                max_tokens=self.config.llm_max_tokens,
                messages=[{"role": "user", "content": enhanced_prompt}],
            )

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_anthropic_usage(response)
            model = self.config.llm_model or self.config.llm.model
            self.cost_tracker.track_llm_usage(LLMProvider.ANTHROPIC, model, input_tokens, output_tokens)

            # Extract text from the response content
            text_content = ""
            for content_block in response.content:
                if hasattr(content_block, "text"):
                    text_content += content_block.text

            return text_content if text_content else "No text content in response"
        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_openai_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using OpenAI with enhanced kit context."""
        try:
            import openai
        except ImportError:
            raise ValueError("OpenAI library not installed. Install with: pip install openai")

        if not self._llm_client:
            # Support custom OpenAI compatible providers via api_base_url
            if self.config.llm_api_base_url:
                self._llm_client = openai.OpenAI(api_key=self.config.llm_api_key, base_url=self.config.llm_api_base_url)
            else:
                self._llm_client = openai.OpenAI(api_key=self.config.llm_api_key)

        try:
            # GPT-5 models use max_completion_tokens instead of max_tokens
            model = self.config.llm_model or self.config.llm.model
            completion_params: Dict[str, Any] = {
                "model": self.config.llm_model,
                "messages": [{"role": "user", "content": enhanced_prompt}],
            }
            if "gpt-5" in model.lower():
                completion_params["max_completion_tokens"] = self.config.llm_max_tokens
            else:
                completion_params["max_tokens"] = self.config.llm_max_tokens

            response = self._llm_client.chat.completions.create(**completion_params)

            # Track cost
            input_tokens, output_tokens = self.cost_tracker.extract_openai_usage(response)
            model = self.config.llm_model or self.config.llm.model
            self.cost_tracker.track_llm_usage(LLMProvider.OPENAI, model, input_tokens, output_tokens)

            content = response.choices[0].message.content
            return content if content is not None else "No response content"
        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_google_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Google with enhanced kit context."""
        try:
            import google.genai as genai
            from google.genai import types
        except ImportError:
            raise ValueError("Google AI library not installed. Install with: pip install google-genai")

        if not self._llm_client:
            self._llm_client = genai.Client(api_key=self.config.llm_api_key)

        try:
            # Use the correct API format for the new google-genai SDK
            response = self._llm_client.models.generate_content(
                model=self.config.llm_model,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.config.llm_max_tokens,
                ),
            )

            # Track cost using accurate token counts from the response
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
                model = self.config.llm_model or self.config.llm.model
                self.cost_tracker.track_llm_usage(LLMProvider.GOOGLE, model, input_tokens, output_tokens)
            else:
                # Fallback: estimate tokens based on character count
                estimated_input_tokens = len(enhanced_prompt) // 4
                estimated_output_tokens = len(str(response.text)) // 4 if response.text else 0
                model = self.config.llm_model or self.config.llm.model
                self.cost_tracker.track_llm_usage(
                    LLMProvider.GOOGLE, model, estimated_input_tokens, estimated_output_tokens
                )

            # Ensure we always return a string
            result_text = response.text
            return result_text if result_text else "No response from Google AI"
        except Exception as e:
            return f"Error during enhanced LLM analysis: {e}"

    async def _analyze_with_ollama_enhanced(self, enhanced_prompt: str) -> str:
        """Analyze using Ollama with enhanced kit context."""
        if not self._llm_client:
            # Create Ollama client
            class OllamaClient:
                def __init__(self, base_url: str, model: str, session: requests.Session):
                    self.base_url = base_url
                    self.model = model
                    self.session = session

                def generate(self, prompt: str, **kwargs) -> str:
                    """Generate text using Ollama's API."""
                    url = f"{self.base_url}/api/generate"
                    data = {"model": self.model, "prompt": prompt, "stream": False, **kwargs}
                    response = self.session.post(url, json=data)
                    response.raise_for_status()
                    return response.json().get("response", "")

            # Create a session if not exists
            if not self._ollama_session:
                self._ollama_session = requests.Session()

            model = self.config.llm_model or self.config.llm.model
            session = self._ollama_session
            assert session is not None  # Type guard for mypy
            self._llm_client = OllamaClient(self.config.llm_api_base_url or "http://localhost:11434", model, session)

        try:
            response = await asyncio.to_thread(
                self._llm_client.generate,
                enhanced_prompt,
                num_predict=self.config.llm_max_tokens,
            )

            # Ollama is free, so no cost tracking needed, but we can track usage
            # For consistency, we'll estimate tokens (very rough)
            estimated_input_tokens = len(enhanced_prompt) // 4
            estimated_output_tokens = len(response) // 4
            model = self.config.llm_model or self.config.llm.model
            self.cost_tracker.track_llm_usage(
                LLMProvider.OLLAMA, model, estimated_input_tokens, estimated_output_tokens
            )

            return response if response else "No response content from Ollama"
        except Exception as e:
            return f"Error during enhanced Ollama analysis: {e}"

    def _format_review_output(self, review_text: str, change: LocalChange, cost: float) -> str:
        """Format the review output for display."""
        # For local reviews, line references are already correct
        # No need to fix them like we do for GitHub URLs

        # Apply priority filtering if configured
        if self.config.priority_filter:
            review_text = filter_review_by_priority(review_text, self.config.priority_filter)

        # Add header and footer
        header = f"""## 🔍 Kit Local Diff Review

**Repository**: {change.repo_path.name}
**Diff**: {change.base_ref}..{change.head_ref}
**Author**: {change.author}

---

"""

        footer = f"""

---

*Generated by kit • Cost: ${cost:.4f} • Model: {self.config.llm_model}*
"""

        return header + review_text + footer

    def _save_review(self, review: str, change: LocalChange) -> Path:
        """Save review to a file."""
        # Create reviews directory if it doesn't exist
        reviews_dir = self.repo_path / ".kit" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_refs = f"{change.base_ref}..{change.head_ref}".replace("/", "_").replace(" ", "_")
        filename = f"review_{timestamp}_{safe_refs}.md"

        review_path = reviews_dir / filename
        review_path.write_text(review)

        return review_path

    def review(self, diff_spec: str) -> str:
        """Review a local diff specification."""
        try:
            # Check if we're in a git repository
            _, code = self._run_git_command("rev-parse", "--git-dir")
            if code != 0:
                raise ValueError("Not in a git repository")

            # Prepare the change object
            if not self.config.quiet:
                print("Analyzing local changes...")

            change = self._prepare_local_change(diff_spec)

            if not change.diff:
                return "No changes to review."

            # Analyze with kit
            if not self.config.quiet:
                print("Analyzing repository with kit...")

            analysis = asyncio.run(self._analyze_with_kit(change))

            # Generate review prompt
            prompt = self._generate_review_prompt(change, analysis)

            # Get LLM review
            if not self.config.quiet:
                print(f"Generating review with {self.config.llm_model}...")

            review_text, usage = asyncio.run(self._get_llm_review(prompt))

            # Get total cost from tracker
            cost = self.cost_tracker.get_total_cost()

            # Format output
            formatted_review = self._format_review_output(review_text, change, cost)

            # Save review if configured
            if self.config.save_reviews:
                try:
                    review_path = self._save_review(formatted_review, change)
                    if not self.config.quiet:
                        print(f"\nReview saved to: {review_path.relative_to(self.repo_path)}")
                except PermissionError as e:
                    if not self.config.quiet:
                        print(f"\n⚠️  Warning: Could not save review to file: {e}")

            # Validate review quality
            validation = validate_review_quality(review_text, change.diff, [f["filename"] for f in change.files])
            if not self.config.quiet and validation.score < 0.5:
                print("\n⚠️  Warning: Review quality score is low. Consider reviewing manually.")

            return formatted_review

        except Exception as e:
            raise RuntimeError(f"Failed to review local diff: {e!s}")
