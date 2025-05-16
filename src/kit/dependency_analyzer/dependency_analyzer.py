"""Base class for language-specific dependency analyzers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository


class DependencyAnalyzer(ABC):
    """
    Abstract base class for language-specific dependency analyzers.

    This class defines the common interface for all dependency analyzers,
    regardless of the language or configuration format they target.
    Implement language-specific analyzers by subclassing this base class.
    """

    def __init__(self, repository: "Repository"):
        """
        Initialize the analyzer with a Repository instance.

        Args:
            repository: A kit.Repository instance
        """
        self.repo = repository
        self.dependency_graph: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    @abstractmethod
    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph.
        """
        pass

    @abstractmethod
    def export_dependency_graph(self, output_format: str = "json", output_path: Optional[str] = None):
        """
        Export the dependency graph in various formats.

        Args:
            output_format: Format to export (e.g., 'json', 'dot', 'graphml')
            output_path: Path to save the output file (if None, returns the data)

        Returns:
            Varies based on implementation:
            - If output_path is provided: Path to the output file
            - If output_path is None: Formatted dependency data
        """
        pass

    @abstractmethod
    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of node identifiers
        """
        pass

    @abstractmethod
    def visualize_dependencies(self, output_path: str, format: str = "png") -> str:
        """
        Generate a visualization of the dependency graph.

        Args:
            output_path: Path to save the visualization
            format: Output format ('png', 'svg', 'pdf')

        Returns:
            Path to the generated visualization file
        """
        pass

    def generate_llm_context(
        self, max_tokens: int = 4000, output_format: str = "markdown", output_path: Optional[str] = None
    ) -> str:
        """
        Generate a concise, natural language description of the dependency graph optimized for LLM consumption.

        This method analyzes the dependency structure and produces a summary suitable for providing
        context to large language models, focusing on the most significant patterns and relationships
        while keeping the output within reasonable token limits.

        Args:
            max_tokens: Approximate maximum number of tokens in the output (rough guideline)
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description of the dependency structure
        """
        if not self._initialized:
            self.build_dependency_graph()

        # Generate overall statistics
        total_nodes = len(self.dependency_graph)
        internal_nodes = len([n for n, data in self.dependency_graph.items() if data.get("type", "") == "internal"])
        external_nodes = total_nodes - internal_nodes

        # Find cycles
        cycles = self.find_cycles()
        has_cycles = len(cycles) > 0

        # Find central nodes (high connectivity)
        node_connections = {}
        for node in self.dependency_graph:
            # Count outgoing connections
            outgoing = len(self.dependency_graph[node].get("dependencies", []))

            # Count incoming connections
            incoming = len(
                [n for n in self.dependency_graph if node in self.dependency_graph[n].get("dependencies", [])]
            )

            node_connections[node] = (incoming, outgoing, incoming + outgoing)

        # Sort by total connections (descending)
        central_nodes = sorted(node_connections.items(), key=lambda x: x[1][2], reverse=True)[:10]

        if output_format == "markdown":
            output = ["# Dependency Analysis Summary\n"]

            output.append("## Overview\n")
            output.append(f"- Total components: {total_nodes}\n")
            output.append(f"- Internal components: {internal_nodes}\n")
            output.append(f"- External dependencies: {external_nodes}\n")
            output.append(f"- Has circular dependencies: {'Yes' if has_cycles else 'No'}\n")

            output.append("\n## Key Components\n")
            output.append("Components with the highest connectivity:\n")

            for i, (node, (incoming, outgoing, total)) in enumerate(central_nodes[:5], 1):
                component_type = self.dependency_graph[node].get("type", "component")
                output.append(f"{i}. **{node}** ({component_type})\n")
                output.append(f"   - Depends on: {outgoing} components\n")
                output.append(f"   - Used by: {incoming} components\n")

            if has_cycles:
                output.append("\n## Circular Dependencies\n")
                output.append("The following circular dependencies were detected:\n")

                for i, cycle in enumerate(cycles[:3], 1):
                    output.append(f"{i}. {' → '.join(cycle)} → {cycle[0]}\n")

                if len(cycles) > 3:
                    output.append(f"...and {len(cycles) - 3} more cycles\n")

            output.append("\n## Additional Insights\n")
            output.append("This is a base implementation. Language-specific analyzers may ")
            output.append("provide more detailed insights.\n")

        else:
            output = ["DEPENDENCY ANALYSIS SUMMARY\n"]
            output.append("=========================\n\n")

            output.append("OVERVIEW:\n")
            output.append(f"- Total components: {total_nodes}\n")
            output.append(f"- Internal components: {internal_nodes}\n")
            output.append(f"- External dependencies: {external_nodes}\n")
            output.append(f"- Has circular dependencies: {'Yes' if has_cycles else 'No'}\n\n")

            output.append("KEY COMPONENTS:\n")
            output.append("Components with the highest connectivity:\n")

            for i, (node, (incoming, outgoing, total)) in enumerate(central_nodes[:5], 1):
                component_type = self.dependency_graph[node].get("type", "component")
                output.append(f"{i}. {node} ({component_type})\n")
                output.append(f"   - Depends on: {outgoing} components\n")
                output.append(f"   - Used by: {incoming} components\n")

            if has_cycles:
                output.append("\nCIRCULAR DEPENDENCIES:\n")
                output.append("The following circular dependencies were detected:\n")

                for i, cycle in enumerate(cycles[:3], 1):
                    output.append(f"{i}. {' -> '.join(cycle)} -> {cycle[0]}\n")

                if len(cycles) > 3:
                    output.append(f"...and {len(cycles) - 3} more cycles\n")

            output.append("\nADDITIONAL INSIGHTS:\n")
            output.append("This is a base implementation. Language-specific analyzers may ")
            output.append("provide more detailed insights.\n")

        result = "".join(output)

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result

    @classmethod
    def get_for_language(cls, repository: "Repository", language: str) -> "DependencyAnalyzer":
        """
        Factory method to get an appropriate DependencyAnalyzer for the specified language.

        Args:
            repository: A kit.Repository instance
            language: Language identifier (e.g., 'python', 'terraform')

        Returns:
            An appropriate DependencyAnalyzer instance for the language

        Raises:
            ValueError: If the specified language is not supported
        """
        from .python_dependency_analyzer import PythonDependencyAnalyzer
        from .terraform_dependency_analyzer import TerraformDependencyAnalyzer

        language = language.lower()

        if language == "python":
            return PythonDependencyAnalyzer(repository)
        elif language == "terraform":
            return TerraformDependencyAnalyzer(repository)
        else:
            raise ValueError(
                f"Unsupported language for dependency analysis: {language}. "
                f"Currently supported languages: python, terraform"
            )

    # ------------------------------------------------------------------
    # Convenience wrapper used by REST API
    # ------------------------------------------------------------------

    def analyze(self, file_path: Optional[str] = None, depth: int = 1):  # type: ignore[override]
        """Return the dependency graph, optionally scoped to a single file/module.

        The FastAPI route delegates here instead of calling the language-specific
        helpers directly.  For now we just build (or reuse) the in-memory
        dependency graph and filter it if *file_path* is provided.  *depth* is
        accepted for forward-compatibility but currently ignored.
        """

        # Ensure the graph is ready
        if not self._initialized:
            self.build_dependency_graph()

        if file_path is None:
            return self.dependency_graph

        # Basic filter: take nodes whose stored "path" matches the requested file
        scoped = {node: data for node, data in self.dependency_graph.items() if data.get("path") == file_path}

        # If nothing matched we simply return an empty graph rather than erroring.
        return scoped
