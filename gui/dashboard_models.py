"""Data models for dashboard panel.

Re-exports core run index models and adds GUI-specific models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

# Re-export from core
from orchestrator.run_index import (
    RunStatus,
    RunSummary,
    RunMetrics,
    RunFilter,
    RunIndex,
    get_run_index,
)


@dataclass
class DashboardUIState:
    """Complete UI state for dashboard panel."""
    runs: List[RunSummary] = field(default_factory=list)
    metrics: Optional[RunMetrics] = None
    filter: RunFilter = field(default_factory=RunFilter)
    selected_run_id: Optional[str] = None
    is_loading: bool = False
    last_refresh: Optional[datetime] = None
    auto_refresh_enabled: bool = True
    auto_refresh_interval_ms: int = 5000
    available_profiles: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def get_selected_run(self) -> Optional[RunSummary]:
        """Get the currently selected run."""
        if not self.selected_run_id:
            return None
        for run in self.runs:
            if run.run_id == self.selected_run_id:
                return run
        return None

    def apply_filter(self) -> List[RunSummary]:
        """Apply current filter to runs."""
        return [r for r in self.runs if self.filter.matches(r)]

    def get_status_counts(self) -> Dict[RunStatus, int]:
        """Get count of runs by status."""
        counts: Dict[RunStatus, int] = {}
        for run in self.runs:
            counts[run.status] = counts.get(run.status, 0) + 1
        return counts


@dataclass
class MetricCard:
    """Model for a metric display card."""
    label: str
    value: int
    color: str = "#64748b"
    icon: str = ""
    tooltip: str = ""

    @classmethod
    def from_metrics(cls, metrics: RunMetrics) -> List["MetricCard"]:
        """Create metric cards from RunMetrics."""
        return [
            cls(
                label="Total",
                value=metrics.total_runs,
                color="#3b82f6",
                tooltip="Total de runs no workspace"
            ),
            cls(
                label="Em Execucao",
                value=metrics.running_runs,
                color="#f59e0b",
                tooltip="Runs atualmente em execucao"
            ),
            cls(
                label="Concluidas",
                value=metrics.completed_runs,
                color="#22c55e",
                tooltip="Runs finalizadas com sucesso"
            ),
            cls(
                label="Falhas",
                value=metrics.failed_runs,
                color="#ef4444",
                tooltip="Runs que falharam"
            ),
            cls(
                label="Checkpoint",
                value=metrics.checkpoint_runs,
                color="#a855f7",
                tooltip="Runs aguardando aprovacao"
            ),
            cls(
                label="Bloqueadas",
                value=metrics.blocked_runs,
                color="#6b7280",
                tooltip="Runs bloqueadas"
            ),
        ]


def get_status_display(status: RunStatus) -> tuple:
    """Get display text and color for a status."""
    status_map = {
        RunStatus.UNKNOWN: ("Desconhecido", "#6b7280"),
        RunStatus.RUNNING: ("Em Execucao", "#f59e0b"),
        RunStatus.COMPLETED: ("Concluido", "#22c55e"),
        RunStatus.FAILED: ("Falhou", "#ef4444"),
        RunStatus.CHECKPOINT: ("Checkpoint", "#a855f7"),
        RunStatus.BLOCKED: ("Bloqueado", "#6b7280"),
        RunStatus.CANCELLED: ("Cancelado", "#94a3b8"),
        RunStatus.INCOMPLETE: ("Incompleto", "#f59e0b"),
    }
    return status_map.get(status, ("?", "#6b7280"))


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "-"
    now = datetime.now()
    delta = now - dt

    if delta.days == 0:
        return dt.strftime("%H:%M:%S")
    elif delta.days == 1:
        return "Ontem " + dt.strftime("%H:%M")
    elif delta.days < 7:
        return f"{delta.days} dias atras"
    else:
        return dt.strftime("%d/%m/%Y")
