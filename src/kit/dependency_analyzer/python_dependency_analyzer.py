"""Analyzes and visualizes code dependencies within a Python repository."""

from __future__ import annotations

import ast
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository


class PythonDependencyAnalyzer(DependencyAnalyzer):
    """
    Analyzes internal and external dependencies in a codebase.

    This class provides functionality to:
    1. Build a dependency graph of modules within a repository
    2. Identify import relationships between files
    3. Export dependency information in various formats
    4. Detect dependency cycles and other potential issues
    """

    def __init__(self, repository: "Repository"):
        """
        Initialize the analyzer with a Repository instance.

        Args:
            repository: A kit.Repository instance
        """
        super().__init__(repository)
        self._module_map: Dict[str, str] = {}

    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph, where:
            - Keys are module identifiers
            - Values are dictionaries containing:
                - 'type': 'internal' or 'external'
                - 'path': File path (for internal dependencies)
                - 'dependencies': List of module identifiers this module depends on
        """
        self.dependency_graph = {}
        self._module_map = {}

        self._build_module_map()

        for file_info in self.repo.get_file_tree():
            if file_info["path"].endswith(".py"):
                self._process_file(file_info["path"])

        self._initialized = True
        return self.dependency_graph

    def _build_module_map(self):
        """Maps module names to file paths for internal imports."""
        for file_info in self.repo.get_file_tree():
            if not file_info["path"].endswith(".py"):
                continue

            module_path = os.path.splitext(file_info["path"])[0]
            module_name = module_path.replace("/", ".").replace("\\", ".")

            if module_name.endswith(".__init__"):
                package_name = module_name[:-9]
                self._module_map[package_name] = os.path.dirname(file_info["path"])

            self._module_map[module_name] = file_info["path"]

            parts = module_name.split(".")
            for i in range(1, len(parts) + 1):
                potential_module = ".".join(parts[:i])
                if potential_module not in self._module_map:
                    parent_dir = os.path.dirname(file_info["path"])
                    for _ in range(len(parts) - i):
                        parent_dir = os.path.dirname(parent_dir)
                    self._module_map[potential_module] = parent_dir

    def _process_file(self, file_path: str):
        """
        Process a single file to extract its dependencies.

        Args:
            file_path: Path to the file to analyze
        """
        try:
            file_content = self.repo.get_file_content(file_path)
            tree = ast.parse(file_content)

            module_path = os.path.splitext(file_path)[0]
            module_name = module_path.replace("/", ".").replace("\\", ".")
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]

            if module_name not in self.dependency_graph:
                self.dependency_graph[module_name] = {"type": "internal", "path": file_path, "dependencies": set()}

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imported_name = name.name
                        self._add_dependency(module_name, imported_name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module is not None:
                        module_path = node.module

                        for name in node.names:
                            specific_module = f"{module_path}.{name.name}"

                            if specific_module in self._module_map:
                                self._add_dependency(module_name, specific_module)
                            else:
                                self._add_dependency(module_name, module_path)

        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")

    def _add_dependency(self, source: str, target: str):
        """
        Add a dependency from source to target in the graph.

        Args:
            source: Source module name
            target: Target module/package name
        """
        self.dependency_graph[source]["dependencies"].add(target)

        if target not in self.dependency_graph:
            if target in self._module_map:
                dependency_type = "internal"
                dependency_path = self._module_map[target]
            else:
                dependency_type = "external"
                dependency_path = None

            self.dependency_graph[target] = {"type": dependency_type, "path": dependency_path, "dependencies": set()}

    def export_dependency_graph(
        self, output_format: str = "json", output_path: Optional[str] = None
    ) -> Union[Dict, str]:
        """
        Export the dependency graph in various formats.

        Args:
            output_format: Format to export ('json', 'dot', 'graphml', 'adjacency')
            output_path: Path to save the output file (if None, returns the data)

        Returns:
            Depending on format and output_path:
            - If output_path is provided: Path to the output file
            - If output_path is None: Formatted dependency data
        """
        if not self._initialized:
            self.build_dependency_graph()

        serializable_graph = {}
        for module, data in self.dependency_graph.items():
            serializable_graph[module] = {
                "type": data["type"],
                "path": data["path"],
                "dependencies": list(data["dependencies"]),
            }

        if output_format == "json":
            import json

            if output_path:
                with open(output_path, "w") as f:
                    json.dump(serializable_graph, f, indent=2)
                return output_path
            return serializable_graph

        elif output_format == "dot":
            dot_content = self._generate_dot_file(serializable_graph)
            if output_path:
                with open(output_path, "w") as f:
                    f.write(dot_content)
                return output_path
            return dot_content

        elif output_format == "graphml":
            graphml_content = self._generate_graphml_file(serializable_graph)
            if output_path:
                with open(output_path, "w") as f:
                    f.write(graphml_content)
                return output_path
            return graphml_content

        elif output_format == "adjacency":
            adjacency_list = {}
            for module, data in serializable_graph.items():
                adjacency_list[module] = data["dependencies"]

            if output_path:
                import json

                with open(output_path, "w") as f:
                    json.dump(adjacency_list, f, indent=2)
                return output_path
            return adjacency_list

        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _generate_dot_file(self, graph: Dict[str, Dict[str, Any]]) -> str:
        """Generate a DOT file for visualization with Graphviz."""
        dot_lines = ["digraph G {", '  rankdir="LR";', "  node [shape=box];"]

        # Add nodes
        for module, data in graph.items():
            node_color = "lightblue" if data["type"] == "internal" else "lightgreen"
            # Escape quotes in module name
            safe_module = module.replace('"', '\\"')
            dot_lines.append(f'  "{safe_module}" [style=filled, fillcolor={node_color}];')

        # Add edges
        for module, data in graph.items():
            safe_module = module.replace('"', '\\"')
            for dep in data["dependencies"]:
                if dep in graph:  # Only add edges for modules in the graph
                    safe_dep = dep.replace('"', '\\"')
                    dot_lines.append(f'  "{safe_module}" -> "{safe_dep}";')

        dot_lines.append("}")
        return "\n".join(dot_lines)

    def _generate_graphml_file(self, graph: Dict[str, Dict[str, Any]]) -> str:
        """Generate a GraphML file for visualization with tools like Gephi or yEd."""
        graphml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '  xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '  http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '<key id="type" for="node" attr.name="type" attr.type="string"/>',
            '<key id="path" for="node" attr.name="path" attr.type="string"/>',
            '<graph id="G" edgedefault="directed">',
        ]

        # Add nodes
        for module, data in graph.items():
            # XML-escape module name
            safe_module = module.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

            graphml_lines.append(f'  <node id="{safe_module}">')
            graphml_lines.append(f'    <data key="type">{data["type"]}</data>')
            if data["path"]:
                safe_path = (
                    data["path"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                )
                graphml_lines.append(f'    <data key="path">{safe_path}</data>')
            graphml_lines.append("  </node>")

        # Add edges
        edge_id = 0
        for module, data in graph.items():
            safe_module = module.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            for dep in data["dependencies"]:
                if dep in graph:  # Only add edges for modules in the graph
                    safe_dep = (
                        dep.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    )
                    graphml_lines.append(f'  <edge id="e{edge_id}" source="{safe_module}" target="{safe_dep}"/>')
                    edge_id += 1

        graphml_lines.append("</graph>")
        graphml_lines.append("</graphml>")
        return "\n".join(graphml_lines)

    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of module names
        """
        if not self._initialized:
            self.build_dependency_graph()

        cycles = []

        for start_module in self.dependency_graph:
            if self.dependency_graph[start_module]["type"] != "internal":
                continue

            path: List[str] = []
            visited = set()

            def dfs(module):
                if module in path:
                    cycle_start = path.index(module)
                    cycle = path[cycle_start:] + [module]
                    if cycle not in cycles and len(cycle) > 1:
                        cycles.append(cycle)
                    return

                if module in visited or module not in self.dependency_graph:
                    return

                visited.add(module)
                path.append(module)

                for dep in self.dependency_graph[module]["dependencies"]:
                    if self.dependency_graph.get(dep, {}).get("type") == "internal":
                        dfs(dep)

                path.pop()

            dfs(start_module)

        return cycles

    def get_module_dependencies(self, module_name: str, include_indirect: bool = False) -> List[str]:
        """
        Get dependencies for a specific module.

        Args:
            module_name: Name of the module to check
            include_indirect: Whether to include indirect dependencies

        Returns:
            List of module names this module depends on
        """
        if not self._initialized:
            self.build_dependency_graph()

        if module_name not in self.dependency_graph:
            return []

        if include_indirect:
            all_deps = set()
            visited = set()

            def dfs(module):
                if module in visited or module not in self.dependency_graph:
                    return

                visited.add(module)

                for dep in self.dependency_graph[module]["dependencies"]:
                    if dep in self.dependency_graph:
                        all_deps.add(dep)
                        dfs(dep)

            dfs(module_name)
            return list(all_deps)
        else:
            return [dep for dep in self.dependency_graph[module_name]["dependencies"] if dep in self.dependency_graph]

    def get_dependents(self, module_name: str, include_indirect: bool = False) -> List[str]:
        """
        Get modules that depend on the specified module.

        Args:
            module_name: Name of the module to check
            include_indirect: Whether to include indirect dependents

        Returns:
            List of module names that depend on this module
        """
        if not self._initialized:
            self.build_dependency_graph()

        if module_name not in self.dependency_graph:
            return []

        direct_dependents = [mod for mod, data in self.dependency_graph.items() if module_name in data["dependencies"]]

        if not include_indirect:
            return direct_dependents

        all_dependents = set(direct_dependents)

        def find_ancestors(module):
            parents = [
                mod
                for mod, data in self.dependency_graph.items()
                if module in data["dependencies"] and mod not in all_dependents
            ]

            for parent in parents:
                all_dependents.add(parent)
                find_ancestors(parent)

        for dep in direct_dependents:
            find_ancestors(dep)

        return list(all_dependents)

    def get_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed dependency information for a specific file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dictionary with dependency information for the file
        """
        if not self._initialized:
            self.build_dependency_graph()

        module_path = os.path.splitext(file_path)[0]
        module_name = module_path.replace("/", ".").replace("\\", ".")

        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]

        if module_name not in self.dependency_graph:
            return {"file_path": file_path, "module_name": module_name, "dependencies": [], "dependents": []}

        dependencies = self.get_module_dependencies(module_name)
        dependents = self.get_dependents(module_name)

        dependencies_info = []
        for dep in dependencies:
            if dep in self.dependency_graph:
                dependencies_info.append(
                    {
                        "module": dep,
                        "type": self.dependency_graph[dep]["type"],
                        "path": self.dependency_graph[dep]["path"],
                    }
                )
            else:
                dependencies_info.append({"module": dep, "type": "external", "path": None})

        dependents_info = []
        for dep in dependents:
            dependents_info.append(
                {"module": dep, "type": self.dependency_graph[dep]["type"], "path": self.dependency_graph[dep]["path"]}
            )

        return {
            "file_path": file_path,
            "module_name": module_name,
            "dependencies": dependencies_info,
            "dependents": dependents_info,
        }

    def generate_dependency_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive dependency report for the repository.

        Args:
            output_path: Optional path to save the report JSON

        Returns:
            Dictionary with the complete dependency report
        """
        if not self._initialized:
            self.build_dependency_graph()

        internal_modules = [m for m, data in self.dependency_graph.items() if data["type"] == "internal"]
        external_modules = [m for m, data in self.dependency_graph.items() if data["type"] == "external"]

        cycles = self.find_cycles()

        high_dependency_modules = []
        for module, data in self.dependency_graph.items():
            if data["type"] == "internal":
                dependents = self.get_dependents(module)
                dependencies = self.get_module_dependencies(module)

                if len(dependents) > 5 or len(dependencies) > 10:
                    high_dependency_modules.append(
                        {
                            "module": module,
                            "path": data["path"],
                            "dependent_count": len(dependents),
                            "dependency_count": len(dependencies),
                        }
                    )

        report = {
            "summary": {
                "total_modules": len(self.dependency_graph),
                "internal_modules": len(internal_modules),
                "external_modules": len(external_modules),
                "dependency_cycles": len(cycles),
            },
            "cycles": cycles,
            "high_dependency_modules": sorted(
                high_dependency_modules, key=lambda x: x["dependent_count"] + x["dependency_count"], reverse=True
            ),
            "external_dependencies": sorted(external_modules),
        }

        if output_path:
            import json

            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report

    def visualize_dependencies(self, output_path: str, format: str = "png") -> str:
        """
        Generate a visualization of the dependency graph.

        Note: Requires Graphviz to be installed.

        Args:
            output_path: Path to save the visualization
            format: Output format ('png', 'svg', 'pdf')

        Returns:
            Path to the generated visualization file
        """
        try:
            import graphviz
        except ImportError:
            raise ImportError(
                "Graphviz Python package is required for visualization. "
                "Install with 'pip install graphviz'. "
                "You also need the Graphviz binary installed on your system."
            )

        if not self._initialized:
            self.build_dependency_graph()

        dot = graphviz.Digraph("dependencies", comment="Module Dependencies", format=format, engine="dot")
        dot.attr(rankdir="LR")

        for module, data in self.dependency_graph.items():
            if data["type"] == "external":
                continue

            if "." in module:
                label = module.split(".")[-1]
                tooltip = module
            else:
                label = module
                tooltip = module

            dot.node(module, label=label, tooltip=tooltip, style="filled", fillcolor="lightblue", shape="box")

        for module, data in self.dependency_graph.items():
            if data["type"] == "external":
                continue

            for dep in data["dependencies"]:
                if dep in self.dependency_graph and self.dependency_graph[dep]["type"] == "internal":
                    dot.edge(module, dep)

        dot.render(output_path, cleanup=True)
        return f"{output_path}.{format}"

    def generate_llm_context(
        self, max_tokens: int = 4000, output_format: str = "markdown", output_path: Optional[str] = None
    ) -> str:
        """
        Generate a Python-specific natural language description of the dependency graph optimized for LLM consumption.

        This method extends the base implementation with Python-specific insights about imports,
        modules, and package structure to provide richer context to large language models.

        Args:
            max_tokens: Approximate maximum number of tokens in the output (rough guideline)
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description of the dependency structure
        """
        base_summary = super().generate_llm_context(max_tokens, output_format, None)

        # Define standard library modules (simplified list for common ones)
        stdlib_modules = {
            "os",
            "sys",
            "io",
            "time",
            "datetime",
            "math",
            "random",
            "json",
            "re",
            "collections",
            "functools",
            "itertools",
            "pathlib",
            "typing",
            "abc",
            "argparse",
            "ast",
            "asyncio",
            "base64",
            "csv",
            "ctypes",
            "enum",
            "glob",
            "hashlib",
            "http",
            "inspect",
            "logging",
            "pickle",
            "platform",
            "shutil",
            "socket",
            "sqlite3",
            "statistics",
            "string",
            "subprocess",
            "tempfile",
            "threading",
            "unittest",
            "urllib",
            "uuid",
            "xml",
            "zipfile",
        }

        try:
            if hasattr(sys, "stdlib_module_names"):
                stdlib_modules = set(sys.stdlib_module_names)
        except Exception:
            pass

        standard_lib_count = len(
            [
                m
                for m in self.dependency_graph
                if self.dependency_graph[m].get("type") == "external" and m.split(".")[0] in stdlib_modules
            ]
        )
        third_party_count = len(
            [
                m
                for m in self.dependency_graph
                if self.dependency_graph[m].get("type") == "external" and m.split(".")[0] not in stdlib_modules
            ]
        )

        heavy_importers = sorted(
            [
                (m, len(deps))
                for m, deps in [
                    (m, self.dependency_graph[m].get("dependencies", []))
                    for m in self.dependency_graph
                    if self.dependency_graph[m].get("type") == "internal"
                ]
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        module_import_counts: Dict[str, int] = {}
        for m in self.dependency_graph:
            if self.dependency_graph[m].get("type") == "internal":
                for dep in self.dependency_graph[m].get("dependencies", []):
                    module_import_counts[dep] = module_import_counts.get(dep, 0) + 1

        most_imported = sorted(module_import_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        if output_format == "markdown":
            parts = base_summary.split("## Additional Insights")

            python_insights = ["## Python-Specific Insights\n"]

            python_insights.append("### Dependency Types\n")
            python_insights.append(f"- Standard library imports: {standard_lib_count}\n")
            python_insights.append(f"- Third-party library imports: {third_party_count}\n\n")

            if heavy_importers:
                python_insights.append("### Modules with Most Dependencies\n")
                for module, count in heavy_importers:
                    python_insights.append(f"- **{module}** imports {count} modules\n")
                python_insights.append("\n")

            if most_imported:
                python_insights.append("### Most Commonly Used Modules\n")
                for module, count in most_imported:
                    module_type = (
                        "internal"
                        if module in self.dependency_graph and self.dependency_graph[module].get("type") == "internal"
                        else "external"
                    )
                    python_insights.append(f"- **{module}** ({module_type}) is imported by {count} modules\n")
                python_insights.append("\n")

            result = parts[0] + "".join(python_insights) + "## Additional Insights" + parts[1]

        else:
            parts = base_summary.split("ADDITIONAL INSIGHTS:")

            python_insights = ["PYTHON-SPECIFIC INSIGHTS:\n"]
            python_insights.append("------------------------\n\n")

            python_insights.append("Dependency Types:\n")
            python_insights.append(f"- Standard library imports: {standard_lib_count}\n")
            python_insights.append(f"- Third-party library imports: {third_party_count}\n\n")

            if heavy_importers:
                python_insights.append("Modules with Most Dependencies:\n")
                for module, count in heavy_importers:
                    python_insights.append(f"- {module} imports {count} modules\n")
                python_insights.append("\n")

            if most_imported:
                python_insights.append("Most Commonly Used Modules:\n")
                for module, count in most_imported:
                    module_type = (
                        "internal"
                        if module in self.dependency_graph and self.dependency_graph[module].get("type") == "internal"
                        else "external"
                    )
                    python_insights.append(f"- {module} ({module_type}) is imported by {count} modules\n")
                python_insights.append("\n")

            result = parts[0] + "".join(python_insights) + "ADDITIONAL INSIGHTS:" + parts[1]

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result
