#!/usr/bin/env python3
"""
Terraform Dependency Analysis Demo

This script demonstrates how to use the Kit SDK's TerraformDependencyAnalyzer
to analyze and visualize dependencies in a Terraform codebase.
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
    parser = argparse.ArgumentParser(description="Analyze Terraform dependencies")
    parser.add_argument(
        "--repo-path", default=str(script_dir), help="Path to the Terraform repository (default: current directory)"
    )
    parser.add_argument("--output-dir", default=str(script_dir / "output"), help="Directory to store output files")
    parser.add_argument(
        "--format",
        choices=["json", "dot", "graphml"],
        default="dot",
        help="Output format for dependency graph (default: dot)",
    )
    parser.add_argument("--visualize", action="store_true", help="Generate a visualization of the dependency graph")
    parser.add_argument(
        "--llm-context", action="store_true", help="Generate LLM-friendly context about the infrastructure"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Load the repository
    print(f"Loading repository from {args.repo_path}...")
    repo = Repository(args.repo_path)

    # Get the Terraform dependency analyzer
    print("Initializing Terraform dependency analyzer...")
    analyzer = repo.get_dependency_analyzer("terraform")

    # Build the dependency graph
    print("Building dependency graph... (this might take a moment)")
    graph = analyzer.build_dependency_graph()
    print(f"Found {len(graph)} resources in the dependency graph")

    # Export the dependency graph
    output_file = output_dir / f"terraform_dependencies.{args.format}"
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
        cycles_file = output_dir / "terraform_cycles.txt"
        with open(cycles_file, "w") as f:
            f.write(f"Found {len(cycles)} circular dependencies:\n\n")
            for i, cycle in enumerate(cycles, 1):
                f.write(f"{i}. {' → '.join(cycle)} → {cycle[0]}\n")
        print(f"Cycles exported to {cycles_file}")
    else:
        print("No circular dependencies found. Great job!")

    # Generate visualization if requested
    if args.visualize:
        viz_file = output_dir / "terraform_visualization.png"
        print(f"Generating visualization to {viz_file}...")
        analyzer.visualize_dependencies(output_path=str(viz_file), format="png")
        print(f"Visualization saved to {viz_file}")

    # Generate LLM context if requested
    if args.llm_context:
        context_file = output_dir / "terraform_llm_context.md"
        print(f"Generating LLM-friendly context to {context_file}...")
        analyzer.generate_llm_context(output_format="markdown", output_path=str(context_file))
        print(f"LLM context saved to {context_file}")

    # Print some key resources and their dependencies
    print("\nAnalyzing key infrastructure components:")

    # Find resources with the most dependencies
    resources_by_deps = sorted(
        [(res_id, len(data.get("dependencies", []))) for res_id, data in graph.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    print("\nTop 5 resources with most dependencies:")
    for res_id, dep_count in resources_by_deps[:5]:
        res_type = graph[res_id].get("type", "unknown")
        print(f"  - {res_id} ({res_type}): depends on {dep_count} resources")

    # Find resources with the most dependents
    resources_by_dependents = []
    for res_id in graph:
        dependents = analyzer.get_dependents(res_id)
        resources_by_dependents.append((res_id, len(dependents)))

    resources_by_dependents.sort(key=lambda x: x[1], reverse=True)

    print("\nTop 5 resources with most dependents:")
    for res_id, dep_count in resources_by_dependents[:5]:
        res_type = graph[res_id].get("type", "unknown")
        print(f"  - {res_id} ({res_type}): used by {dep_count} resources")

    print("\nDependency analysis complete!")
    print(f"All output files are saved in {output_dir}")


if __name__ == "__main__":
    main()
