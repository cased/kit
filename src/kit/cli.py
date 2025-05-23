"""kit Command Line Interface."""

import json
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="A modular toolkit for LLM-powered codebase understanding.")


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


if __name__ == "__main__":
    app()
