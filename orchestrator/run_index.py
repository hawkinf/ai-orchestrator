"""Run index for dashboard aggregation.

Reads run data from workspace and provides aggregated views for the dashboard.
Does not duplicate core logic - reads from existing state/artifacts.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

logger = logging.getLogger("ai_orchestrator.run_index")


class RunStatus(Enum):
    """Run status for dashboard display."""
    UNKNOWN = "unknown"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINT = "checkpoint"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


@dataclass
class RunSummary:
    """Summary of a single run for dashboard display."""
    run_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    task_summary: str = ""
    full_task: str = ""
    status: RunStatus = RunStatus.UNKNOWN
    current_stage: str = ""
    iteration: int = 0
    max_iterations: int = 3
    duration_seconds: int = 0
    project_type: str = "generic"
    has_checkpoint: bool = False
    checkpoint_reason: str = ""
    has_final_report: bool = False
    has_diff: bool = False
    commit_hash: str = ""
    last_error_summary: str = ""
    plan_objective: str = ""
    execution_summary: str = ""
    review_status: str = ""
    risks: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    is_corrupted: bool = False
    corruption_reason: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "task_summary": self.task_summary,
            "full_task": self.full_task,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "duration_seconds": self.duration_seconds,
            "project_type": self.project_type,
            "has_checkpoint": self.has_checkpoint,
            "checkpoint_reason": self.checkpoint_reason,
            "has_final_report": self.has_final_report,
            "has_diff": self.has_diff,
            "commit_hash": self.commit_hash,
            "last_error_summary": self.last_error_summary,
            "plan_objective": self.plan_objective,
            "execution_summary": self.execution_summary,
            "review_status": self.review_status,
            "risks": self.risks,
            "files_changed": self.files_changed,
            "is_corrupted": self.is_corrupted,
            "corruption_reason": self.corruption_reason,
        }


@dataclass
class RunMetrics:
    """Aggregated metrics for dashboard display."""
    total_runs: int = 0
    running_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    checkpoint_runs: int = 0
    blocked_runs: int = 0
    cancelled_runs: int = 0
    incomplete_runs: int = 0
    corrupted_runs: int = 0
    avg_duration_seconds: int = 0
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_runs": self.total_runs,
            "running_runs": self.running_runs,
            "completed_runs": self.completed_runs,
            "failed_runs": self.failed_runs,
            "checkpoint_runs": self.checkpoint_runs,
            "blocked_runs": self.blocked_runs,
            "cancelled_runs": self.cancelled_runs,
            "incomplete_runs": self.incomplete_runs,
            "corrupted_runs": self.corrupted_runs,
            "avg_duration_seconds": self.avg_duration_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
        }


@dataclass
class RunFilter:
    """Filter criteria for run list."""
    search_text: str = ""
    status_filter: Optional[List[RunStatus]] = None
    profile_filter: Optional[str] = None
    has_checkpoint: Optional[bool] = None
    has_error: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    def matches(self, run: RunSummary) -> bool:
        """Check if a run matches this filter."""
        # Search text
        if self.search_text:
            search_lower = self.search_text.lower()
            if not (
                search_lower in run.run_id.lower() or
                search_lower in run.task_summary.lower() or
                search_lower in run.full_task.lower()
            ):
                return False

        # Status filter
        if self.status_filter and run.status not in self.status_filter:
            return False

        # Profile filter
        if self.profile_filter and run.project_type != self.profile_filter:
            return False

        # Checkpoint filter
        if self.has_checkpoint is not None:
            if self.has_checkpoint and not run.has_checkpoint:
                return False
            if not self.has_checkpoint and run.has_checkpoint:
                return False

        # Error filter
        if self.has_error is not None:
            has_err = bool(run.last_error_summary)
            if self.has_error and not has_err:
                return False
            if not self.has_error and has_err:
                return False

        # Date range
        if self.date_from and run.created_at:
            if run.created_at < self.date_from:
                return False
        if self.date_to and run.created_at:
            if run.created_at > self.date_to:
                return False

        return True


class RunIndex:
    """
    Index for reading and aggregating run data from workspace.

    Usage:
        index = RunIndex(workspace_path)
        runs = index.get_all_runs()
        metrics = index.get_metrics()
        filtered = index.filter_runs(RunFilter(status_filter=[RunStatus.FAILED]))
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.state_dir = workspace_path / "state"
        self.runs_dir = workspace_path / "runs"
        self._cache: Dict[str, RunSummary] = {}
        self._last_scan: Optional[datetime] = None

    def refresh(self):
        """Force refresh of the index cache."""
        self._cache.clear()
        self._last_scan = None

    def get_all_runs(
        self,
        limit: Optional[int] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[RunSummary]:
        """
        Get all runs from workspace.

        Args:
            limit: Maximum number of runs to return
            sort_by: Field to sort by (created_at, updated_at, status)
            sort_desc: Sort descending if True

        Returns:
            List of RunSummary objects
        """
        self._scan_runs()

        runs = list(self._cache.values())

        # Sort
        if sort_by == "created_at":
            runs.sort(
                key=lambda r: r.created_at or datetime.min,
                reverse=sort_desc
            )
        elif sort_by == "updated_at":
            runs.sort(
                key=lambda r: r.updated_at or datetime.min,
                reverse=sort_desc
            )
        elif sort_by == "status":
            runs.sort(
                key=lambda r: r.status.value,
                reverse=sort_desc
            )

        if limit:
            runs = runs[:limit]

        return runs

    def get_run(self, run_id: str) -> Optional[RunSummary]:
        """Get a specific run by ID."""
        self._scan_runs()
        return self._cache.get(run_id)

    def filter_runs(
        self,
        filter_criteria: RunFilter,
        limit: Optional[int] = None,
    ) -> List[RunSummary]:
        """
        Get runs matching filter criteria.

        Args:
            filter_criteria: Filter to apply
            limit: Maximum runs to return

        Returns:
            Filtered list of RunSummary
        """
        all_runs = self.get_all_runs()
        filtered = [r for r in all_runs if filter_criteria.matches(r)]

        if limit:
            filtered = filtered[:limit]

        return filtered

    def get_metrics(self) -> RunMetrics:
        """Calculate aggregated metrics from all runs."""
        runs = self.get_all_runs()

        metrics = RunMetrics()
        metrics.total_runs = len(runs)

        total_duration = 0
        duration_count = 0

        for run in runs:
            if run.status == RunStatus.RUNNING:
                metrics.running_runs += 1
            elif run.status == RunStatus.COMPLETED:
                metrics.completed_runs += 1
            elif run.status == RunStatus.FAILED:
                metrics.failed_runs += 1
            elif run.status == RunStatus.CHECKPOINT:
                metrics.checkpoint_runs += 1
            elif run.status == RunStatus.BLOCKED:
                metrics.blocked_runs += 1
            elif run.status == RunStatus.CANCELLED:
                metrics.cancelled_runs += 1
            elif run.status == RunStatus.INCOMPLETE:
                metrics.incomplete_runs += 1

            if run.is_corrupted:
                metrics.corrupted_runs += 1

            if run.duration_seconds > 0:
                total_duration += run.duration_seconds
                duration_count += 1

            # Track timestamps
            if run.created_at:
                if not metrics.last_run_at or run.created_at > metrics.last_run_at:
                    metrics.last_run_at = run.created_at

            if run.status == RunStatus.COMPLETED and run.completed_at:
                if not metrics.last_success_at or run.completed_at > metrics.last_success_at:
                    metrics.last_success_at = run.completed_at

            if run.status == RunStatus.FAILED and run.updated_at:
                if not metrics.last_failure_at or run.updated_at > metrics.last_failure_at:
                    metrics.last_failure_at = run.updated_at

        if duration_count > 0:
            metrics.avg_duration_seconds = total_duration // duration_count

        return metrics

    def get_profiles(self) -> List[str]:
        """Get list of unique profiles/project types."""
        runs = self.get_all_runs()
        profiles = set()
        for run in runs:
            if run.project_type:
                profiles.add(run.project_type)
        return sorted(profiles)

    def export_to_json(self, output_path: Path) -> Path:
        """Export dashboard data to JSON."""
        runs = self.get_all_runs()
        metrics = self.get_metrics()

        data = {
            "exported_at": datetime.now().isoformat(),
            "metrics": metrics.to_dict(),
            "runs": [r.to_dict() for r in runs],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported dashboard to: {output_path}")
        return output_path

    def export_to_markdown(self, output_path: Path) -> Path:
        """Export dashboard summary to Markdown."""
        runs = self.get_all_runs()
        metrics = self.get_metrics()

        lines = [
            "# AI Orchestrator - Dashboard Export",
            "",
            f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Metrics Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Runs | {metrics.total_runs} |",
            f"| Running | {metrics.running_runs} |",
            f"| Completed | {metrics.completed_runs} |",
            f"| Failed | {metrics.failed_runs} |",
            f"| Checkpoint Pending | {metrics.checkpoint_runs} |",
            f"| Blocked | {metrics.blocked_runs} |",
            f"| Avg Duration | {metrics.avg_duration_seconds}s |",
            "",
            "---",
            "",
            "## Runs List",
            "",
        ]

        if runs:
            lines.append("| Run ID | Status | Task | Created |")
            lines.append("|--------|--------|------|---------|")
            for run in runs[:50]:  # Limit to 50 for readability
                created = run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "-"
                task = run.task_summary[:40] + "..." if len(run.task_summary) > 40 else run.task_summary
                lines.append(f"| {run.run_id[:16]} | {run.status.value.upper()} | {task} | {created} |")

            if len(runs) > 50:
                lines.append(f"\n*... and {len(runs) - 50} more runs*")
        else:
            lines.append("*No runs found*")

        lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported dashboard markdown to: {output_path}")
        return output_path

    def _scan_runs(self):
        """Scan workspace for runs and update cache."""
        if not self.state_dir.exists():
            return

        # Find all state files
        state_files = list(self.state_dir.glob("*.json"))

        for state_file in state_files:
            run_id = state_file.stem
            if run_id in self._cache:
                # Check if file was modified
                mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
                if self._cache[run_id].updated_at and mtime <= self._cache[run_id].updated_at:
                    continue

            # Load and parse
            summary = self._load_run_summary(run_id, state_file)
            if summary:
                self._cache[run_id] = summary

        self._last_scan = datetime.now()

    def _load_run_summary(self, run_id: str, state_file: Path) -> Optional[RunSummary]:
        """Load a run summary from state file."""
        summary = RunSummary(run_id=run_id)

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Parse timestamps
            if state_data.get("created_at"):
                try:
                    summary.created_at = datetime.fromisoformat(
                        state_data["created_at"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            if state_data.get("updated_at"):
                try:
                    summary.updated_at = datetime.fromisoformat(
                        state_data["updated_at"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            if state_data.get("completed_at"):
                try:
                    summary.completed_at = datetime.fromisoformat(
                        state_data["completed_at"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # Calculate duration
            if summary.created_at:
                end_time = summary.completed_at or summary.updated_at or datetime.now()
                delta = end_time - summary.created_at
                summary.duration_seconds = int(delta.total_seconds())

            # Parse task
            task_data = state_data.get("task", {})
            if isinstance(task_data, dict):
                summary.full_task = task_data.get("description", "")
                summary.project_type = task_data.get("profile", "generic")
            summary.task_summary = self._summarize_task(summary.full_task)

            # Parse status
            status_str = state_data.get("status", "unknown")
            summary.status = self._map_status(status_str, state_data)

            # Parse iteration
            summary.iteration = state_data.get("current_iteration", 0)
            summary.max_iterations = state_data.get("max_iterations", 3)

            # Current stage from status
            summary.current_stage = status_str

            # Parse checkpoint
            checkpoint = state_data.get("checkpoint")
            if checkpoint and isinstance(checkpoint, dict):
                if not checkpoint.get("resolved", True):
                    summary.has_checkpoint = True
                    summary.checkpoint_reason = checkpoint.get("reason", "")
                    if summary.status not in (RunStatus.FAILED, RunStatus.BLOCKED):
                        summary.status = RunStatus.CHECKPOINT

            # Parse plan
            plan = state_data.get("plan")
            if plan and isinstance(plan, dict):
                summary.plan_objective = plan.get("objective", "")

            # Parse iterations for execution/review info
            iterations = state_data.get("iterations", [])
            if iterations and isinstance(iterations, list):
                last_iter = iterations[-1] if iterations else {}
                if isinstance(last_iter, dict):
                    exec_report = last_iter.get("execution_report", {})
                    if isinstance(exec_report, dict):
                        summary.execution_summary = exec_report.get("summary", "")
                        summary.files_changed = exec_report.get("files_changed", [])
                        summary.risks = exec_report.get("risks", [])

                    review = last_iter.get("review_response", {})
                    if isinstance(review, dict):
                        summary.review_status = review.get("status", "")

            # Parse git
            git_result = state_data.get("git_result_final")
            if git_result and isinstance(git_result, dict):
                summary.commit_hash = git_result.get("commit_hash", "")

            # Parse error
            summary.last_error_summary = state_data.get("error_message", "")

            # Check for artifacts
            run_dir = self.runs_dir / run_id
            if run_dir.exists():
                summary.has_final_report = (
                    (run_dir / "final" / "final_report.json").exists() or
                    (run_dir / "final" / "final_report.md").exists()
                )
                summary.has_diff = (
                    (run_dir / "git" / "diff.patch").exists() or
                    (run_dir / "git" / "changes.diff").exists()
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted state file for {run_id}: {e}")
            summary.is_corrupted = True
            summary.corruption_reason = f"JSON parse error: {str(e)[:50]}"
            summary.status = RunStatus.INCOMPLETE

        except Exception as e:
            logger.warning(f"Error loading run {run_id}: {e}")
            summary.is_corrupted = True
            summary.corruption_reason = str(e)[:100]
            summary.status = RunStatus.INCOMPLETE

        return summary

    def _summarize_task(self, full_task: str, max_len: int = 80) -> str:
        """Create a short summary from full task description."""
        if not full_task:
            return "(sem descricao)"

        # Take first line or first max_len chars
        first_line = full_task.split("\n")[0].strip()
        if len(first_line) > max_len:
            return first_line[:max_len - 3] + "..."
        return first_line

    def _map_status(self, status_str: str, state_data: dict) -> RunStatus:
        """Map state status string to RunStatus enum."""
        status_lower = status_str.lower()

        if status_lower in ("running", "executing", "planning", "reviewing", "validating"):
            return RunStatus.RUNNING
        elif status_lower in ("completed", "finalized", "done"):
            return RunStatus.COMPLETED
        elif status_lower in ("failed", "error"):
            return RunStatus.FAILED
        elif status_lower in ("checkpoint", "checkpoint_pending", "awaiting_approval"):
            return RunStatus.CHECKPOINT
        elif status_lower in ("blocked", "stopped"):
            return RunStatus.BLOCKED
        elif status_lower in ("cancelled", "canceled", "aborted"):
            return RunStatus.CANCELLED
        elif status_lower in ("incomplete", "unknown", "not_started"):
            return RunStatus.INCOMPLETE
        else:
            # Check for error message as fallback
            if state_data.get("error_message"):
                return RunStatus.FAILED
            return RunStatus.UNKNOWN


def get_run_index(workspace_path: Path) -> RunIndex:
    """Factory function to create a RunIndex."""
    return RunIndex(workspace_path)
