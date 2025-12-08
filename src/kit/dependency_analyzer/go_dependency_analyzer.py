"""Analyzes and visualizes code dependencies within a Go repository."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository

# Common Go standard library packages (top-level)
GO_STDLIB_PACKAGES = {
    "archive",
    "bufio",
    "builtin",
    "bytes",
    "cmp",
    "compress",
    "container",
    "context",
    "crypto",
    "database",
    "debug",
    "embed",
    "encoding",
    "errors",
    "expvar",
    "flag",
    "fmt",
    "go",
    "hash",
    "html",
    "image",
    "index",
    "io",
    "iter",
    "log",
    "maps",
    "math",
    "mime",
    "net",
    "os",
    "path",
    "plugin",
    "reflect",
    "regexp",
    "runtime",
    "slices",
    "sort",
    "strconv",
    "strings",
    "structs",
    "sync",
    "syscall",
    "testing",
    "text",
    "time",
    "unicode",
    "unique",
    "unsafe",
}


class GoDependencyAnalyzer(DependencyAnalyzer):
    """
    Analyzes internal and external dependencies in a Go codebase.

    This class provides functionality to:
    1. Build a dependency graph of packages within a Go module
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
        self._module_path: Optional[str] = None
        self._package_map: Dict[str, str] = {}  # package import path -> directory

    def _parse_go_mod(self) -> Optional[str]:
        """Parse go.mod to find the module path."""
        try:
            content = self.repo.get_file_content("go.mod")
            # Match: module github.com/user/repo
            match = re.search(r"^\s*module\s+(\S+)", content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception as e:
            logger.debug(f"Could not read go.mod: {e}")
        return None

    def _extract_imports_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract import statements from a Go file using TreeSitter.

        Args:
            file_path: Path to the Go file

        Returns:
            List of dicts with 'path' and 'alias' keys
        """
        imports = []
        try:
            from tree_sitter_language_pack import get_parser

            content = self.repo.get_file_content(file_path)
            parser = get_parser("go")
            tree = parser.parse(content.encode("utf-8"))

            # Walk the tree to find import declarations
            def visit_node(node):
                if node.type == "import_declaration":
                    # Handle both single imports and import blocks
                    for child in node.children:
                        if child.type == "import_spec":
                            import_info = self._parse_import_spec(child, content)
                            if import_info:
                                imports.append(import_info)
                        elif child.type == "import_spec_list":
                            for spec in child.children:
                                if spec.type == "import_spec":
                                    import_info = self._parse_import_spec(spec, content)
                                    if import_info:
                                        imports.append(import_info)
                else:
                    for child in node.children:
                        visit_node(child)

            visit_node(tree.root_node)

        except Exception as e:
            logger.warning(f"Error extracting imports from {file_path}: {e}")
            # Fallback to regex-based parsing
            imports = self._extract_imports_regex(file_path)

        return imports

    def _parse_import_spec(self, node, content: str) -> Optional[Dict[str, Any]]:
        """Parse a single import_spec node."""
        alias = None
        path = None

        for child in node.children:
            if child.type == "package_identifier" or child.type == "dot" or child.type == "blank_identifier":
                alias = content[child.start_byte : child.end_byte]
            elif child.type == "interpreted_string_literal":
                # Remove quotes
                path = content[child.start_byte : child.end_byte].strip('"')

        if path:
            return {"path": path, "alias": alias}
        return None

    def _extract_imports_regex(self, file_path: str) -> List[Dict[str, Any]]:
        """Fallback regex-based import extraction."""
        imports = []
        try:
            content = self.repo.get_file_content(file_path)

            # Match single imports: import "path" or import alias "path"
            single_pattern = r'import\s+(?:(\w+|\.)\s+)?"([^"]+)"'
            for match in re.finditer(single_pattern, content):
                alias = match.group(1)
                path = match.group(2)
                imports.append({"path": path, "alias": alias})

            # Match import blocks
            block_pattern = r"import\s*\((.*?)\)"
            for block_match in re.finditer(block_pattern, content, re.DOTALL):
                block_content = block_match.group(1)
                # Match each import in the block
                spec_pattern = r'(?:(\w+|\.)\s+)?"([^"]+)"'
                for spec_match in re.finditer(spec_pattern, block_content):
                    alias = spec_match.group(1)
                    path = spec_match.group(2)
                    imports.append({"path": path, "alias": alias})

        except Exception as e:
            logger.warning(f"Error in regex import extraction from {file_path}: {e}")

        return imports

    def _get_package_name(self, file_path: str) -> Optional[str]:
        """Extract the package name from a Go file."""
        try:
            content = self.repo.get_file_content(file_path)
            match = re.search(r"^\s*package\s+(\w+)", content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception as e:
            logger.debug(f"Could not extract package name from {file_path}: {e}")
        return None

    def _classify_import(self, import_path: str) -> str:
        """
        Classify an import as 'internal', 'stdlib', or 'external'.

        Args:
            import_path: The Go import path

        Returns:
            'internal', 'stdlib', or 'external'
        """
        # Check if it's a standard library import
        top_level = import_path.split("/")[0]
        if top_level in GO_STDLIB_PACKAGES:
            return "stdlib"

        # Check if it's an internal import (matches module path)
        if self._module_path and import_path.startswith(self._module_path):
            return "internal"

        # Everything else is external
        return "external"

    def _build_package_map(self):
        """Build a map of internal package paths to their directories."""
        if not self._module_path:
            return

        for file_info in self.repo.get_file_tree():
            if not file_info["path"].endswith(".go"):
                continue
            if "_test.go" in file_info["path"]:
                continue

            dir_path = os.path.dirname(file_info["path"])
            if dir_path == "":
                dir_path = "."

            # Construct the import path for this directory
            if dir_path == ".":
                import_path = self._module_path
            else:
                import_path = f"{self._module_path}/{dir_path}"

            if import_path not in self._package_map:
                self._package_map[import_path] = dir_path

    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph, where:
            - Keys are package import paths
            - Values are dictionaries containing:
                - 'type': 'internal', 'stdlib', or 'external'
                - 'path': Directory path (for internal packages)
                - 'dependencies': Set of package import paths this package depends on
        """
        self.dependency_graph = {}
        self._package_map = {}

        # Parse go.mod to get module path
        self._module_path = self._parse_go_mod()
        if not self._module_path:
            logger.warning("No go.mod found or could not parse module path")

        # Build map of internal packages
        self._build_package_map()

        # Process each Go file
        for file_info in self.repo.get_file_tree():
            if not file_info["path"].endswith(".go"):
                continue
            if "_test.go" in file_info["path"]:
                continue

            dir_path = os.path.dirname(file_info["path"])
            if dir_path == "":
                dir_path = "."

            # Determine import path for this package
            if self._module_path:
                if dir_path == ".":
                    pkg_import_path = self._module_path
                else:
                    pkg_import_path = f"{self._module_path}/{dir_path}"
            else:
                pkg_import_path = dir_path if dir_path != "." else "main"

            # Initialize package in graph if needed
            if pkg_import_path not in self.dependency_graph:
                self.dependency_graph[pkg_import_path] = {
                    "type": "internal",
                    "path": dir_path,
                    "dependencies": set(),
                }

            # Extract and add imports
            imports = self._extract_imports_from_file(file_info["path"])
            for imp in imports:
                import_path = imp["path"]
                self.dependency_graph[pkg_import_path]["dependencies"].add(import_path)

                # Add the dependency to the graph if not present
                if import_path not in self.dependency_graph:
                    import_type = self._classify_import(import_path)
                    dep_dir = self._package_map.get(import_path)
                    self.dependency_graph[import_path] = {
                        "type": import_type,
                        "path": dep_dir,
                        "dependencies": set(),
                    }

        self._initialized = True
        return self.dependency_graph

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

        # Convert sets to lists for serialization
        serializable_graph = {}
        for pkg, data in self.dependency_graph.items():
            serializable_graph[pkg] = {
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
            for pkg, data in serializable_graph.items():
                adjacency_list[pkg] = data["dependencies"]

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

        # Color scheme: internal=lightblue, stdlib=lightgray, external=lightgreen
        color_map = {
            "internal": "lightblue",
            "stdlib": "lightgray",
            "external": "lightgreen",
        }

        # Add nodes
        for pkg, data in graph.items():
            node_color = color_map.get(data["type"], "white")
            safe_pkg = pkg.replace('"', '\\"')
            # Use short name for display
            short_name = pkg.split("/")[-1] if "/" in pkg else pkg
            dot_lines.append(f'  "{safe_pkg}" [label="{short_name}", style=filled, fillcolor={node_color}];')

        # Add edges (only for internal packages to keep graph manageable)
        for pkg, data in graph.items():
            if data["type"] != "internal":
                continue
            safe_pkg = pkg.replace('"', '\\"')
            for dep in data["dependencies"]:
                if dep in graph:
                    safe_dep = dep.replace('"', '\\"')
                    dot_lines.append(f'  "{safe_pkg}" -> "{safe_dep}";')

        dot_lines.append("}")
        return "\n".join(dot_lines)

    def _generate_graphml_file(self, graph: Dict[str, Dict[str, Any]]) -> str:
        """Generate a GraphML file for visualization."""
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

        def xml_escape(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        # Add nodes
        for pkg, data in graph.items():
            safe_pkg = xml_escape(pkg)
            graphml_lines.append(f'  <node id="{safe_pkg}">')
            graphml_lines.append(f'    <data key="type">{data["type"]}</data>')
            if data["path"]:
                safe_path = xml_escape(data["path"])
                graphml_lines.append(f'    <data key="path">{safe_path}</data>')
            graphml_lines.append("  </node>")

        # Add edges
        edge_id = 0
        for pkg, data in graph.items():
            safe_pkg = xml_escape(pkg)
            for dep in data["dependencies"]:
                if dep in graph:
                    safe_dep = xml_escape(dep)
                    graphml_lines.append(f'  <edge id="e{edge_id}" source="{safe_pkg}" target="{safe_dep}"/>')
                    edge_id += 1

        graphml_lines.append("</graph>")
        graphml_lines.append("</graphml>")
        return "\n".join(graphml_lines)

    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of package import paths
        """
        if not self._initialized:
            self.build_dependency_graph()

        cycles = []

        for start_pkg in self.dependency_graph:
            if self.dependency_graph[start_pkg]["type"] != "internal":
                continue

            path: List[str] = []
            visited = set()

            def dfs(pkg):
                if pkg in path:
                    cycle_start = path.index(pkg)
                    cycle = [*path[cycle_start:], pkg]
                    if cycle not in cycles and len(cycle) > 1:
                        cycles.append(cycle)
                    return

                if pkg in visited or pkg not in self.dependency_graph:
                    return

                visited.add(pkg)
                path.append(pkg)

                for dep in self.dependency_graph[pkg]["dependencies"]:
                    if self.dependency_graph.get(dep, {}).get("type") == "internal":
                        dfs(dep)

                path.pop()

            dfs(start_pkg)

        return cycles

    def get_package_dependencies(self, package_path: str, include_indirect: bool = False) -> List[str]:
        """
        Get dependencies for a specific package.

        Args:
            package_path: Import path of the package
            include_indirect: Whether to include indirect dependencies

        Returns:
            List of package import paths this package depends on
        """
        if not self._initialized:
            self.build_dependency_graph()

        if package_path not in self.dependency_graph:
            return []

        if include_indirect:
            all_deps = set()
            visited = set()

            def dfs(pkg):
                if pkg in visited or pkg not in self.dependency_graph:
                    return
                visited.add(pkg)
                for dep in self.dependency_graph[pkg]["dependencies"]:
                    if dep in self.dependency_graph:
                        all_deps.add(dep)
                        dfs(dep)

            dfs(package_path)
            return list(all_deps)
        else:
            return [dep for dep in self.dependency_graph[package_path]["dependencies"] if dep in self.dependency_graph]

    def get_dependents(self, package_path: str, include_indirect: bool = False) -> List[str]:
        """
        Get packages that depend on the specified package.

        Args:
            package_path: Import path of the package
            include_indirect: Whether to include indirect dependents

        Returns:
            List of package import paths that depend on this package
        """
        if not self._initialized:
            self.build_dependency_graph()

        if package_path not in self.dependency_graph:
            return []

        direct_dependents = [pkg for pkg, data in self.dependency_graph.items() if package_path in data["dependencies"]]

        if not include_indirect:
            return direct_dependents

        all_dependents = set(direct_dependents)

        def find_ancestors(pkg):
            parents = [
                p
                for p, data in self.dependency_graph.items()
                if pkg in data["dependencies"] and p not in all_dependents
            ]
            for parent in parents:
                all_dependents.add(parent)
                find_ancestors(parent)

        for dep in direct_dependents:
            find_ancestors(dep)

        return list(all_dependents)

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

        dot = graphviz.Digraph("dependencies", comment="Package Dependencies", format=format, engine="dot")
        dot.attr(rankdir="LR")

        # Color scheme
        color_map = {
            "internal": "lightblue",
            "stdlib": "lightgray",
            "external": "lightgreen",
        }

        for pkg, data in self.dependency_graph.items():
            if data["type"] != "internal":
                continue

            # Use short name for label
            if "/" in pkg:
                label = pkg.split("/")[-1]
            else:
                label = pkg

            dot.node(
                pkg,
                label=label,
                tooltip=pkg,
                style="filled",
                fillcolor=color_map.get(data["type"], "white"),
                shape="box",
            )

        for pkg, data in self.dependency_graph.items():
            if data["type"] != "internal":
                continue

            for dep in data["dependencies"]:
                if dep in self.dependency_graph and self.dependency_graph[dep]["type"] == "internal":
                    dot.edge(pkg, dep)

        dot.render(output_path, cleanup=True)
        return f"{output_path}.{format}"

    def generate_llm_context(
        self, max_tokens: int = 4000, output_format: str = "markdown", output_path: Optional[str] = None
    ) -> str:
        """
        Generate a Go-specific natural language description of the dependency graph.

        Args:
            max_tokens: Approximate maximum number of tokens in the output
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description
        """
        base_summary = super().generate_llm_context(max_tokens, output_format, None)

        # Count by type
        internal_count = len([p for p, d in self.dependency_graph.items() if d["type"] == "internal"])
        stdlib_count = len([p for p, d in self.dependency_graph.items() if d["type"] == "stdlib"])
        external_count = len([p for p, d in self.dependency_graph.items() if d["type"] == "external"])

        # Find packages with most imports
        heavy_importers = sorted(
            [(p, len(d["dependencies"])) for p, d in self.dependency_graph.items() if d["type"] == "internal"],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Find most imported packages
        import_counts: Dict[str, int] = {}
        for p, d in self.dependency_graph.items():
            if d["type"] == "internal":
                for dep in d["dependencies"]:
                    import_counts[dep] = import_counts.get(dep, 0) + 1

        most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        if output_format == "markdown":
            parts = base_summary.split("## Additional Insights")

            go_insights = ["## Go-Specific Insights\n"]
            go_insights.append(f"\n**Module:** `{self._module_path or 'unknown'}`\n\n")

            go_insights.append("### Dependency Types\n")
            go_insights.append(f"- Internal packages: {internal_count}\n")
            go_insights.append(f"- Standard library imports: {stdlib_count}\n")
            go_insights.append(f"- External dependencies: {external_count}\n\n")

            if heavy_importers:
                go_insights.append("### Packages with Most Imports\n")
                for pkg, count in heavy_importers:
                    short_name = pkg.split("/")[-1] if "/" in pkg else pkg
                    go_insights.append(f"- **{short_name}** imports {count} packages\n")
                go_insights.append("\n")

            if most_imported:
                go_insights.append("### Most Commonly Imported\n")
                for pkg, count in most_imported:
                    pkg_type = self.dependency_graph.get(pkg, {}).get("type", "external")
                    short_name = pkg.split("/")[-1] if "/" in pkg else pkg
                    go_insights.append(f"- **{short_name}** ({pkg_type}) imported by {count} packages\n")
                go_insights.append("\n")

            result = parts[0] + "".join(go_insights) + "## Additional Insights" + parts[1]

        else:
            parts = base_summary.split("ADDITIONAL INSIGHTS:")

            go_insights = ["GO-SPECIFIC INSIGHTS:\n"]
            go_insights.append("--------------------\n\n")
            go_insights.append(f"Module: {self._module_path or 'unknown'}\n\n")

            go_insights.append("Dependency Types:\n")
            go_insights.append(f"- Internal packages: {internal_count}\n")
            go_insights.append(f"- Standard library imports: {stdlib_count}\n")
            go_insights.append(f"- External dependencies: {external_count}\n\n")

            if heavy_importers:
                go_insights.append("Packages with Most Imports:\n")
                for pkg, count in heavy_importers:
                    short_name = pkg.split("/")[-1] if "/" in pkg else pkg
                    go_insights.append(f"- {short_name} imports {count} packages\n")
                go_insights.append("\n")

            if most_imported:
                go_insights.append("Most Commonly Imported:\n")
                for pkg, count in most_imported:
                    pkg_type = self.dependency_graph.get(pkg, {}).get("type", "external")
                    short_name = pkg.split("/")[-1] if "/" in pkg else pkg
                    go_insights.append(f"- {short_name} ({pkg_type}) imported by {count} packages\n")
                go_insights.append("\n")

            result = parts[0] + "".join(go_insights) + "ADDITIONAL INSIGHTS:" + parts[1]

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result
