"""kit Command Line Interface."""
import typer
import os
from typing import Optional

app = typer.Typer(help="A modular toolkit for LLM-powered codebase understanding.")


@app.command()
def serve(
    host: str = "0.0.0.0", 
    port: int = 8000, 
    reload: bool = True,
    repo_path: Optional[str] = typer.Option(
        None, 
        "--repo-path", 
        help="Path to the repository to load and serve via the API."
    )
):
    """Run the kit REST API server (requires `kit[api]` dependencies)."""
    try:
        import uvicorn
        # No FastMCP import here
    except ImportError as e:
        typer.secho(
            f"Error: Necessary import failed. Ensure kit[api] dependencies are installed. Details: {e}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    # Set environment variable for the FastAPI app to pick up
    if repo_path:
        abs_repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(abs_repo_path):
            typer.secho(f"Error: Repository path not found or not a directory: {abs_repo_path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        os.environ["KIT_REPO_PATH"] = abs_repo_path
        typer.echo(f"Kit server will attempt to load repository from: {abs_repo_path}")
    else:
        if "KIT_REPO_PATH" in os.environ: del os.environ["KIT_REPO_PATH"]
        typer.echo("No --repo-path provided. Repository features will be disabled.")
    
    typer.echo(f"Starting kit REST API server on http://{host}:{port}")
    app_import_string = "kit.api.app:app" 
    uvicorn.run(app_import_string, host=host, port=port, reload=reload)


@app.command()
def search(
    path: str = typer.Argument(..., help="Path to the local repository."),
    query: str = typer.Argument(..., help="Text or regex pattern to search for."),
    pattern: str = typer.Option("*.py", "--pattern", "-p", help="Glob pattern for files to search.")
):
    """Perform a textual search in a local repository."""
    from kit import Repository

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
