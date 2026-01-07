"""Review Quality Validator - Objective validation of PR review quality."""

import re
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Pattern, Set, Union


@dataclass
class ValidationResult:
    """Result of review validation."""

    score: float  # 0-1 quality score
    issues: List[str]  # List of quality issues found
    metrics: Dict[str, Union[int, float]]  # Detailed metrics


class ReviewValidator:
    """Validates PR review quality using objective metrics."""

    # Pre-compiled regex patterns for performance (5-10x faster than compiling per-call)
    _LINE_PATTERNS: ClassVar[List[Pattern[str]]] = [
        re.compile(r"\w+\.\w+:\d+", re.IGNORECASE),  # file.py:123
        re.compile(r"line\s+\d+", re.IGNORECASE),  # line 123
        re.compile(r"L\d+", re.IGNORECASE),  # L123
    ]
    _SPECIFIC_PATTERNS: ClassVar[List[Pattern[str]]] = [
        re.compile(r"should\s+use\s+\w+", re.IGNORECASE),
        re.compile(r"missing\s+\w+", re.IGNORECASE),
        re.compile(r"consider\s+\w+", re.IGNORECASE),
        re.compile(r"add\s+\w+", re.IGNORECASE),
        re.compile(r"remove\s+\w+", re.IGNORECASE),
        re.compile(r"fix\s+\w+", re.IGNORECASE),
        re.compile(r"\w+\s+is\s+(unused|incorrect|missing)", re.IGNORECASE),
    ]
    _VAGUE_PATTERNS: ClassVar[List[Pattern[str]]] = [
        re.compile(r"looks?\s+good", re.IGNORECASE),
        re.compile(r"seems?\s+fine", re.IGNORECASE),
        re.compile(r"overall\s+\w+", re.IGNORECASE),
        re.compile(r"generally\s+\w+", re.IGNORECASE),
        re.compile(r"might\s+want\s+to\s+consider", re.IGNORECASE),
        re.compile(r"it\s+would\s+be\s+nice", re.IGNORECASE),
    ]
    # Combined pattern for extracting code definitions (def/class) in one pass
    _CODE_DEF_PATTERN: ClassVar[Pattern[str]] = re.compile(r"(?:def|class)\s+(\w+)")
    _IDENTIFIER_PATTERN: ClassVar[Pattern[str]] = re.compile(r"\b[a-zA-Z_]\w*\b")

    def __init__(self):
        self.min_score_threshold = 0.7  # Minimum acceptable quality score

    def validate_review(self, review_content: str, pr_diff: str, changed_files: List[str]) -> ValidationResult:
        """Validate review quality using objective metrics."""
        issues = []
        metrics: Dict[str, Union[int, float]] = {}

        # 1. Reference validation - does review reference actual diff content?
        metrics["file_references"] = self._count_file_references(review_content, changed_files)
        if metrics["file_references"] == 0 and len(changed_files) > 0:
            issues.append("Review doesn't reference any changed files")

        # 2. Line number validation - are line references plausible?
        metrics["line_references"] = self._count_line_references(review_content)
        invalid_lines = self._validate_line_references(review_content, pr_diff)
        if invalid_lines:
            issues.append(f"Invalid line references: {invalid_lines}")

        # 3. Specificity check - concrete vs vague feedback
        metrics["specific_issues"] = self._count_specific_issues(review_content)
        metrics["vague_statements"] = self._count_vague_statements(review_content)

        if metrics["specific_issues"] == 0 and len(changed_files) > 0:
            issues.append("Review contains no specific, actionable feedback")

        # 4. GitHub link validation
        metrics["github_links"] = self._count_github_links(review_content)
        broken_links = self._validate_github_links(review_content, changed_files)
        if broken_links:
            issues.append(f"Broken GitHub links: {broken_links}")

        # 5. Content relevance - does review discuss code changes?
        code_relevance = self._assess_code_relevance(review_content, pr_diff)
        metrics["code_relevance"] = code_relevance
        if code_relevance < 0.3:
            issues.append("Review doesn't seem to discuss actual code changes")

        # 6. Completeness - covers major changes?
        major_changes = self._identify_major_changes(pr_diff)
        coverage = self._assess_change_coverage(review_content, major_changes)
        metrics["change_coverage"] = coverage
        if coverage < 0.5 and len(major_changes) > 0:
            issues.append("Review misses major code changes")

        # Calculate overall score
        score = self._calculate_quality_score(metrics, issues)

        return ValidationResult(score=score, issues=issues, metrics=metrics)

    def _count_file_references(self, review: str, changed_files: List[str]) -> int:
        """Count how many changed files are referenced in the review."""
        count = 0
        for file_path in changed_files:
            # Check for various file reference patterns
            filename = file_path.split("/")[-1]
            if filename in review or file_path in review:
                count += 1
        return count

    def _count_line_references(self, review: str) -> int:
        """Count line number references in the review."""
        count = 0
        for pattern in self._LINE_PATTERNS:
            count += len(pattern.findall(review))
        return count

    def _validate_line_references(self, review: str, pr_diff: str) -> List[str]:
        """Check if line references are plausible given the diff."""
        # Extract line numbers from review
        line_refs = re.findall(r":(\d+)", review)

        # Extract line ranges from diff (simplified check)
        diff_lines: Set[int] = set()
        for line in pr_diff.split("\n"):
            if line.startswith("@@"):
                # Parse @@ -old_start,old_count +new_start,new_count @@
                match = re.search(r"\+(\d+),?(\d+)?", line)
                if match:
                    start = int(match.group(1))
                    count = int(match.group(2)) if match.group(2) else 1
                    diff_lines.update(range(start, start + count))

        # Check for obviously invalid references
        invalid = []
        for line_num in line_refs:
            line_int = int(line_num)
            # Very basic sanity checks
            if line_int > 10000:  # Suspiciously high line number
                invalid.append(f"Line {line_int} seems too high")
            elif line_int == 0:
                invalid.append("Line 0 is invalid")

        return invalid

    def _count_specific_issues(self, review: str) -> int:
        """Count specific, actionable issues in the review."""
        count = 0
        for pattern in self._SPECIFIC_PATTERNS:
            count += len(pattern.findall(review))
        return count

    def _count_vague_statements(self, review: str) -> int:
        """Count vague, non-actionable statements."""
        count = 0
        for pattern in self._VAGUE_PATTERNS:
            count += len(pattern.findall(review))
        return count

    def _count_github_links(self, review: str) -> int:
        """Count GitHub file links in the review."""
        github_link_pattern = r"\[([^\]]+)\]\(https://github\.com/[^)]+\)"
        return len(re.findall(github_link_pattern, review))

    def _validate_github_links(self, review: str, changed_files: List[str]) -> List[str]:
        """Check if GitHub links reference actual changed files."""
        # Extract links
        links = re.findall(r"\[([^\]]+)\]\((https://github\.com/[^)]+)\)", review)

        invalid = []
        for link_text, url in links:
            # Extract filename from URL
            if "/blob/" in url:
                file_part = url.split("/blob/")[-1]
                file_path = "/".join(file_part.split("/")[1:]).split("#")[0]

                # Check if this file was actually changed
                if file_path not in changed_files:
                    filename = file_path.split("/")[-1]
                    if not any(filename in cf for cf in changed_files):
                        invalid.append(f"Link to unchanged file: {file_path}")

        return invalid

    def _assess_code_relevance(self, review: str, pr_diff: str) -> float:
        """Assess how much the review discusses actual code changes."""
        # Extract key terms from diff
        diff_terms: Set[str] = set()

        # Get function/class names from diff using pre-compiled patterns
        for line in pr_diff.split("\n"):
            if line.startswith("+") or line.startswith("-"):
                # Extract function/class names in one pass
                for match in self._CODE_DEF_PATTERN.finditer(line):
                    diff_terms.add(match.group(1))

                # Get variable names and keywords
                words = self._IDENTIFIER_PATTERN.findall(line)
                diff_terms.update(w for w in words if len(w) > 2)

        # Count how many diff terms appear in review
        if not diff_terms:
            return 0.5  # Neutral if no terms to check

        mentioned_terms = sum(1 for term in diff_terms if term.lower() in review.lower())
        return min(1.0, mentioned_terms / max(5, len(diff_terms) * 0.3))

    def _identify_major_changes(self, pr_diff: str) -> List[str]:
        """Identify major code changes in the diff."""
        major_changes: Set[str] = set()

        for line in pr_diff.split("\n"):
            if line.startswith("+") or line.startswith("-"):
                # Check for function/class definitions using pre-compiled pattern
                match = self._CODE_DEF_PATTERN.search(line)
                if match:
                    # Determine if it's a function or class based on prefix
                    if "def " in line:
                        major_changes.add("function_definition")
                    elif "class " in line:
                        major_changes.add("class_definition")
                # Import changes
                elif "import " in line:
                    major_changes.add("import_change")
                # Error handling
                elif any(keyword in line.lower() for keyword in ["try:", "except:", "raise ", "error"]):
                    major_changes.add("error_handling")

        return list(major_changes)

    def _assess_change_coverage(self, review: str, major_changes: List[str]) -> float:
        """Assess how well the review covers major changes."""
        if not major_changes:
            return 1.0

        coverage_keywords = {
            "function_definition": ["function", "method", "def"],
            "class_definition": ["class"],
            "import_change": ["import", "dependency", "module"],
            "error_handling": ["error", "exception", "try", "catch", "handling"],
        }

        covered = 0
        for change_type in major_changes:
            keywords = coverage_keywords.get(change_type, [])
            if any(keyword in review.lower() for keyword in keywords):
                covered += 1

        return covered / len(major_changes)

    def _calculate_quality_score(self, metrics: Dict[str, Union[int, float]], issues: List[str]) -> float:
        """Calculate overall quality score."""
        score = 1.0

        # Deduct for each issue
        score -= len(issues) * 0.15

        # Bonus for specific content
        if metrics.get("specific_issues", 0) > 0:
            score += 0.1
        if metrics.get("github_links", 0) > 0:
            score += 0.1
        if metrics.get("code_relevance", 0) > 0.7:
            score += 0.1

        # Penalty for vague content
        if metrics.get("vague_statements", 0) > metrics.get("specific_issues", 0):
            score -= 0.2

        return max(0.0, min(1.0, score))


def validate_review_quality(review_content: str, pr_diff: str, changed_files: List[str]) -> ValidationResult:
    """Convenience function to validate review quality."""
    validator = ReviewValidator()
    return validator.validate_review(review_content, pr_diff, changed_files)
