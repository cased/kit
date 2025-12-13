"""Multi-repository analysis and search."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from .repository import Repository

logger = logging.getLogger(__name__)


class MultiRepo:
    """
    Unified interface for analyzing multiple repositories.

    MultiRepo enables searching, analyzing, and querying across multiple
    codebases as if they were one. Useful for:
    - Microservices architectures
    - Frontend + backend splits
    - Finding patterns across team repos
    - Auditing dependencies across projects

    Example:
        >>> repos = MultiRepo([
        ...     "~/code/frontend",
        ...     "~/code/backend",
        ...     "~/code/shared-lib",
        ... ])
        >>> results = repos.search("handleAuth")
        >>> results = repos.search_semantic("error handling patterns")
    """

    def __init__(
        self,
        paths: Sequence[Union[str, Path]],
        names: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize MultiRepo with a list of repository paths.

        Args:
            paths: List of paths to repositories (local paths or URLs)
            names: Optional dict mapping paths to friendly names.
                   If not provided, directory names are used.
        """
        self._repos: Dict[str, Repository] = {}
        self._paths: Dict[str, str] = {}

        for path in paths:
            path_str = str(path)

            # Check if it's a remote URL
            is_remote = path_str.startswith(("http://", "https://", "git@"))

            if is_remote:
                # For remote URLs, extract repo name from URL
                resolved_path = path_str
                name = names.get(path_str) if names else None
                if name is None:
                    # Extract name from URL (e.g., "repo" from "https://github.com/owner/repo")
                    name = path_str.rstrip("/").split("/")[-1]
                    if name.endswith(".git"):
                        name = name[:-4]
            else:
                # For local paths, resolve and expand
                local_path = Path(path_str).expanduser().resolve()
                resolved_path = str(local_path)
                name = names.get(resolved_path) if names else None
                if name is None:
                    name = local_path.name

            # Handle name collisions
            original_name = name
            counter = 1
            while name in self._repos:
                name = f"{original_name}_{counter}"
                counter += 1

            self._repos[name] = Repository(resolved_path)
            self._paths[name] = resolved_path

    @property
    def repos(self) -> Dict[str, Repository]:
        """Access individual repositories by name."""
        return self._repos

    @property
    def names(self) -> List[str]:
        """List of repository names."""
        return list(self._repos.keys())

    def __len__(self) -> int:
        return len(self._repos)

    def __getitem__(self, name: str) -> Repository:
        return self._repos[name]

    def __iter__(self):
        return iter(self._repos.items())

    # -------------------------------------------------------------------------
    # Unified Search
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        file_pattern: str = "*",
        max_results_per_repo: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for text across all repositories.

        Args:
            query: Search query (regex supported)
            file_pattern: Glob pattern to filter files (e.g., "*.py")
            max_results_per_repo: Limit results per repo (None = unlimited)

        Returns:
            List of matches with repo name, file path, line number, and content
        """
        all_results = []

        for name, repo in self._repos.items():
            try:
                results = repo.grep(query, include_pattern=file_pattern)
                count = 0
                for r in results:
                    r["repo"] = name
                    all_results.append(r)
                    count += 1
                    if max_results_per_repo and count >= max_results_per_repo:
                        break
            except Exception as e:
                logger.warning(f"Error searching {name}: {e}")

        return all_results

    def search_semantic(
        self,
        query: str,
        top_k: int = 10,
        top_k_per_repo: Optional[int] = None,
        embed_fn: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across all repositories.

        Searches each repo's vector index and merges results by relevance score.

        Args:
            query: Natural language query
            top_k: Total number of results to return
            top_k_per_repo: Results to fetch per repo before merging.
                           Defaults to top_k if not specified.
            embed_fn: Optional custom embedding function

        Returns:
            List of matches sorted by relevance, with repo attribution
        """
        if top_k_per_repo is None:
            top_k_per_repo = top_k

        all_results = []

        for name, repo in self._repos.items():
            try:
                results = repo.search_semantic(query, top_k=top_k_per_repo, embed_fn=embed_fn)
                for r in results:
                    r["repo"] = name
                    all_results.append(r)
            except Exception as e:
                logger.warning(f"Error in semantic search for {name}: {e}")

        # Sort by score (higher is better) and return top_k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:top_k]

    # -------------------------------------------------------------------------
    # Symbol Analysis
    # -------------------------------------------------------------------------

    def find_symbol(
        self,
        symbol_name: str,
        symbol_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find a symbol (function, class, etc.) across all repositories.

        Args:
            symbol_name: Name of the symbol to find
            symbol_type: Optional filter by type ('function', 'class', 'method', etc.)

        Returns:
            List of symbol definitions with repo attribution
        """
        all_symbols = []

        for name, repo in self._repos.items():
            try:
                symbols = repo.extract_symbols()
                for sym in symbols:
                    if sym.get("name") == symbol_name:
                        if symbol_type is None or sym.get("type") == symbol_type:
                            sym["repo"] = name
                            all_symbols.append(sym)
            except Exception as e:
                logger.warning(f"Error extracting symbols from {name}: {e}")

        return all_symbols

    def extract_all_symbols(
        self,
        symbol_type: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all symbols from all repositories.

        Args:
            symbol_type: Optional filter by type ('function', 'class', etc.)

        Returns:
            Dict mapping repo name to list of symbols
        """
        result = {}

        for name, repo in self._repos.items():
            try:
                symbols = repo.extract_symbols()
                if symbol_type:
                    symbols = [s for s in symbols if s.get("type") == symbol_type]
                result[name] = symbols
            except Exception as e:
                logger.warning(f"Error extracting symbols from {name}: {e}")
                result[name] = []

        return result

    # -------------------------------------------------------------------------
    # Audit & Reporting
    # -------------------------------------------------------------------------

    def audit_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """
        Audit dependencies across all repositories.

        Parses package.json, requirements.txt, Cargo.toml, go.mod, etc.
        to report what packages each repo uses.

        Returns:
            Dict mapping repo name to dependency info
        """
        result = {}

        for name, repo in self._repos.items():
            repo_deps: Dict[str, Any] = {
                "python": {},
                "javascript": {},
                "rust": {},
                "go": {},
            }

            try:
                # Python - requirements.txt
                try:
                    content = repo.get_file_content("requirements.txt")
                    for line in content.strip().split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Parse "package==version" or "package>=version" etc.
                            for sep in ["==", ">=", "<=", "~=", "!=", ">"]:
                                if sep in line:
                                    pkg, ver = line.split(sep, 1)
                                    repo_deps["python"][pkg.strip()] = ver.strip()
                                    break
                            else:
                                repo_deps["python"][line] = "*"
                except Exception:
                    pass

                # Python - pyproject.toml
                try:
                    content = repo.get_file_content("pyproject.toml")
                    # Simple extraction - look for dependencies
                    in_deps = False
                    for line in content.split("\n"):
                        if "dependencies" in line and "=" in line:
                            in_deps = True
                        elif in_deps and line.strip().startswith("]"):
                            in_deps = False
                        elif in_deps and '"' in line:
                            # Extract package name from "package>=version"
                            match = line.strip().strip('",')
                            if match:
                                for sep in [">=", "<=", "==", "~=", ">"]:
                                    if sep in match:
                                        pkg, ver = match.split(sep, 1)
                                        repo_deps["python"][pkg.strip()] = ver.strip()
                                        break
                except Exception:
                    pass

                # JavaScript - package.json
                try:
                    content = repo.get_file_content("package.json")
                    pkg = json.loads(content)
                    if isinstance(pkg, dict):
                        for dep_type in ["dependencies", "devDependencies"]:
                            if dep_type in pkg and isinstance(pkg[dep_type], dict):
                                repo_deps["javascript"].update(pkg[dep_type])
                except Exception:
                    pass

                # Rust - Cargo.toml (use tomllib if available)
                try:
                    import sys

                    if sys.version_info >= (3, 11):
                        import tomllib
                    else:
                        import tomli as tomllib
                    content = repo.get_file_content("Cargo.toml")
                    cargo = tomllib.loads(content)
                    for dep_type in ["dependencies", "dev-dependencies", "build-dependencies"]:
                        if dep_type in cargo:
                            for pkg, ver in cargo[dep_type].items():
                                if isinstance(ver, str):
                                    repo_deps["rust"][pkg] = ver
                                elif isinstance(ver, dict):
                                    repo_deps["rust"][pkg] = ver.get("version", "*")
                except Exception:
                    pass

                # Go - go.mod
                try:
                    content = repo.get_file_content("go.mod")
                    for line in content.split("\n"):
                        line = line.strip()
                        if (
                            line
                            and not line.startswith("//")
                            and not line.startswith("module")
                            and not line.startswith("go ")
                            and not line.startswith("require")
                            and not line.startswith("replace")
                            and not line.startswith("exclude")
                            and not line.startswith("retract")
                            and line != ")"
                        ):
                            parts = line.split()
                            if len(parts) >= 2:
                                repo_deps["go"][parts[0]] = parts[1]
                except Exception:
                    pass

                # Filter out empty categories
                repo_deps = {k: v for k, v in repo_deps.items() if v}
                result[name] = repo_deps

            except Exception as e:
                logger.warning(f"Error auditing {name}: {e}")
                result[name] = {}

        return result

    def summarize(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate a summary of each repository.

        Returns:
            Dict mapping repo name to summary info (file count, languages, etc.)
        """
        result = {}

        for name, repo in self._repos.items():
            try:
                file_tree = repo.get_file_tree()

                # Count files by extension
                extensions: Dict[str, int] = {}
                for f in file_tree:
                    ext = Path(f["path"]).suffix.lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1

                # Detect primary languages
                lang_map = {
                    ".py": "Python",
                    ".js": "JavaScript",
                    ".ts": "TypeScript",
                    ".tsx": "TypeScript",
                    ".jsx": "JavaScript",
                    ".go": "Go",
                    ".rs": "Rust",
                    ".java": "Java",
                    ".rb": "Ruby",
                    ".php": "PHP",
                    ".cs": "C#",
                    ".cpp": "C++",
                    ".c": "C",
                }

                languages: Dict[str, int] = {}
                for ext, count in extensions.items():
                    if ext in lang_map:
                        lang = lang_map[ext]
                        languages[lang] = languages.get(lang, 0) + count

                result[name] = {
                    "path": self._paths[name],
                    "file_count": len(file_tree),
                    "extensions": dict(sorted(extensions.items(), key=lambda x: -x[1])[:10]),
                    "languages": dict(sorted(languages.items(), key=lambda x: -x[1])),
                }

            except Exception as e:
                logger.warning(f"Error summarizing {name}: {e}")
                result[name] = {"error": str(e)}

        return result

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def index_all(self, embed_fn: Optional[Callable] = None) -> None:
        """
        Build or refresh vector indexes for all repositories.

        Args:
            embed_fn: Optional custom embedding function
        """
        for name, repo in self._repos.items():
            try:
                logger.info(f"Indexing {name}...")
                repo.get_vector_searcher(embed_fn=embed_fn)
            except Exception as e:
                logger.warning(f"Error indexing {name}: {e}")

    def get_file_content(
        self,
        repo_name: str,
        file_path: str,
    ) -> str:
        """
        Get file content from a specific repository.

        Args:
            repo_name: Name of the repository
            file_path: Path to the file within the repo

        Returns:
            File content as string
        """
        return self._repos[repo_name].get_file_content(file_path)
