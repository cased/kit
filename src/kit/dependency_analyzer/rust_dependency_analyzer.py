"""Analyzes and visualizes code dependencies within a Rust repository."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union

# Use tomllib (3.11+) or tomli (3.10)
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository

# Rust standard library crates
RUST_STD_CRATES = {
    "std",
    "core",
    "alloc",
    "proc_macro",
    "test",
}


class RustDependencyAnalyzer(DependencyAnalyzer):
    """
    Analyzes internal and external dependencies in a Rust codebase.

    This class provides functionality to:
    1. Build a dependency graph of modules within a Rust crate
    2. Identify use/mod relationships between files
    3. Export dependency information in various formats
    4. Detect dependency cycles and other potential issues
    """

    # Color scheme for visualization
    _COLOR_MAP: ClassVar[Dict[str, str]] = {
        "internal": "lightblue",
        "std": "lightgray",
        "external": "lightgreen",
    }

    def __init__(self, repository: "Repository"):
        """
        Initialize the analyzer with a Repository instance.

        Args:
            repository: A kit.Repository instance
        """
        super().__init__(repository)
        self._crate_name: Optional[str] = None
        self._cargo_toml: Optional[Dict[str, Any]] = None
        self._file_map: Dict[str, str] = {}  # module path -> file path
        self._external_crates: set[str] = set()
        self._workspace_members: Dict[str, str] = {}  # crate name -> path

    def _parse_cargo_toml(self) -> Optional[Dict[str, Any]]:
        """Parse Cargo.toml to get crate info and dependencies."""
        try:
            content = self.repo.get_file_content("Cargo.toml")
            return tomllib.loads(content)
        except Exception as e:
            logger.debug(f"Could not parse Cargo.toml: {e}")
        return None

    def _parse_toml_file(self, path: str) -> Optional[Dict[str, Any]]:
        """Parse a TOML file at the given path."""
        try:
            content = self.repo.get_file_content(path)
            return tomllib.loads(content)
        except Exception as e:
            logger.debug(f"Could not parse {path}: {e}")
        return None

    def _get_external_crates(self) -> set[str]:
        """Get all external crate names from Cargo.toml."""
        crates = set()
        if self._cargo_toml:
            for section in ["dependencies", "dev-dependencies", "build-dependencies"]:
                if section in self._cargo_toml:
                    crates.update(self._cargo_toml[section].keys())
        return crates

    def _expand_glob_pattern(self, pattern: str) -> List[str]:
        """Expand a glob pattern like 'crates/*' to actual paths."""
        import fnmatch

        if "*" not in pattern and "?" not in pattern:
            return [pattern]

        # Get all directories that match the pattern
        matches = []
        file_tree = self.repo.get_file_tree()

        # Get unique directories from file tree
        dirs = set()
        for f in file_tree:
            path = f["path"]
            # Get parent directories
            parts = path.split("/")
            for i in range(1, len(parts)):
                dirs.add("/".join(parts[:i]))

        for dir_path in dirs:
            if fnmatch.fnmatch(dir_path, pattern):
                matches.append(dir_path)

        return sorted(matches)

    def _parse_workspace(self) -> Dict[str, str]:
        """
        Parse workspace members from root Cargo.toml.

        Returns:
            Dict mapping crate name to its path
        """
        members: Dict[str, str] = {}
        if not self._cargo_toml:
            return members

        workspace = self._cargo_toml.get("workspace", {})
        if not isinstance(workspace, dict):
            return members

        # Get members list (proper TOML parser returns a list)
        member_paths = workspace.get("members", [])
        if not isinstance(member_paths, list):
            return members

        # Expand globs and parse each member's Cargo.toml
        expanded_paths: List[str] = []
        for pattern in member_paths:
            expanded_paths.extend(self._expand_glob_pattern(pattern))

        for member_path in expanded_paths:
            member_toml_path = f"{member_path}/Cargo.toml"
            parsed = self._parse_toml_file(member_toml_path)
            if parsed:
                package = parsed.get("package", {})
                if isinstance(package, dict):
                    name = package.get("name")
                    if name:
                        members[name] = member_path
                        # Also collect this member's external dependencies
                        for section in ["dependencies", "dev-dependencies", "build-dependencies"]:
                            if section in parsed:
                                self._external_crates.update(parsed[section].keys())

        return members

    def _extract_imports_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract use statements from a Rust file using TreeSitter.

        Args:
            file_path: Path to the file

        Returns:
            List of dicts with 'path' (use path) and 'type' (use/mod)
        """
        imports = []
        try:
            from tree_sitter_language_pack import get_parser

            content = self.repo.get_file_content(file_path)
            parser = get_parser("rust")
            tree = parser.parse(content.encode("utf-8"))
            imports = self._extract_imports_from_tree(tree.root_node, content)

        except Exception as e:
            logger.warning(f"Error extracting imports from {file_path} with tree-sitter: {e}")
            imports = self._extract_imports_regex(file_path)

        return imports

    def _extract_imports_from_tree(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract imports by walking the tree-sitter AST."""
        imports = []

        def get_text(n) -> str:
            return content[n.start_byte : n.end_byte]

        def visit(n):
            # use statements: use std::collections::HashMap;
            if n.type == "use_declaration":
                # Find the use path
                for child in n.children:
                    if child.type in ("scoped_identifier", "identifier", "use_wildcard", "scoped_use_list"):
                        full_path = get_text(child)
                        # Split path and extract the relevant module
                        parts = full_path.split("::")
                        # Handle crate::/self::/super:: - get the next segment
                        if parts[0] in ("crate", "self", "super") and len(parts) > 1:
                            path = parts[1]
                            imports.append({"path": path, "type": "use_internal"})
                        else:
                            path = parts[0]
                            imports.append({"path": path, "type": "use"})
                        break

            # mod declarations: mod foo;
            elif n.type == "mod_item":
                for child in n.children:
                    if child.type == "identifier":
                        mod_name = get_text(child)
                        imports.append({"path": mod_name, "type": "mod"})
                        break

            # extern crate declarations (older style)
            elif n.type == "extern_crate_declaration":
                for child in n.children:
                    if child.type == "identifier":
                        crate_name = get_text(child)
                        imports.append({"path": crate_name, "type": "extern"})
                        break

            for child in n.children:
                visit(child)

        visit(node)
        return imports

    def _extract_imports_regex(self, file_path: str) -> List[Dict[str, Any]]:
        """Fallback regex-based import extraction."""
        imports = []
        try:
            content = self.repo.get_file_content(file_path)

            # use statements: use foo::bar; or pub use foo::bar;
            # Also captures crate::foo::bar, self::foo, super::foo
            use_pattern = r"^\s*(?:pub\s+)?use\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:::([a-zA-Z_][a-zA-Z0-9_]*))?"
            for match in re.finditer(use_pattern, content, re.MULTILINE):
                first_segment = match.group(1)
                second_segment = match.group(2)
                # Handle crate::/self::/super:: - get the next segment
                if first_segment in ("crate", "self", "super") and second_segment:
                    imports.append({"path": second_segment, "type": "use_internal"})
                else:
                    imports.append({"path": first_segment, "type": "use"})

            # mod declarations: mod foo;
            mod_pattern = r"^\s*(?:pub\s+)?mod\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;"
            for match in re.finditer(mod_pattern, content, re.MULTILINE):
                imports.append({"path": match.group(1), "type": "mod"})

            # extern crate: extern crate foo;
            extern_pattern = r"^\s*extern\s+crate\s+([a-zA-Z_][a-zA-Z0-9_]*)"
            for match in re.finditer(extern_pattern, content, re.MULTILINE):
                imports.append({"path": match.group(1), "type": "extern"})

        except Exception as e:
            logger.warning(f"Error in regex import extraction from {file_path}: {e}")

        return imports

    def _resolve_import(self, import_path: str, import_type: str) -> tuple[str, str]:
        """
        Resolve an import path and classify it.

        Args:
            import_path: The crate/module name
            import_type: 'use', 'use_internal', 'mod', or 'extern'

        Returns:
            Tuple of (resolved_id, type) where type is 'internal', 'std', or 'external'
        """
        # use_internal comes from crate::/self::/super:: paths - always internal
        if import_type == "use_internal":
            return import_path, "internal"

        # mod declarations are internal
        if import_type == "mod":
            return import_path, "internal"

        # Check for std library
        if import_path in RUST_STD_CRATES:
            return import_path, "std"

        # Check for workspace members (internal cross-crate deps)
        if import_path in self._workspace_members:
            return import_path, "internal"

        # Check for external crates
        if import_path in self._external_crates:
            return import_path, "external"

        # If it matches the crate name, it's internal
        if self._crate_name and import_path == self._crate_name:
            return import_path, "internal"

        # Default: assume external if not recognized
        return import_path, "external"

    def _build_file_map(self, rust_files: List[Dict[str, Any]]):
        """Build a map of module paths to file paths."""
        for file_info in rust_files:
            path = file_info["path"]
            self._file_map[path] = path

            # Map module names to files
            # src/foo.rs -> foo
            # src/foo/mod.rs -> foo
            basename = os.path.basename(path)
            dirname = os.path.dirname(path)

            if basename == "mod.rs":
                # src/foo/mod.rs -> foo
                mod_name = os.path.basename(dirname)
                self._file_map[mod_name] = path
            elif basename == "lib.rs" or basename == "main.rs":
                # Entry points
                self._file_map[basename] = path
            elif basename.endswith(".rs"):
                # src/foo.rs -> foo
                mod_name = basename[:-3]
                self._file_map[mod_name] = path

    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph, where:
            - Keys are module identifiers (file paths for internal, crate names for external)
            - Values are dictionaries containing:
                - 'type': 'internal', 'std', or 'external'
                - 'path': File path (for internal modules)
                - 'dependencies': Set of module identifiers this module depends on
        """
        self.dependency_graph = {}
        self._file_map = {}

        # Parse Cargo.toml
        self._cargo_toml = self._parse_cargo_toml()
        if self._cargo_toml:
            package = self._cargo_toml.get("package", {})
            self._crate_name = package.get("name") if isinstance(package, dict) else None
            self._external_crates = self._get_external_crates()
            # Parse workspace members (also adds their deps to _external_crates)
            self._workspace_members = self._parse_workspace()
            # Remove workspace members from external crates (they're internal)
            # Also pre-populate the graph with workspace members
            for member_name, member_path in self._workspace_members.items():
                self._external_crates.discard(member_name)
                # Add workspace member to graph as internal
                if member_name not in self.dependency_graph:
                    self.dependency_graph[member_name] = {
                        "type": "internal",
                        "path": member_path,
                        "dependencies": set(),
                    }

        # Get all Rust files
        file_tree = self.repo.get_file_tree()
        rust_files = [
            f
            for f in file_tree
            if f["path"].endswith(".rs") and "target/" not in f["path"] and "/target/" not in f["path"]
        ]

        self._build_file_map(rust_files)

        # Process each file
        for file_info in rust_files:
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
                path = imp["path"]
                imp_type = imp["type"]
                resolved, dep_type = self._resolve_import(path, imp_type)

                # Add to dependencies
                self.dependency_graph[file_path]["dependencies"].add(resolved)

                # Add dependency node to graph if not present
                if resolved not in self.dependency_graph:
                    self.dependency_graph[resolved] = {
                        "type": dep_type,
                        "path": self._file_map.get(resolved),
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
        Generate a Rust-specific description of the dependency graph.

        Args:
            max_tokens: Approximate maximum number of tokens in the output
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description
        """
        if not self._initialized:
            self.build_dependency_graph()

        base_summary = super().generate_llm_context(max_tokens, output_format, None)

        # Count by type
        internal_count = len([m for m, d in self.dependency_graph.items() if d["type"] == "internal"])
        std_count = len([m for m, d in self.dependency_graph.items() if d["type"] == "std"])
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

            rust_insights = ["## Rust-Specific Insights\n"]
            if self._crate_name:
                rust_insights.append(f"\n**Crate:** `{self._crate_name}`\n\n")

            rust_insights.append("### Dependency Types\n")
            rust_insights.append(f"- Internal modules: {internal_count}\n")
            rust_insights.append(f"- Std library crates: {std_count}\n")
            rust_insights.append(f"- External crates: {external_count}\n\n")

            if heavy_importers:
                rust_insights.append("### Modules with Most Imports\n")
                for module, count in heavy_importers:
                    short_name = module.split("/")[-1] if "/" in module else module
                    rust_insights.append(f"- **{short_name}** imports {count} modules\n")
                rust_insights.append("\n")

            if most_imported:
                rust_insights.append("### Most Commonly Imported\n")
                for module, count in most_imported:
                    module_type = self.dependency_graph.get(module, {}).get("type", "external")
                    short_name = module.split("/")[-1] if "/" in module else module
                    rust_insights.append(f"- **{short_name}** ({module_type}) imported by {count} modules\n")
                rust_insights.append("\n")

            if external_deps:
                rust_insights.append("### External Crates\n")
                for dep in sorted(external_deps)[:10]:
                    rust_insights.append(f"- `{dep}`\n")
                if len(external_deps) > 10:
                    rust_insights.append(f"- ...and {len(external_deps) - 10} more\n")
                rust_insights.append("\n")

            result = parts[0] + "".join(rust_insights) + "## Additional Insights" + parts[1]

        else:
            parts = base_summary.split("ADDITIONAL INSIGHTS:")

            rust_insights = ["RUST-SPECIFIC INSIGHTS:\n"]
            rust_insights.append("----------------------------------------\n\n")
            if self._crate_name:
                rust_insights.append(f"Crate: {self._crate_name}\n\n")

            rust_insights.append("Dependency Types:\n")
            rust_insights.append(f"- Internal modules: {internal_count}\n")
            rust_insights.append(f"- Std library crates: {std_count}\n")
            rust_insights.append(f"- External crates: {external_count}\n\n")

            if heavy_importers:
                rust_insights.append("Modules with Most Imports:\n")
                for module, count in heavy_importers:
                    short_name = module.split("/")[-1] if "/" in module else module
                    rust_insights.append(f"- {short_name} imports {count} modules\n")
                rust_insights.append("\n")

            if most_imported:
                rust_insights.append("Most Commonly Imported:\n")
                for module, count in most_imported:
                    module_type = self.dependency_graph.get(module, {}).get("type", "external")
                    short_name = module.split("/")[-1] if "/" in module else module
                    rust_insights.append(f"- {short_name} ({module_type}) imported by {count} modules\n")
                rust_insights.append("\n")

            if external_deps:
                rust_insights.append("External Crates:\n")
                for dep in sorted(external_deps)[:10]:
                    rust_insights.append(f"- {dep}\n")
                if len(external_deps) > 10:
                    rust_insights.append(f"- ...and {len(external_deps) - 10} more\n")
                rust_insights.append("\n")

            result = parts[0] + "".join(rust_insights) + "ADDITIONAL INSIGHTS:" + parts[1]

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
        std_modules = [m for m, data in self.dependency_graph.items() if data["type"] == "std"]

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
                "crate_name": self._crate_name,
                "total_modules": len(self.dependency_graph),
                "internal_modules": len(internal_modules),
                "external_crates": len(external_modules),
                "std_crates": len(std_modules),
                "dependency_cycles": len(cycles),
            },
            "cycles": cycles,
            "high_dependency_modules": sorted(
                high_dependency_modules, key=lambda x: x["dependent_count"] + x["dependency_count"], reverse=True
            ),
            "external_crates": sorted(external_modules),
            "std_crates_used": sorted(std_modules),
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report
