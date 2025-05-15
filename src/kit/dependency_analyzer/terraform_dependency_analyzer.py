"""Analyzes and visualizes infrastructure dependencies in Terraform code."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import hcl2

from .dependency_analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..repository import Repository


class TerraformDependencyAnalyzer(DependencyAnalyzer):
    """
    Analyzes dependencies between Terraform resources, modules, and data sources.

    This class provides functionality to:
    1. Build a dependency graph of Terraform resources within a repository
    2. Identify reference relationships between infrastructure components
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
        self._resource_map: Dict[str, str] = {}
        self._variable_map: Dict[str, str] = {}
        self._local_map: Dict[str, str] = {}
        self._output_map: Dict[str, str] = {}
        self._module_map: Dict[str, str] = {}

    def build_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes the entire repository and builds a dependency graph.

        Returns:
            A dictionary representing the dependency graph, where:
            - Keys are resource identifiers (e.g., aws_s3_bucket.example)
            - Values are dictionaries containing:
                - 'type': Resource type (e.g., 'aws_s3_bucket')
                - 'name': Resource name
                - 'path': File path
                - 'dependencies': List of resource identifiers this resource depends on
                - 'attributes': Key attributes of the resource
        """
        self.dependency_graph = {}
        self._resource_map = {}
        self._variable_map = {}
        self._local_map = {}
        self._output_map = {}
        self._module_map = {}

        for file_info in self.repo.get_file_tree():
            if file_info["path"].endswith(".tf"):
                self._build_resource_maps(file_info["path"])

        for file_info in self.repo.get_file_tree():
            if file_info["path"].endswith(".tf"):
                self._process_file(file_info["path"])

        for resource_id, data in self.dependency_graph.items():
            if "dependencies" in data and isinstance(data["dependencies"], set):
                data["dependencies"] = list(data["dependencies"])

        self._initialized = True
        return self.dependency_graph

    def _build_resource_maps(self, file_path: str):
        """
        Maps resource types and names to file paths for future reference.

        Args:
            file_path: Path to the Terraform file
        """
        try:
            file_content = self.repo.get_file_content(file_path)
            terraform_dict = hcl2.loads(file_content)
            correct_abs_path = self.repo.get_abs_path(file_path)

            if "resource" in terraform_dict:
                for resource_block in terraform_dict["resource"]:
                    for resource_type, resources in resource_block.items():
                        for resource_name, _ in resources.items():
                            resource_id = f"{resource_type}.{resource_name}"
                            self._resource_map[resource_id] = correct_abs_path

            if "variable" in terraform_dict:
                for var_block in terraform_dict["variable"]:
                    for var_name, _ in var_block.items():
                        var_id = f"var.{var_name}"
                        self._variable_map[var_id] = correct_abs_path

            if "locals" in terraform_dict:
                for locals_block in terraform_dict["locals"]:
                    for local_name, _ in locals_block.items():
                        local_id = f"local.{local_name}"
                        self._local_map[local_id] = correct_abs_path

            if "output" in terraform_dict:
                for output_block in terraform_dict["output"]:
                    for output_name, _ in output_block.items():
                        output_id = f"output.{output_name}"
                        self._output_map[output_id] = correct_abs_path

            if "module" in terraform_dict:
                for module_block in terraform_dict["module"]:
                    for module_name, _ in module_block.items():
                        module_id = f"module.{module_name}"
                        self._module_map[module_id] = correct_abs_path

        except Exception as e:
            logger.warning(f"Error processing {file_path} for resource mapping: {e}")

    def _process_file(self, file_path: str):
        """
        Process a single file to extract its dependencies.

        Args:
            file_path: Path to the file to analyze
        """
        try:
            file_content = self.repo.get_file_content(file_path)
            terraform_dict = hcl2.loads(file_content)

            self._process_blocks(terraform_dict, file_path)

        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")

    def _process_blocks(self, terraform_dict: Dict, file_path: str):
        """
        Process Terraform blocks and identify dependencies.

        Args:
            terraform_dict: Dictionary of parsed Terraform configuration blocks
            file_path: Path to the file being processed
        """
        # Ensure we're using absolute path relative to the repository
        correct_abs_path = self.repo.get_abs_path(file_path)

        if "resource" in terraform_dict:
            for resource_block in terraform_dict["resource"]:
                for resource_type, resources in resource_block.items():
                    for resource_name, resource_config in resources.items():
                        resource_id = f"{resource_type}.{resource_name}"
                        self._add_node(resource_id, "resource", resource_type, resource_name, correct_abs_path)
                        self._find_dependencies(resource_id, resource_config)

        if "module" in terraform_dict:
            for module_block in terraform_dict["module"]:
                for module_name, module_config in module_block.items():
                    module_id = f"module.{module_name}"
                    self._add_node(module_id, "module", "module", module_name, correct_abs_path)
                    self._find_dependencies(module_id, module_config)

        if "data" in terraform_dict:
            for data_block in terraform_dict["data"]:
                for data_type, data_resources in data_block.items():
                    for data_name, data_config in data_resources.items():
                        data_id = f"data.{data_type}.{data_name}"
                        self._add_node(data_id, "data", data_type, data_name, correct_abs_path)
                        self._find_dependencies(data_id, data_config)

        if "variable" in terraform_dict:
            for variable_block in terraform_dict["variable"]:
                for var_name, var_config in variable_block.items():
                    var_id = f"var.{var_name}"
                    self._add_node(var_id, "variable", "variable", var_name, correct_abs_path)
                    # Variables might have default values with references
                    if "default" in var_config:
                        self._find_dependencies(var_id, var_config["default"])

        if "locals" in terraform_dict:
            for locals_block in terraform_dict["locals"]:
                for local_name, local_value in locals_block.items():
                    local_id = f"local.{local_name}"
                    self._add_node(local_id, "local", "local", local_name, correct_abs_path)
                    self._find_dependencies(local_id, local_value)

        if "output" in terraform_dict:
            for output_block in terraform_dict["output"]:
                for output_name, output_config in output_block.items():
                    output_id = f"output.{output_name}"
                    self._add_node(output_id, "output", "output", output_name, correct_abs_path)
                    self._find_dependencies(output_id, output_config)

    def _add_node(self, node_id: str, node_category: str, node_type: str, node_name: str, file_path: str):
        """
        Add a node to the dependency graph.

        Args:
            node_id: Unique identifier for the node
            node_category: Category (resource, module, data, variable, local, output)
            node_type: Type (e.g., aws_s3_bucket for resources)
            node_name: Name of the node
            file_path: Path to the file containing this node
        """
        if node_id not in self.dependency_graph:
            # Node doesn't exist yet – add with provided details.
            self.dependency_graph[node_id] = {
                "category": node_category,
                "type": node_type,
                "name": node_name,
                "path": file_path,
                "dependencies": set(),
            }
        else:
            # Node exists – make sure we don't lose file path information.
            if file_path and not self.dependency_graph[node_id].get("path"):
                self.dependency_graph[node_id]["path"] = file_path

    def _find_dependencies(self, source_id: str, config: Any):
        """
        Recursively find dependencies in a Terraform configuration block.

        Args:
            source_id: Source resource ID
            config: Configuration to analyze for dependencies
        """
        if isinstance(config, dict):
            for key, value in config.items():
                if key == "depends_on" and isinstance(value, list):
                    for dep in value:
                        self._add_dependency(source_id, dep)
                else:
                    self._find_dependencies(source_id, value)

        elif isinstance(config, list):
            for item in config:
                self._find_dependencies(source_id, item)

        elif isinstance(config, str):
            self._find_string_dependencies(source_id, config)

    def _find_string_dependencies(self, source_id: str, value: str):
        """
        Find dependencies in string interpolations.

        Args:
            source_id: Source resource ID
            value: String to check for references
        """
        if not isinstance(value, str):
            return

        interp_pattern = r"\${([^{}]+)}"
        matches = re.findall(interp_pattern, value)

        self._find_reference_dependencies(source_id, value)

        for match in matches:
            self._find_reference_dependencies(source_id, match)

    def _find_reference_dependencies(self, source_id: str, text: str):
        """
        Find resource references in a text string.

        Args:
            source_id: Source resource ID
            text: Text to scan for references
        """
        if not isinstance(text, str):
            return

        resource_pattern = r"([a-zA-Z][a-zA-Z0-9_-]*)\.([\-\w]+)"
        resource_matches = re.findall(resource_pattern, text)

        for res_type, res_name in resource_matches:
            if f"{res_type}.{res_name}" == source_id:
                continue

            if res_type in ("each", "count", "index", "value", "key"):
                continue

            if res_type == "var":
                dep_id = f"var.{res_name}"
                self._add_dependency(source_id, dep_id)
            elif res_type == "local":
                dep_id = f"local.{res_name}"
                self._add_dependency(source_id, dep_id)
            elif res_type == "module":
                dep_id = f"module.{res_name}"
                self._add_dependency(source_id, dep_id)
            elif res_type == "data":
                data_pattern = r"data\.([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)"
                data_matches = re.findall(data_pattern, text)
                if data_matches:
                    for data_type, data_name in data_matches:
                        dep_id = f"data.{data_type}.{data_name}"
                        self._add_dependency(source_id, dep_id)
            else:
                dep_id = f"{res_type}.{res_name}"
                self._add_dependency(source_id, dep_id)

    def _add_dependency(self, source: str, target: str):
        """
        Add a dependency from source to target in the graph.

        Args:
            source: Source resource ID
            target: Target resource ID
        """
        if source not in self.dependency_graph:
            logger.warning(f"Source node {source} not found in dependency graph")
            return

        self.dependency_graph[source]["dependencies"].add(target)

        if target not in self.dependency_graph:
            parts = target.split(".")
            if len(parts) >= 2:
                if parts[0] == "data" and len(parts) >= 3:
                    node_category = "data"
                    node_type = parts[1]
                    node_name = parts[2]
                else:
                    node_category = "external"
                    node_type = parts[0]
                    node_name = parts[1]

                # Attempt to resolve the file path from pre-built maps before defaulting to empty string.
                file_path = (
                    self._resource_map.get(target)
                    or self._variable_map.get(target)
                    or self._local_map.get(target)
                    or self._output_map.get(target)
                    or self._module_map.get(target)
                    or ""
                )

                self._add_node(target, node_category, node_type, node_name, file_path)

    def export_dependency_graph(
        self, output_format: str = "json", output_path: Optional[str] = None
    ) -> Union[Dict, str]:
        """
        Export the dependency graph in various formats.

        Args:
            output_format: Format to export ('json', 'dot', 'graphml')
            output_path: Path to save the output file (if None, returns the data)

        Returns:
            Depending on format and output_path:
            - If output_path is provided: Path to the output file
            - If output_path is None: Formatted dependency data
        """
        if not self._initialized:
            self.build_dependency_graph()

        serializable_graph = {}
        for node_id, data in self.dependency_graph.items():
            serializable_graph[node_id] = {
                "category": data["category"],
                "type": data["type"],
                "name": data["name"],
                "path": data["path"],
                "dependencies": list(data["dependencies"])
                if isinstance(data["dependencies"], set)
                else data["dependencies"],
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

        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _generate_dot_file(self, graph: Dict[str, Dict[str, Any]]):
        """Generate a DOT file for visualization with Graphviz."""
        dot_lines = ["digraph TerraformDependencies {", '    rankdir="LR";', "    node [shape=box];"]

        # Add nodes with categories as colors
        for node_id, data in graph.items():
            color = '"#1f77b4"'  # Default blue
            if data.get("category") == "resource":
                color = '"#ff7f0e"'  # Orange
            elif data.get("category") == "module":
                color = '"#2ca02c"'  # Green
            elif data.get("category") == "data":
                color = '"#9467bd"'  # Purple

            # Include file path in the label
            file_path = data.get("path", "")
            path_to_display = file_path if file_path else "unknown file"
            label = f'"{node_id}\n({data.get("type", "unknown")})\n[{path_to_display}]"'
            dot_lines.append(f'    "{node_id}" [label={label}, style="filled", fillcolor={color}];')

        # Add edges
        for node_id, data in graph.items():
            if "dependencies" in data:
                for dep in data["dependencies"]:
                    if dep in graph:  # Only add edges to nodes that exist
                        dot_lines.append(f'    "{node_id}" -> "{dep}";')

        dot_lines.append("}")

        return "\n".join(dot_lines)

    def _generate_graphml_file(self, graph: Dict[str, Dict[str, Any]]):
        """Generate a GraphML file for visualization with tools like Gephi or yEd."""
        graphml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '  <key id="d0" for="node" attr.name="category" attr.type="string"/>',
            '  <key id="d1" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="d2" for="node" attr.name="name" attr.type="string"/>',
            '  <key id="d3" for="node" attr.name="file" attr.type="string"/>',
            '  <graph id="G" edgedefault="directed">',
        ]

        # Add nodes
        for node_id, data in graph.items():
            safe_id = node_id.replace(".", "_").replace("-", "_")
            graphml_lines.append(f'    <node id="{safe_id}">')
            graphml_lines.append(f'      <data key="d0">{data.get("category", "unknown")}</data>')
            graphml_lines.append(f'      <data key="d1">{data.get("type", "unknown")}</data>')
            graphml_lines.append(f'      <data key="d2">{data.get("name", "unknown")}</data>')
            file_path = data.get("path", "")
            path_to_display = file_path if file_path else "unknown file"
            graphml_lines.append(f'      <data key="d3">{path_to_display}</data>')
            graphml_lines.append("    </node>")

        # Add edges
        edge_id = 0
        for node_id, data in graph.items():
            if "dependencies" in data:
                for dep in data["dependencies"]:
                    if dep in graph:  # Only add edges to nodes that exist
                        source_id = node_id.replace(".", "_").replace("-", "_")
                        target_id = dep.replace(".", "_").replace("-", "_")
                        graphml_lines.append(f'    <edge id="e{edge_id}" source="{source_id}" target="{target_id}"/>')
                        edge_id += 1
                edge_id += 1

        graphml_lines.append("</graph>")
        graphml_lines.append("</graphml>")
        return "\n".join(graphml_lines)

    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of resource IDs
        """
        if not self._initialized:
            self.build_dependency_graph()

        cycles = []

        for start_node in self.dependency_graph:
            path: List[str] = []
            visited = set()

            def dfs(node):
                if node in path:
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    if cycle not in cycles and len(cycle) > 1:
                        cycles.append(cycle)
                    return

                if node in visited or node not in self.dependency_graph:
                    return

                visited.add(node)
                path.append(node)

                for dep in self.dependency_graph[node]["dependencies"]:
                    if dep in self.dependency_graph:
                        dfs(dep)

                path.pop()

            dfs(start_node)

        return cycles

    def get_resource_dependencies(self, resource_id: str, include_indirect: bool = False) -> List[str]:
        """
        Get dependencies for a specific resource.

        Args:
            resource_id: ID of the resource to check
            include_indirect: Whether to include indirect dependencies

        Returns:
            List of resource IDs this resource depends on
        """
        if not self._initialized:
            self.build_dependency_graph()

        if resource_id not in self.dependency_graph:
            return []

        if include_indirect:
            all_deps = set()
            visited = set()

            def dfs(node):
                if node in visited or node not in self.dependency_graph:
                    return

                visited.add(node)

                for dep in self.dependency_graph[node]["dependencies"]:
                    if dep in self.dependency_graph:
                        all_deps.add(dep)
                        dfs(dep)

            dfs(resource_id)
            return list(all_deps)
        else:
            return [dep for dep in self.dependency_graph[resource_id]["dependencies"] if dep in self.dependency_graph]

    def get_dependents(self, resource_id: str, include_indirect: bool = False) -> List[str]:
        """
        Get resources that depend on the specified resource.

        Args:
            resource_id: ID of the resource to check
            include_indirect: Whether to include indirect dependents

        Returns:
            List of resource IDs that depend on this resource
        """
        if not self._initialized:
            self.build_dependency_graph()

        if resource_id not in self.dependency_graph:
            return []

        direct_dependents = [
            node for node, data in self.dependency_graph.items() if resource_id in data["dependencies"]
        ]

        if not include_indirect:
            return direct_dependents

        all_dependents = set(direct_dependents)

        def find_ancestors(node):
            parents = [
                parent
                for parent, data in self.dependency_graph.items()
                if node in data["dependencies"] and parent not in all_dependents
            ]

            for parent in parents:
                all_dependents.add(parent)
                find_ancestors(parent)

        for dep in direct_dependents:
            find_ancestors(dep)

        return list(all_dependents)

    def get_resource_by_type(self, resource_type: str) -> List[str]:
        """
        Find all resources of a specific type.

        Args:
            resource_type: Type of resource (e.g., aws_s3_bucket)

        Returns:
            List of resource IDs matching the specified type
        """
        if not self._initialized:
            self.build_dependency_graph()

        return [
            node_id
            for node_id, data in self.dependency_graph.items()
            if data["category"] == "resource" and data["type"] == resource_type
        ]

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

        dot = graphviz.Digraph(
            "terraform_dependencies", comment="Terraform Resource Dependencies", format=format, engine="dot"
        )
        dot.attr(rankdir="LR")

        resource_colors = {
            "resource": "lightblue",
            "data": "lightgreen",
            "module": "lightyellow",
            "variable": "lightgrey",
            "output": "lightpink",
            "local": "lightcyan",
        }

        for node_id, data in self.dependency_graph.items():
            node_category = data.get("category", "resource")
            fillcolor = resource_colors.get(node_category, "white")

            if "." in node_id:
                parts = node_id.split(".")
                label = parts[-1]  # Use the resource name as label
                tooltip = node_id  # Full resource ID as tooltip
            else:
                label = node_id
                tooltip = node_id

            dot.node(node_id, label=label, tooltip=tooltip, style="filled", fillcolor=fillcolor, shape="box")

        for node_id, data in self.dependency_graph.items():
            for dep in data.get("dependencies", []):
                if dep in self.dependency_graph:
                    dot.edge(node_id, dep)

        dot.render(output_path, cleanup=True)
        return f"{output_path}.{format}"

    def generate_llm_context(
        self, max_tokens: int = 4000, output_format: str = "markdown", output_path: Optional[str] = None
    ) -> str:
        """
        Generate a Terraform-specific natural language description of the dependency graph optimized for LLM consumption.

        This method extends the base implementation with infrastructure-specific insights about resources,
        modules, and provider dependencies to provide richer context to large language models.

        Args:
            max_tokens: Approximate maximum number of tokens in the output (rough guideline)
            output_format: Format of the output ('markdown', 'text')
            output_path: Optional path to save the output to a file

        Returns:
            A string containing the natural language description of the dependency structure
        """
        base_summary = super().generate_llm_context(max_tokens, output_format, None)

        resource_counts: Dict[str, int] = {}
        for node_id, data in self.dependency_graph.items():
            if data.get("category") == "resource":
                resource_type = data.get("type", "unknown")
                resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

        providers = set()
        for res_type in resource_counts.keys():
            if "_" in res_type:
                provider = res_type.split("_")[0]
                providers.add(provider)

        resource_importance = {}
        for node_id, data in self.dependency_graph.items():
            if data.get("category") == "resource":
                dependents = self.get_dependents(node_id)
                dependencies = data.get("dependencies", [])

                importance = len(dependents) + len(dependencies)
                resource_importance[node_id] = importance

        key_resources = sorted(resource_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        modules = [node_id for node_id, data in self.dependency_graph.items() if data.get("category") == "module"]

        if output_format == "markdown":
            # Locate the "Additional Insights" header in a whitespace-tolerant way
            match = re.search(r"##\s+Additional\s+Insights[ \t]*", base_summary, flags=re.IGNORECASE)

            if match:
                insert_pos = match.start()
                before = base_summary[:insert_pos]
                after = base_summary[insert_pos:]
            else:
                # Header not found – append insights at the end
                before = base_summary
                after = ""

            tf_insights = ["## Terraform-Specific Insights\n"]

            tf_insights.append("### Resource Types\n")
            top_resource_types = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for res_type, count in top_resource_types:
                tf_insights.append(f"- **{res_type}**: {count} resources\n")

            tf_insights.append("\n### Cloud Providers\n")
            for provider in sorted(providers):
                tf_insights.append(f"- **{provider}**\n")

            if key_resources:
                tf_insights.append("\n### Key Infrastructure Resources\n")
                tf_insights.append("Resources with the most dependencies and dependents:\n")
                for resource, importance in key_resources:
                    res_type = self.dependency_graph[resource].get("type", "unknown")
                    deps = len(self.dependency_graph[resource].get("dependencies", []))
                    dependents_count = len(self.get_dependents(resource))
                    file_path = self.dependency_graph[resource].get("path", "")
                    # Ensure file_path is treated as a string
                    path_to_display = str(file_path) if file_path else "unknown file"
                    tf_insights.append(f"- **{resource}** ({res_type}) [File: {path_to_display}]\n")
                    tf_insights.append(f"  - Dependencies: {deps}, Dependents: {dependents_count}\n")

            if modules:
                tf_insights.append("\n### Terraform Modules\n")
                for module in modules:
                    module_deps = len(self.dependency_graph[module].get("dependencies", []))
                    file_path = self.dependency_graph[module].get("path", "")
                    path_to_display = file_path if file_path else "unknown file"
                    tf_insights.append(f"- **{module}** [File: {path_to_display}]\n")
                    tf_insights.append(f"  - Dependencies: {module_deps}\n")

            result = before + "".join(tf_insights) + after

        else:
            # Locate the "Additional Insights" header in a whitespace-tolerant way
            match_txt = re.search(r"ADDITIONAL\s+INSIGHTS:\s*", base_summary, flags=re.IGNORECASE)

            if match_txt:
                insert_pos = match_txt.start()
                before = base_summary[:insert_pos]
                after = base_summary[insert_pos:]
            else:
                before = base_summary
                after = ""

            tf_insights = ["TERRAFORM-SPECIFIC INSIGHTS:\n"]
            tf_insights.append("------------------------------\n\n")

            tf_insights.append("Resource Types:\n")
            top_resource_types = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for res_type, count in top_resource_types:
                tf_insights.append(f"- {res_type}: {count} resources\n")

            tf_insights.append("\nCloud Providers:\n")
            for provider in sorted(providers):
                tf_insights.append(f"- {provider}\n")

            if key_resources:
                tf_insights.append("\nKey Infrastructure Resources:\n")
                tf_insights.append("Resources with the most dependencies and dependents:\n")
                for resource, importance in key_resources:
                    res_type = self.dependency_graph[resource].get("type", "unknown")
                    deps = len(self.dependency_graph[resource].get("dependencies", []))
                    dependents_count = len(self.get_dependents(resource))
                    file_path = self.dependency_graph[resource].get("path", "")
                    # Ensure file_path is treated as a string
                    path_to_display = str(file_path) if file_path else "unknown file"
                    tf_insights.append(f"- {resource} ({res_type}) [File: {path_to_display}]\n")
                    tf_insights.append(f"  - Dependencies: {deps}, Dependents: {dependents_count}\n")

            if modules:
                tf_insights.append("\nTerraform Modules:\n")
                for module in modules:
                    module_deps = len(self.dependency_graph[module].get("dependencies", []))
                    file_path = self.dependency_graph[module].get("path", "")
                    path_to_display = file_path if file_path else "unknown file"
                    tf_insights.append(f"- {module} [File: {path_to_display}]\n")
                    tf_insights.append(f"  - Dependencies: {module_deps}\n")

            result = before + "".join(tf_insights) + after

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result
