"""Agentic PR Reviewer - Multi-turn analysis with tool use."""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, cast

import requests

from .cache import RepoCache
from .config import LLMProvider, ReviewConfig
from .cost_tracker import CostTracker
from .diff_parser import DiffParser, FileDiff
from .file_prioritizer import FilePrioritizer
from .priority_filter import filter_review_by_priority


class AgenticPRReviewer:
    """Agentic PR reviewer that uses multi-turn analysis with kit tools."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.github_session = requests.Session()
        self.github_session.headers.update(
            {
                "Authorization": f"token {config.github.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "kit-agentic-reviewer/0.1.0",
            }
        )
        self._llm_client: Optional[Any] = None
        self.repo_cache = RepoCache(config)
        self.cost_tracker = CostTracker(config.custom_pricing)
        self.conversation_history: List[Dict[str, str]] = []
        self.analysis_state: Dict[str, Any] = {}

        # Customizable turn limit - default to 15 for reasonable completion rate
        self.max_turns = getattr(config, "agentic_max_turns", 15)
        self.finalize_threshold = getattr(config, "agentic_finalize_threshold", 10)

        # Diff caching placeholders
        self._cached_diff_key: Optional[tuple[str, str, int]] = None
        self._cached_diff_text: Optional[str] = None
        self._cached_parsed_diff: Optional[Dict[str, FileDiff]] = None
        self._cached_parsed_key: Optional[tuple[str, str, int]] = None

    def parse_pr_url(self, pr_input: str) -> tuple[str, str, int]:
        """Parse PR URL to extract owner, repo, and PR number."""
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
        key = (owner, repo, pr_number)

        if getattr(self, "_cached_diff_key", None) == key and hasattr(self, "_cached_diff_text"):
            assert self._cached_diff_text is not None
            return self._cached_diff_text

        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = dict(self.github_session.headers)
        headers["Accept"] = "application/vnd.github.v3.diff"

        response = self.github_session.get(url, headers=headers)
        response.raise_for_status()

        self._cached_diff_key = key
        self._cached_diff_text = response.text
        if hasattr(self, "_cached_parsed_diff"):
            delattr(self, "_cached_parsed_diff")

        return response.text

    def get_parsed_diff(self, owner: str, repo: str, pr_number: int) -> Dict[str, FileDiff]:
        key = (owner, repo, pr_number)

        if self._cached_parsed_key == key and self._cached_parsed_diff is not None:
            return self._cached_parsed_diff

        diff_text = self.get_pr_diff(owner, repo, pr_number)
        parsed: Dict[str, FileDiff] = DiffParser.parse_diff(diff_text)
        self._cached_parsed_key = key
        self._cached_parsed_diff = parsed
        return parsed

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

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get kit's tools plus our PR-specific analysis tools."""
        try:
            from kit.tool_schemas import get_tool_schemas

            # Get all kit's existing tool schemas
            kit_tools_raw = get_tool_schemas()

            kit_tools = []
            for tool in kit_tools_raw:
                # Skip open_repository since we already have a Repository instance
                if tool["name"] == "open_repository":
                    continue
                anthropic_tool = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["inputSchema"],
                }
                kit_tools.append(anthropic_tool)

        except ImportError:
            kit_tools = []

        # Add PR-specific analysis tools
        pr_specific_tools = [
            {
                "name": "finalize_review",
                "description": "Finalize the review with comprehensive analysis",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "review_content": {"type": "string", "description": "The final comprehensive review content"}
                    },
                    "required": ["review_content"],
                },
            },
            {
                "name": "get_relevant_chunks",
                "description": ("Get specific chunks from a file based on relevance to the PR changes"),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to chunk"},
                        "relevance_query": {"type": "string", "description": "What to look for in chunks"},
                        "max_chunks": {"type": "integer", "description": "Maximum chunks to return", "default": 3},
                    },
                    "required": ["file_path", "relevance_query"],
                },
            },
            {
                "name": "batch_analyze_files",
                "description": "Analyze multiple files at once for efficiency",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_paths": {"type": "array", "items": {"type": "string"}},
                        "include_symbols": {"type": "boolean", "default": True},
                        "max_content_length": {"type": "integer", "default": 3000},
                    },
                    "required": ["file_paths"],
                },
            },
            {
                "name": "deep_code_analysis",
                "description": ("Perform deep analysis of code quality, patterns, and issues"),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "analysis_focus": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["security", "performance", "maintainability", "correctness"],
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "analyze_cross_file_impact",
                "description": ("Analyze how changes affect other files and the broader codebase"),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "changed_files": {"type": "array", "items": {"type": "string"}},
                        "impact_depth": {
                            "type": "string",
                            "enum": ["immediate", "extended", "full"],
                            "default": "extended",
                        },
                    },
                    "required": ["changed_files"],
                },
            },
        ]

        return kit_tools + pr_specific_tools

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute a tool call using kit's Repository class."""
        try:
            repo = self.analysis_state.get("repo")
            if not repo:
                return "Error: Repository not initialized"

            # Handle kit's MCP tools (adapt parameters but use Repository methods directly)
            if tool_name == "get_file_content":
                # Kit expects: repo_id, file_path | We have: file_path
                file_path = parameters.get("file_path")
                if not file_path:
                    return "Error: file_path parameter required"
                content = repo.get_file_content(file_path)
                return f"File content for {file_path}:\n```\n{content}\n```"

            elif tool_name == "extract_symbols":
                # Kit expects: repo_id, file_path, symbol_type | We have: file_path, symbol_type
                file_path = parameters.get("file_path")
                symbol_type = parameters.get("symbol_type")
                if not file_path:
                    return "Error: file_path parameter required"
                symbols = repo.extract_symbols(file_path)
                if symbol_type:
                    symbols = [s for s in symbols if s.get("type") == symbol_type]
                return f"Symbols in {file_path}:\n" + json.dumps(symbols, indent=2)

            elif tool_name == "find_symbol_usages":
                # Kit expects: repo_id, symbol_name, symbol_type, file_path | We have: symbol_name, symbol_type, file_path
                symbol_name = parameters.get("symbol_name")
                symbol_type = parameters.get("symbol_type")
                file_path = parameters.get("file_path")
                if not symbol_name:
                    return "Error: symbol_name parameter required"
                usages = repo.find_symbol_usages(symbol_name, symbol_type=symbol_type)
                if file_path:
                    usages = [u for u in usages if u.get("file") == file_path]
                return f"Usages of '{symbol_name}':\n" + json.dumps(usages, indent=2)

            elif tool_name == "search_code":
                # Kit expects: repo_id, query, pattern | We have: query, pattern
                query = parameters.get("query")
                pattern = parameters.get("pattern", "*.py")
                if not query:
                    return "Error: query parameter required"
                results = repo.search_text(query, file_pattern=pattern)
                return f"Search results for '{query}' in {pattern}:\n" + json.dumps(results, indent=2)

            elif tool_name == "get_file_tree":
                # Kit expects: repo_id | We have: (no params needed)
                tree = repo.get_file_tree()
                return (
                    f"File tree ({len(tree)} files):\n"
                    + json.dumps(tree[:50], indent=2)
                    + (f"\n... and {len(tree) - 50} more files" if len(tree) > 50 else "")
                )

            elif tool_name == "get_code_summary":
                # Kit expects: repo_id, file_path, symbol_name | We have: file_path, symbol_name
                file_path = parameters.get("file_path")
                symbol_name = parameters.get("symbol_name")
                if not file_path:
                    return "Error: file_path parameter required"
                # For now, just return file content since we don't have code summarizer integrated
                content = repo.get_file_content(file_path)
                if len(content) > 1000:
                    content = content[:1000] + "... (truncated)"
                result = f"Code summary for {file_path}:\n```\n{content}\n```"
                if symbol_name:
                    symbols = repo.extract_symbols(file_path)
                    matching_symbols = [s for s in symbols if s.get("name") == symbol_name]
                    if matching_symbols:
                        result += f"\n\nSymbol '{symbol_name}' details:\n" + json.dumps(matching_symbols, indent=2)
                return result

            elif tool_name == "get_git_info":
                # Kit expects: repo_id | We have: (no params needed)
                try:
                    git_info = {
                        "current_sha": repo.current_sha,
                        "current_branch": repo.current_branch,
                        "remote_url": getattr(repo, "remote_url", "unknown"),
                    }
                    return "Git info:\n" + json.dumps(git_info, indent=2)
                except Exception as e:
                    return f"Git info unavailable: {e!s}"

            # Legacy kit tools that might still be called directly (backwards compatibility)
            elif tool_name == "search_text":
                pattern = parameters["pattern"]
                file_pattern = parameters.get("file_pattern", "*")
                results = repo.search_text(pattern, file_pattern=file_pattern)
                return f"Search results for '{pattern}' in {file_pattern}:\n" + json.dumps(results, indent=2)

            elif tool_name == "get_dependency_analysis":
                analyzer = repo.get_dependency_analyzer()
                context = analyzer.generate_llm_context()
                return f"Dependency analysis:\n{context}"

            elif tool_name == "chunk_file_by_symbols":
                chunks = repo.chunk_file_by_symbols(parameters["file_path"])
                result = f"Symbol chunks for {parameters['file_path']} ({len(chunks)} chunks):\n"
                for i, chunk in enumerate(chunks[:3]):
                    result += f"\nChunk {i + 1}:\n{chunk.content}\n---\n"
                if len(chunks) > 3:
                    result += f"\n... and {len(chunks) - 3} more chunks"
                return result

            elif tool_name == "extract_context_around_line":
                context = repo.extract_context_around_line(
                    parameters["file_path"], parameters["line_number"], parameters.get("context_lines", 10)
                )
                return f"Context around line {parameters['line_number']} in {parameters['file_path']}:\n```\n{context}\n```"

            # PR-specific analysis tools
            elif tool_name == "finalize_review":
                self.analysis_state["final_review"] = parameters["review_content"]
                return "Review finalized successfully"

            elif tool_name == "get_relevant_chunks":
                return self._get_relevant_chunks(repo, parameters)

            elif tool_name == "batch_analyze_files":
                return self._batch_analyze_files(repo, parameters)

            elif tool_name == "deep_code_analysis":
                return self._deep_code_analysis(repo, parameters)

            elif tool_name == "analyze_cross_file_impact":
                return self._analyze_cross_file_impact(repo, parameters)

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing {tool_name}: {e!s}"

    def _get_relevant_chunks(self, repo, parameters: Dict[str, Any]) -> str:
        """Get relevant chunks from a file based on query."""
        chunks = repo.chunk_file_by_symbols(parameters["file_path"])
        relevance_query = parameters["relevance_query"].lower()
        max_chunks = parameters.get("max_chunks", 3)

        # Score chunks based on relevance
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            content_lower = chunk.content.lower()
            score = sum(content_lower.count(word) for word in relevance_query.split())
            # Boost for function/class definitions
            if any(
                f"def {word}" in content_lower or f"class {word}" in content_lower for word in relevance_query.split()
            ):
                score += 10
            scored_chunks.append((score, i, chunk))

        # Sort by relevance and take top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        relevant_chunks = scored_chunks[:max_chunks]

        result = f"Relevant chunks for '{relevance_query}' in {parameters['file_path']}:\n"
        for score, chunk_idx, chunk in relevant_chunks:
            if score > 0:
                result += f"\nChunk {chunk_idx + 1}:\n{chunk.content}\n---\n"

        if not any(score > 0 for score, _, _ in relevant_chunks):
            result += f"\nNo chunks found matching '{relevance_query}'"

        return result

    def _batch_analyze_files(self, repo, parameters: Dict[str, Any]) -> str:
        """Analyze multiple files at once."""
        file_paths = parameters["file_paths"]
        include_symbols = parameters.get("include_symbols", True)
        max_content_length = parameters.get("max_content_length", 3000)

        result = f"Batch analysis of {len(file_paths)} files:\n\n"

        for file_path in file_paths:
            try:
                result += f"## {file_path}\n"

                # Get file content (truncated)
                content = repo.get_file_content(file_path)
                if len(content) > max_content_length:
                    content = content[:max_content_length] + f"\n... (truncated, {len(content)} total chars)"

                result += f"Content:\n```\n{content}\n```\n"

                # Get symbols if requested
                if include_symbols:
                    try:
                        symbols = repo.extract_symbols(file_path)
                        if symbols:
                            result += f"Symbols ({len(symbols)} found):\n"
                            for symbol in symbols[:5]:  # Limit to first 5
                                result += f"- {symbol.get('type', 'unknown')}: {symbol.get('name', 'unnamed')}\n"
                            if len(symbols) > 5:
                                result += f"... and {len(symbols) - 5} more symbols\n"
                        else:
                            result += "Symbols: None found\n"
                    except Exception as e:
                        result += f"Symbols: Error extracting - {e!s}\n"

                result += "\n---\n\n"

            except Exception as e:
                result += f"Error analyzing {file_path}: {e!s}\n\n"

        return result

    def _deep_code_analysis(self, repo, parameters: Dict[str, Any]) -> str:
        """Perform deep code analysis."""
        file_path = parameters["file_path"]
        analysis_focus = parameters.get("analysis_focus", ["security", "performance", "maintainability", "correctness"])

        result = f"Deep code analysis for {file_path}:\n\n"

        try:
            content = repo.get_file_content(file_path)
            symbols = repo.extract_symbols(file_path)
            lines = content.split("\n")

            for focus in analysis_focus:
                result += f"## {focus.title()} Analysis\n"

                if focus == "security":
                    issues = []
                    for i, line in enumerate(lines, 1):
                        line_lower = line.lower()
                        if any(pattern in line_lower for pattern in ["eval(", "exec(", "subprocess.", "os.system"]):
                            issues.append(f"Line {i}: Potential code execution risk")
                        if (
                            any(pattern in line_lower for pattern in ["password", "secret", "token", "api_key"])
                            and "=" in line
                        ):
                            issues.append(f"Line {i}: Potential hardcoded credential")

                    if issues:
                        result += "Security concerns found:\n"
                        for issue in issues[:3]:
                            result += f"  - {issue}\n"
                    else:
                        result += "No obvious security issues detected\n"

                elif focus == "performance":
                    issues = []
                    for i, line in enumerate(lines, 1):
                        line_lower = line.lower()
                        if (
                            "for" in line_lower
                            and "in" in line_lower
                            and any(pattern in line_lower for pattern in [".find(", ".index("])
                        ):
                            issues.append(f"Line {i}: Potential O(n²) operation")
                        if any(pattern in line_lower for pattern in ["time.sleep(", "sleep("]):
                            issues.append(f"Line {i}: Blocking sleep operation")

                    if issues:
                        result += "Performance concerns found:\n"
                        for issue in issues[:3]:
                            result += f"  - {issue}\n"
                    else:
                        result += "No obvious performance issues detected\n"

                elif focus == "maintainability":
                    issues = []
                    for symbol in symbols:
                        if symbol.get("type") == "function":
                            func_content = symbol.get("code", "")
                            if func_content:
                                complexity = (
                                    func_content.count("if ")
                                    + func_content.count("for ")
                                    + func_content.count("while ")
                                )
                                if complexity > 10:
                                    issues.append(
                                        f"Function '{symbol.get('name')}': High complexity ({complexity} branches)"
                                    )

                    if issues:
                        result += "Maintainability concerns found:\n"
                        for issue in issues[:3]:
                            result += f"  - {issue}\n"
                    else:
                        result += "Good maintainability characteristics\n"

                elif focus == "correctness":
                    issues = []
                    for i, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        if "except:" in line_stripped and i < len(lines) and "pass" in lines[i].strip():
                            issues.append(f"Line {i}: Silent exception handling")
                        if "==" in line_stripped and "None" in line_stripped:
                            issues.append(f"Line {i}: Use 'is None' instead of '== None'")

                    if issues:
                        result += "Correctness concerns found:\n"
                        for issue in issues[:3]:
                            result += f"  - {issue}\n"
                    else:
                        result += "No obvious correctness issues detected\n"

                result += "\n"

            result += f"Summary: Analyzed {len(content.split())} words across {len(analysis_focus)} dimensions.\n"

        except Exception as e:
            result += f"Error during analysis: {e!s}\n"

        return result

    def _analyze_cross_file_impact(self, repo, parameters: Dict[str, Any]) -> str:
        """Analyze cross-file impact of changes."""
        changed_files = parameters["changed_files"]

        result = f"Cross-file impact analysis for {len(changed_files)} changed files:\n\n"

        try:
            high_risk_files = []
            medium_risk_files = []

            for file_path in changed_files:
                result += f"## {file_path}\n"

                try:
                    symbols = repo.extract_symbols(file_path)
                    external_usages = 0

                    # Check symbol usage across codebase
                    for symbol in symbols[:5]:  # Check first 5 symbols
                        symbol_name = symbol.get("name", "")
                        if symbol_name:
                            try:
                                usages = repo.find_symbol_usages(symbol_name)
                                external = [u for u in usages if u.get("file") != file_path]
                                external_usages += len(external)
                                if external:
                                    result += f"- {symbol_name}: used in {len(external)} other places\n"
                            except Exception:
                                continue

                    # Determine risk level
                    if external_usages > 20:
                        risk = "high"
                        high_risk_files.append(file_path)
                    elif external_usages > 5:
                        risk = "medium"
                        medium_risk_files.append(file_path)
                    else:
                        risk = "low"

                    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                    result += f"Risk Assessment: {risk_emoji[risk]} {risk.upper()}\n"

                except Exception as e:
                    result += f"Error analyzing {file_path}: {e!s}\n"

                result += "\n"

            # Summary
            result += "## Summary\n"
            result += f"- High risk files: {len(high_risk_files)}\n"
            result += f"- Medium risk files: {len(medium_risk_files)}\n"

            if high_risk_files:
                result += "\nHigh Risk Files:\n"
                for file_path in high_risk_files:
                    result += f"- {file_path}\n"

        except Exception as e:
            result += f"Error during analysis: {e!s}\n"

        return result

    async def _run_agentic_analysis_anthropic(self, initial_prompt: str) -> str:
        """Run multi-turn agentic analysis using Anthropic Claude."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        if not self._llm_client:
            self._llm_client = anthropic.Anthropic(api_key=self.config.llm.api_key)

        tools = self._get_available_tools()
        messages: List[Dict[str, Any]] = [{"role": "user", "content": initial_prompt}]

        max_turns = self.max_turns  # Use the customizable turn limit
        turn = 0

        while turn < max_turns:
            turn += 1
            print(f"🤖 Agentic turn {turn}...")

            # If we're near the end, encourage finalization more aggressively
            if turn >= max_turns - 3:  # Last 3 turns
                messages.append(
                    {
                        "role": "user",
                        "content": f"URGENT: You are on turn {turn} of {max_turns}. You MUST finalize your review NOW using the finalize_review tool. Do not use any other tools.",
                    }
                )
            elif turn >= self.finalize_threshold:
                messages.append(
                    {
                        "role": "user",
                        "content": f"You are on turn {turn} of {max_turns}. Please finalize your review soon using the finalize_review tool with your comprehensive analysis.",
                    }
                )

            try:

                async def make_api_call():
                    # Anthropic client is synchronous, so we need to run it in a thread
                    import asyncio

                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self._llm_client.messages.create(
                            model=self.config.llm.model,
                            max_tokens=self.config.llm.max_tokens,
                            tools=tools,
                            messages=messages,
                        ),
                    )

                response = await retry_with_backoff(make_api_call)

                # Track cost
                input_tokens, output_tokens = self.cost_tracker.extract_anthropic_usage(response)
                self.cost_tracker.track_llm_usage(
                    self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
                )

                # Collect all tool calls and text content
                assistant_message: Dict[str, Any] = {"role": "assistant", "content": []}
                tool_calls = []
                has_text_content = False

                # Process all content blocks
                for content_block in response.content:
                    if content_block.type == "text":
                        cast(List[Any], assistant_message["content"]).append(
                            {"type": "text", "text": content_block.text}
                        )
                        print(f"💭 Agent thinking: {content_block.text[:200]}...")
                        has_text_content = True

                    elif content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_use_id = content_block.id

                        print(f"🔧 Agent using tool: {tool_name} with {tool_input}")

                        # Add tool use to assistant message
                        cast(List[Any], assistant_message["content"]).append(
                            {"type": "tool_use", "id": tool_use_id, "name": tool_name, "input": tool_input}
                        )

                        # Collect for parallel execution
                        tool_calls.append((tool_name, tool_input, tool_use_id))

                # Add assistant message to conversation
                messages.append(assistant_message)

                # Execute all tool calls in parallel if any exist
                if tool_calls:
                    print(
                        f"🚀 Executing {len(tool_calls)} {'tool' if len(tool_calls) == 1 else 'tools'} in parallel..."
                    )

                    # Execute tools in parallel
                    tool_tasks = [self._execute_tool(tool_name, tool_input) for tool_name, tool_input, _ in tool_calls]
                    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

                    # Create tool result messages
                    tool_result_contents = []
                    finalize_called = False

                    for (tool_name, tool_input, tool_use_id), result in zip(tool_calls, tool_results):
                        result_text: str
                        if isinstance(result, Exception):
                            result_text = f"Error executing {tool_name}: {result!s}"
                        else:
                            result_text = str(result)

                        tool_result_contents.append(
                            {"type": "tool_result", "tool_use_id": tool_use_id, "content": result_text}
                        )

                        # Check if finalize_review was called
                        if tool_name == "finalize_review":
                            finalize_called = True

                    # Add all tool results as a single user message
                    messages.append({"role": "user", "content": tool_result_contents})

                    # If finalize_review was called, return the final review
                    if finalize_called:
                        return self.analysis_state.get("final_review", "Review finalized")

                # If no tool calls and we have text content, this might be the final response
                elif has_text_content:
                    text_content = ""
                    for content_block in response.content:
                        if content_block.type == "text":
                            text_content += content_block.text
                    return text_content

            except Exception as e:
                return f"Error during agentic analysis turn {turn}: {e}"

        return "Analysis completed after maximum turns"

    async def _run_agentic_analysis_openai(self, initial_prompt: str) -> str:
        """Run multi-turn agentic analysis using OpenAI GPT."""
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

        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],  # Convert camelCase to snake_case
                },
            }
            for tool in self._get_available_tools()
        ]
        messages: List[Dict[str, Any]] = [{"role": "user", "content": initial_prompt}]

        max_turns = self.max_turns
        turn = 0

        while turn < max_turns:
            turn += 1
            print(f"🤖 Agentic turn {turn}...")

            # If we're near the end, encourage finalization more aggressively
            if turn >= max_turns - 3:  # Last 3 turns
                messages.append(
                    {
                        "role": "user",
                        "content": f"URGENT: You are on turn {turn} of {max_turns}. You MUST finalize your review NOW using the finalize_review tool. Do not use any other tools.",
                    }
                )
            elif turn >= self.finalize_threshold:
                messages.append(
                    {
                        "role": "user",
                        "content": f"You are on turn {turn} of {max_turns}. Please finalize your review soon using the finalize_review tool with your comprehensive analysis.",
                    }
                )

            try:

                async def make_api_call():
                    # OpenAI client is also synchronous
                    import asyncio

                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self._llm_client.chat.completions.create(
                            model=self.config.llm.model,
                            max_tokens=self.config.llm.max_tokens,
                            tools=tools,
                            messages=messages,
                        ),
                    )

                response = await retry_with_backoff(make_api_call)

                # Track cost
                input_tokens, output_tokens = self.cost_tracker.extract_openai_usage(response)
                self.cost_tracker.track_llm_usage(
                    self.config.llm.provider, self.config.llm.model, input_tokens, output_tokens
                )

                message = response.choices[0].message
                messages.append(message)

                if message.tool_calls:
                    print(
                        f"🚀 Executing {len(message.tool_calls)} {'tool' if len(message.tool_calls) == 1 else 'tools'} in parallel..."
                    )

                    # Execute all tool calls in parallel
                    tool_tasks = []
                    tool_call_info = []

                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)

                        print(f"🔧 Agent using tool: {tool_name} with {tool_input}")

                        tool_tasks.append(self._execute_tool(tool_name, tool_input))
                        tool_call_info.append((tool_call.id, tool_name, tool_input))

                    # Execute tools in parallel
                    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

                    # Create tool result messages
                    finalize_called = False

                    for (tool_call_id, tool_name, tool_input), result in zip(tool_call_info, tool_results):
                        result_text: str
                        if isinstance(result, Exception):
                            result_text = f"Error executing {tool_name}: {result!s}"
                        else:
                            result_text = str(result)

                        messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": result_text})

                        if tool_name == "finalize_review":
                            finalize_called = True

                    # If finalize_review was called, return the final review
                    if finalize_called:
                        return self.analysis_state.get("final_review", "Review finalized")
                else:
                    # No tool calls, return the content
                    return message.content or "Analysis completed"

            except Exception as e:
                return f"Error during agentic analysis turn {turn}: {e}"

        return "Analysis completed after maximum turns"

    async def analyze_pr_agentic(self, repo_path: str, pr_details: Dict[str, Any], files: List[Dict[str, Any]]) -> str:
        """Run agentic analysis of the PR."""
        from kit import Repository

        # Initialize repository and state
        repo = Repository(repo_path)
        self.analysis_state["repo"] = repo

        # Get basic context
        try:
            pass  # Git context not critical for agentic review
        except Exception:
            pass  # Git context not critical for agentic review

        # Prioritize files for focused analysis (smart prioritization for Agentic reviewer)
        priority_files, skipped_count = FilePrioritizer.smart_priority(files, max_files=20)

        # Generate analysis summary for transparency
        # Summary helps with transparency but not used in current implementation

        # Extract owner and repo for GitHub links
        owner = pr_details["head"]["repo"]["owner"]["login"]
        repo_name = pr_details["head"]["repo"]["name"]
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

        pr_status = (
            "WIP"
            if "WIP" in pr_details["title"].upper() or "WORK IN PROGRESS" in pr_details["title"].upper()
            else "Ready for Review"
        )

        # Create initial prompt for agentic analysis
        initial_prompt = f"""You are an expert code reviewer. Analyze this GitHub PR efficiently and provide a focused review.

**PR Information:**
- Title: {pr_details["title"]}
- Author: {pr_details["user"]["login"]}
- Files: {len(files)} changed
- Status: {pr_status}

**Changed Files:**
{chr(10).join([f"- {f['filename']} (+{f['additions']} -{f['deletions']})" for f in priority_files])}

{line_number_context}"""

        # Add custom context from profile if available
        if self.config.profile_context:
            initial_prompt += f"""

**Custom Review Guidelines:**
{self.config.profile_context}"""

        initial_prompt += f"""

**Diff:**
```diff
{pr_diff}
```

**Your task:** Use the available tools to investigate this PR and provide a concise, actionable review. Focus on finding real issues that matter.

**Quality Standards:**
- Be specific with file:line references using the EXACT line numbers from the line number reference above
- Format as clickable links: `[file.py:123](https://github.com/{owner}/{repo_name}/blob/{pr_details["head"]["sha"]}/file.py#L123)`
- Professional tone, no drama
- Focus on actionable feedback

**Available tools:** get_file_content, extract_symbols, find_symbol_usages, search_text, get_file_tree, chunk_file_by_symbols, extract_context_around_line, get_relevant_chunks, batch_analyze_files, deep_code_analysis, analyze_cross_file_impact, finalize_review.

**Output format:** When ready, use finalize_review with a structured review following this format:

## Priority Issues
- [High/Medium/Low priority] findings with [file.py:123](https://github.com/{owner}/{repo_name}/blob/{pr_details["head"]["sha"]}/file.py#L123) links

## Summary
- What this PR does
- Key concerns (if any)

## Recommendations
- Security, performance, or logic issues with specific fixes; missing error handling or edge cases; cross-codebase impact concerns

Keep it focused and valuable. Begin your analysis.
"""

        # Run the agentic analysis
        if self.config.llm.provider == LLMProvider.ANTHROPIC:
            analysis = await self._run_agentic_analysis_anthropic(initial_prompt)
        else:
            analysis = await self._run_agentic_analysis_openai(initial_prompt)

        # Apply priority filtering if requested
        priority_filter = self.config.priority_filter
        filtered_analysis = filter_review_by_priority(analysis, priority_filter, self.config.max_review_size_mb)

        return filtered_analysis

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, comment: str) -> Dict[str, Any]:
        """Post a comment on the PR."""
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"

        data = {"body": comment}
        response = self.github_session.post(url, json=data)
        response.raise_for_status()

        return response.json()

    def review_pr_agentic(self, pr_input: str) -> str:
        """Review a PR using agentic analysis."""
        try:
            # Parse PR input
            owner, repo, pr_number = self.parse_pr_url(pr_input)
            print(
                f"🤖 Reviewing PR #{pr_number} in {owner}/{repo} "
                f"[AGENTIC MODE - {self.max_turns} turns - {self.config.llm.model} | max_tokens={self.config.llm.max_tokens}]"
            )

            # Get PR details
            pr_details = self.get_pr_details(owner, repo, pr_number)
            print(f"PR Title: {pr_details['title']}")
            print(f"PR Author: {pr_details['user']['login']}")

            # Get changed files
            files = self.get_pr_files(owner, repo, pr_number)
            print(f"Changed files: {len(files)}")

            # Clone repository for analysis
            if self.config.repo_path:
                # Show warning when using existing repository
                print("⚠️ WARNING: Using existing repository - results may not reflect the main branch")
                print(f"Using existing repository at: {self.config.repo_path}")
            else:
                print("Cloning repository for agentic analysis...")

            repo_path = self.get_repo_for_analysis(owner, repo, pr_details)

            if not self.config.repo_path:
                print(f"Repository cloned to: {repo_path}")

            # Run agentic analysis
            analysis = asyncio.run(self.analyze_pr_agentic(repo_path, pr_details, files))

            # Check if analysis actually completed successfully
            if analysis in ["Analysis completed after maximum turns", "Review finalized"] or len(analysis.strip()) < 50:
                print("❌ Agentic analysis did not complete successfully")
                print(f"Analysis result: {analysis}")
                print("💡 Try reducing --agentic-turns or use standard mode instead")
                return "Agentic analysis failed to complete. Try reducing turn count or use standard mode."

            # Generate final comment
            review_comment = self._generate_agentic_comment(pr_details, files, analysis)

            # Post comment if configured to do so AND analysis completed successfully
            if self.config.post_as_comment:
                comment_result = self.post_pr_comment(owner, repo, pr_number, review_comment)
                print(f"Posted comment: {comment_result['html_url']}")
            else:
                print("Comment posting disabled in configuration")

            # Display cost summary
            print(self.cost_tracker.get_cost_summary())

            return review_comment

        except Exception as e:
            raise RuntimeError(f"Agentic review failed: {e}")

    def _generate_agentic_comment(self, pr_details: Dict[str, Any], files: list[Dict[str, Any]], analysis: str) -> str:
        """Generate an agentic review comment."""
        comment = f"""## 🤖 Kit Agentic Code Review

{analysis}

---
*Generated by [cased kit](https://github.com/cased/kit) v{self._get_kit_version()} with agentic analysis using {self.config.llm.provider.value}*
"""
        return comment

    def _get_kit_version(self) -> str:
        """Get kit version for comment attribution."""
        try:
            import kit

            return getattr(kit, "__version__", "dev")
        except Exception:
            return "dev"


async def retry_with_backoff(func, max_retries=3, base_delay=1.0, max_delay=60.0):
    """Retry function with exponential backoff for API rate limiting."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            error_str = str(e)
            # Check for rate limiting or overload errors
            if any(keyword in error_str.lower() for keyword in ["overloaded", "rate limit", "529", "503", "502"]):
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    print(f"⏳ API overloaded (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
            # Re-raise if not a retryable error or max retries reached
            raise
