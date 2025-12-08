"""Analyzes and visualizes code dependencies within a JavaScript/TypeScript repository."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union

from .dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository

# Node.js built-in modules
NODE_BUILTIN_MODULES = {
    "assert",
    "async_hooks",
    "buffer",
    "child_process",
    "cluster",
    "console",
    "constants",
    "crypto",
    "dgram",
    "diagnostics_channel",
    "dns",
    "domain",
    "events",
    "fs",
    "http",
    "http2",
    "https",
    "inspector",
    "module",
    "net",
    "os",
    "path",
    "perf_hooks",
    "process",
    "punycode",
    "querystring",
    "readline",
    "repl",
    "stream",
    "string_decoder",
    "timers",
    "tls",
    "trace_events",
    "tty",
    "url",
    "util",
    "v8",
    "vm",
    "wasi",
    "worker_threads",
    "zlib",
}


class JavaScriptDependencyAnalyzer(DependencyAnalyzer):
    """
    Analyzes internal and external dependencies in a JavaScript/TypeScript codebase.

    This class provides functionality to:
    1. Build a dependency graph of modules within a repository
    2. Identify import relationships between files (ESM and CommonJS)
    3. Export dependency information in various formats
    4. Detect dependency cycles and other potential issues
    """

    # Color scheme for visualization
    _COLOR_MAP: ClassVar[Dict[str, str]] = {
        "internal": "lightblue",
        "node_builtin": "lightgray",
        "external": "lightgreen",
    }

    def __init__(self, repository: "Repository"):
        """
        Initialize the analyzer with a Repository instance.

        Args:
            repository: A kit.Repository instance
        """
        super().__init__(repository)
        self._package_name: Optional[str] = None
        self._package_json: Optional[Dict[str, Any]] = None
        self._file_map: Dict[str, str] = {}  # normalized path -> actual path

    def _parse_package_json(self) -> Optional[Dict[str, Any]]:
        """Parse package.json to get package info and dependencies."""
        try:
            content = self.repo.get_file_content("package.json")
            return json.loads(content)
        except Exception as e:
            logger.debug(f"Could not read package.json: {e}")
        return None

    def _extract_imports_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract import statements from a JS/TS file using TreeSitter.

        Args:
            file_path: Path to the file

        Returns:
            List of dicts with 'source' (import path) and 'type' (esm/cjs/dynamic)
        """
        imports = []
        try:
            from tree_sitter_language_pack import get_parser

            content = self.repo.get_file_content(file_path)

            # Determine language
            if file_path.endswith((".ts", ".tsx")):
                parser = get_parser("typescript")
            else:
                parser = get_parser("javascript")

            tree = parser.parse(content.encode("utf-8"))
            imports = self._extract_imports_from_tree(tree.root_node, content)

        except Exception as e:
            logger.warning(f"Error extracting imports from {file_path} with tree-sitter: {e}")
            # Fallback to regex
            imports = self._extract_imports_regex(file_path)

        return imports

    def _extract_imports_from_tree(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract imports by walking the tree-sitter AST."""
        imports = []

        def get_text(n) -> str:
            return content[n.start_byte : n.end_byte]

        def visit(n):
            # ESM: import x from 'source'
            if n.type == "import_statement":
                for child in n.children:
                    if child.type == "string":
                        source = get_text(child).strip("'\"")
                        imports.append({"source": source, "type": "esm"})

            # ESM: export { x } from 'source'
            elif n.type == "export_statement":
                for child in n.children:
                    if child.type == "string":
                        source = get_text(child).strip("'\"")
                        imports.append({"source": source, "type": "esm"})

            # CJS: require('source')
            elif n.type == "call_expression":
                func = n.child_by_field_name("function")
                args = n.child_by_field_name("arguments")
                if func and get_text(func) == "require" and args:
                    for arg in args.children:
                        if arg.type == "string":
                            source = get_text(arg).strip("'\"")
                            imports.append({"source": source, "type": "cjs"})

                # Also check for dynamic import: import('source')
                if func and func.type == "import":
                    for arg in args.children:
                        if arg.type == "string":
                            source = get_text(arg).strip("'\"")
                            imports.append({"source": source, "type": "dynamic"})

            for child in n.children:
                visit(child)

        visit(node)
        return imports

    def _extract_imports_regex(self, file_path: str) -> List[Dict[str, Any]]:
        """Fallback regex-based import extraction."""
        imports = []
        try:
            content = self.repo.get_file_content(file_path)

            # ESM imports: import ... from 'source' or import 'source'
            esm_pattern = r"""(?:import\s+(?:(?:\*\s+as\s+\w+|\{[^}]*\}|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+))?\s+from\s+)?['"]([^'"]+)['"])"""
            for match in re.finditer(esm_pattern, content):
                imports.append({"source": match.group(1), "type": "esm"})

            # ESM exports with source: export ... from 'source'
            export_pattern = r"""export\s+(?:\*|\{[^}]*\})\s+from\s+['"]([^'"]+)['"]"""
            for match in re.finditer(export_pattern, content):
                imports.append({"source": match.group(1), "type": "esm"})

            # CJS require: require('source')
            cjs_pattern = r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""
            for match in re.finditer(cjs_pattern, content):
                imports.append({"source": match.group(1), "type": "cjs"})

            # Dynamic import: import('source')
            dynamic_pattern = r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""
            for match in re.finditer(dynamic_pattern, content):
                imports.append({"source": match.group(1), "type": "dynamic"})

        except Exception as e:
            logger.warning(f"Error in regex import extraction from {file_path}: {e}")

        return imports

    def _resolve_import(self, import_source: str, from_file: str) -> tuple[str, str]:
        """
        Resolve an import source to a module identifier and classify it.

        Args:
            import_source: The import path (e.g., './utils', 'lodash', 'fs')
            from_file: The file containing the import

        Returns:
            Tuple of (resolved_module_id, type) where type is 'internal', 'node_builtin', or 'external'
        """
        # Handle node: protocol
        if import_source.startswith("node:"):
            module_name = import_source[5:]
            return module_name, "node_builtin"

        # Check for Node.js built-in
        base_module = import_source.split("/")[0]
        if base_module in NODE_BUILTIN_MODULES:
            return base_module, "node_builtin"

        # Relative imports are internal
        if import_source.startswith("./") or import_source.startswith("../"):
            # Resolve to absolute-ish path
            from_dir = os.path.dirname(from_file)
            resolved = os.path.normpath(os.path.join(from_dir, import_source))
            # Normalize path separators
            resolved = resolved.replace("\\", "/")
            return resolved, "internal"

        # Check for scoped packages (@org/pkg)
        if import_source.startswith("@"):
            parts = import_source.split("/")
            if len(parts) >= 2:
                package_name = f"{parts[0]}/{parts[1]}"
            else:
                package_name = import_source
            return package_name, "external"

        # Regular package import
        package_name = import_source.split("/")[0]
        return package_name, "external"

    def _build_file_map(self, js_ts_files: List[Dict[str, Any]]):
        """Build a map of file paths for resolving imports."""
        for file_info in js_ts_files:
            path = file_info["path"]
            # Store with and without extension for resolution
            self._file_map[path] = path
            # Also store without extension
            for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
                if path.endswith(ext):
                    no_ext = path[: -len(ext)]
                    self._file_map[no_ext] = path
                    break
            # Handle index files - map directory to index file
            basename = os.path.basename(path)
            if basename.startswith("index."):
                dir_path = os.path.dirname(path)
                if dir_path not in self._file_map:
                    self._file_map[dir_path] = path

    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph, where:
            - Keys are module identifiers (file paths for internal, package names for external)
            - Values are dictionaries containing:
                - 'type': 'internal', 'node_builtin', or 'external'
                - 'path': File path (for internal modules)
                - 'dependencies': Set of module identifiers this module depends on
        """
        self.dependency_graph = {}
        self._file_map = {}

        # Parse package.json
        self._package_json = self._parse_package_json()
        if self._package_json:
            self._package_name = self._package_json.get("name")

        # Get all JS/TS files
        file_tree = self.repo.get_file_tree()
        js_ts_files = [
            f
            for f in file_tree
            if f["path"].endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"))
            and "node_modules" not in f["path"]
            and not f["path"].endswith(".d.ts")  # Skip declaration files
        ]

        self._build_file_map(js_ts_files)

        # Process each file
        for file_info in js_ts_files:
            file_path = file_info["path"]

            # Initialize node in graph
            if file_path not in self.dependency_graph:
                self.dependency_graph[file_path] = {
                    "type": "internal",
                    "path": file_path,
                    "dependencies": set(),
                }

            # Extract imports
            imports = self._extract_imports_from_file(file_path)
            for imp in imports:
                source = imp["source"]
                resolved, dep_type = self._resolve_import(source, file_path)

                # For internal imports, try to resolve to actual file path
                if dep_type == "internal":
                    actual_path = self._file_map.get(resolved)
                    if actual_path:
                        resolved = actual_path

                # Add to dependencies
                self.dependency_graph[file_path]["dependencies"].add(resolved)

                # Add dependency node to graph if not present
                if resolved not in self.dependency_graph:
                    self.dependency_graph[resolved] = {
                        "type": dep_type,
                        "path": resolved if dep_type == "internal" else None,
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
        for module, data in self.dependency_graph.items():
            serializable_graph[module] = {
                "type": data["type"],
                "path": data["path"],
                "dependencies": list(data["dependencies"]),
            }

        if output_format == "json":
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
            node_color = self._COLOR_MAP.get(data["type"], "white")
            safe_module = module.replace('"', '\\"')
            # Use short name for display
            if "/" in module:
                short_name = module.split("/")[-1]
            else:
                short_name = module
            dot_lines.append(f'  "{safe_module}" [label="{short_name}", style=filled, fillcolor={node_color}];')

        # Add edges (only from internal modules to keep graph manageable)
        for module, data in graph.items():
            if data["type"] != "internal":
                continue
            safe_module = module.replace('"', '\\"')
            for dep in data["dependencies"]:
                if dep in graph:
                    safe_dep = dep.replace('"', '\\"')
                    dot_lines.append(f'  "{safe_module}" -> "{safe_dep}";')

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
        for module, data in graph.items():
            safe_module = xml_escape(module)
            graphml_lines.append(f'  <node id="{safe_module}">')
            graphml_lines.append(f'    <data key="type">{data["type"]}</data>')
            if data["path"]:
                safe_path = xml_escape(data["path"])
                graphml_lines.append(f'    <data key="path">{safe_path}</data>')
            graphml_lines.append("  </node>")

        # Add edges
        edge_id = 0
        for module, data in graph.items():
            safe_module = xml_escape(module)
            for dep in data["dependencies"]:
                if dep in graph:
                    safe_dep = xml_escape(dep)
                    graphml_lines.append(f'  <edge id="e{edge_id}" source="{safe_module}" target="{safe_dep}"/>')
                    edge_id += 1

        graphml_lines.append("</graph>")
        graphml_lines.append("</graphml>")
        return "\n".join(graphml_lines)

    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of module identifiers
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
                    cycle = [*path[cycle_start:], module]
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

    def get_dependencies(self, item: str, include_indirect: bool = False) -> List[str]:
        """
        Get dependencies for a specific component.

        Args:
            item: Path to the module file
            include_indirect: Whether to include indirect dependencies

        Returns:
            List of module identifiers this module depends on
        """
        return self.get_module_dependencies(item, include_indirect)

    def get_module_dependencies(self, module_path: str, include_indirect: bool = False) -> List[str]:
        """
        Get dependencies for a specific module.

        Args:
            module_path: Path to the module file
            include_indirect: Whether to include indirect dependencies

        Returns:
            List of module identifiers this module depends on
        """
        if not self._initialized:
            self.build_dependency_graph()

        if module_path not in self.dependency_graph:
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

            dfs(module_path)
            return list(all_deps)
        else:
            return [dep for dep in self.dependency_graph[module_path]["dependencies"] if dep in self.dependency_graph]

    def get_dependents(self, module_path: str, include_indirect: bool = False) -> List[str]:
        """
        Get modules that depend on the specified module.

        Args:
            module_path: Path to the module file
            include_indirect: Whether to include indirect dependents

        Returns:
            List of module identifiers that depend on this module
        """
        if not self._initialized:
            self.build_dependency_graph()

        if module_path not in self.dependency_graph:
            return []

        direct_dependents = [mod for mod, data in self.dependency_graph.items() if module_path in data["dependencies"]]

        if not include_indirect:
            return direct_dependents

        all_dependents = set(direct_dependents)

        def find_ancestors(module):
            parents = [
                m
                for m, data in self.dependency_graph.items()
                if module in data["dependencies"] and m not in all_dependents
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

        dot = graphviz.Digraph("dependencies", comment="Module Dependencies", format=format, engine="dot")
        dot.attr(rankdir="LR")

        for module, data in self.dependency_graph.items():
            if data["type"] != "internal":
                continue

            # Use short name for label
            if "/" in module:
                label = module.split("/")[-1]
            else:
                label = module

            dot.node(
                module,
                label=label,
                tooltip=module,
                style="filled",
                fillcolor=self._COLOR_MAP.get(data["type"], "white"),
                shape="box",
            )

        for module, data in self.dependency_graph.items():
            if data["type"] != "internal":
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
        Generate a JavaScript/TypeScript-specific description of the dependency graph.

        Args:
            max_tokens: Approximate maximum number of tokens in the output
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description
        """
        base_summary = super().generate_llm_context(max_tokens, output_format, None)

        # Count by type
        internal_count = len([m for m, d in self.dependency_graph.items() if d["type"] == "internal"])
        builtin_count = len([m for m, d in self.dependency_graph.items() if d["type"] == "node_builtin"])
        external_count = len([m for m, d in self.dependency_graph.items() if d["type"] == "external"])

        # Find modules with most imports
        heavy_importers = sorted(
            [(m, len(d["dependencies"])) for m, d in self.dependency_graph.items() if d["type"] == "internal"],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Find most imported modules
        import_counts: Dict[str, int] = {}
        for m, d in self.dependency_graph.items():
            if d["type"] == "internal":
                for dep in d["dependencies"]:
                    import_counts[dep] = import_counts.get(dep, 0) + 1

        most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Categorize external dependencies
        external_deps = [m for m, d in self.dependency_graph.items() if d["type"] == "external"]

        if output_format == "markdown":
            parts = base_summary.split("## Additional Insights")

            js_insights = ["## JavaScript/TypeScript-Specific Insights\n"]
            if self._package_name:
                js_insights.append(f"\n**Package:** `{self._package_name}`\n\n")

            js_insights.append("### Dependency Types\n")
            js_insights.append(f"- Internal modules: {internal_count}\n")
            js_insights.append(f"- Node.js built-ins: {builtin_count}\n")
            js_insights.append(f"- External packages: {external_count}\n\n")

            if heavy_importers:
                js_insights.append("### Modules with Most Imports\n")
                for module, count in heavy_importers:
                    short_name = module.split("/")[-1] if "/" in module else module
                    js_insights.append(f"- **{short_name}** imports {count} modules\n")
                js_insights.append("\n")

            if most_imported:
                js_insights.append("### Most Commonly Imported\n")
                for module, count in most_imported:
                    module_type = self.dependency_graph.get(module, {}).get("type", "external")
                    short_name = module.split("/")[-1] if "/" in module else module
                    js_insights.append(f"- **{short_name}** ({module_type}) imported by {count} modules\n")
                js_insights.append("\n")

            if external_deps:
                js_insights.append("### External Dependencies\n")
                for dep in sorted(external_deps)[:10]:
                    js_insights.append(f"- `{dep}`\n")
                if len(external_deps) > 10:
                    js_insights.append(f"- ...and {len(external_deps) - 10} more\n")
                js_insights.append("\n")

            result = parts[0] + "".join(js_insights) + "## Additional Insights" + parts[1]

        else:
            parts = base_summary.split("ADDITIONAL INSIGHTS:")

            js_insights = ["JAVASCRIPT/TYPESCRIPT-SPECIFIC INSIGHTS:\n"]
            js_insights.append("----------------------------------------\n\n")
            if self._package_name:
                js_insights.append(f"Package: {self._package_name}\n\n")

            js_insights.append("Dependency Types:\n")
            js_insights.append(f"- Internal modules: {internal_count}\n")
            js_insights.append(f"- Node.js built-ins: {builtin_count}\n")
            js_insights.append(f"- External packages: {external_count}\n\n")

            if heavy_importers:
                js_insights.append("Modules with Most Imports:\n")
                for module, count in heavy_importers:
                    short_name = module.split("/")[-1] if "/" in module else module
                    js_insights.append(f"- {short_name} imports {count} modules\n")
                js_insights.append("\n")

            if most_imported:
                js_insights.append("Most Commonly Imported:\n")
                for module, count in most_imported:
                    module_type = self.dependency_graph.get(module, {}).get("type", "external")
                    short_name = module.split("/")[-1] if "/" in module else module
                    js_insights.append(f"- {short_name} ({module_type}) imported by {count} modules\n")
                js_insights.append("\n")

            if external_deps:
                js_insights.append("External Dependencies:\n")
                for dep in sorted(external_deps)[:10]:
                    js_insights.append(f"- {dep}\n")
                if len(external_deps) > 10:
                    js_insights.append(f"- ...and {len(external_deps) - 10} more\n")
                js_insights.append("\n")

            result = parts[0] + "".join(js_insights) + "ADDITIONAL INSIGHTS:" + parts[1]

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result

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
        builtin_modules = [m for m, data in self.dependency_graph.items() if data["type"] == "node_builtin"]

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
                "package_name": self._package_name,
                "total_modules": len(self.dependency_graph),
                "internal_modules": len(internal_modules),
                "external_packages": len(external_modules),
                "node_builtins": len(builtin_modules),
                "dependency_cycles": len(cycles),
            },
            "cycles": cycles,
            "high_dependency_modules": sorted(
                high_dependency_modules, key=lambda x: x["dependent_count"] + x["dependency_count"], reverse=True
            ),
            "external_dependencies": sorted(external_modules),
            "node_builtins_used": sorted(builtin_modules),
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report
