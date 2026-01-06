"""kit Command Line Interface."""

import json
import os
from pathlib import Path
from typing import List, Optional, Union

import httpx
import typer


def _get_version() -> str:
    """Get kit version without importing the entire package."""
    try:
        from importlib.metadata import version

        return version("cased-kit")
    except Exception:
        return "unknown"


def version_callback(value: bool):
    if value:
        typer.echo(f"kit version {_get_version()}")
        raise typer.Exit()


app = typer.Typer(help="A modular toolkit for LLM-powered codebase understanding.", rich_markup_mode="rich")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
):
    """
    [bold blue]Kit[/] - A modular toolkit for LLM-powered codebase understanding.

    [bold yellow]🤖 AI-Powered Commands:[/]
    • [cyan]review[/]     - AI code reviews for GitHub PRs or local diffs
    • [cyan]summarize[/]  - Quick PR summaries for triage
    • [cyan]commit[/]     - Generate intelligent commit messages

    [bold green]📊 Analysis Commands:[/]
    • [cyan]dependencies[/] - Analyze & visualize code dependencies
    • [cyan]symbols[/]    - Extract functions, classes, etc.
    • [cyan]search[/]     - Find patterns across codebase
    • [cyan]search-semantic[/] - AI-powered semantic code search
    • [cyan]file-tree[/]  - Repository structure overview

    [bold purple]📦 Package Search Commands:[/]
    • [cyan]package-search-grep[/] - Regex search in package source code
    • [cyan]package-search-hybrid[/] - Semantic + regex search in packages
    • [cyan]package-search-read[/] - Read files from packages

    [bold magenta]🔧 Utility Commands:[/]
    • [cyan]serve[/]      - Start REST API server
    • [cyan]export[/]     - Export data to JSON files
    """
    pass


@app.command("cache")
def cache_command(
    action: str = typer.Argument(..., help="Action: status, cleanup, clear, stats"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Repository path"),
):
    """🗄️ Manage incremental analysis cache."""
    from kit.repository import Repository

    try:
        repo = Repository(repo_path)

        if action == "status":
            stats = repo.get_incremental_stats()
            if stats.get("status") == "not_initialized":
                typer.echo("📭 Incremental cache not initialized")
            else:
                typer.echo("📊 Incremental Cache Status:")
                typer.echo(f"   Cached files: {stats.get('cached_files', 0)}")
                typer.echo(f"   Total symbols: {stats.get('total_symbols', 0)}")
                typer.echo(f"   Cache size: {stats.get('cache_size_mb', 0):.2f} MB")
                typer.echo(f"   Cache hit rate: {stats.get('cache_hit_rate', '0%')}")
                typer.echo(f"   Files analyzed: {stats.get('files_analyzed', 0)}")
                typer.echo(f"   Cache directory: {stats.get('cache_dir', 'N/A')}")

        elif action == "cleanup":
            repo.cleanup_incremental_cache()
            typer.echo("✅ Cleaned up stale cache entries")

        elif action == "clear":
            repo.clear_incremental_cache()
            typer.echo("✅ Cleared incremental cache")

        elif action == "stats":
            # Run a quick analysis to generate stats
            typer.echo("🔍 Analyzing repository for cache statistics...")
            symbols = repo.extract_symbols_incremental()
            stats = repo.get_incremental_stats()

            typer.echo("📈 Analysis Performance:")
            typer.echo(f"   Total symbols found: {len(symbols)}")
            typer.echo(f"   Files analyzed: {stats.get('files_analyzed', 0)}")
            typer.echo(f"   Cache hits: {stats.get('cache_hits', 0)}")
            typer.echo(f"   Cache misses: {stats.get('cache_misses', 0)}")
            typer.echo(f"   Hit rate: {stats.get('cache_hit_rate', '0%')}")
            typer.echo(f"   Average analysis time: {stats.get('avg_analysis_time', 0):.4f}s per file")

            # Finalize to save cache
            repo.finalize_analysis()

        else:
            typer.secho(f"❌ Unknown action: {action}. Use: status, cleanup, clear, stats", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    except Exception as e:
        typer.secho(f"❌ Cache operation failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("chunk-lines")
def chunk_by_lines(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_path: str = typer.Argument(..., help="Relative path to the file within the repository."),
    max_lines: int = typer.Option(50, "--max-lines", "-n", help="Maximum lines per chunk."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
):
    """Chunk a file's content by line count."""
    from kit import Repository

    try:
        repo = Repository(path)
        chunks = repo.chunk_file_by_lines(file_path, max_lines)

        if output:
            Path(output).write_text(json.dumps(chunks, indent=2))
            typer.echo(f"File chunks written to {output}")
        else:
            for i, chunk in enumerate(chunks, 1):
                typer.echo(f"--- Chunk {i} ---")
                typer.echo(chunk)
                if i < len(chunks):
                    typer.echo()
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("chunk-symbols")
def chunk_by_symbols(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_path: str = typer.Argument(..., help="Relative path to the file within the repository."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
):
    """Chunk a file's content by symbols (functions, classes)."""
    from kit import Repository

    try:
        repo = Repository(path)
        chunks = repo.chunk_file_by_symbols(file_path)

        if output:
            Path(output).write_text(json.dumps(chunks, indent=2))
            typer.echo(f"Symbol chunks written to {output}")
        else:
            for chunk in chunks:
                typer.echo(f"--- {chunk.get('type', 'Symbol')}: {chunk.get('name', 'N/A')} ---")
                typer.echo(chunk.get("code", ""))
                typer.echo()
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("commit")
def commit_changes(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: ~/.kit/review-config.yaml)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Override LLM model (e.g., gpt-4.1-nano, claude-sonnet-4-20250514)"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show generated message without committing"),
):
    """Generate intelligent commit messages and commit staged changes."""
    from kit.pr_review.commit_generator import CommitMessageGenerator
    from kit.pr_review.config import ReviewConfig

    try:
        # Load configuration (reuse PR review config)
        review_config = ReviewConfig.from_file(config)

        # Override model if specified
        if model:
            # Auto-detect provider from model name
            from kit.pr_review.config import _detect_provider_from_model

            detected_provider = _detect_provider_from_model(model)

            if detected_provider and detected_provider != review_config.llm.provider:
                # Switch provider and update API key
                from kit.pr_review.config import LLMProvider

                old_provider = review_config.llm.provider.value
                review_config.llm.provider = detected_provider

                # Update API key for new provider
                if detected_provider == LLMProvider.ANTHROPIC:
                    new_api_key = os.getenv("KIT_ANTHROPIC_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires Anthropic API key"),
                            "Configuration error",
                            "Set KIT_ANTHROPIC_TOKEN environment variable",
                        )
                elif detected_provider == LLMProvider.GOOGLE:
                    new_api_key = os.getenv("KIT_GOOGLE_TOKEN") or os.getenv("GOOGLE_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires Google API key"),
                            "Configuration error",
                            "Set KIT_GOOGLE_TOKEN environment variable",
                        )
                elif detected_provider == LLMProvider.OLLAMA:
                    new_api_key = "not_required"  # Ollama doesn't need API key
                else:  # OpenAI
                    new_api_key = os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires OpenAI API key"),
                            "Configuration error",
                            "Set KIT_OPENAI_TOKEN environment variable",
                        )

                # Assert for mypy that new_api_key is not None after error checks
                assert new_api_key is not None
                review_config.llm.api_key = new_api_key
                review_config.llm.provider = detected_provider
                review_config.llm_provider = detected_provider.value
                typer.echo(f"🔄 Switched provider: {old_provider} → {detected_provider.value}")

            review_config.llm.model = model
            review_config.llm_model = model
            typer.echo(f"🎛️  Using model: {model}")

        # Create commit generator
        generator = CommitMessageGenerator(review_config)

        # Check for staged changes
        if not generator.check_staged_changes():
            typer.secho("❌ No staged changes to commit.", fg=typer.colors.RED)
            typer.echo("💡 Use 'git add <files>' to stage changes first")
            raise typer.Exit(code=1)

        if dry_run:
            # Just show the generated message
            import asyncio

            typer.echo("🔍 Analyzing staged changes...")
            message = asyncio.run(generator.analyze_changes_for_commit("."))
            typer.echo("\n💭 Generated commit message:")
            typer.echo("=" * 50)
            typer.echo(message)
            typer.echo("=" * 50)
        else:
            # Generate and commit
            result = generator.generate_and_commit(".")
            typer.echo(result)

    except ValueError as e:
        typer.secho(f"❌ Configuration error: {e}", fg=typer.colors.RED)
        typer.echo("\n💡 Try running: kit review --init-config")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Commit failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("context")
def extract_context(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_path: str = typer.Argument(..., help="Relative path to the file within the repository."),
    line: int = typer.Argument(..., help="Line number to extract context around."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
):
    """Extract surrounding code context for a specific line."""
    from kit import Repository

    try:
        repo = Repository(path)
        context = repo.extract_context_around_line(file_path, line)

        if output:
            Path(output).write_text(json.dumps(context, indent=2) if context else "null")
            typer.echo(f"Context written to {output}")
        else:
            if context:
                typer.echo(f"Context for {file_path}:{line}")
                typer.echo(f"Symbol: {context.get('name', 'N/A')} ({context.get('type', 'N/A')})")
                typer.echo(f"Lines: {context.get('start_line', 'N/A')}-{context.get('end_line', 'N/A')}")
                typer.echo("Code:")
                typer.echo(context.get("code", ""))
            else:
                typer.echo(f"No context found for {file_path}:{line}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("dependencies")
def analyze_dependencies(
    path: str = typer.Argument(..., help="Path to the local repository."),
    language: str = typer.Option(..., "--language", "-l", help="Language to analyze: python, terraform, go"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to file instead of stdout."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, dot, graphml, adjacency"),
    visualize: bool = typer.Option(False, "--visualize", "-v", help="Generate visualization (requires Graphviz)"),
    viz_format: str = typer.Option("png", "--viz-format", help="Visualization format: png, svg, pdf"),
    cycles: bool = typer.Option(False, "--cycles", "-c", help="Show only circular dependencies"),
    llm_context: bool = typer.Option(False, "--llm-context", help="Generate LLM-friendly context description"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Analyze specific module/resource"),
    include_indirect: bool = typer.Option(
        False, "--include-indirect", "-i", help="Include indirect dependencies (for module analysis)"
    ),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Analyze and visualize code dependencies within a repository.

    Supports Python, Terraform, Go, and JavaScript/TypeScript dependency analysis with features including:
    • Dependency graph generation and export
    • Circular dependency detection
    • Module-specific analysis
    • Visualization generation
    • LLM-friendly context generation

    Examples:
        kit dependencies . --language python --format dot --output deps.dot
        kit dependencies . --language terraform --cycles --visualize
        kit dependencies . --language javascript --module src/index.js --include-indirect
        kit dependencies . --language python --llm-context --output context.md
    """
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)

        # Validate language
        supported_languages = ["python", "terraform", "go", "golang", "javascript", "typescript", "js", "ts", "rust"]
        if language.lower() not in supported_languages:
            typer.secho(
                f"❌ Unsupported language: {language}. Supported: python, terraform, go, javascript, typescript, rust",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        # Get the appropriate analyzer
        analyzer = repo.get_dependency_analyzer(language.lower())

        # Build the dependency graph
        typer.echo(f"🔍 Analyzing {language} dependencies...")
        graph = analyzer.build_dependency_graph()
        typer.echo(f"📊 Found {len(graph)} components in the dependency graph")

        # Handle different modes of operation
        if cycles:
            # Show only cycles
            detected_cycles = analyzer.find_cycles()
            if detected_cycles:
                typer.echo(f"🔄 Found {len(detected_cycles)} circular dependencies:")
                for i, cycle in enumerate(detected_cycles, 1):
                    cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
                    typer.echo(f"  {i}. {cycle_str}")

                if output:
                    cycles_data = {
                        "cycles_count": len(detected_cycles),
                        "cycles": [
                            {"cycle_number": i, "components": cycle, "cycle_path": " → ".join(cycle) + f" → {cycle[0]}"}
                            for i, cycle in enumerate(detected_cycles, 1)
                        ],
                    }
                    Path(output).write_text(json.dumps(cycles_data, indent=2))
                    typer.echo(f"💾 Cycles data written to {output}")
            else:
                typer.echo("✅ No circular dependencies found!")
                if output:
                    Path(output).write_text(json.dumps({"cycles_count": 0, "cycles": []}, indent=2))
                    typer.echo(f"💾 Cycles data written to {output}")

        elif module:
            # Analyze specific module/resource
            typer.echo(f"🔍 Analyzing dependencies for: {module}")

            if module not in graph:
                typer.secho(f"❌ Module/resource '{module}' not found in dependency graph", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            # Get dependencies and dependents using the generic interface
            dependencies = analyzer.get_dependencies(module, include_indirect=include_indirect)  # type: ignore
            dependents = analyzer.get_dependents(module, include_indirect=include_indirect)  # type: ignore

            dep_type = "All" if include_indirect else "Direct"
            typer.echo(f"📥 {dep_type} dependencies ({len(dependencies)}):")
            for dep in sorted(dependencies):
                dep_info = graph.get(dep, {})
                dep_category = dep_info.get("type", "unknown")
                typer.echo(f"  • {dep} ({dep_category})")

            typer.echo(f"📤 {dep_type} dependents ({len(dependents)}):")
            for dep in sorted(dependents):
                dep_info = graph.get(dep, {})
                dep_category = dep_info.get("type", "unknown")
                typer.echo(f"  • {dep} ({dep_category})")

            if output:
                module_data = {
                    "module": module,
                    "language": language.lower(),
                    "include_indirect": include_indirect,
                    "dependencies": {
                        "count": len(dependencies),
                        "items": [
                            {"name": dep, "type": graph.get(dep, {}).get("type", "unknown")}
                            for dep in sorted(dependencies)
                        ],
                    },
                    "dependents": {
                        "count": len(dependents),
                        "items": [
                            {"name": dep, "type": graph.get(dep, {}).get("type", "unknown")}
                            for dep in sorted(dependents)
                        ],
                    },
                }
                Path(output).write_text(json.dumps(module_data, indent=2))
                typer.echo(f"💾 Module analysis written to {output}")

        elif llm_context:
            # Generate LLM-friendly context
            typer.echo("🤖 Generating LLM-friendly context...")
            context = analyzer.generate_llm_context(
                output_format="markdown" if output and output.endswith(".md") else "text"
            )

            if output:
                Path(output).write_text(context)
                typer.echo(f"💾 LLM context written to {output}")
            else:
                typer.echo("\n" + "=" * 60)
                typer.echo("LLM CONTEXT")
                typer.echo("=" * 60)
                typer.echo(context)

        else:
            # Export dependency graph
            if output:
                result = analyzer.export_dependency_graph(output_format=format, output_path=output)
                typer.echo(f"💾 Dependency graph exported to {output} ({format} format)")
            else:
                # Output to stdout
                result = analyzer.export_dependency_graph(output_format=format, output_path=None)
                typer.echo(result)

            # Show summary
            internal_count = len([k for k, v in graph.items() if v.get("type") == "internal"])
            external_count = len([k for k, v in graph.items() if v.get("type") != "internal"])
            typer.echo(f"📈 Summary: {internal_count} internal, {external_count} external dependencies")

            # Check for cycles
            detected_cycles = analyzer.find_cycles()
            if detected_cycles:
                typer.echo(f"⚠️  Warning: {len(detected_cycles)} circular dependencies detected")
                typer.echo("💡 Run with --cycles to see details")

        # Generate visualization if requested
        if visualize:
            if not output:
                # Default visualization filename
                viz_output = f"dependencies_visualization.{viz_format}"
            else:
                # Use output filename but change extension
                base_name = Path(output).stem
                viz_output = f"{base_name}_visualization.{viz_format}"

            typer.echo(f"🎨 Generating visualization ({viz_format})...")
            try:
                viz_path = analyzer.visualize_dependencies(
                    output_path=viz_output.replace(f".{viz_format}", ""), format=viz_format
                )
                typer.echo(f"🖼️  Visualization saved to {viz_path}")
            except Exception as e:
                typer.secho(f"⚠️  Visualization failed: {e}", fg=typer.colors.YELLOW)
                typer.echo(
                    "💡 Make sure Graphviz is installed: brew install graphviz (macOS) or apt-get install graphviz (Linux)"
                )

    except ValueError as e:
        typer.secho(f"❌ Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Dependency analysis failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("export")
def export_data(
    path: str = typer.Argument(..., help="Path to the local repository."),
    data_type: str = typer.Argument(..., help="Type of data to export: index, symbols, file-tree, or symbol-usages."),
    output: str = typer.Argument(..., help="Output file path."),
    symbol_name: Optional[str] = typer.Option(
        None, "--symbol", help="Symbol name (required for symbol-usages export)."
    ),
    symbol_type: Optional[str] = typer.Option(
        None, "--symbol-type", help="Symbol type filter (for symbol-usages export)."
    ),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Export repository data to JSON files."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)

        if data_type == "index":
            repo.write_index(output)
            typer.echo(f"Repository index exported to {output}")
        elif data_type == "symbols":
            repo.write_symbols(output)
            typer.echo(f"Symbols exported to {output}")
        elif data_type == "file-tree":
            repo.write_file_tree(output)
            typer.echo(f"File tree exported to {output}")
        elif data_type == "symbol-usages":
            if not symbol_name:
                typer.secho("Error: --symbol is required for symbol-usages export", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            repo.write_symbol_usages(symbol_name, output, symbol_type)
            typer.echo(f"Symbol usages for '{symbol_name}' exported to {output}")
        else:
            typer.secho(
                f"Error: Unknown data type '{data_type}'. Use: index, symbols, file-tree, or symbol-usages",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("file-content")
def file_content(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_paths: List[str] = typer.Argument(
        ..., metavar="FILE_PATH...", help="One or more relative paths within the repository"
    ),
):
    """Get the content of one or more files in the repository.

    Examples:
        • Single file: `kit file-content . src/main.py`
        • Multiple files: `kit file-content . src/main.py src/utils/helper.py`
    """
    from kit import Repository

    try:
        repo = Repository(path)

        # Determine if single or multiple
        file_input: Union[str, List[str]] = file_paths[0] if len(file_paths) == 1 else file_paths

        content = repo.get_file_content(file_input)

        if isinstance(content, str):
            # Single file output directly
            typer.echo(content)
        else:
            # Multiple files – print header per file for readability
            for fp, text in content.items():
                header = f"\n===== {fp} =====\n"
                typer.echo(header)
                typer.echo(text)
    except FileNotFoundError as e:
        # Preserve previous behavior for single file to satisfy existing expectations
        if len(file_paths) == 1:
            typer.secho(f"Error: File not found: {file_paths[0]}", fg=typer.colors.RED)
        else:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("file-tree")
def file_tree(
    path: str = typer.Argument(..., help="Path to the local repository."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    subpath: Optional[str] = typer.Option(
        None, "--path", "-p", help="Subdirectory path to show tree for (relative to repo root)."
    ),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Get the file tree structure of a repository or subdirectory."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        tree = repo.get_file_tree(subpath=subpath)

        if output:
            Path(output).write_text(json.dumps(tree, indent=2))
            typer.echo(f"File tree written to {output}")
        else:
            if subpath:
                typer.echo(f"File tree for {subpath}:")
            for file_info in tree:
                indicator = "📁" if file_info.get("is_dir") else "📄"
                size = f" ({file_info.get('size', 0)} bytes)" if not file_info.get("is_dir") else ""
                typer.echo(f"{indicator} {file_info['path']}{size}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("git-info")
def git_info(
    path: str = typer.Argument(..., help="Path to the local repository."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Show git repository metadata (current SHA, branch, remote URL)."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)

        git_data = {
            "current_sha": repo.current_sha,
            "current_sha_short": repo.current_sha_short,
            "current_branch": repo.current_branch,
            "remote_url": repo.remote_url,
        }

        if output:
            import json

            Path(output).write_text(json.dumps(git_data, indent=2))
            typer.echo(f"Git info exported to {output}")
        else:
            # Human-readable format
            typer.echo("Git Repository Information:")
            typer.echo("-" * 30)
            if git_data["current_sha"]:
                typer.echo(f"Current SHA:     {git_data['current_sha']}")
                typer.echo(f"Short SHA:       {git_data['current_sha_short']}")
            if git_data["current_branch"]:
                typer.echo(f"Current Branch:  {git_data['current_branch']}")
            else:
                typer.echo("Current Branch:  (detached HEAD)")
            if git_data["remote_url"]:
                typer.echo(f"Remote URL:      {git_data['remote_url']}")

            # Check if any git info is missing
            if not any(git_data.values()):
                typer.echo("Not a git repository or no git metadata available.")

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("grep")
def grep_command(
    path: str = typer.Argument(..., help="Path to the local repository."),
    pattern: str = typer.Argument(..., help="Literal string to search for."),
    case_sensitive: bool = typer.Option(True, "--case-sensitive/--ignore-case", "-c/-i", help="Case sensitive search."),
    include: Optional[str] = typer.Option(None, "--include", help="Include files matching pattern (e.g., '*.py')."),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="Exclude files matching pattern."),
    max_results: int = typer.Option(1000, "--max-results", "-n", help="Maximum number of results to return."),
    directory: Optional[str] = typer.Option(None, "--directory", "-d", help="Limit search to specific directory."),
    include_hidden: bool = typer.Option(False, "--include-hidden", help="Include hidden directories in search."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Perform literal grep search on repository files.

    By default, excludes common directories like node_modules, __pycache__, .git,
    build directories, and hidden directories for better performance.

    Examples:
        kit grep . "TODO" --ignore-case --include "*.py"
        kit grep . "function main" --exclude "*.test.js" --directory "src"
        kit grep . "config" --include-hidden  # Search hidden directories too
    """
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        matches = repo.grep(
            pattern,
            case_sensitive=case_sensitive,
            include_pattern=include,
            exclude_pattern=exclude,
            max_results=max_results,
            directory=directory,
            include_hidden=include_hidden,
        )

        if output:
            Path(output).write_text(json.dumps(matches, indent=2))
            typer.echo(f"Grep results written to {output}")
        else:
            if not matches:
                typer.echo(f"No matches found for '{pattern}'")
            else:
                typer.echo(f"Found {len(matches)} matches for '{pattern}':")
                for match in matches:
                    typer.echo(f"📄 {match['file']}:{match['line_number']}: {match['line_content'].strip()}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("index")
def index(
    path: str = typer.Argument(..., help="Path to the local repository."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
):
    """Build and return a comprehensive index of the repository."""
    from kit import Repository

    try:
        repo = Repository(path)
        index_data = repo.index()

        if output:
            Path(output).write_text(json.dumps(index_data, indent=2))
            typer.echo(f"Repository index written to {output}")
        else:
            typer.echo(json.dumps(index_data, indent=2))
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("review")
def review_pr(
    init_config: bool = typer.Option(False, "--init-config", help="Create a default configuration file and exit"),
    target: str = typer.Argument("", help="GitHub PR URL or local diff (e.g., main..feature, HEAD~3)"),
    staged: bool = typer.Option(False, "--staged", help="Review staged changes"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: ~/.kit/review-config.yaml)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override LLM model (e.g., gpt-4.1-nano, claude-sonnet-4-20250514)",
    ),
    priority: Optional[str] = typer.Option(
        None,
        "--priority",
        "-P",
        help="Filter by priority level (comma-separated): high, medium, low. Default: all",
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Custom context profile to use for review guidelines"
    ),
    plain: bool = typer.Option(False, "--plain", "-p", help="Output raw review content for piping (no formatting)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Don't post comment, just show what would be posted"),
    agentic: bool = typer.Option(
        False, "--agentic", help="Use multi-turn agentic analysis (more thorough but expensive)"
    ),
    agentic_turns: int = typer.Option(
        15, "--agentic-turns", help="Number of analysis turns for agentic mode (default: 15)"
    ),
    repo_path: Optional[str] = typer.Option(
        None, "--repo-path", help="Path to existing repository (skips cloning, uses current state)"
    ),
):
    """Review a GitHub PR or local diff using kit's repository intelligence and AI analysis."""
    from kit.pr_review.config import ReviewConfig
    from kit.pr_review.local_reviewer import LocalDiffReviewer
    from kit.pr_review.reviewer import PRReviewer

    if init_config:
        try:
            # Create default config without needing ReviewConfig.from_file()
            config_path = config or "~/.kit/review-config.yaml"
            config_path = str(Path(config_path).expanduser())

            # Create a temporary ReviewConfig just to use the create_default_config_file method
            from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider

            temp_config = ReviewConfig(
                github=GitHubConfig(token="temp"),
                llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="temp", api_key="temp"),
            )

            created_path = temp_config.create_default_config_file(config_path)
            typer.echo(f"✅ Created default config file at: {created_path}")
            typer.echo("\n📝 Next steps:")
            typer.echo("1. Edit the config file to add your tokens")
            typer.echo(
                "2. Set KIT_GITHUB_TOKEN and either KIT_ANTHROPIC_TOKEN or KIT_OPENAI_TOKEN environment variables, or"
            )
            typer.echo("3. Update the config file with your actual tokens")
            typer.echo("\n💡 Then try:")
            typer.echo("   - GitHub PR: kit review --dry-run https://github.com/owner/repo/pull/123")
            typer.echo("   - Local diff: kit review --dry-run main..feature")
            return
        except Exception as e:
            typer.secho(f"❌ Failed to create config: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    # Handle --staged flag
    if staged:
        target = "--staged"
    elif not target:
        typer.secho("❌ Target is required", fg=typer.colors.RED)
        typer.echo("\n💡 Examples:")
        typer.echo("  - GitHub PR: kit review https://github.com/owner/repo/pull/123")
        typer.echo("  - Local diff: kit review main..feature")
        typer.echo("  - Staged changes: kit review --staged")
        typer.echo("💡 Or run: kit review --help")
        raise typer.Exit(code=1)

    try:
        # Load configuration with profile support and model hint
        review_config = ReviewConfig.from_file(config, profile, repo_path=repo_path, model_hint=model)

        # Show profile info if one is being used
        if profile and not plain:
            typer.echo(f"📋 Using profile: {profile}")

        # Show repo path info if one is being used
        if repo_path and not plain:
            typer.echo(f"📁 Using existing repository: {repo_path}")
            typer.echo("⚠️ WARNING: Analysis will be performed against current local state")

        # Parse priority filter
        if priority:
            try:
                from kit.pr_review.priority_utils import Priority

                priority_levels = [p.strip() for p in priority.split(",")]
                validated_priorities = Priority.validate_priorities(priority_levels)
                review_config.priority_filter = validated_priorities
                if not plain:
                    typer.echo(f"🔍 Priority filter: {', '.join(validated_priorities)}")
            except ValueError as e:
                handle_cli_error(e, "Priority filter error", "Valid priorities: high, medium, low")
        else:
            review_config.priority_filter = None

        # Override model if specified
        if model:
            # Auto-detect provider from model name
            from kit.pr_review.config import _detect_provider_from_model

            detected_provider = _detect_provider_from_model(model)

            if detected_provider and detected_provider != review_config.llm.provider:
                # Switch provider and update API key
                from kit.pr_review.config import LLMProvider

                old_provider = review_config.llm.provider.value
                review_config.llm.provider = detected_provider

                # Update API key for new provider
                if detected_provider == LLMProvider.ANTHROPIC:
                    new_api_key = os.getenv("KIT_ANTHROPIC_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires Anthropic API key"),
                            "Configuration error",
                            "Set KIT_ANTHROPIC_TOKEN environment variable",
                        )
                else:  # OpenAI
                    new_api_key = os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires OpenAI API key"),
                            "Configuration error",
                            "Set KIT_OPENAI_TOKEN environment variable",
                        )

                # Assert for mypy that new_api_key is not None after error checks
                assert new_api_key is not None
                review_config.llm.api_key = new_api_key
                review_config.llm.provider = detected_provider
                review_config.llm_provider = detected_provider.value
                typer.echo(f"🔄 Switched provider: {old_provider} → {detected_provider.value}")

            review_config.llm.model = model
            review_config.llm_model = model
            if not plain:  # Only show this message if not in plain mode
                typer.echo(f"🎛️  Overriding model to: {model}")

        # Override comment posting if dry run or plain mode
        if dry_run or plain:
            review_config.post_as_comment = False
            if not plain:  # Only show this message if not in plain mode
                typer.echo("🔍 Dry run mode - will not post comments")

        # Set quiet mode for plain output
        if plain:
            # Set quiet mode to suppress all status output
            review_config.quiet = True

        # Configure agentic settings if requested
        if agentic:
            review_config.agentic_max_turns = agentic_turns
            if not plain:  # Only show this message if not in plain mode
                print(f"🤖 Agentic mode configured - max turns: {agentic_turns}")
                if agentic_turns <= 8:
                    print("💰 Expected cost: ~$0.36-0.80 (budget mode)")
                elif agentic_turns <= 15:
                    print("💰 Expected cost: ~$0.80-1.50 (standard mode)")
                else:
                    print("💰 Expected cost: ~$1.50-2.57 (extended mode)")
        else:
            if not plain:  # Only show this message if not in plain mode
                print("🛠️ Standard mode configured - repository intelligence enabled")

        # Determine if target is a PR URL or local diff
        is_pr_url = (
            isinstance(target, str) and target.startswith("http") and "github.com" in target and "/pull/" in target
        )

        # Create reviewer and run review
        if is_pr_url:
            # GitHub PR review
            if agentic:
                from kit.pr_review.agentic_reviewer import AgenticPRReviewer

                agentic_reviewer = AgenticPRReviewer(review_config)
                comment = agentic_reviewer.review_pr_agentic(target)
            else:
                standard_reviewer = PRReviewer(review_config)
                comment = standard_reviewer.review_pr(target)
        else:
            # Local diff review
            if agentic:
                typer.secho("⚠️  Agentic mode is not yet supported for local diffs", fg=typer.colors.YELLOW)
                raise typer.Exit(code=1)

            # Use current directory or specified repo path
            local_repo_path = repo_path or "."
            local_reviewer = LocalDiffReviewer(review_config, local_repo_path)
            comment = local_reviewer.review(target)

        # Handle output based on mode
        if plain:
            # Plain mode: just output the review content for piping
            typer.echo(comment)
        elif dry_run:
            # Dry run mode: show formatted preview
            typer.echo("\n" + "=" * 60)
            typer.echo("REVIEW COMMENT THAT WOULD BE POSTED:")
            typer.echo("=" * 60)
            typer.echo(comment)
            typer.echo("=" * 60)
        else:
            # Normal mode: check if there were actually changes to review
            if comment.strip() == "No changes to review.":
                typer.echo("No changes to review.")
            else:
                # Show the review content by default
                typer.echo(comment)
                # Show completion message after the review
                if is_pr_url:
                    typer.echo("\n✅ Review completed and comment posted!")
                else:
                    typer.echo("\n✅ Review completed!")

    except ValueError as e:
        typer.secho(f"❌ Configuration error: {e}", fg=typer.colors.RED)
        typer.echo("\n💡 Try running: kit review --init-config")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Review failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("review-cache")
def review_cache(
    action: str = typer.Argument(..., help="Action: status, cleanup, clear"),
    max_size: Optional[float] = typer.Option(None, "--max-size", help="Maximum cache size in GB (for cleanup)"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Manage repository cache for PR reviews."""
    from kit.pr_review.cache import RepoCache
    from kit.pr_review.config import ReviewConfig

    try:
        # Load configuration
        review_config = ReviewConfig.from_file(config)
        cache = RepoCache(review_config)

        if action == "status":
            if cache.cache_dir.exists():
                # Calculate cache size
                total_size = sum(f.stat().st_size for f in cache.cache_dir.rglob("*") if f.is_file()) / (
                    1024**3
                )  # Convert to GB

                # Count repositories
                repo_count = 0
                for owner_dir in cache.cache_dir.iterdir():
                    if owner_dir.is_dir():
                        repo_count += len([d for d in owner_dir.iterdir() if d.is_dir()])

                typer.echo(f"📁 Cache location: {cache.cache_dir}")
                typer.echo(f"📊 Cache size: {total_size:.2f} GB")
                typer.echo(f"📦 Cached repositories: {repo_count}")
                typer.echo(f"⏰ TTL: {review_config.cache_ttl_hours} hours")
            else:
                typer.echo("📭 No cache directory found")

        elif action == "cleanup":
            cache.cleanup_cache(max_size)
            typer.echo("✅ Cache cleanup completed")

        elif action == "clear":
            cache.clear_cache()
            typer.echo("✅ Cache cleared")

        else:
            typer.secho(f"❌ Unknown action: {action}. Use: status, cleanup, clear", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    except Exception as e:
        typer.secho(f"❌ Cache operation failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("review-profile")
def review_profile_command(
    action: str = typer.Argument(..., help="Action: create, list, show, edit, delete, copy, export, import"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Profile name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Profile description"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="File to read context from or export to"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    target: Optional[str] = typer.Option(None, "--target", help="Target name for copy operation"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, names"),
):
    """Manage custom context profiles for PR reviews."""
    from kit.pr_review.profile_manager import ProfileManager

    try:
        profile_manager = ProfileManager()

        if action == "create":
            if not name:
                typer.secho("❌ Profile name is required for create", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if not description:
                typer.secho("❌ Profile description is required for create", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if file:
                # Create from file
                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                profile = profile_manager.create_profile_from_file(name, description, file, tag_list)
                typer.echo(f"✅ Created profile '{name}' from file '{file}'")
            else:
                # Create from interactive input
                typer.echo(
                    "Enter the custom context (type your content, press Enter for new lines, then Ctrl+D to finish):"
                )
                try:
                    import sys

                    context_lines = []
                    try:
                        for line in sys.stdin:
                            context_lines.append(line.rstrip("\n"))
                    except EOFError:
                        # Handle explicit EOF gracefully
                        pass

                    context = "\n".join(context_lines)

                    if not context.strip():
                        typer.secho("❌ Context cannot be empty", fg=typer.colors.RED)
                        raise typer.Exit(code=1)

                except KeyboardInterrupt:
                    typer.echo("\n❌ Creation cancelled")
                    raise typer.Exit(code=1)

                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                profile = profile_manager.create_profile(name, description, context, tag_list)
                typer.echo(f"✅ Created profile '{name}'")

        elif action == "list":
            profiles = profile_manager.list_profiles()

            if not profiles:
                typer.echo("📭 No profiles found")
                return

            if format == "json":
                import json

                profile_data = [
                    {
                        "name": p.name,
                        "description": p.description,
                        "tags": p.tags,
                        "created_at": p.created_at,
                        "updated_at": p.updated_at,
                    }
                    for p in profiles
                ]
                typer.echo(json.dumps(profile_data, indent=2))
            elif format == "names":
                for profile in profiles:
                    typer.echo(profile.name)
            else:  # table format
                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("Name", style="cyan")
                table.add_column("Description")
                table.add_column("Tags", style="yellow")
                table.add_column("Created", style="dim")

                for profile in profiles:
                    created_date = profile.created_at.split("T")[0] if "T" in profile.created_at else profile.created_at
                    tags_str = ", ".join(profile.tags) if profile.tags else ""
                    table.add_row(profile.name, profile.description, tags_str, created_date)

                console.print(table)

        elif action == "show":
            if not name:
                typer.secho("❌ Profile name is required for show", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            profile = profile_manager.get_profile(name)

            typer.echo(f"📋 Profile: {profile.name}")
            typer.echo(f"📝 Description: {profile.description}")
            if profile.tags:
                typer.echo(f"🏷️  Tags: {', '.join(profile.tags)}")
            typer.echo(f"📅 Created: {profile.created_at}")
            typer.echo(f"📅 Updated: {profile.updated_at}")
            typer.echo("\n📄 Context:")
            typer.echo("-" * 50)
            typer.echo(profile.context)

        elif action == "edit":
            if not name:
                typer.secho("❌ Profile name is required for edit", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            # Get current profile
            current_profile = profile_manager.get_profile(name)

            # Update fields if provided
            new_description = description if description else current_profile.description
            new_tags = [tag.strip() for tag in tags.split(",")] if tags else current_profile.tags

            if file:
                # Update context from file
                new_context = Path(file).read_text(encoding="utf-8")
            else:
                # Interactive context editing
                typer.echo(f"Current context for '{name}':")
                typer.echo("-" * 30)
                typer.echo(current_profile.context)
                typer.echo("-" * 30)
                typer.echo(
                    "Enter new context (type content, press Enter for new lines, then Ctrl+D to finish, or Ctrl+C to keep current):"
                )

                try:
                    import sys

                    context_lines = []
                    for line in sys.stdin:
                        context_lines.append(line.rstrip("\n"))
                    new_context = "\n".join(context_lines)
                    if not new_context.strip():
                        new_context = current_profile.context
                except KeyboardInterrupt:
                    new_context = current_profile.context
                    typer.echo("\n⏭️  Keeping current context")

            profile_manager.update_profile(name, new_description, new_context, new_tags)
            typer.echo(f"✅ Updated profile '{name}'")

        elif action == "delete":
            if not name:
                typer.secho("❌ Profile name is required for delete", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            if profile_manager.delete_profile(name):
                typer.echo(f"✅ Deleted profile '{name}'")
            else:
                typer.secho(f"❌ Profile '{name}' not found", fg=typer.colors.RED)
                raise typer.Exit(code=1)

        elif action == "copy":
            if not name or not target:
                typer.secho("❌ Both --name and --target are required for copy", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            profile_manager.copy_profile(name, target)
            typer.echo(f"✅ Copied profile '{name}' to '{target}'")

        elif action == "export":
            if not name or not file:
                typer.secho("❌ Both --name and --file are required for export", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            profile_manager.export_profile(name, file)
            typer.echo(f"✅ Exported profile '{name}' to '{file}'")

        elif action == "import":
            if not file:
                typer.secho("❌ --file is required for import", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            profile = profile_manager.import_profile(file, name)
            typer.echo(f"✅ Imported profile '{profile.name}' from '{file}'")

        else:
            typer.secho(f"❌ Unknown action: {action}", fg=typer.colors.RED)
            typer.echo("Valid actions: create, list, show, edit, delete, copy, export, import")
            raise typer.Exit(code=1)

    except ValueError as e:
        typer.secho(f"❌ Profile error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Profile operation failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("search")
def search_text(
    path: str = typer.Argument(..., help="Path to the local repository."),
    query: str = typer.Argument(..., help="Text or regex pattern to search for."),
    pattern: str = typer.Option("*", "--pattern", "-p", help="Glob pattern for files to search."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Perform a textual search in a local repository."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        results = repo.search_text(query, file_pattern=pattern)

        if output:
            Path(output).write_text(json.dumps(results, indent=2))
            typer.echo(f"Search results written to {output}")
        else:
            if results:
                for res in results:
                    file_rel = res["file"].replace(str(repo.local_path), "").lstrip("/")
                    typer.echo(f"{file_rel}:{res['line_number']}: {res['line'].strip()}")
            else:
                typer.echo("No results found.")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Run the kit REST API server."""
    try:
        import uvicorn

        from kit.api import app as fastapi_app
    except ImportError:
        typer.secho(
            "Error: FastAPI or Uvicorn not installed. Please reinstall kit: `pip install cased-kit`",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Starting kit API server on http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port, reload=reload)


@app.command("summarize")
def summarize_pr(
    pr_url: str = typer.Argument(..., help="GitHub PR URL (https://github.com/owner/repo/pull/123)"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: ~/.kit/review-config.yaml)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Override LLM model (e.g., gpt-4.1-nano, claude-sonnet-4-20250514)"
    ),
    plain: bool = typer.Option(False, "--plain", "-p", help="Output raw summary content for piping (no formatting)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to file instead of stdout"),
    update_pr_body: bool = typer.Option(
        False, "--update-pr-body", "-u", help="Update the PR description with the summary"
    ),
    repo_path: Optional[str] = typer.Option(
        None, "--repo-path", help="Path to existing repository (skips cloning, uses current state)"
    ),
):
    """Generate a concise summary of a GitHub PR using kit's repository intelligence."""
    from kit.pr_review.config import ReviewConfig
    from kit.pr_review.summarizer import PRSummarizer

    try:
        # Load configuration (can reuse same config as review)
        review_config = ReviewConfig.from_file(config, repo_path=repo_path)

        # Show repo path info if one is being used
        if repo_path and not plain:
            typer.echo(f"📁 Using existing repository: {repo_path}")
            typer.echo("⚠️ WARNING: Analysis will be performed against current local state")

        # Override model if specified
        if model:
            # Auto-detect provider from model name
            from kit.pr_review.config import _detect_provider_from_model

            detected_provider = _detect_provider_from_model(model)

            if detected_provider and detected_provider != review_config.llm.provider:
                # Switch provider and update API key
                from kit.pr_review.config import LLMProvider

                old_provider = review_config.llm.provider.value
                review_config.llm.provider = detected_provider

                # Update API key for new provider
                if detected_provider == LLMProvider.ANTHROPIC:
                    new_api_key = os.getenv("KIT_ANTHROPIC_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires Anthropic API key"),
                            "Configuration error",
                            "Set KIT_ANTHROPIC_TOKEN environment variable",
                        )
                elif detected_provider == LLMProvider.GOOGLE:
                    new_api_key = os.getenv("KIT_GOOGLE_TOKEN") or os.getenv("GOOGLE_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires Google API key"),
                            "Configuration error",
                            "Set KIT_GOOGLE_TOKEN environment variable",
                        )
                elif detected_provider == LLMProvider.OLLAMA:
                    new_api_key = "not_required"  # Ollama doesn't need API key
                else:  # OpenAI
                    new_api_key = os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")
                    if not new_api_key:
                        handle_cli_error(
                            ValueError(f"Model {model} requires OpenAI API key"),
                            "Configuration error",
                            "Set KIT_OPENAI_TOKEN environment variable",
                        )

                # Assert for mypy that new_api_key is not None after error checks
                assert new_api_key is not None
                review_config.llm.api_key = new_api_key
                review_config.llm.provider = detected_provider
                review_config.llm_provider = detected_provider.value
                if not plain:
                    typer.echo(f"🔄 Switched provider: {old_provider} → {detected_provider.value}")

            review_config.llm.model = model
            review_config.llm_model = model
            if not plain:
                typer.echo(f"🎛️  Using model: {model}")

        # Set quiet mode for plain output
        if plain:
            review_config.quiet = True

        # Never post comments for summarization
        review_config.post_as_comment = False

        # Create summarizer and run summarization
        summarizer = PRSummarizer(review_config)
        summary = summarizer.summarize_pr(pr_url, update_body=update_pr_body)

        # Handle output
        if output:
            # Write to file
            with open(output, "w", encoding="utf-8") as f:
                f.write(summary)
            if not plain:
                typer.echo(f"✅ Summary saved to: {output}")
        else:
            # Output to stdout
            if plain:
                typer.echo(summary)
            else:
                typer.echo("\n" + "=" * 60)
                typer.echo("PR SUMMARY")
                typer.echo("=" * 60)
                typer.echo(summary)
                typer.echo("=" * 60)

        # Show update status
        if update_pr_body and not plain:
            typer.echo("✅ PR description updated with AI summary!")

    except ValueError as e:
        typer.secho(f"❌ Configuration error: {e}", fg=typer.colors.RED)
        typer.echo("\n💡 Try running: kit review --init-config")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Summarization failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("symbols")
def extract_symbols(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="Extract symbols from specific file only."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    format: str = typer.Option("table", "--format", help="Output format: table, json, or names"),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Extract code symbols (functions, classes, etc.) from the repository."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        symbols = repo.extract_symbols(file_path)

        if output:
            Path(output).write_text(json.dumps(symbols, indent=2))
            typer.echo(f"Symbols written to {output}")
        elif format == "json":
            typer.echo(json.dumps(symbols, indent=2))
        elif format == "names":
            for symbol in symbols:
                typer.echo(symbol["name"])
        else:  # table format
            if symbols:
                typer.echo(f"{'Name':<30} {'Type':<15} {'File':<40} {'Lines'}")
                typer.echo("-" * 95)
                for symbol in symbols:
                    file_rel = symbol.get("file", "").replace(str(repo.local_path), "").lstrip("/")
                    lines = f"{symbol.get('start_line', 'N/A')}-{symbol.get('end_line', 'N/A')}"
                    typer.echo(f"{symbol['name']:<30} {symbol['type']:<15} {file_rel:<40} {lines}")
            else:
                typer.echo("No symbols found.")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("usages")
def find_symbol_usages(
    path: str = typer.Argument(..., help="Path to the local repository."),
    symbol_name: str = typer.Argument(..., help="Name of the symbol to find usages for."),
    symbol_type: Optional[str] = typer.Option(None, "--type", "-t", help="Symbol type filter (function, class, etc.)."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Find definitions and references of a specific symbol."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        usages = repo.find_symbol_usages(symbol_name, symbol_type)

        if output:
            Path(output).write_text(json.dumps(usages, indent=2))
            typer.echo(f"Symbol usages written to {output}")
        else:
            if usages:
                typer.echo(f"Found {len(usages)} usage(s) of '{symbol_name}':")
                for usage in usages:
                    file_rel = usage.get("file", "").replace(str(repo.local_path), "").lstrip("/")
                    line = usage.get("line_number", usage.get("line", "N/A"))
                    context = usage.get("line_content") or usage.get("context") or ""
                    if context:
                        context = str(context).strip()
                    typer.echo(f"{file_rel}:{line}: {context}")
            else:
                typer.echo(f"No usages found for symbol '{symbol_name}'.")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("search-semantic")
def search_semantic(
    path: str = typer.Argument(..., help="Path to the local repository."),
    query: str = typer.Argument(..., help="Natural language query to search for."),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Maximum number of results to return."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2", "--embedding-model", "-e", help="SentenceTransformers model name for embeddings."
    ),
    chunk_by: str = typer.Option("symbols", "--chunk-by", "-c", help="Chunking strategy: 'symbols' or 'lines'."),
    build_index: bool = typer.Option(
        False, "--build-index/--no-build-index", help="Force rebuild of vector index (default: false)."
    ),
    persist_dir: Optional[str] = typer.Option(None, "--persist-dir", "-p", help="Directory to persist vector index."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: table, json, plain"),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Perform semantic search using vector embeddings and natural language queries.

    This command uses vector embeddings to find code based on meaning rather than just keywords.
    It requires the 'sentence-transformers' package for embedding generation.

    Examples:
        kit search-semantic . "authentication logic"
        kit search-semantic . "error handling patterns" --top-k 10
        kit search-semantic . "database connection" --chunk-by lines
        kit search-semantic . "user registration" --embedding-model all-mpnet-base-v2
    """
    from kit import Repository

    try:
        # Import sentence-transformers with helpful error message
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            typer.secho("❌ The 'sentence-transformers' package is required for semantic search.", fg=typer.colors.RED)
            typer.echo("💡 Install it with: pip install sentence-transformers")
            typer.echo("💡 Or install kit with semantic search support: pip install 'cased-kit[ml]'")
            raise typer.Exit(code=1)

        # Validate chunk_by parameter
        if chunk_by not in ["symbols", "lines"]:
            typer.secho(f"❌ Invalid chunk_by value: {chunk_by}. Use 'symbols' or 'lines'.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Initialize repository
        try:
            repo = Repository(path, ref=ref)
        except Exception as e:
            if format == "plain":
                typer.echo(f"Error: {e}")
            else:
                typer.secho(f"Error: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Load embedding model
        if format not in ["plain", "json"]:
            typer.echo(f"Loading embedding model: {embedding_model}")
        try:
            model = SentenceTransformer(embedding_model)
        except Exception as e:
            if format == "plain":
                typer.echo(f"Failed to load embedding model '{embedding_model}': {e}")
                typer.echo("Popular models: all-MiniLM-L6-v2, all-mpnet-base-v2, paraphrase-MiniLM-L6-v2")
            else:
                typer.secho(f"Failed to load embedding model '{embedding_model}': {e}", fg=typer.colors.RED)
                typer.echo("Popular models: all-MiniLM-L6-v2, all-mpnet-base-v2, paraphrase-MiniLM-L6-v2")
            raise typer.Exit(code=1)

        # Create embedding function
        def embed_fn(texts):
            if isinstance(texts, str):
                # Single string input - return single embedding
                return model.encode(texts).tolist()
            else:
                # List of strings - return list of embeddings
                return model.encode(texts).tolist()

        # Get or create vector searcher
        if format not in ["plain", "json"]:
            typer.echo("Initializing vector searcher...")
        try:
            vector_searcher = repo.get_vector_searcher(embed_fn=embed_fn, persist_dir=persist_dir)
        except Exception as e:
            if format == "plain":
                typer.echo(f"Failed to initialize vector searcher: {e}")
            else:
                typer.secho(f"Failed to initialize vector searcher: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Check if index exists
        try:
            index_exists = vector_searcher.backend.count() > 0
        except Exception:
            index_exists = False

        # Build index if requested or if it doesn't exist
        if build_index or not index_exists:
            if format not in ["plain", "json"]:
                if build_index:
                    typer.echo(f"Rebuilding vector index (chunking by {chunk_by})...")
                else:
                    typer.echo(f"Building vector index for the first time (chunking by {chunk_by})...")
            try:
                vector_searcher.build_index(chunk_by=chunk_by)
                if format not in ["plain", "json"]:
                    typer.echo("Vector index built successfully")
            except Exception as e:
                if format == "plain":
                    typer.echo(f"Failed to build vector index: {e}")
                else:
                    typer.secho(f"Failed to build vector index: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)
        else:
            if format not in ["plain", "json"]:
                typer.echo("Using existing vector index")

        # Perform semantic search
        if format not in ["plain", "json"]:
            typer.echo(f"Searching for: '{query}'")
        try:
            results = repo.search_semantic(query, top_k=top_k, embed_fn=embed_fn)
        except Exception as e:
            if format == "plain":
                typer.echo(f"Semantic search failed: {e}")
                if "collection" in str(e).lower():
                    typer.echo("The vector index might not exist. Try with --build-index")
            else:
                typer.secho(f"Semantic search failed: {e}", fg=typer.colors.RED)
                # Try to provide helpful error message
                if "collection" in str(e).lower():
                    typer.echo("The vector index might not exist. Try with --build-index")
            raise typer.Exit(code=1)

        # Output results
        if output:
            Path(output).write_text(json.dumps(results, indent=2))
            if format == "plain":
                typer.echo(f"Semantic search results written to {output}")
            else:
                typer.echo(f"Semantic search results written to {output}")
        else:
            if not results:
                if format == "plain":
                    typer.echo(f"No semantic matches found for '{query}'")
                    typer.echo("Try building the index with --build-index or using different keywords")
                else:
                    typer.echo(f"No semantic matches found for '{query}'")
                    typer.echo("Try building the index with --build-index or using different keywords")
            else:
                if format == "json":
                    typer.echo(json.dumps(results, indent=2))
                elif format == "plain":
                    for result in results:
                        file_path = result.get("file", "Unknown file")
                        score = result.get("score", 0)
                        typer.echo(f"{file_path}:{score:.3f}")
                else:  # table format
                    typer.echo(f"Found {len(results)} semantic matches:")
                    for i, result in enumerate(results, 1):
                        file_path = result.get("file", "Unknown file")
                        name = result.get("name", "")
                        symbol_type = result.get("type", "")
                        score = result.get("score", 0)

                        # Format the result display
                        if name and symbol_type:
                            typer.echo(f"{i}. {file_path} - {symbol_type} '{name}' (score: {score:.3f})")
                        else:
                            typer.echo(f"{i}. {file_path} (score: {score:.3f})")

                        # Show a snippet of the code if available
                        code = result.get("code", "")
                        if code:
                            # Show first 100 characters of code, cleaned up
                            code_snippet = code.strip().replace("\n", " ")[:100]
                            if len(code_snippet) == 100:
                                code_snippet += "..."
                            typer.echo(f"   {code_snippet}")
                        typer.echo()

    except Exception as e:
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("package-search-grep")
def package_search_grep_cmd(
    package: str = typer.Argument(..., help="Package name to search (e.g., 'numpy', 'django')"),
    pattern: str = typer.Argument(..., help="Regex pattern to search for"),
    max_results: int = typer.Option(20, "--max-results", "-m", help="Maximum number of results"),
    file_pattern: Optional[str] = typer.Option(
        None, "--file-pattern", "-f", help="Filter files by glob pattern (e.g., '*.py')"
    ),
    case_sensitive: bool = typer.Option(True, "--case-sensitive/--ignore-case", "-c/-i", help="Case sensitivity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    formatted: bool = typer.Option(
        False, "--formatted", "-F", help="Output with formatting and emojis (default is plain like grep)"
    ),
):
    """
    Search package source code using regex patterns (outputs plain text like grep by default).

    Examples:
        kit package-search-grep numpy "def.*fft"
        kit package-search-grep fastapi "async def" | head -10
        kit package-search-grep django "@login_required" -f "*.py"
        kit package-search-grep requests "class.*Response" --json
        kit package-search-grep flask "route" --formatted
    """
    try:
        from .package_search import ChromaPackageSearch

        client = ChromaPackageSearch()
        results = client.grep(
            package=package,
            pattern=pattern,
            max_results=max_results,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive,
        )

        if json_output:
            typer.echo(json.dumps(results, indent=2))
        elif formatted:
            # Formatted output with emojis (opt-in)
            typer.echo(f"🔍 Found {len(results)} matches in {package}:")
            for i, result in enumerate(results[:max_results], 1):
                file_path = result.get("file_path", "unknown")
                line_num = result.get("line_number", "?")
                content = result.get("content", "")
                typer.echo(f"\n{i}. {file_path}:{line_num}")
                typer.echo(f"   {content[:100]}...")
        else:
            # Default plain output like Unix grep: file:line:content
            for result in results[:max_results]:
                file_path = result.get("file_path", "unknown")
                line_num = result.get("line_number", "?")
                content = result.get("content", "").strip()
                typer.echo(f"{file_path}:{line_num}:{content}")

    except ValueError as e:
        handle_cli_error(e, "Package search error", "Check your API key and package name")
    except Exception as e:
        handle_cli_error(e, "Unexpected error")


@app.command("package-search-hybrid")
def package_search_hybrid_cmd(
    package: str = typer.Argument(..., help="Package name to search"),
    query: str = typer.Argument(..., help="Semantic search query"),
    regex_filter: Optional[str] = typer.Option(None, "--regex", "-r", help="Optional regex filter"),
    max_results: int = typer.Option(10, "--max-results", "-m", help="Maximum number of results"),
    file_pattern: Optional[str] = typer.Option(None, "--file-pattern", "-f", help="Filter files by glob pattern"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    formatted: bool = typer.Option(
        False, "--formatted", "-F", help="Output with formatting and emojis (default is plain)"
    ),
):
    """
    Semantic search with optional regex filtering in package source code (outputs plain text by default).

    Examples:
        kit package-search-hybrid numpy "fast fourier transform"
        kit package-search-hybrid django "authentication middleware" --regex "class.*Middleware"
        kit package-search-hybrid tensorflow "gradient computation" --formatted
        kit package-search-hybrid requests "HTTP pooling" --json
    """
    try:
        from .package_search import ChromaPackageSearch

        client = ChromaPackageSearch()
        results = client.hybrid_search(
            package=package,
            query=query,
            regex_filter=regex_filter,
            max_results=max_results,
            file_pattern=file_pattern,
        )

        if json_output:
            typer.echo(json.dumps(results, indent=2))
        elif formatted:
            # Formatted output with emojis (opt-in)
            typer.echo(f"🔎 Found {len(results)} relevant snippets in {package}:")
            for i, result in enumerate(results[:max_results], 1):
                file_path = result.get("file_path", "unknown")
                snippet = result.get("snippet", result.get("content", ""))[:200]
                typer.echo(f"\n{i}. {file_path}")
                typer.echo(f"   {snippet}...")
        else:
            # Default plain output: just file:snippet
            for result in results[:max_results]:
                file_path = result.get("file_path", "unknown")
                snippet = result.get("snippet", result.get("content", ""))[:200].strip()
                typer.echo(f"{file_path}:{snippet}")

    except ValueError as e:
        handle_cli_error(e, "Package search error", "Check your API key and package name")
    except Exception as e:
        handle_cli_error(e, "Unexpected error")


@app.command("package-search-read")
def package_search_read_cmd(
    package: str = typer.Argument(..., help="Package name"),
    file_path: str = typer.Argument(..., help="Path to file within package"),
    start_line: Optional[int] = typer.Option(None, "--start", "-s", help="Starting line number"),
    end_line: Optional[int] = typer.Option(None, "--end", "-e", help="Ending line number"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    plain: bool = typer.Option(False, "--plain", "-p", help="Output plain text without formatting"),
):
    """
    Read a specific file from a package.

    Examples:
        kit package-search-read numpy numpy/__init__.py
        kit package-search-read requests requests/models.py --start 100 --end 200
        kit package-search-read django django/contrib/auth/middleware.py
    """
    try:
        from .package_search import ChromaPackageSearch

        client = ChromaPackageSearch()
        content = client.read_file(
            package=package,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )

        if json_output:
            result = {
                "package": package,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "content": content,
            }
            typer.echo(json.dumps(result, indent=2))
        elif plain:
            # Plain output: just the content
            typer.echo(content)
        else:
            # Formatted output with header
            lines = f"{start_line}-{end_line}" if start_line and end_line else "all"
            typer.echo(f"📄 {package}/{file_path} (lines: {lines})")
            typer.echo("-" * 60)
            typer.echo(content)

    except ValueError as e:
        handle_cli_error(e, "Package search error", "Check your API key, package name, and file path")
    except httpx.ReadTimeout:
        typer.secho("⏱️ Request timed out. The Chroma API may be slow for this package.", fg=typer.colors.YELLOW)
        typer.secho("   Try again with a smaller file or different package.", fg=typer.colors.BRIGHT_BLACK)
        raise typer.Exit(1)
    except httpx.RemoteProtocolError as e:
        typer.secho(f"⚠️ Connection issue: {e}", fg=typer.colors.YELLOW)
        typer.secho("   The Chroma API may be having issues. Try again later.", fg=typer.colors.BRIGHT_BLACK)
        raise typer.Exit(1)
    except Exception as e:
        handle_cli_error(e, "Unexpected error")


def handle_cli_error(error: Exception, error_type: str = "Error", help_text: Optional[str] = None) -> None:
    """Consistent error handling for CLI commands."""
    if isinstance(error, ValueError):
        typer.secho(f"❌ {error_type}: {error}", fg=typer.colors.RED)
    else:
        typer.secho(f"❌ {error_type}: {error}", fg=typer.colors.RED)

    if help_text:
        typer.echo(f"💡 {help_text}")

    raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Multi-Repository Commands
# -----------------------------------------------------------------------------

multi_app = typer.Typer(help="Commands for analyzing multiple repositories together.")
app.add_typer(multi_app, name="multi")


@multi_app.command("search")
def multi_search(
    repos: List[str] = typer.Argument(..., help="Paths to repositories (space-separated)."),
    query: str = typer.Option(..., "--query", "-q", help="Text or regex pattern to search for."),
    pattern: str = typer.Option("*", "--pattern", "-p", help="Glob pattern for files to search."),
    max_per_repo: Optional[int] = typer.Option(None, "--max-per-repo", "-m", help="Max results per repo."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file."),
):
    """Search for text/regex across multiple repositories.

    Examples:
        kit multi search ~/frontend ~/backend -q "handleAuth"
        kit multi search ~/api ~/web ~/common -q "TODO" -p "*.py"
        kit multi search . ../other-repo -q "database" --max-per-repo 5
    """
    from kit import MultiRepo

    try:
        multi = MultiRepo(repos)
        results = multi.search(query, file_pattern=pattern, max_results_per_repo=max_per_repo)

        if output:
            Path(output).write_text(json.dumps(results, indent=2))
            typer.echo(f"Results written to {output}")
        else:
            if results:
                for r in results:
                    typer.echo(
                        f"[{r['repo']}] {r['file']}:{r.get('line_number', '?')}: {r.get('line_content', '').strip()}"
                    )
            else:
                typer.echo("No results found.")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@multi_app.command("symbols")
def multi_symbols(
    repos: List[str] = typer.Argument(..., help="Paths to repositories (space-separated)."),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Find specific symbol by name."),
    symbol_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (function, class, etc.)."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file."),
):
    """Find or list symbols across multiple repositories.

    Examples:
        kit multi symbols ~/frontend ~/backend -n "handleAuth"
        kit multi symbols ~/api ~/web -t function
        kit multi symbols ~/service-a ~/service-b -n "UserModel" -t class
    """
    from kit import MultiRepo

    try:
        multi = MultiRepo(repos)

        if name:
            found_symbols = multi.find_symbol(name, symbol_type=symbol_type)
            if output:
                Path(output).write_text(json.dumps(found_symbols, indent=2))
                typer.echo(f"Results written to {output}")
            else:
                if found_symbols:
                    typer.echo(f"Found {len(found_symbols)} definition(s) of '{name}':")
                    for s in found_symbols:
                        typer.echo(f"  [{s['repo']}] {s.get('file', '?')}:{s.get('line', '?')} ({s.get('type', '?')})")
                else:
                    typer.echo(f"No definitions found for '{name}'.")
        else:
            all_symbols = multi.extract_all_symbols(symbol_type=symbol_type)
            if output:
                Path(output).write_text(json.dumps(all_symbols, indent=2))
                typer.echo(f"Results written to {output}")
            else:
                for repo_name, symbols in all_symbols.items():
                    typer.echo(f"\n[{repo_name}] {len(symbols)} symbols")
                    for s in symbols[:10]:  # Show first 10 per repo
                        typer.echo(f"  {s.get('type', '?'):10} {s.get('name', '?')}")
                    if len(symbols) > 10:
                        typer.echo(f"  ... and {len(symbols) - 10} more")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@multi_app.command("deps")
def multi_deps(
    repos: List[str] = typer.Argument(..., help="Paths to repositories (space-separated)."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file."),
):
    """Audit dependencies across multiple repositories.

    Parses package.json, requirements.txt, Cargo.toml, go.mod, etc.

    Examples:
        kit multi deps ~/frontend ~/backend ~/shared-lib
        kit multi deps ~/service-* -o deps.json
    """
    from kit import MultiRepo

    try:
        multi = MultiRepo(repos)
        audit = multi.audit_dependencies()

        if output:
            Path(output).write_text(json.dumps(audit, indent=2))
            typer.echo(f"Dependency audit written to {output}")
        else:
            for repo_name, deps in audit.items():
                typer.echo(f"\n[{repo_name}]")
                for lang, packages in deps.items():
                    if packages:
                        typer.echo(f"  {lang}:")
                        for pkg, ver in list(packages.items())[:10]:
                            typer.echo(f"    {pkg}: {ver}")
                        if len(packages) > 10:
                            typer.echo(f"    ... and {len(packages) - 10} more")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@multi_app.command("summary")
def multi_summary(
    repos: List[str] = typer.Argument(..., help="Paths to repositories (space-separated)."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file."),
):
    """Generate summaries of multiple repositories.

    Shows file counts, detected languages, and extensions for each repo.

    Examples:
        kit multi summary ~/frontend ~/backend ~/mobile
        kit multi summary ~/project-* -o summary.json
    """
    from kit import MultiRepo

    try:
        multi = MultiRepo(repos)
        summaries = multi.summarize()

        if output:
            Path(output).write_text(json.dumps(summaries, indent=2))
            typer.echo(f"Summaries written to {output}")
        else:
            for repo_name, info in summaries.items():
                typer.echo(f"\n[{repo_name}]")
                typer.echo(f"  Path: {info.get('path', '?')}")
                typer.echo(f"  Files: {info.get('file_count', '?')}")
                languages = info.get("languages", {})
                if languages:
                    langs_str = ", ".join(f"{k} ({v})" for k, v in list(languages.items())[:5])
                    typer.echo(f"  Languages: {langs_str}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
