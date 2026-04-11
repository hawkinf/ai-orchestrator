"""CLI interface for the orchestrator."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config, OrchestratorConfig
from .models import TaskStatus
from .paths import OrchestratorPaths
from .state_store import StateStore
from .task_engine import TaskEngine


app = typer.Typer(
    name="orchestrator",
    help="AI Orchestrator - Local development assistant orchestration system",
    add_completion=False,
)
console = Console()


def get_engine(config_path: Optional[Path] = None) -> TaskEngine:
    """Initialize and return the task engine."""
    config = load_config(config_path)
    paths = OrchestratorPaths(config.workspace_path)
    return TaskEngine(config, paths, manual_mode=True)


@app.command()
def start(
    task: str = typer.Argument(..., help="Task description"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Project profile"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Start a new task run."""
    engine = get_engine(config)
    state = engine.start(task, profile)

    console.print()
    console.print(Panel(
        f"[bold green]Run Started[/bold green]\n\n"
        f"[bold]Run ID:[/bold] {state.run_id}\n"
        f"[bold]Status:[/bold] {state.status.value}\n"
        f"[bold]Task:[/bold] {task[:80]}{'...' if len(task) > 80 else ''}",
        title="AI Orchestrator",
    ))

    console.print()
    console.print("[yellow]Next Steps:[/yellow]")
    console.print("1. Copy the planner prompt from workspace/prompts/")
    console.print("2. Paste into ChatGPT and get the response")
    console.print("3. Save response to workspace/prompts/planner_response.json")
    console.print(f"4. Run: [cyan]python -m orchestrator.main resume --run-id {state.run_id}[/cyan]")


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run ID to resume"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Resume an existing run."""
    engine = get_engine(config)
    state = engine.resume(run_id)

    if not state:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    _print_status(state)


@app.command()
def status(
    run_id: Optional[str] = typer.Argument(None, help="Run ID (optional, shows all if omitted)"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Show status of a run or all runs."""
    cfg = load_config(config)
    paths = OrchestratorPaths(cfg.workspace_path)
    store = StateStore(paths)

    if run_id:
        state = store.load_state(run_id)
        if not state:
            console.print(f"[red]Run not found: {run_id}[/red]")
            raise typer.Exit(1)
        _print_status(state)
    else:
        _print_all_runs(store)


@app.command(name="approve")
def approve_checkpoint(
    run_id: str = typer.Argument(..., help="Run ID"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Approval note"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Approve a pending checkpoint."""
    engine = get_engine(config)
    state = engine.approve_checkpoint(run_id, note)

    if not state:
        console.print(f"[red]Run not found or no pending checkpoint: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Checkpoint approved for run: {run_id}[/green]")
    _print_status(state)


@app.command(name="reject")
def reject_checkpoint(
    run_id: str = typer.Argument(..., help="Run ID"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Rejection reason"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Reject a pending checkpoint."""
    engine = get_engine(config)
    state = engine.reject_checkpoint(run_id, reason)

    if not state:
        console.print(f"[red]Run not found or no pending checkpoint: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[yellow]Checkpoint rejected for run: {run_id}[/yellow]")
    _print_status(state)


@app.command()
def validate(
    run_id: str = typer.Argument(..., help="Run ID"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Run validations for a run."""
    engine = get_engine(config)
    summary = engine.validate(run_id)

    if not summary:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    console.print()
    if summary.all_passed:
        console.print("[bold green]All validations passed![/bold green]")
    else:
        console.print("[bold red]Some validations failed[/bold red]")

    table = Table(title="Validation Results")
    table.add_column("Command", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")

    for result in summary.results:
        status = "[green]✓ Passed[/green]" if result.success else "[red]✗ Failed[/red]"
        table.add_row(result.command, status, f"{result.duration_seconds:.1f}s")

    console.print(table)


@app.command()
def finalize(
    run_id: str = typer.Argument(..., help="Run ID"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Force finalize a run (commit and complete)."""
    engine = get_engine(config)
    state = engine.finalize(run_id)

    if not state:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    _print_status(state)


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run ID"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Show detailed report for a run."""
    cfg = load_config(config)
    paths = OrchestratorPaths(cfg.workspace_path)
    store = StateStore(paths)

    state = store.load_state(run_id)
    if not state:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    # Check for final report
    report_path = paths.run_final_dir(run_id) / "final_report.md"
    if report_path.exists():
        console.print(report_path.read_text())
    else:
        _print_detailed_status(state)


@app.command(name="list")
def list_runs(
    limit: int = typer.Option(10, "--limit", "-l", help="Max runs to show"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """List recent runs."""
    cfg = load_config(config)
    paths = OrchestratorPaths(cfg.workspace_path)
    store = StateStore(paths)

    _print_all_runs(store, limit)


@app.command()
def checkpoints(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """List runs with pending checkpoints."""
    cfg = load_config(config)
    paths = OrchestratorPaths(cfg.workspace_path)
    store = StateStore(paths)

    runs = store.get_checkpoint_runs()
    if not runs:
        console.print("[green]No pending checkpoints[/green]")
        return

    table = Table(title="Pending Checkpoints")
    table.add_column("Run ID", style="cyan")
    table.add_column("Reason")
    table.add_column("Description")
    table.add_column("Created")

    for state in runs:
        if state.checkpoint:
            table.add_row(
                state.run_id,
                state.checkpoint.reason.value,
                state.checkpoint.description[:50],
                state.checkpoint.created_at.strftime("%Y-%m-%d %H:%M"),
            )

    console.print(table)


def _print_status(state):
    """Print run status."""
    status_color = {
        TaskStatus.PENDING: "yellow",
        TaskStatus.PLANNING: "blue",
        TaskStatus.EXECUTING: "blue",
        TaskStatus.REVIEWING: "blue",
        TaskStatus.VALIDATING: "blue",
        TaskStatus.CHECKPOINT: "yellow",
        TaskStatus.COMMITTING: "blue",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
        TaskStatus.CANCELLED: "red",
    }

    color = status_color.get(state.status, "white")

    console.print()
    console.print(Panel(
        f"[bold]Run ID:[/bold] {state.run_id}\n"
        f"[bold]Status:[/bold] [{color}]{state.status.value}[/{color}]\n"
        f"[bold]Task:[/bold] {state.task.description[:80]}\n"
        f"[bold]Iteration:[/bold] {state.current_iteration}\n"
        f"[bold]Created:[/bold] {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        title="Run Status",
    ))

    if state.checkpoint and not state.checkpoint.resolved:
        console.print()
        console.print(Panel(
            f"[bold]Reason:[/bold] {state.checkpoint.reason.value}\n"
            f"[bold]Description:[/bold] {state.checkpoint.description}",
            title="[yellow]Pending Checkpoint[/yellow]",
        ))
        console.print()
        console.print("[yellow]To continue:[/yellow]")
        console.print(f"  Approve: [cyan]python -m orchestrator.main approve {state.run_id}[/cyan]")
        console.print(f"  Reject:  [cyan]python -m orchestrator.main reject {state.run_id}[/cyan]")

    if state.error_message:
        console.print()
        console.print(f"[red]Error: {state.error_message}[/red]")


def _print_detailed_status(state):
    """Print detailed run status."""
    _print_status(state)

    if state.plan:
        console.print()
        console.print(Panel(
            f"[bold]Objective:[/bold] {state.plan.objective}\n"
            f"[bold]Scope:[/bold] {state.plan.scope}",
            title="Plan",
        ))

    if state.iterations:
        console.print()
        table = Table(title="Iterations")
        table.add_column("#")
        table.add_column("Status")
        table.add_column("Duration")
        table.add_column("Files Changed")

        for iteration in state.iterations:
            status = "✓" if iteration.execution_result and iteration.execution_result.success else "✗"
            duration = f"{iteration.execution_result.duration_seconds:.1f}s" if iteration.execution_result else "-"
            files = len(iteration.execution_report.files_changed) if iteration.execution_report else 0
            table.add_row(str(iteration.iteration_number), status, duration, str(files))

        console.print(table)

    if state.validation_final:
        console.print()
        status = "[green]✓ All Passed[/green]" if state.validation_final.all_passed else "[red]✗ Some Failed[/red]"
        console.print(f"[bold]Validation:[/bold] {status}")

    if state.git_result_final:
        console.print()
        console.print(f"[bold]Commit:[/bold] {state.git_result_final.commit_hash}")


def _print_all_runs(store: StateStore, limit: int = 10):
    """Print list of all runs."""
    runs = store.list_runs(limit)

    if not runs:
        console.print("[yellow]No runs found[/yellow]")
        return

    table = Table(title="Recent Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status")
    table.add_column("Task")
    table.add_column("Created")

    for run_info in runs:
        state = store.load_state(run_info["run_id"])
        if state:
            status_color = "green" if state.status == TaskStatus.COMPLETED else (
                "red" if state.status in (TaskStatus.FAILED, TaskStatus.CANCELLED) else "yellow"
            )
            table.add_row(
                state.run_id,
                f"[{status_color}]{state.status.value}[/{status_color}]",
                state.task.description[:40] + "..." if len(state.task.description) > 40 else state.task.description,
                state.created_at.strftime("%Y-%m-%d %H:%M"),
            )

    console.print(table)


if __name__ == "__main__":
    app()
