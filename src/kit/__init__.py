"""
A modular toolkit for LLM-powered codebase understanding.
"""

__author__ = "cased"
__version__ = "0.2.0"

from .code_searcher import CodeSearcher
from .context_extractor import ContextExtractor
from .docstring_indexer import DocstringIndexer, SummarySearcher
from .llm_context import ContextAssembler
from .repo_mapper import RepoMapper
from .repository import Repository
from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

# search helpers
from .vector_searcher import VectorSearcher

try:
    from .summaries import LLMError, OpenAIConfig, Summarizer
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
    "DependencyAnalyzer",
    "TreeSitterSymbolExtractor",
    # Conditionally add Summarizer related classes if they were imported
    *(["Summarizer", "OpenAIConfig", "LLMError"] if "Summarizer" in globals() else []),
]
