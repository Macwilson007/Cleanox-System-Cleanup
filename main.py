import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.prompt import Confirm

from scanner import SmartScanner
from cleaner import SafeCleaner

app = typer.Typer(
    help="Cleanox: Advanced CLI System Cleaner & Optimizer",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

def format_size(size_bytes: int) -> str:
    """Helper for human-readable file sizes."""
    if size_bytes == 0: return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f}{units[i]}"

@app.command()
def scan(
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Target specific folder for analysis."),
    deep: bool = typer.Option(False, "--deep", "-d", help="Enable deep discovery for stale dev artifacts.")
):
    """
    Analyzes the system or a specific path for potential space savings.
    """
    scanner = SmartScanner()
    target = Path(path) if path else None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Scanning for junk...", total=None)
        results = scanner.scan(deep=deep, target_path=target)

    if not results:
        console.print("[green]No junk found! Your system is clean.[/green]")
        return

    table = Table(title="Cleanox Scan Results", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Potential Savings", justify="right")
    table.add_column("Description", style="dim")

    total_size = sum(r.size for r in results)
    for res in results:
        table.add_row(res.name, format_size(res.size), f"Ready to free up this space.")

    console.print(table)
    console.print(f"\n[bold yellow]Total potential savings: {format_size(total_size)}[/bold yellow]")
    console.print("\nRun [bold red]'cleanox clean'[/bold red] to start the cleanup process.")

@app.command()
def clean(
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Target only a specific folder."),
    auto: bool = typer.Option(False, "--auto", "-y", help="Skip confirmation (DANGEROUS)."),
    deep: bool = typer.Option(False, "--deep", "-d", help="Include deep-scan dev artifacts."),
    shred: bool = typer.Option(False, "--shred", "-s", help="Overwrite small files before deletion."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview deletion without executing.")
):
    """
    Frees up space by deleting identified junk files.
    """
    scanner = SmartScanner()
    cleaner = SafeCleaner(dry_run=dry_run, secure=shred)
    target = Path(path) if path else None

    if dry_run:
        console.print("[bold blue]DRY RUN ACTIVE: No files will be deleted.[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Looking for targets...", total=None)
        results = scanner.scan(deep=deep, target_path=target)

    if not results:
        console.print("[green]Nothing to clean.[/green]")
        return

    for res in results:
        should_clean = auto or Confirm.ask(f"Do you want to clean [cyan]{res.name}[/cyan] ({format_size(res.size)})?")
        if should_clean:
            success, failed = cleaner.delete_files(res.files)
            verb = "Previewed" if dry_run else "Deleted"
            console.print(f"[bold green]✓ {verb} {success} files[/bold green] in {res.name}")
            if failed > 0:
                console.print(f"[dim]! Skipped {failed} files (likely in use or protected)[/dim]")

    if target and not dry_run:
        cleaner.cleanup_empty_folders(target)

    if not dry_run:
        console.print("\n[bold green]Cleanup Complete![/bold green]")
    else:
        console.print("\n[bold blue]Dry run complete. No folders actually purged.[/bold blue]")

@app.command()
def large(
    path: str = typer.Argument(".", help="Folder to search for large files."),
    size: int = typer.Option(100, "--min-size", "-m", help="Minimum file size in MB.")
):
    """
    Discovers monstrous files taking up space in a directory.
    """
    scanner = SmartScanner()
    target = Path(path).resolve()
    
    console.print(f"[bold blue]Searching for files > {size}MB in {target}...[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Measuring monsters...", total=None)
        monsters = scanner.find_large_files(target, min_size_mb=size)

    if not monsters:
        console.print(f"[green]No monsters found. All files are under {size}MB.[/green]")
        return

    table = Table(title=f"Large Files in {target.name}", box=None)
    table.add_column("Size", style="bold red", justify="right")
    table.add_column("Path", style="dim")

    for p, s in monsters[:20]: # Show top 20
        table.add_row(format_size(s), str(p))

    console.print(table)
    if len(monsters) > 20:
        console.print(f"[dim]... and {len(monsters)-20} more monsters.[/dim]")

@app.command()
def optimize(
    dns: bool = typer.Option(True, "--dns", help="Clear the DNS resolution cache.")
):
    """
    Runs system maintenance tasks to boost performance. (Admin Required)
    """
    if dns:
        console.print("[cyan]Flushing DNS cache...[/cyan]")
        try:
            subprocess.run(["ipconfig", "/flushdns"], check=True, capture_output=True)
            console.print("[bold green]✓ DNS Cache Flushed Successfully.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]✗ Failed to flush DNS: {e}[/bold red]")

if __name__ == "__main__":
    app()
