"""kit Command Line Interface."""

import json
import os
from pathlib import Path
from typing import Optional

import typer

from . import __version__


def version_callback(value: bool):
    if value:
        typer.echo(f"kit version {__version__}")
        raise typer.Exit()


app = typer.Typer(help="A modular toolkit for LLM-powered codebase understanding.")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
):
    """A modular toolkit for LLM-powered codebase understanding."""
    pass


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


# File Operations
@app.command("file-tree")
def file_tree(
    path: str = typer.Argument(..., help="Path to the local repository."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output to JSON file instead of stdout."),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (SHA, tag, or branch) to checkout for remote repositories."
    ),
):
    """Get the file tree structure of a repository."""
    from kit import Repository

    try:
        repo = Repository(path, ref=ref)
        tree = repo.get_file_tree()

        if output:
            Path(output).write_text(json.dumps(tree, indent=2))
            typer.echo(f"File tree written to {output}")
        else:
            for file_info in tree:
                indicator = "📁" if file_info.get("is_dir") else "📄"
                size = f" ({file_info.get('size', 0)} bytes)" if not file_info.get("is_dir") else ""
                typer.echo(f"{indicator} {file_info['path']}{size}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("file-content")
def file_content(
    path: str = typer.Argument(..., help="Path to the local repository."),
    file_path: str = typer.Argument(..., help="Relative path to the file within the repository."),
):
    """Get the content of a specific file in the repository."""
    from kit import Repository

    try:
        repo = Repository(path)
        content = repo.get_file_content(file_path)
        typer.echo(content)
    except FileNotFoundError:
        typer.secho(f"Error: File not found: {file_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
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


# Symbol Operations
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


# Search Operations
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


# Context Operations
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


# Export Operations
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


# Git Operations
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


# PR Review Operations
@app.command("review")
def review_pr(
    init_config: bool = typer.Option(False, "--init-config", help="Create a default configuration file and exit"),
    pr_url: str = typer.Argument("", help="GitHub PR URL (https://github.com/owner/repo/pull/123)"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: ~/.kit/review-config.yaml)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override LLM model (validated against supported models: e.g., gpt-4.1-nano, gpt-4.1, claude-sonnet-4-20250514)",
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
):
    """Review a GitHub PR using kit's repository intelligence and AI analysis.

    MODES:
    • Standard (~$0.01-0.05): kit review <pr-url>
    • Agentic (~$0.36-2.57): kit review --agentic <pr-url>

    EXAMPLES:
    kit review --init-config                                      # Setup
    kit review --dry-run https://github.com/owner/repo/pull/123   # Preview
    kit review --plain https://github.com/owner/repo/pull/123     # Pipe-friendly
    kit review https://github.com/owner/repo/pull/123             # Standard
    kit review --profile company-standards <pr-url>               # Use custom context
    kit review --priority=high https://github.com/owner/repo/pull/123  # Only high priority
    kit review --priority=high,medium <pr-url>                    # High and medium only
    kit review --model gpt-4.1-nano <pr-url>                      # Ultra budget
    kit review --model claude-opus-4-20250514 <pr-url>            # Premium
    kit review --agentic --agentic-turns 8 <pr-url>               # Budget agentic
    """
    from kit.pr_review.config import ReviewConfig
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
            typer.echo("\n💡 Then try: kit review --dry-run https://github.com/owner/repo/pull/123")
            return
        except Exception as e:
            typer.secho(f"❌ Failed to create config: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    if not pr_url:
        typer.secho("❌ PR URL is required", fg=typer.colors.RED)
        typer.echo("\n💡 Example: kit review https://github.com/owner/repo/pull/123")
        typer.echo("💡 Or run: kit review --help")
        raise typer.Exit(code=1)

    try:
        # Load configuration with profile support
        review_config = ReviewConfig.from_file(config, profile)

        # Show profile info if one is being used
        if profile and not plain:
            typer.echo(f"📋 Using profile: {profile}")

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
                typer.echo(f"🔄 Switched provider: {old_provider} → {detected_provider.value}")

            review_config.llm.model = model
            if not plain:  # Only show this message if not in plain mode
                typer.echo(f"🎛️  Overriding model to: {model}")

        # Validate model exists
        from kit.pr_review.cost_tracker import CostTracker

        if not CostTracker.is_valid_model(review_config.llm.model):
            suggestions = CostTracker.get_model_suggestions(review_config.llm.model)
            error_msg = f"Invalid model: {review_config.llm.model}"
            help_msg = (
                f"Did you mean: {', '.join(suggestions[:3])}?"
                if suggestions
                else "Run 'kit review --help' to see available models"
            )
            handle_cli_error(ValueError(error_msg), "Model validation error", help_msg)

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

        # Create reviewer and run review
        if agentic:
            from kit.pr_review.agentic_reviewer import AgenticPRReviewer

            agentic_reviewer = AgenticPRReviewer(review_config)
            comment = agentic_reviewer.review_pr_agentic(pr_url)
        else:
            standard_reviewer = PRReviewer(review_config)
            comment = standard_reviewer.review_pr(pr_url)

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
            # Normal mode: post comment and show success
            typer.echo("✅ Review completed and comment posted!")

    except ValueError as e:
        typer.secho(f"❌ Configuration error: {e}", fg=typer.colors.RED)
        typer.echo("\n💡 Try running: kit review --init-config")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"❌ Review failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


# Cache Management
@app.command("review-cache")
def review_cache(
    action: str = typer.Argument(..., help="Action: status, cleanup, clear"),
    max_size: Optional[float] = typer.Option(None, "--max-size", help="Maximum cache size in GB (for cleanup)"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Manage repository cache for PR reviews.

    Actions:
    - status: Show cache size and location
    - cleanup: Remove old cached repositories (optionally with --max-size)
    - clear: Remove all cached repositories

    Examples:

    # Show cache status
    kit review-cache status

    # Clean up cache to max 2GB
    kit review-cache cleanup --max-size 2.0

    # Clear all cache
    kit review-cache clear
    """
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


# Review Profile Management
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
    """Manage custom context profiles for PR reviews.

    EXAMPLES:

    # Create a profile from text input
    kit review-profile create --name company-standards --description "Company coding standards"
    # Type your guidelines, press Enter for new lines, then Ctrl+D to finish

    # Create a profile from a file
    kit review-profile create --name python-style --file python-guidelines.md --description "Python style guide"

    # List all profiles
    kit review-profile list

    # Show profile details
    kit review-profile show --name company-standards

    # Copy a profile
    kit review-profile copy --name company-standards --target team-standards

    # Export a profile
    kit review-profile export --name company-standards --file exported-standards.md

    # Import a profile
    kit review-profile import --file guidelines.md --name imported-standards

    # Delete a profile
    kit review-profile delete --name old-profile
    """
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


def handle_cli_error(error: Exception, error_type: str = "Error", help_text: Optional[str] = None) -> None:
    """Consistent error handling for CLI commands."""
    if isinstance(error, ValueError):
        typer.secho(f"❌ {error_type}: {error}", fg=typer.colors.RED)
    else:
        typer.secho(f"❌ {error_type}: {error}", fg=typer.colors.RED)

    if help_text:
        typer.echo(f"💡 {help_text}")

    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
