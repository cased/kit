"""
A modular toolkit for LLM-powered codebase understanding.
"""

__author__ = "cased"
__version__ = "0.1.0"

from .repository import Repository
from .repo_mapper import RepoMapper
from .code_searcher import CodeSearcher
from .context_extractor import ContextExtractor
# search helpers
from .vector_searcher import VectorSearcher
from .docstring_indexer import DocstringIndexer, SummarySearcher
from .llm_context import ContextAssembler

try:
    from .summaries import Summarizer, OpenAIConfig, LLMError
except ImportError:
    # Allow kit to be imported even if LLM extras aren't installed.
    # Users will get an ImportError later if they try to use Summarizer.
    pass

__all__ = [
    "Repository",
    "RepoMapper",
    "CodeSearcher",
    "ContextExtractor",
    "VectorSearcher",
    "DocstringIndexer",
    "SummarySearcher",
    "ContextAssembler",
    # Conditionally add Summarizer related classes if they were imported
    *(["Summarizer", "OpenAIConfig", "LLMError"] if "Summarizer" in globals() else [])
]
