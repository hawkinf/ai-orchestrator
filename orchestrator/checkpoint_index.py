"""Checkpoint index for centralized checkpoint management.

Aggregates checkpoint data from all runs for the Checkpoint Center panel.
Does not duplicate core logic - reads from existing state files and uses
CheckpointManager for actions.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import CheckpointReason, CheckpointRequest, TaskStatus

logger = logging.getLogger("ai_orchestrator.checkpoint_index")


class CheckpointSeverity(Enum):
    """Severity level for checkpoints."""
    INFO = "info"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


class CheckpointDecisionStatus(Enum):
    """Status of checkpoint decision."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class CheckpointSummary:
    """Summary of a checkpoint for list display."""
    checkpoint_id: str  # Format: {run_id}_{timestamp}
    run_id: str
    reason: str  # CheckpointReason value
    reason_display: str
    description: str
    status: CheckpointDecisionStatus
    severity: CheckpointSeverity
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: str = ""
    resolution_note: str = ""
    pipeline_stage: str = ""
    task_summary: str = ""
    project_type: str = "generic"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "reason": self.reason,
            "reason_display": self.reason_display,
            "description": self.description,
            "status": self.status.value,
            "severity": self.severity.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "resolution_note": self.resolution_note,
            "pipeline_stage": self.pipeline_stage,
            "task_summary": self.task_summary,
            "project_type": self.project_type,
        }


@dataclass
class CheckpointDetail:
    """Full details of a checkpoint."""
    checkpoint_id: str
    run_id: str
    reason: str
    reason_display: str
    description: str
    status: CheckpointDecisionStatus
    severity: CheckpointSeverity
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: str = ""
    resolution_note: str = ""

    # Context from run
    full_task: str = ""
    task_summary: str = ""
    project_type: str = "generic"
    pipeline_stage: str = ""
    iteration: int = 0
    max_iterations: int = 3

    # Checkpoint-specific details
    details: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)

    # Related data
    command: str = ""
    files_affected: List[str] = field(default_factory=list)
    diff_preview: str = ""
    system_recommendation: str = ""
    estimated_risk: str = ""
    suggested_action: str = ""

    # Plan context
    plan_objective: str = ""
    risks: List[str] = field(default_factory=list)

    # Post-decision data (for history)
    run_status_after: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "reason": self.reason,
            "reason_display": self.reason_display,
            "description": self.description,
            "status": self.status.value,
            "severity": self.severity.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "resolution_note": self.resolution_note,
            "full_task": self.full_task,
            "task_summary": self.task_summary,
            "project_type": self.project_type,
            "pipeline_stage": self.pipeline_stage,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "details": self.details,
            "options": self.options,
            "command": self.command,
            "files_affected": self.files_affected,
            "diff_preview": self.diff_preview,
            "system_recommendation": self.system_recommendation,
            "estimated_risk": self.estimated_risk,
            "suggested_action": self.suggested_action,
            "plan_objective": self.plan_objective,
            "risks": self.risks,
            "run_status_after": self.run_status_after,
            "commit_hash": self.commit_hash,
        }


@dataclass
class CheckpointMetrics:
    """Aggregated metrics for checkpoint center."""
    total_checkpoints: int = 0
    pending_checkpoints: int = 0
    approved_checkpoints: int = 0
    rejected_checkpoints: int = 0
    critical_pending: int = 0
    high_risk_pending: int = 0
    warning_pending: int = 0
    last_checkpoint_at: Optional[datetime] = None
    avg_resolution_time_seconds: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_checkpoints": self.total_checkpoints,
            "pending_checkpoints": self.pending_checkpoints,
            "approved_checkpoints": self.approved_checkpoints,
            "rejected_checkpoints": self.rejected_checkpoints,
            "critical_pending": self.critical_pending,
            "high_risk_pending": self.high_risk_pending,
            "warning_pending": self.warning_pending,
            "last_checkpoint_at": (
                self.last_checkpoint_at.isoformat() if self.last_checkpoint_at else None
            ),
            "avg_resolution_time_seconds": self.avg_resolution_time_seconds,
        }


@dataclass
class CheckpointFilter:
    """Filter criteria for checkpoint list."""
    status_filter: Optional[List[CheckpointDecisionStatus]] = None
    severity_filter: Optional[List[CheckpointSeverity]] = None
    reason_filter: Optional[List[str]] = None
    run_id_filter: Optional[str] = None
    search_text: str = ""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    def matches(self, checkpoint: CheckpointSummary) -> bool:
        """Check if a checkpoint matches this filter."""
        # Status filter
        if self.status_filter and checkpoint.status not in self.status_filter:
            return False

        # Severity filter
        if self.severity_filter and checkpoint.severity not in self.severity_filter:
            return False

        # Reason filter
        if self.reason_filter and checkpoint.reason not in self.reason_filter:
            return False

        # Run ID filter
        if self.run_id_filter:
            if self.run_id_filter.lower() not in checkpoint.run_id.lower():
                return False

        # Search text
        if self.search_text:
            search_lower = self.search_text.lower()
            if not (
                search_lower in checkpoint.run_id.lower() or
                search_lower in checkpoint.description.lower() or
                search_lower in checkpoint.task_summary.lower() or
                search_lower in checkpoint.reason_display.lower()
            ):
                return False

        # Date range
        if self.date_from and checkpoint.created_at:
            if checkpoint.created_at < self.date_from:
                return False
        if self.date_to and checkpoint.created_at:
            if checkpoint.created_at > self.date_to:
                return False

        return True


# Reason display mapping
REASON_DISPLAY_MAP = {
    "destructive_operation": "Operacao Destrutiva",
    "migration": "Migracao",
    "infrastructure_change": "Mudanca de Infraestrutura",
    "architecture_rewrite": "Reescrita de Arquitetura",
    "git_destructive": "Git Destrutivo",
    "command_not_allowed": "Comando Nao Permitido",
    "repeated_failures": "Falhas Repetidas",
    "manual_request": "Requisicao Manual",
}

# Severity mapping by reason
REASON_SEVERITY_MAP = {
    "destructive_operation": CheckpointSeverity.HIGH_RISK,
    "migration": CheckpointSeverity.HIGH_RISK,
    "infrastructure_change": CheckpointSeverity.CRITICAL,
    "architecture_rewrite": CheckpointSeverity.CRITICAL,
    "git_destructive": CheckpointSeverity.CRITICAL,
    "command_not_allowed": CheckpointSeverity.WARNING,
    "repeated_failures": CheckpointSeverity.WARNING,
    "manual_request": CheckpointSeverity.INFO,
}


class CheckpointIndex:
    """
    Index for reading and aggregating checkpoint data from workspace.

    Usage:
        index = CheckpointIndex(workspace_path)
        checkpoints = index.get_all_checkpoints()
        pending = index.get_pending_checkpoints()
        metrics = index.get_metrics()
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.state_dir = workspace_path / "state"
        self.runs_dir = workspace_path / "runs"
        self._cache: Dict[str, CheckpointSummary] = {}
        self._details_cache: Dict[str, CheckpointDetail] = {}
        self._last_scan: Optional[datetime] = None

    def refresh(self):
        """Force refresh of the index cache."""
        self._cache.clear()
        self._details_cache.clear()
        self._last_scan = None

    def get_all_checkpoints(
        self,
        limit: Optional[int] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[CheckpointSummary]:
        """
        Get all checkpoints from workspace.

        Args:
            limit: Maximum number of checkpoints to return
            sort_by: Field to sort by (created_at, status, severity)
            sort_desc: Sort descending if True

        Returns:
            List of CheckpointSummary objects
        """
        self._scan_checkpoints()

        checkpoints = list(self._cache.values())

        # Sort
        if sort_by == "created_at":
            checkpoints.sort(
                key=lambda c: c.created_at or datetime.min,
                reverse=sort_desc
            )
        elif sort_by == "status":
            # Pending first
            status_order = {
                CheckpointDecisionStatus.PENDING: 0,
                CheckpointDecisionStatus.APPROVED: 1,
                CheckpointDecisionStatus.REJECTED: 2,
            }
            checkpoints.sort(
                key=lambda c: status_order.get(c.status, 99),
                reverse=sort_desc
            )
        elif sort_by == "severity":
            severity_order = {
                CheckpointSeverity.CRITICAL: 0,
                CheckpointSeverity.HIGH_RISK: 1,
                CheckpointSeverity.WARNING: 2,
                CheckpointSeverity.INFO: 3,
            }
            checkpoints.sort(
                key=lambda c: severity_order.get(c.severity, 99),
                reverse=sort_desc
            )

        if limit:
            checkpoints = checkpoints[:limit]

        return checkpoints

    def get_pending_checkpoints(self) -> List[CheckpointSummary]:
        """Get only pending checkpoints, sorted by severity."""
        all_checkpoints = self.get_all_checkpoints(sort_by="severity", sort_desc=False)
        return [c for c in all_checkpoints if c.status == CheckpointDecisionStatus.PENDING]

    def get_checkpoint_detail(self, checkpoint_id: str) -> Optional[CheckpointDetail]:
        """Get full details of a checkpoint."""
        self._scan_checkpoints()

        if checkpoint_id in self._details_cache:
            return self._details_cache[checkpoint_id]

        # Extract run_id from checkpoint_id
        parts = checkpoint_id.rsplit("_", 1)
        if not parts:
            return None

        run_id = parts[0]
        return self._load_checkpoint_detail(run_id, checkpoint_id)

    def get_checkpoint_by_run(self, run_id: str) -> Optional[CheckpointSummary]:
        """Get checkpoint for a specific run (if exists)."""
        self._scan_checkpoints()

        for checkpoint in self._cache.values():
            if checkpoint.run_id == run_id:
                return checkpoint
        return None

    def filter_checkpoints(
        self,
        filter_criteria: CheckpointFilter,
        limit: Optional[int] = None,
    ) -> List[CheckpointSummary]:
        """
        Get checkpoints matching filter criteria.

        Args:
            filter_criteria: Filter to apply
            limit: Maximum checkpoints to return

        Returns:
            Filtered list of CheckpointSummary
        """
        all_checkpoints = self.get_all_checkpoints()
        filtered = [c for c in all_checkpoints if filter_criteria.matches(c)]

        if limit:
            filtered = filtered[:limit]

        return filtered

    def get_metrics(self) -> CheckpointMetrics:
        """Calculate aggregated metrics from all checkpoints."""
        checkpoints = self.get_all_checkpoints()

        metrics = CheckpointMetrics()
        metrics.total_checkpoints = len(checkpoints)

        total_resolution_time = 0
        resolution_count = 0

        for cp in checkpoints:
            if cp.status == CheckpointDecisionStatus.PENDING:
                metrics.pending_checkpoints += 1
                if cp.severity == CheckpointSeverity.CRITICAL:
                    metrics.critical_pending += 1
                elif cp.severity == CheckpointSeverity.HIGH_RISK:
                    metrics.high_risk_pending += 1
                elif cp.severity == CheckpointSeverity.WARNING:
                    metrics.warning_pending += 1
            elif cp.status == CheckpointDecisionStatus.APPROVED:
                metrics.approved_checkpoints += 1
            elif cp.status == CheckpointDecisionStatus.REJECTED:
                metrics.rejected_checkpoints += 1

            # Track last checkpoint
            if cp.created_at:
                if not metrics.last_checkpoint_at or cp.created_at > metrics.last_checkpoint_at:
                    metrics.last_checkpoint_at = cp.created_at

            # Calculate resolution time
            if cp.created_at and cp.resolved_at:
                delta = cp.resolved_at - cp.created_at
                total_resolution_time += int(delta.total_seconds())
                resolution_count += 1

        if resolution_count > 0:
            metrics.avg_resolution_time_seconds = total_resolution_time // resolution_count

        return metrics

    def get_reasons(self) -> List[str]:
        """Get list of unique checkpoint reasons."""
        checkpoints = self.get_all_checkpoints()
        reasons = set()
        for cp in checkpoints:
            if cp.reason:
                reasons.add(cp.reason)
        return sorted(reasons)

    def export_to_json(self, output_path: Path) -> Path:
        """Export checkpoint data to JSON."""
        checkpoints = self.get_all_checkpoints()
        metrics = self.get_metrics()

        data = {
            "exported_at": datetime.now().isoformat(),
            "metrics": metrics.to_dict(),
            "checkpoints": [c.to_dict() for c in checkpoints],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported checkpoints to: {output_path}")
        return output_path

    def export_to_markdown(self, output_path: Path) -> Path:
        """Export checkpoint summary to Markdown."""
        checkpoints = self.get_all_checkpoints()
        metrics = self.get_metrics()

        lines = [
            "# AI Orchestrator - Checkpoint Center Export",
            "",
            f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Metrics Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Checkpoints | {metrics.total_checkpoints} |",
            f"| Pending | {metrics.pending_checkpoints} |",
            f"| Approved | {metrics.approved_checkpoints} |",
            f"| Rejected | {metrics.rejected_checkpoints} |",
            f"| Critical Pending | {metrics.critical_pending} |",
            f"| High Risk Pending | {metrics.high_risk_pending} |",
            "",
            "---",
            "",
            "## Pending Checkpoints",
            "",
        ]

        pending = [c for c in checkpoints if c.status == CheckpointDecisionStatus.PENDING]
        if pending:
            lines.append("| Run ID | Reason | Severity | Description | Created |")
            lines.append("|--------|--------|----------|-------------|---------|")
            for cp in pending:
                created = cp.created_at.strftime("%Y-%m-%d %H:%M") if cp.created_at else "-"
                desc = cp.description[:30] + "..." if len(cp.description) > 30 else cp.description
                lines.append(
                    f"| {cp.run_id[:16]} | {cp.reason_display} | "
                    f"{cp.severity.value.upper()} | {desc} | {created} |"
                )
        else:
            lines.append("*No pending checkpoints*")

        lines.extend([
            "",
            "---",
            "",
            "## History (Last 20)",
            "",
        ])

        history = [c for c in checkpoints if c.status != CheckpointDecisionStatus.PENDING][:20]
        if history:
            lines.append("| Run ID | Reason | Decision | Resolved At |")
            lines.append("|--------|--------|----------|-------------|")
            for cp in history:
                resolved = cp.resolved_at.strftime("%Y-%m-%d %H:%M") if cp.resolved_at else "-"
                lines.append(
                    f"| {cp.run_id[:16]} | {cp.reason_display} | "
                    f"{cp.status.value.upper()} | {resolved} |"
                )
        else:
            lines.append("*No checkpoint history*")

        lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported checkpoints markdown to: {output_path}")
        return output_path

    def _scan_checkpoints(self):
        """Scan workspace for checkpoints and update cache."""
        if not self.state_dir.exists():
            return

        # Find all state files
        state_files = list(self.state_dir.glob("*.json"))

        for state_file in state_files:
            if state_file.name == "index.json":
                continue

            run_id = state_file.stem

            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                checkpoint_data = state_data.get("checkpoint")
                if checkpoint_data and isinstance(checkpoint_data, dict):
                    summary = self._parse_checkpoint_summary(run_id, state_data, checkpoint_data)
                    if summary:
                        self._cache[summary.checkpoint_id] = summary

            except json.JSONDecodeError as e:
                logger.warning(f"Error parsing state file {run_id}: {e}")
            except Exception as e:
                logger.warning(f"Error loading checkpoint from {run_id}: {e}")

        self._last_scan = datetime.now()

    def _parse_checkpoint_summary(
        self,
        run_id: str,
        state_data: dict,
        checkpoint_data: dict,
    ) -> Optional[CheckpointSummary]:
        """Parse checkpoint data into CheckpointSummary."""
        # Generate checkpoint_id
        created_at = None
        if checkpoint_data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    checkpoint_data["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        timestamp_str = created_at.strftime("%Y%m%d%H%M%S") if created_at else "unknown"
        checkpoint_id = f"{run_id}_{timestamp_str}"

        # Determine status
        resolved = checkpoint_data.get("resolved", False)
        resolution = checkpoint_data.get("resolution", "")

        if not resolved:
            status = CheckpointDecisionStatus.PENDING
        elif "reject" in resolution.lower():
            status = CheckpointDecisionStatus.REJECTED
        else:
            status = CheckpointDecisionStatus.APPROVED

        # Get reason
        reason = checkpoint_data.get("reason", "manual_request")
        reason_display = REASON_DISPLAY_MAP.get(reason, reason.replace("_", " ").title())

        # Get severity
        severity = REASON_SEVERITY_MAP.get(reason, CheckpointSeverity.INFO)

        # Parse resolved_at
        resolved_at = None
        if checkpoint_data.get("resolved_at"):
            try:
                resolved_at = datetime.fromisoformat(
                    checkpoint_data["resolved_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Get task info
        task_data = state_data.get("task", {})
        task_summary = ""
        project_type = "generic"
        if isinstance(task_data, dict):
            full_task = task_data.get("description", "")
            task_summary = self._summarize_task(full_task)
            project_type = task_data.get("profile", "generic")

        # Get pipeline stage
        pipeline_stage = state_data.get("status", "unknown")

        return CheckpointSummary(
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            reason=reason,
            reason_display=reason_display,
            description=checkpoint_data.get("description", ""),
            status=status,
            severity=severity,
            created_at=created_at,
            resolved_at=resolved_at,
            resolution=resolution,
            resolution_note=self._extract_resolution_note(resolution),
            pipeline_stage=pipeline_stage,
            task_summary=task_summary,
            project_type=project_type,
        )

    def _load_checkpoint_detail(
        self,
        run_id: str,
        checkpoint_id: str,
    ) -> Optional[CheckpointDetail]:
        """Load full checkpoint details from state file."""
        state_file = self.state_dir / f"{run_id}.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            checkpoint_data = state_data.get("checkpoint")
            if not checkpoint_data:
                return None

            # Get summary first
            summary = self._cache.get(checkpoint_id)
            if not summary:
                summary = self._parse_checkpoint_summary(run_id, state_data, checkpoint_data)
                if not summary:
                    return None

            # Build detail
            detail = CheckpointDetail(
                checkpoint_id=summary.checkpoint_id,
                run_id=summary.run_id,
                reason=summary.reason,
                reason_display=summary.reason_display,
                description=summary.description,
                status=summary.status,
                severity=summary.severity,
                created_at=summary.created_at,
                resolved_at=summary.resolved_at,
                resolution=summary.resolution,
                resolution_note=summary.resolution_note,
                pipeline_stage=summary.pipeline_stage,
                task_summary=summary.task_summary,
                project_type=summary.project_type,
            )

            # Add task details
            task_data = state_data.get("task", {})
            if isinstance(task_data, dict):
                detail.full_task = task_data.get("description", "")

            # Add iteration info
            detail.iteration = state_data.get("current_iteration", 0)
            detail.max_iterations = state_data.get("max_iterations", 3)

            # Add checkpoint-specific details
            detail.details = checkpoint_data.get("details", {})
            detail.options = checkpoint_data.get("options", ["approve", "reject"])

            # Extract command if present
            if detail.details.get("command"):
                detail.command = detail.details["command"]

            # Add plan info
            plan_data = state_data.get("plan", {})
            if isinstance(plan_data, dict):
                detail.plan_objective = plan_data.get("objective", "")
                detail.risks = plan_data.get("risks", [])
                detail.files_affected = plan_data.get("files_likely_affected", [])

            # Generate recommendations based on reason
            detail.system_recommendation = self._generate_recommendation(
                summary.reason, summary.severity, detail.details
            )
            detail.estimated_risk = self._estimate_risk(summary.severity)
            detail.suggested_action = self._suggest_action(summary.reason, summary.severity)

            # Load diff preview if available
            run_dir = self.runs_dir / run_id
            diff_files = list(run_dir.glob("git/*.diff")) + list(run_dir.glob("git/*.patch"))
            if diff_files:
                try:
                    with open(diff_files[0], "r", encoding="utf-8") as f:
                        detail.diff_preview = f.read()[:2000]  # First 2000 chars
                except Exception:
                    pass

            # Add post-decision data for history
            if summary.status != CheckpointDecisionStatus.PENDING:
                detail.run_status_after = state_data.get("status", "unknown")
                git_result = state_data.get("git_result_final", {})
                if isinstance(git_result, dict):
                    detail.commit_hash = git_result.get("commit_hash", "")

            self._details_cache[checkpoint_id] = detail
            return detail

        except Exception as e:
            logger.warning(f"Error loading checkpoint detail for {run_id}: {e}")
            return None

    def _summarize_task(self, full_task: str, max_len: int = 60) -> str:
        """Create a short summary from full task description."""
        if not full_task:
            return "(sem descricao)"

        first_line = full_task.split("\n")[0].strip()
        if len(first_line) > max_len:
            return first_line[:max_len - 3] + "..."
        return first_line

    def _extract_resolution_note(self, resolution: str) -> str:
        """Extract user note from resolution string."""
        if not resolution:
            return ""

        # Resolution format might be "approved: user note" or "rejected: reason"
        if ": " in resolution:
            return resolution.split(": ", 1)[1]
        return ""

    def _generate_recommendation(
        self,
        reason: str,
        severity: CheckpointSeverity,
        details: dict,
    ) -> str:
        """Generate system recommendation based on checkpoint type."""
        recommendations = {
            "destructive_operation": (
                "Esta operacao pode causar perda de dados. Verifique se ha backup "
                "e se a operacao e realmente necessaria."
            ),
            "migration": (
                "Migracoes devem ser testadas em ambiente de desenvolvimento primeiro. "
                "Verifique o rollback plan."
            ),
            "infrastructure_change": (
                "Mudancas de infraestrutura podem afetar disponibilidade. "
                "Considere janela de manutencao."
            ),
            "architecture_rewrite": (
                "Reescrita de arquitetura requer revisao cuidadosa. "
                "Verifique testes e documentacao."
            ),
            "git_destructive": (
                "Operacoes destrutivas no Git podem perder historico. "
                "Verifique se ha branches/tags de backup."
            ),
            "command_not_allowed": (
                "Este comando nao esta na lista de permitidos. "
                "Verifique se e seguro e necessario."
            ),
            "repeated_failures": (
                "Multiplas falhas detectadas. Revise os logs de erro "
                "e considere abordagem diferente."
            ),
            "manual_request": (
                "Checkpoint solicitado pelo usuario. "
                "Revise o contexto antes de prosseguir."
            ),
        }

        base_rec = recommendations.get(reason, "Revise o contexto antes de decidir.")

        if severity == CheckpointSeverity.CRITICAL:
            return f"CRITICO: {base_rec}"
        elif severity == CheckpointSeverity.HIGH_RISK:
            return f"ALTO RISCO: {base_rec}"

        return base_rec

    def _estimate_risk(self, severity: CheckpointSeverity) -> str:
        """Estimate risk level based on severity."""
        risk_map = {
            CheckpointSeverity.CRITICAL: "Muito Alto - Impacto potencial irreversivel",
            CheckpointSeverity.HIGH_RISK: "Alto - Pode causar problemas significativos",
            CheckpointSeverity.WARNING: "Medio - Requer atencao mas gerenciavel",
            CheckpointSeverity.INFO: "Baixo - Revisao recomendada mas risco minimo",
        }
        return risk_map.get(severity, "Desconhecido")

    def _suggest_action(self, reason: str, severity: CheckpointSeverity) -> str:
        """Suggest action based on checkpoint type."""
        if severity == CheckpointSeverity.CRITICAL:
            return "Recomendado: Revisar cuidadosamente antes de aprovar"

        if reason in ("repeated_failures", "command_not_allowed"):
            return "Considere rejeitar e ajustar a abordagem"

        return "Revisar contexto e aprovar se apropriado"


def get_checkpoint_index(workspace_path: Path) -> CheckpointIndex:
    """Factory function to create a CheckpointIndex."""
    return CheckpointIndex(workspace_path)
