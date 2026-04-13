"""Data models for diagnostics panel.

Re-exports core diagnostic models and adds GUI-specific models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

# Re-export from core
from orchestrator.diagnostics import (
    DiagnosticStatus,
    CheckCategory,
    DiagnosticCheckResult,
    DiagnosticReport,
    get_check_definitions,
)


@dataclass
class DiagnosticCheckUIState:
    """UI state for a single diagnostic check."""
    key: str
    title: str
    category: str
    description: str
    is_critical: bool
    status: DiagnosticStatus = DiagnosticStatus.NOT_TESTED
    summary: str = ""
    details: List[str] = field(default_factory=list)
    recommendation: Optional[str] = None
    duration_ms: int = 0
    is_expanded: bool = False

    @classmethod
    def from_definition(cls, definition: dict) -> "DiagnosticCheckUIState":
        """Create from check definition."""
        return cls(
            key=definition["key"],
            title=definition["title"],
            category=definition["category"],
            description=definition["description"],
            is_critical=definition.get("is_critical", False),
        )

    def update_from_result(self, result: DiagnosticCheckResult):
        """Update state from check result."""
        self.status = result.status
        self.summary = result.summary
        self.details = result.details
        self.recommendation = result.recommendation
        self.duration_ms = result.duration_ms


@dataclass
class DiagnosticsUIState:
    """Complete UI state for diagnostics panel."""
    checks: List[DiagnosticCheckUIState] = field(default_factory=list)
    overall_status: DiagnosticStatus = DiagnosticStatus.NOT_TESTED
    is_running: bool = False
    current_check: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    environment_summary: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def initialize(cls) -> "DiagnosticsUIState":
        """Initialize with all check definitions."""
        checks = [
            DiagnosticCheckUIState.from_definition(d)
            for d in get_check_definitions()
        ]
        return cls(checks=checks)

    def get_check(self, key: str) -> Optional[DiagnosticCheckUIState]:
        """Get check by key."""
        for check in self.checks:
            if check.key == key:
                return check
        return None

    def update_from_report(self, report: DiagnosticReport):
        """Update state from diagnostic report."""
        self.overall_status = report.overall_status
        self.environment_summary = report.environment_summary
        self.started_at = report.started_at
        self.completed_at = report.completed_at

        for result in report.checks:
            check = self.get_check(result.key)
            if check:
                check.update_from_result(result)

    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        if self.overall_status == DiagnosticStatus.NOT_TESTED:
            return "Nao testado"
        elif self.overall_status == DiagnosticStatus.RUNNING:
            return "Executando..."
        elif self.overall_status == DiagnosticStatus.OK:
            return "Sistema pronto"
        elif self.overall_status == DiagnosticStatus.WARNING:
            return "Sistema utilizavel com avisos"
        elif self.overall_status == DiagnosticStatus.FAILED:
            return "Falhas detectadas"
        elif self.overall_status == DiagnosticStatus.CRITICAL:
            return "Sistema bloqueado por falhas criticas"
        return "Status desconhecido"

    def count_by_status(self) -> Dict[DiagnosticStatus, int]:
        """Count checks by status."""
        counts = {}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts
