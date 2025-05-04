from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from .repo_mapper import RepoMapper
from .code_searcher import CodeSearcher
from .context_extractor import ContextExtractor
from .vector_searcher import VectorSearcher
import os
import tempfile
import subprocess
from pathlib import Path

# Use TYPE_CHECKING for Summarizer to avoid circular imports
if TYPE_CHECKING:
    from .summaries import Summarizer, OpenAIConfig

class Repository:
    """
    Main interface for codebase operations: file tree, symbol extraction, search, and context.
    Provides a unified API for downstream tools and workflows.
    """
    def __init__(self, path_or_url: str, github_token: Optional[str] = None, cache_dir: Optional[str] = None) -> None:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):  # Remote repo
            self.local_path = self._clone_github_repo(path_or_url, github_token, cache_dir)
        else:
            self.local_path = Path(path_or_url).resolve()
        self.repo_path: str = str(self.local_path)
        self.mapper: RepoMapper = RepoMapper(self.repo_path)
        self.searcher: CodeSearcher = CodeSearcher(self.repo_path)
        self.context: ContextExtractor = ContextExtractor(self.repo_path)
        self.vector_searcher: Optional[VectorSearcher] = None

    def _clone_github_repo(self, url: str, token: Optional[str], cache_dir: Optional[str]) -> Path:
        from urllib.parse import urlparse
        repo_name = urlparse(url).path.strip("/").replace("/", "-")
        cache_root = Path(cache_dir or tempfile.gettempdir()) / "kit-repo-cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        repo_path = cache_root / repo_name
        if repo_path.exists() and (repo_path / ".git").exists():
            # Optionally: git pull to update
            return repo_path
        clone_url = url
        if token:
            # Insert token for private repos
            clone_url = url.replace("https://", f"https://{token}@")
        subprocess.run(["git", "clone", "--depth=1", clone_url, str(repo_path)], check=True)
        return repo_path

    def get_file_tree(self) -> List[Dict[str, Any]]:
        """
        Returns the file tree of the repository.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the file tree.
        """
        return self.mapper.get_file_tree()

    def extract_symbols(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts symbols from the repository.
        
        Args:
            file_path (Optional[str], optional): The path to the file to extract symbols from. Defaults to None.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the extracted symbols.
        """
        return self.mapper.extract_symbols(file_path)

    def search_text(self, query: str, file_pattern: str = "*.py") -> List[Dict[str, Any]]:
        """
        Searches for text in the repository.
        
        Args:
            query (str): The text to search for.
            file_pattern (str, optional): The file pattern to search in. Defaults to "*.py".
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the search results.
        """
        return self.searcher.search_text(query, file_pattern)

    def chunk_file_by_lines(self, file_path: str, max_lines: int = 50) -> List[str]:
        """
        Chunks a file into lines.
        
        Args:
            file_path (str): The path to the file to chunk.
            max_lines (int, optional): The maximum number of lines to chunk. Defaults to 50.
        
        Returns:
            List[str]: A list of strings representing the chunked lines.
        """
        return self.context.chunk_file_by_lines(file_path, max_lines)

    def chunk_file_by_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Chunks a file into symbols.
        
        Args:
            file_path (str): The path to the file to chunk.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the chunked symbols.
        """
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
        return self.context.extract_context_around_line(file_path, line)

    def get_file_content(self, file_path: str) -> str:
        """
        Reads and returns the content of a file within the repository.
        
        Args:
            file_path (str): The path to the file, relative to the repository root.
        
        Returns:
            str: The content of the file.
        
        Raises:
            FileNotFoundError: If the file does not exist within the repository.
        """
        full_path = self.local_path / file_path
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found in repository: {file_path}")
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            # Catch potential decoding errors or other file reading issues
            raise IOError(f"Error reading file {file_path}: {e}") from e

    def index(self) -> Dict[str, Any]:
        """
        Builds and returns a full index of the repo, including file tree and symbols.
        
        Returns:
            Dict[str, Any]: A dictionary representing the index.
        """
        return {
            "file_tree": self.get_file_tree(),
            "symbols": {f: syms for f, syms in self.mapper.get_repo_map()["symbols"].items()}
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

    def get_summarizer(self, config: Optional['OpenAIConfig'] = None) -> 'Summarizer': 
        """
        Factory method to get a Summarizer instance configured for this repository.
        
        Requires LLM dependencies (e.g., openai) to be installed.
        Example: `pip install kit[openai]`
        
        Args:
            config: Optional configuration object (e.g., OpenAIConfig). 
                    If None, defaults to OpenAIConfig using environment variables.
        
        Returns:
            A Summarizer instance ready to use.
        
        Raises:
            ImportError: If required LLM libraries (like openai) are not installed.
            ValueError: If configuration (like API key) is missing.
        """
        # Lazy import Summarizer and its config here to avoid mandatory dependency
        try:
            from .summaries import Summarizer, OpenAIConfig 
        except ImportError as e:
             raise ImportError(
                 "Summarizer dependencies not found. Did you install kit[openai]?"
             ) from e

        # Determine config: use provided or default (which checks env vars)
        llm_config = config if config is not None else OpenAIConfig()
        
        # Currently only supports OpenAIConfig, raise if different type is passed
        if not isinstance(llm_config, OpenAIConfig):
             raise NotImplementedError("Currently only OpenAIConfig is supported for summarization.")

        # Return the initialized Summarizer
        return Summarizer(repo=self, config=llm_config)

    def find_symbol_usages(self, symbol_name: str, symbol_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds all usages of a symbol (by name and optional type) across the repo's indexed symbols.
        Args:
            symbol_name (str): The name of the symbol to search for.
            symbol_type (Optional[str], optional): Optionally restrict to a symbol type (e.g., 'function', 'class').
        Returns:
            List[Dict[str, Any]]: List of usage dicts with file, line, and context if available.
        """
        usages = []
        repo_map = self.mapper.get_repo_map()
        for file, symbols in repo_map["symbols"].items():
            for sym in symbols:
                if sym["name"] == symbol_name and (symbol_type is None or sym["type"] == symbol_type):
                    usages.append({
                        "file": file,
                        "type": sym["type"],
                        "name": sym["name"],
                        "line": sym.get("line"),
                        "context": sym.get("context")
                    })
        # Optionally: search for references (calls/imports) using search_text or static analysis
        # Here, we do a simple text search for the symbol name in all files
        text_hits = self.searcher.search_text(symbol_name)
        for hit in text_hits:
            usages.append({
                "file": hit.get("file"),
                "line": hit.get("line"),
                # Always use 'line' or 'line_content' as context for search hits
                "context": hit.get("line_content") or hit.get("line") or ""
            })
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
        syms = symbols if symbols is not None else [s for file_syms in self.index()["symbols"].values() for s in file_syms]
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
