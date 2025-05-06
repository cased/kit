"""kit Command Line Interface."""
import typer

app = typer.Typer(help="A modular toolkit for LLM-powered codebase understanding.")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Run the kit REST API server (requires `kit[api]` dependencies)."""
    try:
        import uvicorn
        from kit.api import app as fastapi_app  # Import the FastAPI app instance
    except ImportError:
        typer.secho(
            "Error: FastAPI or Uvicorn not installed. Please run `pip install kit[api]`",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Starting kit API server on http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port, reload=reload)


@app.command()
def search(
    path: str = typer.Argument(..., help="Path to the local repository."),
    query: str = typer.Argument(..., help="Text or regex pattern to search for."),
    pattern: str = typer.Option("*.py", "--pattern", "-p", help="Glob pattern for files to search.")
):
    """Perform a textual search in a local repository."""
    from kit import Repository  # Local import to avoid circular deps if CLI is imported elsewhere

    try:
        repo = Repository(path)
        results = repo.search_text(query, file_pattern=pattern)
        if results:
            for res in results:
                typer.echo(f"{res['file']}:{res['line_number']}: {res['line_content'].strip()}")
        else:
            typer.echo("No results found.")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
