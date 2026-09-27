"""
PR Sentinel CLI — entry point.

Usage examples:
  sentinel review .                          # review HEAD vs main
  sentinel review /path/to/repo --base main --head feature/my-branch
  sentinel review . --pr-title "Add OAuth" --format json
  sentinel serve                             # start the FastAPI server
  sentinel health                            # check Bob connectivity
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pr_sentinel import bob_client, orchestrator, reporter
from pr_sentinel.ingestion import load_repo_context

app = typer.Typer(
    name="sentinel",
    help="PR Sentinel — local-first PR review agent powered by IBM Bob 2.0",
    add_completion=False,
)
console = Console()


@app.command()
def review(
    repo_path: str = typer.Argument(".", help="Path to the local git repo"),
    base: str = typer.Option("main", "--base", "-b", help="Base branch/ref"),
    head: str = typer.Option("HEAD", "--head", "-H", help="Head branch/ref"),
    pr_title: str = typer.Option("", "--pr-title", "-t", help="PR title"),
    pr_description: str = typer.Option("", "--description", "-d", help="PR description"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write report to file"),
) -> None:
    """Run a full PR review on a local git repository."""

    resolved = Path(repo_path).resolve()
    if not resolved.exists():
        console.print(f"[red]Error:[/red] path not found: {resolved}")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]PR Sentinel[/bold cyan] — powered by IBM Bob 2.0\n"
            f"Repo: [green]{resolved}[/green]\n"
            f"Diff: [yellow]{base}[/yellow] → [yellow]{head}[/yellow]",
            expand=False,
        )
    )

    # Check Bob availability
    if not bob_client.is_available():
        console.print(
            "[red]⚠️  Bob is not reachable.[/red] "
            f"Make sure Bob Desktop is running at [bold]{os.getenv('BOB_API_URL', 'http://localhost:11434')}[/bold]"
        )
        raise typer.Exit(1)

    # Ingest
    console.print("\n[dim]📂 Reading repo context...[/dim]")
    try:
        ctx = load_repo_context(
            str(resolved),
            base_ref=base,
            head_ref=head,
            pr_title=pr_title,
            pr_description=pr_description,
        )
    except Exception as exc:
        console.print(f"[red]Failed to read repo:[/red] {exc}")
        raise typer.Exit(1)

    console.print(
        f"   [dim]{len(ctx.files_changed)} file(s) changed, "
        f"{sum(f.additions for f in ctx.files_changed)} additions, "
        f"{sum(f.deletions for f in ctx.files_changed)} deletions[/dim]"
    )

    # Orchestrate
    console.print()
    progress_lines: list[str] = []

    def _on_progress(msg: str) -> None:
        progress_lines.append(msg)
        console.print(f"  {msg}")

    report = orchestrator.run(ctx, progress_cb=_on_progress)

    # Render
    rendered = reporter.render(report, fmt=fmt if fmt in ("markdown", "json") else "markdown")

    console.print()

    if fmt == "json":
        console.print_json(rendered)
    else:
        console.print(Markdown(rendered))

    if output:
        out_path = Path(output)
        out_path.write_text(rendered, encoding="utf-8")
        console.print(f"\n[dim]Report written to [bold]{out_path}[/bold][/dim]")

    # Exit code: 1 if any critical/high findings
    if report.critical_count > 0 or report.high_count > 0:
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev)"),
) -> None:
    """Start the PR Sentinel FastAPI server."""
    import uvicorn
    console.print(f"[bold cyan]Starting PR Sentinel API[/bold cyan] on http://{host}:{port}")
    uvicorn.run("pr_sentinel.api:app", host=host, port=port, reload=reload)


@app.command()
def health() -> None:
    """Check connectivity to the local Bob instance."""
    bob_url = os.getenv("BOB_API_URL", "http://localhost:11434")
    reachable = bob_client.is_available()
    if reachable:
        console.print(f"[green]✅  Bob is reachable[/green] at {bob_url}")
    else:
        console.print(f"[red]❌  Bob is NOT reachable[/red] at {bob_url}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
