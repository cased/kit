#!/usr/bin/env python3
"""
Python Dependency Analysis Demo

This script demonstrates how to use the Kit SDK's PythonDependencyAnalyzer
to analyze and visualize dependencies in a Python codebase.
It uses the Kit repository itself as an example, showcasing how
the tool can map complex import relationships.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import kit
script_dir = Path(__file__).parent.absolute()
repo_root = script_dir.parent.parent
sys.path.insert(0, str(repo_root))

from kit import Repository


def main():
    parser = argparse.ArgumentParser(description="Analyze Python dependencies in the Kit repository")
    parser.add_argument("--repo-path", default=str(repo_root), help=f"Path to the repository (default: {repo_root})")
    parser.add_argument("--output-dir", default=str(script_dir / "output"), help="Directory to store output files")
    parser.add_argument(
        "--format",
        choices=["json", "dot", "graphml", "adjacency"],
        default="dot",
        help="Output format for dependency graph (default: dot)",
    )
    parser.add_argument("--visualize", action="store_true", help="Generate a visualization of the dependency graph")
    parser.add_argument(
        "--llm-context", action="store_true", help="Generate LLM-friendly context about the code structure"
    )
    parser.add_argument("--module", help="Analyze dependencies for a specific module (e.g., 'kit.dependency_analyzer')")

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Load the repository
    print(f"Loading repository from {args.repo_path}...")
    repo = Repository(args.repo_path)

    # Get the Python dependency analyzer
    print("Initializing Python dependency analyzer...")
    analyzer = repo.get_dependency_analyzer("python")

    # Build the dependency graph
    print("Building dependency graph... (this might take a moment)")
    graph = analyzer.build_dependency_graph()
    print(f"Found {len(graph)} modules in the dependency graph")

    # Count internal vs external modules
    internal_modules = [m for m in graph if graph[m].get("type") == "internal"]
    external_modules = [m for m in graph if graph[m].get("type") == "external"]
    print(f"Internal modules: {len(internal_modules)}")
    print(f"External dependencies: {len(external_modules)}")

    # Export the dependency graph
    output_file = output_dir / f"python_dependencies.{args.format}"
    print(f"Exporting dependency graph to {output_file}...")
    analyzer.export_dependency_graph(output_format=args.format, output_path=str(output_file))

    # Find cycles
    print("Analyzing for circular dependencies...")
    cycles = analyzer.find_cycles()
    if cycles:
        print(f"Found {len(cycles)} circular dependencies:")
        for i, cycle in enumerate(cycles[:5], 1):
            print(f"  {i}. {' → '.join(cycle)} → {cycle[0]}")
        if len(cycles) > 5:
            print(f"  ... and {len(cycles) - 5} more")

        # Export cycles to a file
        cycles_file = output_dir / "python_cycles.txt"
        with open(cycles_file, "w") as f:
            f.write(f"Found {len(cycles)} circular dependencies:\n\n")
            for i, cycle in enumerate(cycles, 1):
                f.write(f"{i}. {' → '.join(cycle)} → {cycle[0]}\n")
        print(f"Cycles exported to {cycles_file}")
    else:
        print("No circular dependencies found. Great job!")

    # Generate visualization if requested
    if args.visualize:
        viz_file = output_dir / "python_visualization.png"
        print(f"Generating visualization to {viz_file}...")
        analyzer.visualize_dependencies(output_path=str(viz_file), format="png")
        print(f"Visualization saved to {viz_file}")

    # Generate LLM context if requested
    if args.llm_context:
        context_file = output_dir / "python_llm_context.md"
        print(f"Generating LLM-friendly context to {context_file}...")
        analyzer.generate_llm_context(output_format="markdown", output_path=str(context_file))
        print(f"LLM context saved to {context_file}")

    # If a specific module was provided, analyze it in detail
    if args.module:
        print(f"\nAnalyzing dependencies for module: {args.module}")

        # Get dependencies for the specified module
        if args.module in graph:
            direct_deps = analyzer.get_module_dependencies(args.module, include_indirect=False)
            all_deps = analyzer.get_module_dependencies(args.module, include_indirect=True)

            print(f"Direct dependencies ({len(direct_deps)}):")
            for dep in sorted(direct_deps):
                dep_type = "internal" if dep in internal_modules else "external"
                print(f"  - {dep} ({dep_type})")

            print(f"\nAll dependencies (including indirect): {len(all_deps)}")

            # Get modules that depend on this module
            dependents = analyzer.get_dependents(args.module, include_indirect=False)
            all_dependents = analyzer.get_dependents(args.module, include_indirect=True)

            print(f"\nModules directly depending on {args.module} ({len(dependents)}):")
            for dep in sorted(dependents):
                print(f"  - {dep}")

            print(f"\nAll dependents (including indirect): {len(all_dependents)}")

            # Export detailed analysis to a file
            module_file = output_dir / f"{args.module.replace('.', '_')}_analysis.md"
            with open(module_file, "w") as f:
                f.write(f"# Dependency Analysis for {args.module}\n\n")

                f.write("## Dependencies\n\n")
                f.write(f"Direct dependencies ({len(direct_deps)}):\n")
                for dep in sorted(direct_deps):
                    dep_type = "internal" if dep in internal_modules else "external"
                    f.write(f"- {dep} ({dep_type})\n")

                f.write(f"\nAll dependencies (including indirect): {len(all_deps)}\n")

                f.write("\n## Dependents\n\n")
                f.write(f"Modules directly depending on {args.module} ({len(dependents)}):\n")
                for dep in sorted(dependents):
                    f.write(f"- {dep}\n")

                f.write(f"\nAll dependents (including indirect): {len(all_dependents)}\n")

            print(f"Detailed analysis for {args.module} saved to {module_file}")
        else:
            print(f"Module {args.module} not found in the dependency graph.")

    # Print some interesting statistics about the codebase
    print("\nAnalyzing key code structure:")

    # Find modules with the most imports
    modules_by_imports = sorted(
        [(module, len(graph[module].get("dependencies", []))) for module in internal_modules],
        key=lambda x: x[1],
        reverse=True,
    )

    print("\nTop 5 modules with most imports:")
    for module, import_count in modules_by_imports[:5]:
        print(f"  - {module}: imports {import_count} modules")

    # Find most imported modules
    module_usage = {}
    for module in graph:
        for dep in graph[module].get("dependencies", []):
            module_usage[dep] = module_usage.get(dep, 0) + 1

    most_imported = sorted(
        [(module, count) for module, count in module_usage.items()], key=lambda x: x[1], reverse=True
    )

    print("\nTop 5 most imported modules:")
    for module, import_count in most_imported[:5]:
        module_type = "internal" if module in internal_modules else "external"
        print(f"  - {module} ({module_type}): imported by {import_count} modules")

    # Analyze dependency analyzer package specifically - it's what this demo is about!
    dependency_analyzer_modules = [m for m in internal_modules if "dependency_analyzer" in m]

    if dependency_analyzer_modules:
        print("\nDependency Analyzer Package Structure:")
        for module in sorted(dependency_analyzer_modules):
            direct_deps = len(analyzer.get_module_dependencies(module, include_indirect=False))
            dependents = len(analyzer.get_dependents(module, include_indirect=False))
            print(f"  - {module}: {direct_deps} imports, {dependents} dependents")

    print("\nDependency analysis complete!")
    print(f"All output files are saved in {output_dir}")


if __name__ == "__main__":
    main()
