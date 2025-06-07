"""Comprehensive unit tests for priority filtering functionality.

This module tests all aspects of priority filtering including:
- Priority validation and normalization
- Review text filtering with various formats
- Error handling and edge cases
- Performance with pre-compiled regex patterns
- Integration with CLI and configuration
"""

import re

import pytest

# Import the modules we're testing
from kit.pr_review.priority_filter import (
    MAJOR_SECTION_PATTERN,
    MAX_LINES,
    MIN_MEANINGFUL_LENGTH,
    PRIORITY_HEADER_PATTERNS,
    PRIORITY_SECTION_PATTERNS,
    _extract_priority_level,
    _filter_priority_content,
    _is_major_section_header,
    _is_meaningful_content,
    _is_priority_section_header,
    count_filtered_issues,
    filter_review_by_priority,
)
from kit.pr_review.priority_utils import Priority


class TestPriorityEnum:
    """Test the Priority enum and validation functionality."""

    def test_priority_enum_values(self):
        """Test that priority enum has correct values."""
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"

    def test_validate_priorities_valid_input(self):
        """Test priority validation with valid inputs."""
        # Standard case
        result = Priority.validate_priorities(["high", "medium"])
        assert result == ["high", "medium"]

        # Case insensitive
        result = Priority.validate_priorities(["HIGH", "Medium", "low"])
        assert result == ["high", "medium", "low"]

        # With whitespace
        result = Priority.validate_priorities([" high ", "  medium  "])
        assert result == ["high", "medium"]

        # Single priority
        result = Priority.validate_priorities(["high"])
        assert result == ["high"]

        # All priorities
        result = Priority.validate_priorities(["high", "medium", "low"])
        assert result == ["high", "medium", "low"]

    def test_validate_priorities_empty_input(self):
        """Test priority validation with empty input."""
        result = Priority.validate_priorities([])
        assert result == []

        result = Priority.validate_priorities(None)
        assert result == []

    def test_validate_priorities_invalid_input(self):
        """Test priority validation with invalid inputs."""
        with pytest.raises(ValueError) as exc_info:
            Priority.validate_priorities(["invalid"])
        assert "Invalid priority levels: ['invalid']" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Priority.validate_priorities(["high", "critical", "medium"])
        assert "Invalid priority levels: ['critical']" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Priority.validate_priorities(["urgent", "important"])
        assert "Invalid priority levels: ['urgent', 'important']" in str(exc_info.value)

    def test_validate_priorities_mixed_valid_invalid(self):
        """Test priority validation with mix of valid and invalid priorities."""
        with pytest.raises(ValueError) as exc_info:
            Priority.validate_priorities(["high", "invalid", "medium"])
        assert "Invalid priority levels: ['invalid']" in str(exc_info.value)


class TestFilterReviewByPriority:
    """Test the main filter_review_by_priority function."""

    @pytest.fixture
    def sample_review_text(self):
        """Sample review text with all priority levels."""
        return """## 🛠️ Kit AI Code Review

## Priority Issues

### High Priority
- Critical security vulnerability in auth.py:45
- Breaking change detected in api.py:123

### Medium Priority
- Performance issue with database queries
- Missing error handling for edge cases

### Low Priority
- Code style inconsistency in utils.py:67
- Missing docstring in helper.py:12

## Summary
This PR introduces new authentication features.

## Recommendations
- Fix security vulnerabilities immediately
- Add comprehensive error handling
"""

    def test_filter_no_priorities_returns_original(self, sample_review_text):
        """Test that passing no priorities returns original text."""
        result = filter_review_by_priority(sample_review_text, None)
        assert result == sample_review_text

        result = filter_review_by_priority(sample_review_text, [])
        assert result == sample_review_text

    def test_filter_high_priority_only(self, sample_review_text):
        """Test filtering for high priority issues only."""
        result = filter_review_by_priority(sample_review_text, ["high"])

        # Should contain high priority content
        assert "Critical security vulnerability" in result
        assert "Breaking change detected" in result

        # Should not contain medium/low priority content
        assert "Performance issue with database" not in result
        assert "Code style inconsistency" not in result

        # Should contain other sections
        assert "Summary" in result
        assert "Recommendations" in result

        # Should contain filter note
        assert "*Note: Showing only high priority issues*" in result

    def test_filter_multiple_priorities(self, sample_review_text):
        """Test filtering for multiple priority levels."""
        result = filter_review_by_priority(sample_review_text, ["high", "medium"])

        # Should contain high and medium priority content
        assert "Critical security vulnerability" in result
        assert "Performance issue with database" in result

        # Should not contain low priority content
        assert "Code style inconsistency" not in result

        # Should contain filter note
        assert "*Note: Showing only high, medium priority issues*" in result

    def test_filter_all_priorities_no_note(self, sample_review_text):
        """Test that filtering all priorities doesn't add a filter note."""
        result = filter_review_by_priority(sample_review_text, ["high", "medium", "low"])

        # Should not contain filter note
        assert "*Note: Showing only" not in result

        # Should contain all content
        assert "Critical security vulnerability" in result
        assert "Performance issue with database" in result
        assert "Code style inconsistency" in result

    def test_input_validation_none_input(self):
        """Test input validation for None input."""
        result = filter_review_by_priority(None, ["high"])
        assert result == ""

    def test_input_validation_non_string_input(self):
        """Test input validation for non-string input."""
        # Integer input should raise TypeError (no longer converts)
        with pytest.raises(TypeError) as exc_info:
            filter_review_by_priority(123, ["high"])
        assert "must be a string" in str(exc_info.value)

        # List input should raise TypeError (no longer converts)
        with pytest.raises(TypeError) as exc_info:
            filter_review_by_priority(["test"], ["high"])
        assert "must be a string" in str(exc_info.value)

        # Object input should raise TypeError (no longer converts)
        class TestObject:
            def __str__(self):
                return "test object"

        with pytest.raises(TypeError) as exc_info:
            filter_review_by_priority(TestObject(), ["high"])
        assert "must be a string" in str(exc_info.value)

    def test_empty_string_input(self):
        """Test handling of empty string input."""
        result = filter_review_by_priority("", ["high"])
        assert result == ""

        result = filter_review_by_priority("   ", ["high"])
        assert result == "   "  # Whitespace-only should be preserved

    def test_invalid_priority_raises_error(self, sample_review_text):
        """Test that invalid priorities raise ValueError."""
        with pytest.raises(ValueError):
            filter_review_by_priority(sample_review_text, ["invalid"])

    def test_performance_safeguards_large_text(self):
        """Test performance safeguards reject excessively large texts."""
        # Test with 1MB limit
        max_size_mb = 1.0
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        # Create text larger than the limit
        large_text = "a" * (max_size_bytes + 1)

        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority(large_text, ["high"], max_review_size_mb=max_size_mb)
        assert "Review text too large" in str(exc_info.value)
        assert "1.0MB" in str(exc_info.value)

    def test_performance_safeguards_too_many_lines(self):
        """Test performance safeguards reject texts with too many lines."""
        # Create text with more lines than the limit
        # Need actual content on each line for proper counting
        many_lines_text = "\n".join(["line content"] * (MAX_LINES + 1))

        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority(many_lines_text, ["high"])
        assert "too many lines" in str(exc_info.value)
        assert "Maximum allowed:" in str(exc_info.value)

    def test_max_review_size_mb_validation(self):
        """Test validation of max_review_size_mb parameter."""
        # Test negative value
        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority("test", ["high"], max_review_size_mb=-1)
        assert "must be a positive number" in str(exc_info.value)

        # Test zero value
        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority("test", ["high"], max_review_size_mb=0)
        assert "must be a positive number" in str(exc_info.value)

        # Test too large value
        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority("test", ["high"], max_review_size_mb=1001)
        assert "too large" in str(exc_info.value)
        assert "maximum allowed: 1000MB" in str(exc_info.value)

        # Test non-numeric value
        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority("test", ["high"], max_review_size_mb="invalid")
        assert "must be a positive number" in str(exc_info.value)

    def test_unicode_byte_counting(self):
        """Test that size validation correctly counts UTF-8 bytes, not characters."""
        # Create text with Unicode characters that have different byte/character counts
        unicode_text = "Hello 🚀🌟⭐ World"  # 15 characters but 23 bytes in UTF-8

        # Test with a very small limit in bytes
        max_size_mb = 20 / (1024 * 1024)  # 20 bytes limit (less than 23 bytes)

        with pytest.raises(ValueError) as exc_info:
            filter_review_by_priority(unicode_text, ["high"], max_review_size_mb=max_size_mb)

        # Should mention bytes, not characters
        error_msg = str(exc_info.value)
        assert "bytes" in error_msg
        assert "23" in error_msg  # Actual byte count

        # Should work with larger limit
        larger_limit = 25 / (1024 * 1024)  # 25 bytes (more than 23 bytes)
        result = filter_review_by_priority(unicode_text, None, max_review_size_mb=larger_limit)
        assert result == unicode_text


class TestPriorityContentFiltering:
    """Test the internal _filter_priority_content function."""

    def test_no_priority_section(self):
        """Test filtering text with no priority section."""
        text = """## Summary
This is a simple PR.

## Recommendations
- No issues found
"""
        result = _filter_priority_content(text, ["high"])
        assert result == text

    def test_empty_priority_section(self):
        """Test filtering text with empty priority section."""
        text = """## Priority Issues

## Summary
No issues found.
"""
        result = _filter_priority_content(text, ["high"])
        # Should add "no issues found" message in the empty priority section
        assert "*No high priority issues found.*" in result

    def test_malformed_priority_headers(self):
        """Test handling of malformed priority headers."""
        text = """## Priority Issues

### High Priority
- Issue with proper header

**High Priority**
- Issue with bold formatting

#### High Priority
- Issue with H4 header

### Medium Priority:
- Issue with proper medium header

### medium priority extra text
- Issue with extra text (should not match)

## Summary
End of issues.
"""
        result = _filter_priority_content(text, ["high"])

        # Should handle various valid header formats
        assert "Issue with proper header" in result  # ### High Priority
        assert "Issue with bold" in result  # **High Priority**
        assert "Issue with H4" in result  # #### High Priority

        # Should not match malformed headers
        assert "Issue with extra text" not in result  # Invalid format
        assert "Issue with proper medium" not in result  # Different priority

    def test_nested_priority_sections(self):
        """Test handling of nested content within priority sections."""
        text = """## Priority Issues

### High Priority
- Main issue
  - Sub-issue detail
  - Another sub-detail
- Second main issue

### Medium Priority
- Medium issue

## Summary
Done.
"""
        result = _filter_priority_content(text, ["high"])

        assert "Main issue" in result
        assert "Sub-issue detail" in result
        assert "Another sub-detail" in result
        assert "Second main issue" in result
        assert "Medium issue" not in result


class TestRegexPatterns:
    """Test the pre-compiled regex patterns for performance and correctness."""

    def test_priority_section_patterns(self):
        """Test priority section header recognition."""
        # Test cases that should match
        positive_cases = [
            "## Priority Issues",
            "### Priority Issues",
            "#### Priority Issue",
            "# Issues by Priority",
            "## PRIORITY ISSUES",
            "### priority issues",
        ]

        for case in positive_cases:
            assert _is_priority_section_header(case), f"Should match: {case}"

        # Test cases that should not match
        negative_cases = [
            "## Summary",
            "### High Priority",  # This is a subsection, not main section
            "Priority issues in the code",  # Not a header
            "## Other Issues",
        ]

        for case in negative_cases:
            assert not _is_priority_section_header(case), f"Should not match: {case}"

    def test_major_section_patterns(self):
        """Test major section header recognition."""
        positive_cases = [
            "## Summary",
            "### Recommendations",
            "# Analysis",
            "## Testing Notes",
        ]

        for case in positive_cases:
            assert _is_major_section_header(case), f"Should match: {case}"

        negative_cases = [
            "### High Priority",  # Priority subsection
            "### Medium Priority",
            "regular text",
            "# lowercase header",  # Doesn't start with uppercase
        ]

        for case in negative_cases:
            assert not _is_major_section_header(case), f"Should not match: {case}"

    def test_priority_header_patterns(self):
        """Test priority level extraction from headers."""
        test_cases = [
            ("### High Priority", "High"),
            ("#### Medium Priority", "Medium"),
            ("### Low Priority", "Low"),
            ("### HIGH PRIORITY", "HIGH"),
            ("**High Priority**", "High"),
            ("**Medium**", "Medium"),
            ("High Priority:", "High"),
            ("High Priority-", "High"),  # With dash but no extra content
        ]

        for header, expected in test_cases:
            result = _extract_priority_level(header)
            assert result == expected, f"Expected {expected} from {header}, got {result}"

        # Test cases that should not match (due to extra content)
        negative_cases = [
            "## Summary",
            "### Other Section",
            "regular text",
            "### Critical Priority",  # Invalid priority level
            "Medium priority - details",  # Extra content after priority
            "High Priority extra text",  # Extra content
        ]

        for case in negative_cases:
            result = _extract_priority_level(case)
            assert result is None, f"Should not extract priority from: {case}, but got {result}"

    def test_regex_patterns_are_compiled(self):
        """Test that regex patterns are pre-compiled for performance."""
        # Verify patterns are compiled regex objects
        assert isinstance(PRIORITY_SECTION_PATTERNS[0], re.Pattern)
        assert isinstance(MAJOR_SECTION_PATTERN, re.Pattern)
        assert isinstance(PRIORITY_HEADER_PATTERNS[0], re.Pattern)


class TestMeaningfulContent:
    """Test meaningful content detection."""

    def test_meaningful_content_detection(self):
        """Test detection of meaningful content lines."""
        meaningful_cases = [
            "- This is a list item",
            "* This is a bullet point",
            "1. This is a numbered item",
            "This is a long sentence with enough characters to be meaningful",
            "  - Indented list item",
        ]

        for case in meaningful_cases:
            assert _is_meaningful_content(case), f"Should be meaningful: {case}"

        non_meaningful_cases = [
            "",
            "   ",  # Only whitespace
            "# Header",  # Headers are not content
            "## Another Header",
            "Short",  # Too short
            "Brief",  # Too short
        ]

        for case in non_meaningful_cases:
            assert not _is_meaningful_content(case), f"Should not be meaningful: {case}"

    def test_min_meaningful_length_constant(self):
        """Test that MIN_MEANINGFUL_LENGTH constant is used correctly."""
        # Content exactly at the threshold
        exactly_min = "a" * MIN_MEANINGFUL_LENGTH
        assert not _is_meaningful_content(exactly_min)  # Exactly at limit, no list marker

        # Content over the threshold
        over_min = "a" * (MIN_MEANINGFUL_LENGTH + 1)
        assert _is_meaningful_content(over_min)


class TestCountFilteredIssues:
    """Test the count_filtered_issues function."""

    def test_count_all_priorities(self):
        """Test counting when no filter is applied."""
        review_text = """## Priority Issues

### High Priority
- Issue 1
- Issue 2

### Medium Priority
- Issue 3

### Low Priority
- Issue 4
- Issue 5
"""
        result = count_filtered_issues(review_text, None)
        assert result == {"shown": "all", "filtered": 0, "total": "all"}

    def test_count_filtered_priorities(self):
        """Test counting when priority filter is applied."""
        review_text = """## Priority Issues

### High Priority
- High issue 1
- High issue 2

### Medium Priority
- Medium issue 1

### Low Priority
- Low issue 1
- Low issue 2
"""
        result = count_filtered_issues(review_text, ["high"])
        assert result["shown"] == 2
        assert result["filtered"] == 3
        assert result["total"] == 5

        result = count_filtered_issues(review_text, ["high", "medium"])
        assert result["shown"] == 3
        assert result["filtered"] == 2
        assert result["total"] == 5


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_extremely_large_review_text(self):
        """Test performance with large review text."""
        # Create a large review text with many priority sections
        large_text = "## Priority Issues\n\n"
        for i in range(100):
            large_text += f"### High Priority\n- Issue {i}\n\n"

        # Should handle large text efficiently
        result = filter_review_by_priority(large_text, ["high"])
        assert "Issue 0" in result
        assert "Issue 99" in result

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        unicode_text = """## Priority Issues

### High Priority
- Issue with émojis 🚀 and unicode ñ
- Issue with special chars: @#$%^&*()

### Medium Priority
- Another issue with unicode: 中文测试

## Summary
Testing unicode handling.
"""
        result = filter_review_by_priority(unicode_text, ["high"])
        assert "émojis 🚀" in result
        assert "special chars" in result
        assert "中文测试" not in result

    def test_mixed_line_endings(self):
        """Test handling of mixed line endings."""
        mixed_endings = "## Priority Issues\r\n\r\n### High Priority\r\n- Issue 1\n- Issue 2\r\n\n### Medium Priority\n- Issue 3\r\n"

        result = filter_review_by_priority(mixed_endings, ["high"])
        assert "Issue 1" in result
        assert "Issue 2" in result
        assert "Issue 3" not in result

    def test_deeply_nested_content(self):
        """Test handling of deeply nested content structures."""
        nested_text = """## Priority Issues

### High Priority
- Main issue
  - Level 2 detail
    - Level 3 detail
      - Level 4 detail
  - Another level 2
- Second main issue

### Medium Priority
- Medium issue
"""
        result = filter_review_by_priority(nested_text, ["high"])
        assert "Main issue" in result
        assert "Level 2 detail" in result
        assert "Level 3 detail" in result
        assert "Level 4 detail" in result
        assert "Another level 2" in result
        assert "Medium issue" not in result


class TestIntegrationScenarios:
    """Test integration scenarios that mirror real usage."""

    def test_real_world_review_format(self):
        """Test with a realistic review format."""
        real_review = """## 🛠️ Kit AI Code Review

*Note: Comprehensive analysis with repository intelligence*

## Priority Issues

### High Priority
- [auth.py:45](https://github.com/example/repo/blob/abc123def/auth.py#L45) Critical SQL injection vulnerability in user authentication
- [api.py:123](https://github.com/example/repo/blob/abc123def/api.py#L123) Breaking change: removed public method `get_user_data()`

### Medium Priority
- [utils.py:67](https://github.com/example/repo/blob/abc123def/utils.py#L67) Performance issue: N+1 query in user lookup
- [config.py:34](https://github.com/example/repo/blob/abc123def/config.py#L34) Missing error handling for database connection failures

### Low Priority
- [helper.py:12](https://github.com/example/repo/blob/abc123def/helper.py#L12) Missing docstring for public function
- [styles.css:45](https://github.com/example/repo/blob/abc123def/styles.css#L45) Inconsistent naming convention

## Summary

This PR introduces user authentication functionality but contains critical security vulnerabilities that must be addressed before merging.

## Recommendations

- **Immediate**: Fix SQL injection vulnerability in auth.py
- **Before merge**: Add proper error handling for all database operations
- **Follow-up**: Address documentation and styling issues

---
*Generated by [cased kit](https://github.com/cased/kit) v0.1.0 • Model: claude-sonnet-4*
"""

        # Test high priority filtering
        result = filter_review_by_priority(real_review, ["high"])
        assert "SQL injection vulnerability" in result
        assert "Breaking change" in result
        assert "Performance issue" not in result
        assert "Missing docstring" not in result
        assert "Summary" in result  # Other sections preserved
        assert "Recommendations" in result

        # Test medium priority filtering
        result = filter_review_by_priority(real_review, ["medium"])
        assert "Performance issue" in result
        assert "Missing error handling" in result

        # The Summary/Recommendations sections are preserved and may contain references to other priorities
        # So we check that the actual Medium Priority section content is there
        # and High Priority section content is not there
        lines = result.split("\n")
        in_high_section = False

        for line in lines:
            if "### High Priority" in line:
                in_high_section = True
            elif "### Medium Priority" in line:
                in_high_section = False
            elif line.startswith("## "):
                in_high_section = False
            elif in_high_section and "Critical SQL injection vulnerability" in line:
                # High priority content should not be in High Priority section
                assert False, "High priority content found in filtered medium-only result"

    def test_empty_priority_sections(self):
        """Test handling of empty priority sections."""
        empty_sections = """## Priority Issues

### High Priority

### Medium Priority
- One medium issue

### Low Priority

## Summary
Some sections are empty.
"""
        result = filter_review_by_priority(empty_sections, ["high"])
        # When filtering for high priority and the high priority section is empty,
        # but there are other non-empty sections, it should show the empty high priority section
        # without adding a "no issues found" message since there are priority sections present
        assert "### High Priority" in result
        assert "One medium issue" not in result  # Medium priority should be filtered out

    def test_no_issues_at_all(self):
        """Test review with no priority issues."""
        no_issues = """## 🛠️ Kit AI Code Review

## Summary
This PR looks good! No issues found.

## Recommendations
- Consider adding more tests
- Update documentation
"""
        result = filter_review_by_priority(no_issues, ["high"])
        # Should preserve the original text since there's no Priority Issues section
        assert "This PR looks good!" in result
        assert "Consider adding more tests" in result

    def test_intelligent_content_filtering(self):
        """Test that Summary and Recommendations are intelligently filtered."""
        review_with_mixed_recommendations = """## 🛠️ Kit AI Code Review

## Priority Issues

### High Priority
- Critical security vulnerability in auth.py

### Medium Priority
- Performance issue in queries

### Low Priority
- Missing documentation

## Summary
This PR has critical security issues and performance problems.

## Recommendations
- **Immediate**: Fix critical security vulnerability
- **Before merge**: Address performance issues
- **Follow-up**: Add documentation improvements
"""

        # Filter for high priority only
        result = filter_review_by_priority(review_with_mixed_recommendations, ["high"])

        # Should keep high priority content
        assert "Critical security vulnerability" in result

        # Should filter out medium/low priority content
        assert "Performance issue" not in result
        assert "Missing documentation" not in result

        # Should intelligently filter recommendations
        assert "Fix critical security vulnerability" in result  # Keep high-priority recommendation
        assert "Address performance issues" not in result  # Filter medium-priority recommendation
        assert "Add documentation improvements" not in result  # Filter low-priority recommendation


if __name__ == "__main__":
    pytest.main([__file__])
