"""UI state models for checkpoint center panel.

Re-exports core models and adds UI-specific state and helpers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Re-export from core for convenience
from orchestrator.checkpoint_index import (
    CheckpointDecisionStatus,
    CheckpointDetail,
    CheckpointFilter,
    CheckpointIndex,
    CheckpointMetrics,
    CheckpointSeverity,
    CheckpointSummary,
    REASON_DISPLAY_MAP,
    REASON_SEVERITY_MAP,
    get_checkpoint_index,
)


@dataclass
class CheckpointUIState:
    """UI state for checkpoint center panel."""
    checkpoints: List[CheckpointSummary] = field(default_factory=list)
    metrics: CheckpointMetrics = field(default_factory=CheckpointMetrics)
    selected_checkpoint_id: Optional[str] = None
    selected_detail: Optional[CheckpointDetail] = None
    filter: CheckpointFilter = field(default_factory=CheckpointFilter)
    is_loading: bool = False
    error_message: str = ""
    auto_refresh_enabled: bool = True
    auto_refresh_interval_ms: int = 5000
    available_reasons: List[str] = field(default_factory=list)
    show_history: bool = False  # Toggle between pending and history view

    def get_selected_checkpoint(self) -> Optional[CheckpointSummary]:
        """Get currently selected checkpoint."""
        if not self.selected_checkpoint_id:
            return None
        for cp in self.checkpoints:
            if cp.checkpoint_id == self.selected_checkpoint_id:
                return cp
        return None

    def apply_filter(self) -> List[CheckpointSummary]:
        """Apply current filter to checkpoints."""
        if not self.filter:
            return self.checkpoints
        return [cp for cp in self.checkpoints if self.filter.matches(cp)]

    def get_pending_checkpoints(self) -> List[CheckpointSummary]:
        """Get only pending checkpoints."""
        return [
            cp for cp in self.checkpoints
            if cp.status == CheckpointDecisionStatus.PENDING
        ]

    def get_history_checkpoints(self) -> List[CheckpointSummary]:
        """Get resolved checkpoints (history)."""
        return [
            cp for cp in self.checkpoints
            if cp.status != CheckpointDecisionStatus.PENDING
        ]

    def get_status_counts(self) -> Dict[CheckpointDecisionStatus, int]:
        """Count checkpoints by status."""
        counts = {status: 0 for status in CheckpointDecisionStatus}
        for cp in self.checkpoints:
            counts[cp.status] += 1
        return counts

    def get_severity_counts(self) -> Dict[CheckpointSeverity, int]:
        """Count pending checkpoints by severity."""
        counts = {sev: 0 for sev in CheckpointSeverity}
        for cp in self.checkpoints:
            if cp.status == CheckpointDecisionStatus.PENDING:
                counts[cp.severity] += 1
        return counts


@dataclass
class MetricCard:
    """Single metric card for display."""
    label: str
    value: int
    color: str
    icon: str = ""

    @staticmethod
    def from_metrics(metrics: CheckpointMetrics) -> List["MetricCard"]:
        """Create metric cards from CheckpointMetrics."""
        return [
            MetricCard("Total", metrics.total_checkpoints, "#64748b"),
            MetricCard("Pendentes", metrics.pending_checkpoints, "#f59e0b"),
            MetricCard("Aprovados", metrics.approved_checkpoints, "#22c55e"),
            MetricCard("Rejeitados", metrics.rejected_checkpoints, "#ef4444"),
            MetricCard("Criticos", metrics.critical_pending, "#dc2626"),
            MetricCard("Alto Risco", metrics.high_risk_pending, "#ea580c"),
        ]


# Status display helpers
def get_status_display(status: CheckpointDecisionStatus) -> tuple[str, str]:
    """Get display text and color for status."""
    display_map = {
        CheckpointDecisionStatus.PENDING: ("Pendente", "#f59e0b"),
        CheckpointDecisionStatus.APPROVED: ("Aprovado", "#22c55e"),
        CheckpointDecisionStatus.REJECTED: ("Rejeitado", "#ef4444"),
    }
    return display_map.get(status, ("Desconhecido", "#64748b"))


def get_severity_display(severity: CheckpointSeverity) -> tuple[str, str]:
    """Get display text and color for severity."""
    display_map = {
        CheckpointSeverity.CRITICAL: ("Critico", "#dc2626"),
        CheckpointSeverity.HIGH_RISK: ("Alto Risco", "#ea580c"),
        CheckpointSeverity.WARNING: ("Alerta", "#f59e0b"),
        CheckpointSeverity.INFO: ("Info", "#3b82f6"),
    }
    return display_map.get(severity, ("Desconhecido", "#64748b"))


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "-"

    now = datetime.now()
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "Agora"
    elif delta < timedelta(hours=1):
        mins = int(delta.total_seconds() // 60)
        return f"{mins}m atras"
    elif delta < timedelta(hours=24):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours}h atras"
    elif delta < timedelta(days=2):
        return f"Ontem {dt.strftime('%H:%M')}"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days} dias atras"
    else:
        return dt.strftime("%d/%m/%Y %H:%M")


def get_reason_display(reason: str) -> str:
    """Get display text for checkpoint reason."""
    return REASON_DISPLAY_MAP.get(reason, reason.replace("_", " ").title())


def get_severity_icon(severity: CheckpointSeverity) -> str:
    """Get icon/symbol for severity level."""
    icons = {
        CheckpointSeverity.CRITICAL: "!!",
        CheckpointSeverity.HIGH_RISK: "!",
        CheckpointSeverity.WARNING: "?",
        CheckpointSeverity.INFO: "i",
    }
    return icons.get(severity, "?")
