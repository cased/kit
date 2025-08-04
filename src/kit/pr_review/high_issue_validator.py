"""High-priority issue validator - Secondary validation pass for critical findings."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .config import LLMConfig, LLMProvider
from .diff_parser import FileDiff


@dataclass
class HighIssueValidation:
    """Result of high-priority issue validation."""

    issue: str  # Original issue text
    is_valid: bool  # Whether the issue passed validation
    confidence: float  # Confidence score (0-1)
    reasoning: str  # Explanation of validation result
    suggested_fix: Optional[str] = None  # Suggested correction if invalid


class HighIssueValidator:
    """Validates high-priority issues using a secondary LLM pass for confirmation."""

    def __init__(self, llm_config: LLMConfig, validation_threshold: float = 0.7):
        """Initialize validator with LLM config and validation threshold.

        Args:
            llm_config: LLM configuration for validation pass
            validation_threshold: Minimum confidence score to consider issue valid (0-1)
        """
        self.llm_config = llm_config
        self.validation_threshold = validation_threshold
        self._llm_client: Optional[Any] = None

    def extract_high_priority_issues(self, review_text: str) -> List[Dict[str, str]]:
        """Extract high-priority issues from review text.

        Returns:
            List of dicts with 'issue', 'file', 'line' keys
        """
        issues = []
        lines = review_text.split("\n")

        in_high_section = False
        current_issue: List[str] = []

        for line in lines:
            # Check for high priority section headers
            if re.match(r"^#{1,4}\s*(High|HIGH)\s*(Priority)?", line, re.IGNORECASE):
                in_high_section = True
                continue

            # Check if we're leaving the high priority section
            if in_high_section and re.match(r"^#{1,4}\s*(Medium|Low|Summary|Recommendations)", line, re.IGNORECASE):
                in_high_section = False
                if current_issue:
                    issues.append(self._parse_issue("\n".join(current_issue)))
                    current_issue = []
                continue

            # Collect high priority issue content
            if in_high_section:
                # Start of new issue (bullet point or dash)
                if re.match(r"^\s*[-*]\s+", line) and current_issue:
                    issues.append(self._parse_issue("\n".join(current_issue)))
                    current_issue = [line]
                elif line.strip():
                    current_issue.append(line)

        # Don't forget the last issue
        if current_issue and in_high_section:
            issues.append(self._parse_issue("\n".join(current_issue)))

        return issues

    def _parse_issue(self, issue_text: str) -> Dict[str, str]:
        """Parse an issue to extract file and line references."""
        # Extract file:line references
        file_match = re.search(r"\[([^\]]+)\]\(https://github\.com/[^#]+#L(\d+)[^\)]*\)", issue_text)
        if file_match:
            file_path = file_match.group(1).split(":")[0]
            line_num = file_match.group(2)
        else:
            # Try simpler patterns
            simple_match = re.search(r"(\w+\.\w+):(\d+)", issue_text)
            if simple_match:
                file_path = simple_match.group(1)
                line_num = simple_match.group(2)
            else:
                file_path = None
                line_num = None

        return {"issue": issue_text, "file": file_path or "", "line": line_num or ""}

    async def validate_issues(
        self, issues: List[Dict[str, str]], pr_diff: str, diff_files: Dict[str, FileDiff], context: Optional[str] = None
    ) -> List[HighIssueValidation]:
        """Validate a list of high-priority issues.

        Args:
            issues: List of issues to validate
            pr_diff: Full PR diff text
            diff_files: Parsed diff files
            context: Additional context about the PR

        Returns:
            List of validation results
        """
        validations = []

        for issue in issues:
            validation = await self._validate_single_issue(issue, pr_diff, diff_files, context)
            validations.append(validation)

        return validations

    async def _validate_single_issue(
        self, issue: Dict[str, str], pr_diff: str, diff_files: Dict[str, FileDiff], context: Optional[str]
    ) -> HighIssueValidation:
        """Validate a single high-priority issue using LLM."""
        # Build validation prompt
        validation_prompt = self._build_validation_prompt(issue, pr_diff, diff_files, context)

        # Get LLM validation
        validation_response = await self._call_llm(validation_prompt)

        # Parse validation response
        return self._parse_validation_response(issue["issue"], validation_response)

    def _build_validation_prompt(
        self, issue: Dict[str, str], pr_diff: str, diff_files: Dict[str, FileDiff], context: Optional[str]
    ) -> str:
        """Build prompt for validating a high-priority issue."""
        prompt = f"""You are a code review validation expert. Your task is to validate whether a high-priority issue identified in a PR review is accurate and truly high-priority.

**Issue to Validate:**
{issue["issue"]}

**Referenced Location:**
File: {issue.get("file", "Not specified")}
Line: {issue.get("line", "Not specified")}
"""

        # Add relevant diff context if we have file/line info
        if issue.get("file") and issue.get("line") and issue["file"] != "" and issue["line"] != "":
            relevant_diff = self._extract_relevant_diff(issue["file"], issue["line"], diff_files, pr_diff)
            if relevant_diff:
                prompt += f"""

**Relevant Code Changes:**
```diff
{relevant_diff}
```"""

        if context:
            prompt += f"""

**Additional Context:**
{context}"""

        prompt += """

**Validation Criteria:**
1. Is the issue accurately describing a real problem in the code?
2. Does the issue reference the correct file and line number?
3. Is this truly a high-priority issue (security, data loss, crash, etc.)?
4. Is the issue based on the actual code changes, not assumptions?

**Response Format:**
VALID: [true/false]
CONFIDENCE: [0.0-1.0]
REASONING: [Brief explanation of validation decision]
SUGGESTED_FIX: [If invalid, suggest how to correct the issue description, or "N/A" if valid]
"""

        return prompt

    def _extract_relevant_diff(
        self, file_path: str, line_num: str, diff_files: Dict[str, FileDiff], pr_diff: str
    ) -> Optional[str]:
        """Extract relevant diff context around the specified line."""
        # Find the file in parsed diffs
        file_diff = None
        for path, diff in diff_files.items():
            if path.endswith(file_path) or file_path in path:
                file_diff = diff
                break

        if not file_diff:
            return None

        # Extract context around the line
        target_line = int(line_num)
        context_lines = []

        for hunk in file_diff.hunks:
            # Check if our target line is in this hunk's range
            if hunk.new_start <= target_line <= hunk.new_start + hunk.new_count:
                # Add hunk header
                context_lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")

                # Add relevant lines with context
                current_new_line = hunk.new_start
                for line in hunk.lines:
                    # Include line if it's near our target
                    if abs(current_new_line - target_line) <= 5:
                        context_lines.append(line)

                    # Track line numbers
                    if not line.startswith("-"):
                        current_new_line += 1

                break

        return "\n".join(context_lines) if context_lines else None

    def _parse_validation_response(self, issue_text: str, response: str) -> HighIssueValidation:
        """Parse LLM validation response into structured result."""
        # Extract validation fields using regex
        valid_match = re.search(r"VALID:\s*(true|false)", response, re.IGNORECASE)
        confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", response)
        reasoning_match = re.search(r"REASONING:\s*(.+?)(?=SUGGESTED_FIX:|$)", response, re.DOTALL)
        fix_match = re.search(r"SUGGESTED_FIX:\s*(.+?)$", response, re.DOTALL)

        is_valid = valid_match.group(1).lower() == "true" if valid_match else False
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
        suggested_fix = fix_match.group(1).strip() if fix_match else None

        if suggested_fix and suggested_fix.upper() == "N/A":
            suggested_fix = None

        return HighIssueValidation(
            issue=issue_text, is_valid=is_valid, confidence=confidence, reasoning=reasoning, suggested_fix=suggested_fix
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for validation based on provider."""
        if self.llm_config.provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(prompt)
        elif self.llm_config.provider == LLMProvider.GOOGLE:
            return await self._call_google(prompt)
        elif self.llm_config.provider == LLMProvider.OLLAMA:
            return await self._call_ollama(prompt)
        else:  # OpenAI
            return await self._call_openai(prompt)

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API for validation."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        if not self._llm_client:
            self._llm_client = anthropic.Anthropic(api_key=self.llm_config.api_key)

        response = self._llm_client.messages.create(
            model=self.llm_config.model,
            max_tokens=500,  # Validation responses are short
            temperature=0.1,  # Low temperature for consistency
            messages=[{"role": "user", "content": prompt}],
        )

        text_content = ""
        for content_block in response.content:
            if hasattr(content_block, "text"):
                text_content += content_block.text

        return text_content

    async def _call_google(self, prompt: str) -> str:
        """Call Google Gemini API for validation."""
        try:
            import google.genai as genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed. Run: pip install google-genai")

        if not self._llm_client:
            self._llm_client = genai.Client(api_key=self.llm_config.api_key)

        response = self._llm_client.models.generate_content(
            model=self.llm_config.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
        )

        return response.text if response.text else ""

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API for validation."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        if not self._llm_client:
            if self.llm_config.api_base_url:
                self._llm_client = openai.OpenAI(api_key=self.llm_config.api_key, base_url=self.llm_config.api_base_url)
            else:
                self._llm_client = openai.OpenAI(api_key=self.llm_config.api_key)

        response = self._llm_client.chat.completions.create(
            model=self.llm_config.model,
            max_tokens=500,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content or ""

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for validation."""
        import asyncio

        import requests

        if not self._llm_client:

            class OllamaClient:
                def __init__(self, base_url: str, model: str):
                    self.base_url = base_url
                    self.model = model
                    self.session = requests.Session()

                def generate(self, prompt: str, **kwargs) -> str:
                    url = f"{self.base_url}/api/generate"
                    data = {"model": self.model, "prompt": prompt, "stream": False, **kwargs}
                    response = self.session.post(url, json=data)
                    response.raise_for_status()
                    return response.json().get("response", "")

            self._llm_client = OllamaClient(
                self.llm_config.api_base_url or "http://localhost:11434", self.llm_config.model
            )

        response = await asyncio.to_thread(
            self._llm_client.generate,
            prompt,
            temperature=0.1,
            num_predict=500,
        )

        return response


def apply_validation_results(
    review_text: str, validations: List[HighIssueValidation], threshold: float = 0.7
) -> Tuple[str, int, int]:
    """Apply validation results to filter out invalid high-priority issues.

    Args:
        review_text: Original review text
        validations: List of validation results
        threshold: Minimum confidence to keep an issue

    Returns:
        Tuple of (filtered_review, removed_count, total_count)
    """
    if not validations:
        return review_text, 0, 0

    # Create a mapping of issues to their validation results
    issue_to_validation = {v.issue: v for v in validations}

    lines = review_text.split("\n")
    filtered_lines = []
    removed_count = 0
    total_count = len(validations)

    in_high_section = False
    current_issue_text: List[str] = []

    for i, line in enumerate(lines):
        # Check for high priority section
        if re.match(r"^#{1,4}\s*(High|HIGH)\s*(Priority)?", line, re.IGNORECASE):
            in_high_section = True
            filtered_lines.append(line)
            continue

        # Check if leaving high section
        if in_high_section and re.match(r"^#{1,4}\s*(Medium|Low|Summary|Recommendations)", line, re.IGNORECASE):
            in_high_section = False
            # Process any pending issue
            if current_issue_text:
                issue_full_text = "\n".join(current_issue_text)
                if not _should_skip_issue(issue_full_text, issue_to_validation, threshold):
                    filtered_lines.extend(current_issue_text)
                else:
                    removed_count += 1
                current_issue_text = []
            filtered_lines.append(line)
            continue

        if in_high_section:
            # Check if this is the start of a new issue
            if re.match(r"^\s*[-*]\s+", line):
                # Process previous issue if any
                if current_issue_text:
                    issue_full_text = "\n".join(current_issue_text)
                    if not _should_skip_issue(issue_full_text, issue_to_validation, threshold):
                        filtered_lines.extend(current_issue_text)
                    else:
                        removed_count += 1
                # Start new issue
                current_issue_text = [line]
            elif line.strip() and current_issue_text:
                # Continue current issue
                current_issue_text.append(line)
            else:
                # Empty line or no current issue
                filtered_lines.append(line)
        else:
            filtered_lines.append(line)

    # Handle last issue if in high section
    if in_high_section and current_issue_text:
        issue_full_text = "\n".join(current_issue_text)
        if not _should_skip_issue(issue_full_text, issue_to_validation, threshold):
            filtered_lines.extend(current_issue_text)
        else:
            removed_count += 1

    # Add validation summary if issues were removed
    if removed_count > 0:
        # Find where to insert the summary (after high priority section)
        insert_idx = -1
        for i, line in enumerate(filtered_lines):
            if re.match(r"^#{1,4}\s*(High|HIGH)\s*(Priority)?", line, re.IGNORECASE):
                # Find the end of high priority section
                for j in range(i + 1, len(filtered_lines)):
                    if re.match(r"^#{1,4}\s*(Medium|Low|Summary|Recommendations)", filtered_lines[j], re.IGNORECASE):
                        insert_idx = j
                        break
                if insert_idx == -1:
                    insert_idx = len(filtered_lines)
                break

        if insert_idx != -1:
            validation_note = f"\n*Note: {removed_count} high-priority issue(s) removed after validation (confidence < {threshold})*\n"
            filtered_lines.insert(insert_idx, validation_note)

    return "\n".join(filtered_lines), removed_count, total_count


def _should_skip_issue(issue_text: str, issue_to_validation: Dict[str, HighIssueValidation], threshold: float) -> bool:
    """Check if an issue should be skipped based on validation."""
    # Try to find a matching validation
    for issue_key, validation in issue_to_validation.items():
        # Check if this issue text contains the validated issue
        if issue_key in issue_text or issue_text in issue_key:
            return not validation.is_valid or validation.confidence < threshold
    return False
