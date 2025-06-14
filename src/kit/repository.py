from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload

from .code_searcher import CodeSearcher
from .context_extractor import ContextExtractor
from .llm_context import ContextAssembler
from .repo_mapper import RepoMapper
from .vector_searcher import VectorSearcher

# Use TYPE_CHECKING for Summarizer to avoid circular imports
if TYPE_CHECKING:
    from .dependency_analyzer.dependency_analyzer import DependencyAnalyzer
    from .summaries import AnthropicConfig, GoogleConfig, OllamaConfig, OpenAIConfig, Summarizer

logger = logging.getLogger(__name__)


class Repository:
    """
    Main interface for codebase operations: file tree, symbol extraction, search, and context.
    Provides a unified API for downstream tools and workflows.
    """

    def __init__(
        self,
        path_or_url: str,
        github_token: Optional[str] = None,
        cache_dir: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> None:
        # Auto-pickup GitHub token from environment if not provided
        if github_token is None:
            github_token = os.getenv("KIT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

        self.ref = ref  # Store the requested ref
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):  # Remote repo
            self.local_path = self._clone_github_repo(path_or_url, github_token, cache_dir, ref)
        else:
            # Use absolute() instead of resolve() to avoid following symlinks (e.g., /var -> /private/var on macOS)
            self.local_path = Path(path_or_url).absolute()
            # For local repos, if ref is specified, try to checkout that ref
            if ref:
                self._checkout_ref(ref)
        self.repo_path: str = str(self.local_path)

        # Track git state for cache invalidation
        self._cached_git_sha: Optional[str] = None
        self._git_state_valid = False

        # Initialize incremental analyzer for enhanced caching
        from .incremental_analyzer import IncrementalAnalyzer

        self._incremental_analyzer: Optional[IncrementalAnalyzer] = None

        self.mapper: RepoMapper = RepoMapper(self.repo_path)
        self.searcher: CodeSearcher = CodeSearcher(self.repo_path)
        self.context: ContextExtractor = ContextExtractor(self.repo_path)
        self.vector_searcher: Optional[VectorSearcher] = None

    def _checkout_ref(self, ref: str) -> None:
        """Checkout a specific ref (SHA, tag, or branch) in a local git repository."""
        git_dir = self.local_path / ".git"
        if not (git_dir.exists() and git_dir.is_dir()):
            raise ValueError(f"Cannot checkout ref '{ref}': not a git repository")

        try:
            # First, try to fetch the ref in case it's not available locally
            subprocess.run(
                ["git", "fetch", "origin", ref],
                cwd=str(self.local_path),
                capture_output=True,
                check=False,  # Don't fail if fetch doesn't work
            )

            # Checkout the ref
            _ = subprocess.run(
                ["git", "checkout", ref], cwd=str(self.local_path), capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to checkout ref '{ref}': {e.stderr}")

    @property
    def current_sha(self) -> Optional[str]:
        """Get the current commit SHA (full)."""
        return self._git_command(["git", "rev-parse", "HEAD"])

    @property
    def current_sha_short(self) -> Optional[str]:
        """Get the current commit SHA (short)."""
        return self._git_command(["git", "rev-parse", "--short", "HEAD"])

    @property
    def current_branch(self) -> Optional[str]:
        """Get the current branch name, or None if in detached HEAD state."""
        branch = self._git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return branch if branch and branch != "HEAD" else None

    @property
    def remote_url(self) -> Optional[str]:
        """Get the remote origin URL."""
        return self._git_command(["git", "config", "--get", "remote.origin.url"])

    @property
    def tags(self) -> List[str]:
        """Get all tags in the repository."""
        result = self._git_command(["git", "tag", "--list"])
        return result.split("\n") if result else []

    @property
    def branches(self) -> List[str]:
        """Get all local branches."""
        result = self._git_command(["git", "branch", "--format=%(refname:short)"])
        return result.split("\n") if result else []

    @property
    def is_dirty(self) -> bool:
        """Check if the working directory has uncommitted changes."""
        result = self._git_command(["git", "status", "--porcelain"])
        return bool(result and result.strip())

    def _git_command(self, cmd: List[str]) -> Optional[str]:
        """Execute a git command and return the output, or None if it fails."""
        git_dir = self.local_path / ".git"
        if not (git_dir.exists() and git_dir.is_dir()):
            return None

        try:
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout.strip() if result.stdout else None
        except subprocess.CalledProcessError:
            return None

    def __str__(self) -> str:
        file_count = len(self.get_file_tree())
        # The self.repo_path is already a string, set in __init__
        path_info = self.repo_path

        # Check if it's a git repo and try to get ref.
        # This assumes local_path is a Path object and points to a git repo.
        ref_info = ""
        # self.local_path is already a Path object from __init__
        git_dir = self.local_path / ".git"
        if git_dir.exists() and git_dir.is_dir():
            try:
                # Get current branch name
                branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                # Use self.repo_path (string) for cwd as subprocess expects string path
                branch_result = subprocess.run(
                    branch_cmd, cwd=self.repo_path, capture_output=True, text=True, check=False
                )
                if branch_result.returncode == 0 and branch_result.stdout.strip() != "HEAD":
                    ref_info = f", branch: {branch_result.stdout.strip()}"
                else:
                    # If not on a branch (detached HEAD), get commit SHA
                    sha_cmd = ["git", "rev-parse", "--short", "HEAD"]
                    sha_result = subprocess.run(
                        sha_cmd, cwd=self.repo_path, capture_output=True, text=True, check=False
                    )
                    if sha_result.returncode == 0:
                        ref_info = f", commit: {sha_result.stdout.strip()}"
            except Exception:
                pass  # Silently ignore errors in getting git info for __str__

        return f"<Repository path='{path_info}'{ref_info}, files: {file_count}>"

    def _clone_github_repo(
        self, url: str, token: Optional[str], cache_dir: Optional[str], ref: Optional[str] = None
    ) -> Path:
        from urllib.parse import urlparse

        repo_name = urlparse(url).path.strip("/").replace("/", "-")
        # Include ref in cache path if specified to avoid conflicts
        if ref:
            repo_name = f"{repo_name}-{ref.replace('/', '-')}"

        cache_root = Path(cache_dir or tempfile.gettempdir()) / "kit-repo-cache"
        cache_root.mkdir(parents=True, exist_ok=True)

        repo_path = cache_root / repo_name
        if repo_path.exists() and (repo_path / ".git").exists():
            # For existing cached repos, checkout the requested ref if different
            if ref:
                try:
                    current_sha = subprocess.run(
                        ["git", "rev-parse", "HEAD"], cwd=str(repo_path), capture_output=True, text=True, check=True
                    ).stdout.strip()

                    # Check if we're already on the requested ref
                    target_sha = subprocess.run(
                        ["git", "rev-parse", ref], cwd=str(repo_path), capture_output=True, text=True, check=False
                    )

                    if target_sha.returncode != 0 or current_sha != target_sha.stdout.strip():
                        # Need to fetch and checkout the ref
                        subprocess.run(["git", "fetch", "origin"], cwd=str(repo_path), check=True)
                        subprocess.run(["git", "checkout", ref], cwd=str(repo_path), check=True)
                except subprocess.CalledProcessError:
                    # If checkout fails, remove cache and re-clone
                    import shutil

                    shutil.rmtree(repo_path)
                else:
                    return repo_path
            else:
                # No specific ref requested, use existing cache
                return repo_path

        # Use GIT_ASKPASS so the token never appears in argv / process list
        env = os.environ.copy()

        # Clone with specific ref if provided
        if ref:
            # Clone without --depth for specific refs, as shallow clones might not have the ref
            clone_cmd = ["git", "clone", "--branch", ref, url, str(repo_path)]
        else:
            # Default shallow clone for main/default branch
            clone_cmd = ["git", "clone", "--depth=1", url, str(repo_path)]

        if token:
            # Create a temporary ask-pass helper that echoes the token once
            askpass_script = tempfile.NamedTemporaryFile("w", delete=False)
            askpass_script.write('#!/bin/sh\necho "%s"\n' % token)
            askpass_script.flush()
            os.chmod(askpass_script.name, 0o700)
            env["GIT_ASKPASS"] = askpass_script.name
            env["GIT_TERMINAL_PROMPT"] = "0"  # disable interactive prompts

        try:
            subprocess.run(clone_cmd, env=env, check=True)
        except subprocess.CalledProcessError as e:
            # If branch clone fails, try cloning without branch and then checkout
            if ref:
                try:
                    # Clone without specific branch
                    fallback_cmd = ["git", "clone", url, str(repo_path)]
                    subprocess.run(fallback_cmd, env=env, check=True)
                    # Then checkout the specific ref
                    subprocess.run(["git", "checkout", ref], cwd=str(repo_path), check=True)
                except subprocess.CalledProcessError:
                    raise ValueError(f"Failed to clone repository at ref '{ref}': {e}")
            else:
                raise
        finally:
            if token:
                try:
                    os.unlink(askpass_script.name)
                except OSError:
                    pass
        return repo_path

    def get_file_tree(self) -> List[Dict[str, Any]]:
        """
        Returns the file tree of the repository.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the file tree.
        """
        self._ensure_git_state_valid()
        return self.mapper.get_file_tree()

    def extract_symbols(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts symbols from the repository.
        If file_path is provided, extracts symbols only from that specific file (on-demand).
        If file_path is None, scans the entire repository (if necessary) and returns all symbols found.

        Args:
            file_path (Optional[str], optional): The path to the file to extract symbols from,
                                               relative to the repository root. Defaults to None (all files).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the extracted symbols.
        """
        self._ensure_git_state_valid()
        if file_path is not None:
            return self.mapper.extract_symbols(str(file_path))
        else:
            # Extract symbols from all relevant files by getting the full repo map.
            # self.mapper.get_repo_map() ensures scan_repo() is called if needed.
            repo_map = self.mapper.get_repo_map()
            all_symbols: List[Dict[str, Any]] = []
            # The symbol map stores symbols keyed by absolute file path
            # The values are lists of symbol dicts for that file
            for file_abs_path_str, symbols_in_file in repo_map.get("symbols", {}).items():
                all_symbols.extend(symbols_in_file)
            return all_symbols

    def search_text(self, query: str, file_pattern: str = "*") -> List[Dict[str, Any]]:
        """
        Searches for text in the repository.

        Args:
            query (str): The text to search for.
            file_pattern (str, optional): The file pattern to search in. Defaults to "*".

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the search results.
        """
        self._ensure_git_state_valid()
        return self.searcher.search_text(query, file_pattern)

    def get_code_searcher(self) -> "CodeSearcher":
        """Return a CodeSearcher bound to this repository.

        This is a lightweight accessor that exposes the underlying
        ``CodeSearcher`` instance created during ``Repository``
        initialization.  It can be useful in interactive scenarios or
        notebooks where you already have a ``Repository`` object and want
        to re-use its searcher without re-instantiating one manually.
        """
        self._ensure_git_state_valid()
        return self.searcher

    def chunk_file_by_lines(self, file_path: str, max_lines: int = 50) -> List[str]:
        """
        Chunks a file into lines.

        Args:
            file_path (str): The path to the file to chunk.
            max_lines (int, optional): The maximum number of lines to chunk. Defaults to 50.

        Returns:
            List[str]: A list of strings representing the chunked lines.
        """
        self._ensure_git_state_valid()
        return self.context.chunk_file_by_lines(file_path, max_lines)

    def chunk_file_by_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Chunks a file into symbols.

        Args:
            file_path (str): The path to the file to chunk.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the chunked symbols.
        """
        self._ensure_git_state_valid()
        return self.context.chunk_file_by_symbols(file_path)

    def extract_context_around_line(self, file_path: str, line: int) -> Optional[Dict[str, Any]]:
        """
        Extracts context around a line in a file.

        Args:
            file_path (str): The path to the file to extract context from.
            line (int): The line number to extract context around.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the extracted context, or None if not found.
        """
        self._ensure_git_state_valid()
        return self.context.extract_context_around_line(file_path, line)

    # Type overloads for precise return types
    @overload
    def get_file_content(self, file_path: str) -> str: ...

    @overload
    def get_file_content(self, file_path: List[str]) -> Dict[str, str]: ...

    def get_file_content(self, file_path: Union[str, List[str]]) -> Union[str, Dict[str, str]]:
        """
        Reads and returns the content of one or more files within the repository.

        Args:
            file_path: Single file path (str) or list of file paths (List[str]),
                      relative to the repository root.

        Returns:
            str: Content of the single file (when file_path is str)
            Dict[str, str]: Mapping of file_path -> content (when file_path is List[str])

        Raises:
            FileNotFoundError: If any file does not exist (includes details of all missing files)
            IOError: If any file reading error occurs
        """
        if isinstance(file_path, str):
            # Single file - existing behavior
            return self._get_single_file_content(file_path)
        else:
            # Multiple files - new behavior
            return self._get_multiple_file_contents(file_path)

    def _get_single_file_content(self, file_path: str) -> str:
        """Reads and returns the content of a single file within the repository."""
        self._ensure_git_state_valid()
        full_path = self.local_path / file_path
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found in repository: {file_path}")
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            # Catch potential decoding errors or other file reading issues
            raise IOError(f"Error reading file {file_path}: {e}") from e

    def _get_multiple_file_contents(self, file_paths: List[str]) -> Dict[str, str]:
        """Reads and returns the contents of multiple files within the repository."""
        self._ensure_git_state_valid()
        if not file_paths:
            return {}

        results = {}
        missing_files = []
        read_errors = []

        for file_path in file_paths:
            try:
                results[file_path] = self._get_single_file_content(file_path)
            except FileNotFoundError:
                missing_files.append(file_path)
            except IOError as e:
                read_errors.append(f"{file_path}: {e!s}")

        # Report all errors at once for better user experience
        if missing_files or read_errors:
            error_parts = []
            if missing_files:
                error_parts.append(f"Files not found: {', '.join(missing_files)}")
            if read_errors:
                error_parts.append(f"Read errors: {'; '.join(read_errors)}")
            raise IOError("; ".join(error_parts))

        return results

    def index(self) -> Dict[str, Any]:
        """
        Builds and returns a full index of the repo, including file tree and symbols.

        Returns:
            Dict[str, Any]: A dictionary representing the index.
        """
        self._ensure_git_state_valid()
        tree = self.get_file_tree()
        return {
            "file_tree": tree,  # legacy key
            "files": tree,  # preferred
            "symbols": self.mapper.get_repo_map()["symbols"],
        }

    def get_vector_searcher(self, embed_fn=None, backend=None, persist_dir=None):
        if self.vector_searcher is None:
            if embed_fn is None:
                raise ValueError("embed_fn must be provided on first use (e.g. OpenAI/HF embedding function)")
            self.vector_searcher = VectorSearcher(self, embed_fn, backend=backend, persist_dir=persist_dir)
        return self.vector_searcher

    def search_semantic(self, query: str, top_k: int = 5, embed_fn=None) -> List[Dict[str, Any]]:
        vs = self.get_vector_searcher(embed_fn=embed_fn)
        return vs.search(query, top_k=top_k)

    def get_summarizer(
        self, config: Optional[Union["OpenAIConfig", "AnthropicConfig", "GoogleConfig", "OllamaConfig"]] = None
    ) -> "Summarizer":
        """
        Factory method to get a Summarizer instance configured for this repository.

        Args:
            config: Optional LLM configuration. If None, defaults to OpenAIConfig using environment variable.

        Returns:
            A Summarizer instance bound to this repository.

        Example:
            >>> from kit.summaries import OpenAIConfig, AnthropicConfig, GoogleConfig, OllamaConfig
            >>> repo = Repository("/path/to/codebase")
            >>> # Use default (OpenAI with OPENAI_API_KEY env var)
            >>> summarizer = repo.get_summarizer()
            >>> # Or provide a specific config
            >>> openai_config = OpenAIConfig(api_key="sk-...", model="gpt-4")
            >>> summarizer = repo.get_summarizer(config=openai_config)
            >>> # Use Anthropic
            >>> anthropic_config = AnthropicConfig(api_key="sk-ant-...", model="claude-3-opus-20240229")
            >>> summarizer = repo.get_summarizer(config=anthropic_config)
            >>> # Use Google
            >>> google_config = GoogleConfig(api_key="...", model="gemini-1.5-pro-latest")
            >>> summarizer = repo.get_summarizer(config=google_config)
            >>> # Use Ollama (completely free!)
            >>> ollama_config = OllamaConfig(model="llama3.2:latest", base_url="http://localhost:11434")
            >>> summarizer = repo.get_summarizer(config=ollama_config)
        """
        from typing import Union

        from .summaries import AnthropicConfig, GoogleConfig, OllamaConfig, OpenAIConfig, Summarizer

        ConfigUnion = Union[OpenAIConfig, AnthropicConfig, GoogleConfig, OllamaConfig]

        if config is None:
            llm_config: ConfigUnion = OpenAIConfig()
        else:
            llm_config = config

        # Check if the provided or default config is one of the supported types
        if not isinstance(llm_config, (OpenAIConfig, AnthropicConfig, GoogleConfig, OllamaConfig)):
            raise NotImplementedError(
                f"Unsupported configuration type: {type(llm_config)}. Supported types are OpenAIConfig, AnthropicConfig, GoogleConfig, OllamaConfig."
            )
        else:
            # Return the initialized Summarizer
            return Summarizer(repo=self, config=llm_config)

    def get_context_assembler(self) -> "ContextAssembler":
        """Return a ContextAssembler bound to this repository."""
        return ContextAssembler(self)

    def get_dependency_analyzer(self, language: str = "python") -> "DependencyAnalyzer":
        """
        Factory method to get a DependencyAnalyzer instance configured for this repository.

        The DependencyAnalyzer helps visualize and analyze dependencies between modules
        or resources in your codebase, identifying relationships, cycles, and more.

        Args:
            language: The language to analyze. Currently supported: 'python', 'terraform'

        Returns:
            A DependencyAnalyzer instance bound to this repository for the specified language.

        Example:
            >>> # Get Python dependency analyzer (default)
            >>> analyzer = repo.get_dependency_analyzer()
            >>> # Or explicitly specify a language
            >>> analyzer = repo.get_dependency_analyzer('terraform')
            >>> graph = analyzer.build_dependency_graph()
            >>> analyzer.export_dependency_graph(output_format="dot", output_path="dependencies.dot")
            >>> cycles = analyzer.find_cycles()

        Raises:
            ValueError: If the specified language is not supported
        """
        from .dependency_analyzer.dependency_analyzer import DependencyAnalyzer

        return DependencyAnalyzer.get_for_language(self, language)

    def find_symbol_usages(self, symbol_name: str, symbol_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds all usages of a symbol (by name and optional type) across the repo's indexed symbols.
        Args:
            symbol_name (str): The name of the symbol to search for.
            symbol_type (Optional[str], optional): Optionally restrict to a symbol type (e.g., 'function', 'class').
        Returns:
            List[Dict[str, Any]]: List of usage dicts with file, line, and context if available.
        """
        self._ensure_git_state_valid()
        usages = []
        repo_map = self.mapper.get_repo_map()
        for file, symbols in repo_map["symbols"].items():
            for sym in symbols:
                if sym["name"] == symbol_name and (symbol_type is None or sym["type"] == symbol_type):
                    usages.append(
                        {
                            "file": file,
                            "type": sym["type"],
                            "name": sym["name"],
                            "line": sym.get("line"),
                            "context": sym.get("context"),
                        }
                    )
        # Optionally: search for references (calls/imports) using search_text or static analysis
        # Here, we do a simple text search for the symbol name in all files
        text_hits = self.searcher.search_text(symbol_name)
        for hit in text_hits:
            usages.append(
                {
                    "file": hit.get("file"),
                    "line": hit.get("line"),
                    # Always use 'line' or 'line_content' as context for search hits
                    "context": hit.get("line_content") or hit.get("line") or "",
                }
            )
        return usages

    def write_index(self, file_path: str) -> None:
        """
        Writes the full repo index (file tree and symbols) to a JSON file.
        Args:
            file_path (str): The path to the output file.
        """
        import json

        with open(file_path, "w") as f:
            json.dump(self.index(), f, indent=2)

    def write_symbols(self, file_path: str, symbols: Optional[list] = None) -> None:
        """
        Writes all extracted symbols (or provided symbols) to a JSON file.
        Args:
            file_path (str): The path to the output file.
            symbols (Optional[list]): List of symbol dicts. If None, extracts all symbols in the repo.
        """
        import json

        syms = (
            symbols if symbols is not None else [s for file_syms in self.index()["symbols"].values() for s in file_syms]
        )
        with open(file_path, "w") as f:
            json.dump(syms, f, indent=2)

    def write_file_tree(self, file_path: str) -> None:
        """
        Writes the file tree to a JSON file.
        Args:
            file_path (str): The path to the output file.
        """
        import json

        with open(file_path, "w") as f:
            json.dump(self.get_file_tree(), f, indent=2)

    def write_symbol_usages(self, symbol_name: str, file_path: str, symbol_type: Optional[str] = None) -> None:
        """
        Writes all usages of a symbol to a JSON file.
        Args:
            symbol_name (str): The name of the symbol.
            file_path (str): The path to the output file.
            symbol_type (Optional[str]): Optionally restrict to a symbol type.
        """
        import json

        usages = self.find_symbol_usages(symbol_name, symbol_type)
        with open(file_path, "w") as f:
            json.dump(usages, f, indent=2)

    def get_abs_path(self, relative_path: str) -> str:
        """
        Resolves a relative path within the repository to an absolute path.

        Args:
            relative_path: The path relative to the repository root.

        Returns:
            The absolute path as a string.
        """
        # Return a canonical absolute path for a file inside the repository.
        # We purposefully call `.resolve()` *after* joining with `self.local_path` so that
        # the repository root itself keeps its original symlink form (important for
        # tests that compare the root path), while individual file paths are resolved to
        # their real locations on disk. This yields stable, non-symlinked paths that
        # downstream tools (and tests) expect.
        return str((self.local_path / relative_path).resolve())

    def _check_git_state_changed(self) -> bool:
        """Check if the git state has changed since last check."""
        current_sha = self.current_sha

        # If we can't get SHA, assume state is valid (non-git repo or error)
        if current_sha is None:
            return False

        # First time checking or SHA changed
        if self._cached_git_sha != current_sha:
            self._cached_git_sha = current_sha
            return True

        return False

    def _ensure_git_state_valid(self) -> None:
        """Ensure caches are valid for current git state."""
        if self._check_git_state_changed():
            # Git state changed, invalidate caches
            self._invalidate_caches()
            self._git_state_valid = True

    def _invalidate_caches(self) -> None:
        """Invalidate all internal caches when git state changes."""
        # Clear mapper caches
        if hasattr(self.mapper, "_file_tree_cache"):
            delattr(self.mapper, "_file_tree_cache")
        if hasattr(self.mapper, "_repo_map_cache"):
            delattr(self.mapper, "_repo_map_cache")
        if hasattr(self.mapper, "_symbols_cache"):
            delattr(self.mapper, "_symbols_cache")

        # Clear searcher caches
        if hasattr(self.searcher, "_cache"):
            self.searcher._cache.clear()

        # Clear context caches
        if hasattr(self.context, "_cache"):
            self.context._cache.clear()

        # Clear incremental analyzer cache
        if self._incremental_analyzer is not None:
            self._incremental_analyzer.clear_cache()

        # Clear vector searcher (it needs to be rebuilt)
        self.vector_searcher = None

    @property
    def incremental_analyzer(self):
        """Get or create the incremental analyzer instance."""
        if self._incremental_analyzer is None:
            from .incremental_analyzer import IncrementalAnalyzer

            # Use a cache directory specific to this repository
            cache_dir = self.local_path / ".kit" / "incremental_cache"
            self._incremental_analyzer = IncrementalAnalyzer(self.local_path, cache_dir)
        return self._incremental_analyzer

    def finalize(self) -> None:
        """Finalize analysis and save cache."""
        if self._incremental_analyzer is not None:
            self._incremental_analyzer.finalize()

    def extract_symbols_incremental(self, file_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Extract symbols using incremental analysis for better performance.

        Args:
            file_paths: Optional list of specific files to analyze. If None, analyzes all supported files.

        Returns:
            List of symbol dictionaries with enhanced caching.
        """
        self._ensure_git_state_valid()

        if file_paths is None:
            # Get all supported files
            try:
                from .tree_sitter_symbol_extractor import TreeSitterSymbolExtractor

                supported_extensions = getattr(TreeSitterSymbolExtractor, "LANGUAGES", {})
            except (ImportError, AttributeError) as e:
                logger.warning(f"TreeSitterSymbolExtractor not available: {e}")
                supported_extensions = {".py", ".js", ".ts", ".go", ".rs"}  # fallback

            supported_files = []
            for file_path in self.local_path.rglob("*"):
                if (
                    file_path.is_file()
                    and ".git" not in file_path.parts
                    and file_path.suffix.lower() in supported_extensions
                ):
                    supported_files.append(file_path)
        else:
            # Convert relative paths to absolute
            supported_files = [self.local_path / fp for fp in file_paths]

        # Use incremental analyzer
        all_symbols = []
        for file_path in supported_files:
            symbols = self.incremental_analyzer.analyze_file(file_path)
            all_symbols.extend(symbols)

        return all_symbols

    def get_incremental_stats(self) -> Dict[str, Any]:
        """Get incremental analysis performance statistics."""
        if self._incremental_analyzer is None:
            return {"status": "not_initialized"}

        return self.incremental_analyzer.get_analysis_stats()

    def cleanup_incremental_cache(self) -> None:
        """Clean up stale entries in the incremental cache."""
        if self._incremental_analyzer is not None:
            self.incremental_analyzer.cleanup_cache()

    def clear_incremental_cache(self) -> None:
        """Clear all incremental analysis cache."""
        if self._incremental_analyzer is not None:
            self.incremental_analyzer.clear_cache()

    def finalize_analysis(self) -> None:
        """Finalize analysis and save incremental cache."""
        if self._incremental_analyzer is not None:
            self.incremental_analyzer.finalize()
