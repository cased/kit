#!/usr/bin/env python3
"""Debug CLI for PR review testing."""

from typing import Optional

import typer

app = typer.Typer(help="Debug tools for PR review testing.")


@app.command("review")
def review_pr(
    pr_url: str,
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    dry_run: bool = typer.Option(True, "--dry-run/--post", help="Run analysis but do not post comment"),
    repo_path: Optional[str] = typer.Option(None, "--repo-path", help="Path to existing repository (skips cloning)"),
):
    """Review a GitHub PR using kit analysis for testing."""
    try:
        from .config import ReviewConfig
        from .reviewer import PRReviewer

        # Load configuration
        if config:
            review_config = ReviewConfig.from_file(config, repo_path=repo_path)
        else:
            review_config = ReviewConfig.from_file(repo_path=repo_path)

        # Override post_as_comment if dry run
        if dry_run:
            review_config.post_as_comment = False

        # Run review
        reviewer = PRReviewer(review_config)
        result = reviewer.review_pr(pr_url)

        if dry_run:
            typer.echo("\n" + "=" * 50)
            typer.echo("REVIEW RESULT (DRY RUN)")
            typer.echo("=" * 50)
            typer.echo(result)
        else:
            typer.echo("✅ Review posted to PR")

    except Exception as e:
        typer.echo(f"❌ Error during review: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
