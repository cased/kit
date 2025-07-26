"""
A modular toolkit for LLM-powered codebase understanding.
"""

__author__ = "cased"
__version__ = "1.8.0"

from .code_searcher import CodeSearcher
from .context_extractor import ContextExtractor
from .docstring_indexer import DocstringIndexer, SummarySearcher
from .llm_context import ContextAssembler
from .repo_mapper import RepoMapper
from .repository import Repository
from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor
from .vector_searcher import VectorSearcher

try:
    from .summaries import AnthropicConfig, GoogleConfig, LLMError, OpenAIConfig, Summarizer
except ImportError:
    # Allow kit to be imported even if LLM extras aren't installed.
    # Users will get an ImportError later if they try to use Summarizer.
    pass

# Helper for LLM tool schemas
from .tool_schemas import get_tool_schemas

# Compatibility patch for Click ≥ 8.2 breaking Typer ≤ 0.15
# -----------------------------------------------------------------------------
# Click 8.2 changed the signature of `Parameter.make_metavar` to require a
# positional `ctx` argument.  Typer (up to v0.15) still calls this method with
# no extra argument, which raises:
#   TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'
# Instead of forcing strict version pinning that might conflict with other
# dependencies or system-wide packages, we monkey-patch the method at runtime so
# that it accepts an optional `ctx` parameter and gracefully degrades when it
# is called without one (as Typer does).
# -----------------------------------------------------------------------------
try:
    import inspect

    import click

    _sig = inspect.signature(click.core.Parameter.make_metavar)
    # Only patch when the new signature (expects ctx) is present and Typer is
    # likely to be in use.
    if len(_sig.parameters) == 2 and "ctx" in _sig.parameters:
        _original_make_metavar = click.core.Parameter.make_metavar  # type: ignore

        def _patched_make_metavar(self, ctx=None):  # type: ignore[override]
            """Backwards-compatible wrapper for Click ≥ 8.2.

            If Typer (or any other library) calls `make_metavar()` with no
            context argument, we provide a dummy one so that the original
            implementation still works.  When a real context *is* supplied we
            simply forward the call.
            """
            # Lazily create a minimal dummy Context only when needed.
            if ctx is None:
                from click.core import Command, Context  # Local import to avoid cycles.

                # Provide a minimal dummy command so that Click's internals expecting
                # attributes such as ``allow_extra_args`` don't explode.
                dummy_cmd = Command(name="_dummy")
                ctx = Context(dummy_cmd)  # type: ignore[arg-type]
            return _original_make_metavar(self, ctx)

        # Apply the monkey-patch.
        click.core.Parameter.make_metavar = _patched_make_metavar  # type: ignore[assignment]

        # Typer defines its own subclass (TyperArgument) that overrides
        # ``make_metavar`` with the *old* 1-arg signature.  When Click ≥8.2
        # calls it with two arguments we get:
        #   TypeError: TyperArgument.make_metavar() takes 1 positional ...
        # Patch that method too if it exists.
        try:
            import typer.core as _typer_core  # Lazy import to avoid hard dep.

            if hasattr(_typer_core, "TyperArgument"):
                _typer_arg_cls = _typer_core.TyperArgument  # type: ignore[attr-defined]

                if "ctx" not in inspect.signature(_typer_arg_cls.make_metavar).parameters:

                    def _typer_make_metavar(self, ctx=None):  # type: ignore[override]
                        # Simply ignore the context; fall back to original 1-arg logic.
                        return _original_make_metavar(self, ctx or click.Context(click.Command("_dummy")))

                    _typer_arg_cls.make_metavar = _typer_make_metavar  # type: ignore[assignment]
        except Exception:
            pass
except Exception:  # pragma: no cover – best-effort patch, never fail hard
    # If anything goes wrong we silently ignore it; worst-case Typer will raise
    # the original error which is easier to diagnose than a failed patch.
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
    "get_tool_schemas",
    # Conditionally add Summarizer related classes if they were imported
    *(
        ["Summarizer", "OpenAIConfig", "AnthropicConfig", "GoogleConfig", "LLMError"]
        if "Summarizer" in globals()
        else []
    ),
]
