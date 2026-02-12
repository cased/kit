"""Utilities for classifying and handling non-actionable review errors."""

# Prefixes emitted by _analyze_with_*_enhanced and agentic analysis methods
# when the underlying LLM/provider call fails.
_ERROR_PREFIXES = (
    "error during enhanced llm analysis:",
    "error during enhanced ollama analysis:",
    "error during agentic analysis turn",
)

# Token / context-length limit patterns (provider-agnostic)
_TOKEN_LIMIT_PATTERNS = (
    "maximum context length",
    "context_length_exceeded",
    "context length exceeded",
    "too many tokens",
    "token limit",
    "context window",
    "prompt is too long",
    "request too large",
    "content_too_large",
    "resource_exhausted",
    "max_tokens",
    "maximum number of tokens",
    "input is too long",
    "string_above_max_length",
)

# Upstream HTTP 5xx patterns
_HTTP_5XX_PATTERNS = (
    "500 internal server error",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
    "overloaded_error",
    "overloaded",
    "internal server error",
    "server_error",
    "the server had an error",
)

# Rate-limit / 429 patterns
_RATE_LIMIT_PATTERNS = (
    "rate_limit",
    "rate limit",
    "429",
    "too many requests",
)


def is_non_actionable_error(text: str) -> bool:
    """Return True if *text* contains a non-actionable infrastructure error.

    Non-actionable errors are transient provider/infrastructure failures that
    a PR author cannot fix (token limits, upstream 5xx, rate limits).  These
    should never be posted as GitHub review comments.

    The check is intentionally conservative: it only fires when the text
    contains one of the known error prefixes **and** a recognised
    infrastructure-error pattern, so legitimate reviews that happen to
    mention "500" or "token" are not affected.
    """
    if not text:
        return False

    lower = text.lower()

    # Only consider text that was produced by an LLM analysis error path.
    if not any(prefix in lower for prefix in _ERROR_PREFIXES):
        return False

    all_patterns = _TOKEN_LIMIT_PATTERNS + _HTTP_5XX_PATTERNS + _RATE_LIMIT_PATTERNS
    return any(pattern in lower for pattern in all_patterns)
