"""Run timeline models and builder.

Provides a human-readable timeline of events for a run,
built from state, logs, and artifacts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import logging

logger = logging.getLogger("ai_orchestrator.run_timeline")


class TimelineEventStatus(Enum):
    """Status of a timeline event."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TimelineEventType(Enum):
    """Types of timeline events."""
    # Main pipeline stages
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    VALIDATION = "validation"
    GIT = "git"
    FINALIZATION = "finalization"

    # Special events
    CHECKPOINT = "checkpoint"
    POLICY_DECISION = "policy_decision"
    ERROR = "error"
    ITERATION_START = "iteration_start"


# Human-friendly explanations for each event type
EVENT_EXPLANATIONS = {
    TimelineEventType.PLANNING: (
        "O sistema analisou sua tarefa e criou um plano de execução, "
        "identificando arquivos afetados, riscos e passos de validação."
    ),
    TimelineEventType.EXECUTION: (
        "O código foi modificado automaticamente pelo executor (Claude), "
        "seguindo o plano definido."
    ),
    TimelineEventType.REVIEW: (
        "O resultado foi analisado pelo revisor (OpenAI) para identificar "
        "problemas, regressões ou melhorias necessárias."
    ),
    TimelineEventType.VALIDATION: (
        "Foram executados testes e verificações do projeto conforme "
        "o perfil configurado (flutter analyze, pytest, etc)."
    ),
    TimelineEventType.GIT: (
        "As alterações foram registradas no Git com commit e/ou push, "
        "preservando o histórico do projeto."
    ),
    TimelineEventType.FINALIZATION: (
        "A run foi finalizada e os artefatos foram salvos para "
        "consulta posterior (relatório, diff, logs)."
    ),
    TimelineEventType.CHECKPOINT: (
        "Uma operação potencialmente arriscada foi detectada e aguarda "
        "sua aprovação antes de continuar."
    ),
    TimelineEventType.POLICY_DECISION: (
        "A policy engine avaliou uma ação e tomou uma decisão "
        "automática baseada nas regras configuradas."
    ),
    TimelineEventType.ERROR: (
        "Um erro ocorreu durante a execução. Verifique os detalhes "
        "para entender o que aconteceu."
    ),
    TimelineEventType.ITERATION_START: (
        "Uma nova iteração foi iniciada para refinar ou corrigir "
        "o trabalho da iteração anterior."
    ),
}

# Display names for event types
EVENT_DISPLAY_NAMES = {
    TimelineEventType.PLANNING: "Planejamento",
    TimelineEventType.EXECUTION: "Execução",
    TimelineEventType.REVIEW: "Revisão",
    TimelineEventType.VALIDATION: "Validação",
    TimelineEventType.GIT: "Git",
    TimelineEventType.FINALIZATION: "Finalização",
    TimelineEventType.CHECKPOINT: "Checkpoint",
    TimelineEventType.POLICY_DECISION: "Decisão de Policy",
    TimelineEventType.ERROR: "Erro",
    TimelineEventType.ITERATION_START: "Nova Iteração",
}


@dataclass
class TimelineEventDetail:
    """Expandable detail for a timeline event."""
    label: str
    content: str
    detail_type: str = "text"  # text, logs, commands, files, diff


@dataclass
class RunTimelineEvent:
    """A single event in the run timeline."""
    event_type: TimelineEventType
    status: TimelineEventStatus
    timestamp: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    title: str = ""
    description: str = ""
    explanation: str = ""

    # Expandable details
    details: List[TimelineEventDetail] = field(default_factory=list)

    # Related data
    files_affected: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # For checkpoints
    checkpoint_reason: str = ""
    checkpoint_resolved: bool = False
    checkpoint_resolution: str = ""

    # For policy decisions
    policy_action: str = ""
    policy_result: str = ""

    # Iteration info
    iteration_number: int = 0

    def __post_init__(self):
        if not self.title:
            self.title = EVENT_DISPLAY_NAMES.get(self.event_type, str(self.event_type))
        if not self.explanation:
            self.explanation = EVENT_EXPLANATIONS.get(self.event_type, "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_seconds": self.duration_seconds,
            "title": self.title,
            "description": self.description,
            "explanation": self.explanation,
            "details": [
                {"label": d.label, "content": d.content, "detail_type": d.detail_type}
                for d in self.details
            ],
            "files_affected": self.files_affected,
            "commands_run": self.commands_run,
            "errors": self.errors,
            "checkpoint_reason": self.checkpoint_reason,
            "checkpoint_resolved": self.checkpoint_resolved,
            "checkpoint_resolution": self.checkpoint_resolution,
            "policy_action": self.policy_action,
            "policy_result": self.policy_result,
            "iteration_number": self.iteration_number,
        }


@dataclass
class RunTimeline:
    """Complete timeline for a run."""
    run_id: str
    events: List[RunTimelineEvent] = field(default_factory=list)
    current_stage: str = ""
    is_complete: bool = False
    has_errors: bool = False
    total_duration_seconds: float = 0.0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_event(self, event: RunTimelineEvent):
        """Add an event to the timeline."""
        self.events.append(event)
        if event.status == TimelineEventStatus.FAILED:
            self.has_errors = True

    def get_current_event(self) -> Optional[RunTimelineEvent]:
        """Get the currently in-progress event."""
        for event in reversed(self.events):
            if event.status == TimelineEventStatus.IN_PROGRESS:
                return event
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "events": [e.to_dict() for e in self.events],
            "current_stage": self.current_stage,
            "is_complete": self.is_complete,
            "has_errors": self.has_errors,
            "total_duration_seconds": self.total_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TimelineBuilder:
    """Builds a RunTimeline from state, logs, and artifacts."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.state_dir = workspace_path / "state"
        self.runs_dir = workspace_path / "runs"

    def build_timeline(self, run_id: str) -> Optional[RunTimeline]:
        """Build timeline for a specific run."""
        state_file = self.state_dir / f"{run_id}.json"
        if not state_file.exists():
            return None

        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read state for {run_id}: {e}")
            return None

        timeline = RunTimeline(run_id=run_id)

        # Parse timestamps
        if state_data.get("created_at"):
            try:
                timeline.created_at = datetime.fromisoformat(
                    state_data["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        if state_data.get("completed_at"):
            try:
                timeline.completed_at = datetime.fromisoformat(
                    state_data["completed_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Calculate total duration
        if timeline.created_at:
            end_time = timeline.completed_at or datetime.now()
            delta = end_time - timeline.created_at
            timeline.total_duration_seconds = delta.total_seconds()

        # Current status
        status_str = state_data.get("status", "unknown")
        timeline.current_stage = status_str
        timeline.is_complete = status_str in ("completed", "failed", "cancelled")

        # Build events
        self._add_planning_event(timeline, state_data)
        self._add_iteration_events(timeline, state_data)
        self._add_checkpoint_event(timeline, state_data)
        self._add_git_event(timeline, state_data)
        self._add_finalization_event(timeline, state_data)

        return timeline

    def _add_planning_event(self, timeline: RunTimeline, state_data: dict):
        """Add planning event to timeline."""
        plan = state_data.get("plan")
        status_str = state_data.get("status", "")

        if not plan and status_str == "pending":
            # Planning not started
            event = RunTimelineEvent(
                event_type=TimelineEventType.PLANNING,
                status=TimelineEventStatus.PENDING,
                timestamp=timeline.created_at,
            )
        elif not plan and status_str == "planning":
            # Planning in progress
            event = RunTimelineEvent(
                event_type=TimelineEventType.PLANNING,
                status=TimelineEventStatus.IN_PROGRESS,
                timestamp=timeline.created_at,
                description="Analisando tarefa e criando plano de execução...",
            )
        elif plan:
            # Planning completed
            event = RunTimelineEvent(
                event_type=TimelineEventType.PLANNING,
                status=TimelineEventStatus.COMPLETED,
                timestamp=timeline.created_at,
            )

            if isinstance(plan, dict):
                objective = plan.get("objective", "")
                if objective:
                    event.description = f"Objetivo: {objective[:200]}"

                # Add details
                if plan.get("scope"):
                    event.details.append(TimelineEventDetail(
                        label="Escopo",
                        content=plan["scope"],
                        detail_type="text"
                    ))

                files = plan.get("files_likely_affected", [])
                if files:
                    event.files_affected = files
                    event.details.append(TimelineEventDetail(
                        label="Arquivos Afetados",
                        content="\n".join(files),
                        detail_type="files"
                    ))

                risks = plan.get("risks", [])
                if risks:
                    event.details.append(TimelineEventDetail(
                        label="Riscos Identificados",
                        content="\n".join(f"• {r}" for r in risks),
                        detail_type="text"
                    ))

                constraints = plan.get("constraints", [])
                if constraints:
                    event.details.append(TimelineEventDetail(
                        label="Restrições",
                        content="\n".join(f"• {c}" for c in constraints),
                        detail_type="text"
                    ))
        else:
            # Planning failed or skipped
            error_msg = state_data.get("error_message", "")
            if "plan" in error_msg.lower():
                event = RunTimelineEvent(
                    event_type=TimelineEventType.PLANNING,
                    status=TimelineEventStatus.FAILED,
                    timestamp=timeline.created_at,
                    description="Falha ao criar plano de execução",
                    errors=[error_msg] if error_msg else [],
                )
            else:
                return  # No planning event to add

        timeline.add_event(event)

    def _add_iteration_events(self, timeline: RunTimeline, state_data: dict):
        """Add execution/review/validation events from iterations."""
        iterations = state_data.get("iterations", [])
        if not iterations:
            # Check if we're in an active stage
            status_str = state_data.get("status", "")
            if status_str == "executing":
                event = RunTimelineEvent(
                    event_type=TimelineEventType.EXECUTION,
                    status=TimelineEventStatus.IN_PROGRESS,
                    description="Executor está modificando o código...",
                    iteration_number=1,
                )
                timeline.add_event(event)
            return

        for iter_data in iterations:
            if not isinstance(iter_data, dict):
                continue

            iter_num = iter_data.get("iteration_number", 1)

            # Add iteration start marker if > 1
            if iter_num > 1:
                iter_start = RunTimelineEvent(
                    event_type=TimelineEventType.ITERATION_START,
                    status=TimelineEventStatus.COMPLETED,
                    iteration_number=iter_num,
                    title=f"Iteração {iter_num}",
                    description="Nova iteração iniciada para refinar o resultado.",
                )
                if iter_data.get("started_at"):
                    try:
                        iter_start.timestamp = datetime.fromisoformat(
                            iter_data["started_at"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        pass
                timeline.add_event(iter_start)

            # Execution event
            self._add_execution_event(timeline, iter_data, iter_num)

            # Review event
            self._add_review_event(timeline, iter_data, iter_num)

            # Validation event
            self._add_validation_event(timeline, iter_data, iter_num)

    def _add_execution_event(self, timeline: RunTimeline, iter_data: dict, iter_num: int):
        """Add execution event from iteration data."""
        exec_result = iter_data.get("execution_result")
        exec_report = iter_data.get("execution_report")

        if not exec_result and not exec_report:
            return

        # Determine status from result
        status = TimelineEventStatus.COMPLETED
        if exec_result and isinstance(exec_result, dict):
            success = exec_result.get("success", False)
            status = TimelineEventStatus.COMPLETED if success else TimelineEventStatus.FAILED

        event = RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=status,
            iteration_number=iter_num,
        )

        # Add timing and details from result
        if exec_result and isinstance(exec_result, dict):

            if exec_result.get("duration_seconds"):
                event.duration_seconds = exec_result["duration_seconds"]

            if exec_result.get("started_at"):
                try:
                    event.timestamp = datetime.fromisoformat(
                        exec_result["started_at"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # Add logs if available
            stdout = exec_result.get("stdout", "")
            stderr = exec_result.get("stderr", "")
            if stdout:
                event.details.append(TimelineEventDetail(
                    label="Output",
                    content=stdout[:5000],  # Limit size
                    detail_type="logs"
                ))
            if stderr:
                event.details.append(TimelineEventDetail(
                    label="Erros",
                    content=stderr[:2000],
                    detail_type="logs"
                ))
                event.errors.append(stderr[:500])

            event.commands_run = exec_result.get("commands_run", [])
            event.files_affected = exec_result.get("files_changed", [])
        else:
            event.status = TimelineEventStatus.COMPLETED

        # Parse execution report
        if exec_report and isinstance(exec_report, dict):
            summary = exec_report.get("summary", "")
            if summary:
                event.description = summary[:300]

            if not event.files_affected:
                event.files_affected = exec_report.get("files_changed", [])

            if not event.commands_run:
                event.commands_run = exec_report.get("commands_executed", [])

            # Add details
            if event.files_affected:
                event.details.append(TimelineEventDetail(
                    label="Arquivos Modificados",
                    content="\n".join(event.files_affected),
                    detail_type="files"
                ))

            if event.commands_run:
                event.details.append(TimelineEventDetail(
                    label="Comandos Executados",
                    content="\n".join(event.commands_run),
                    detail_type="commands"
                ))

            tests = exec_report.get("tests_run", [])
            passed = exec_report.get("tests_passed", 0)
            failed = exec_report.get("tests_failed", 0)
            if tests or passed or failed:
                test_summary = f"Passou: {passed}, Falhou: {failed}"
                if tests:
                    test_summary += "\n\nTestes:\n" + "\n".join(tests)
                event.details.append(TimelineEventDetail(
                    label="Testes",
                    content=test_summary,
                    detail_type="text"
                ))

        timeline.add_event(event)

    def _add_review_event(self, timeline: RunTimeline, iter_data: dict, iter_num: int):
        """Add review event from iteration data."""
        review = iter_data.get("review_response")
        if not review:
            return

        # Determine status and description
        status = TimelineEventStatus.COMPLETED
        description = ""
        if isinstance(review, dict):
            status_str = review.get("status", "")
            if status_str == "approved":
                description = "Revisão aprovada - código pronto para validação."
            elif status_str == "needs_followup":
                description = "Revisão identificou ajustes necessários."
            elif status_str == "blocked":
                status = TimelineEventStatus.FAILED
                description = "Revisão bloqueou a continuação."

        event = RunTimelineEvent(
            event_type=TimelineEventType.REVIEW,
            status=status,
            iteration_number=iter_num,
            description=description,
        )

        if isinstance(review, dict):

            # Add details
            findings = review.get("findings", [])
            if findings:
                event.details.append(TimelineEventDetail(
                    label="Achados da Revisão",
                    content="\n".join(f"• {f}" for f in findings),
                    detail_type="text"
                ))

            risks = review.get("regression_risks", [])
            if risks:
                event.details.append(TimelineEventDetail(
                    label="Riscos de Regressão",
                    content="\n".join(f"⚠ {r}" for r in risks),
                    detail_type="text"
                ))

            suggestions = review.get("suggestions", [])
            if suggestions:
                event.details.append(TimelineEventDetail(
                    label="Sugestões",
                    content="\n".join(f"• {s}" for s in suggestions),
                    detail_type="text"
                ))

            if review.get("human_review_required"):
                event.details.append(TimelineEventDetail(
                    label="Aviso",
                    content="Revisão humana recomendada antes de continuar.",
                    detail_type="text"
                ))
        else:
            event.status = TimelineEventStatus.COMPLETED

        timeline.add_event(event)

    def _add_validation_event(self, timeline: RunTimeline, iter_data: dict, iter_num: int):
        """Add validation event from iteration data."""
        validation = iter_data.get("validation_summary")
        if not validation:
            return

        # Determine status
        status = TimelineEventStatus.COMPLETED
        description = ""
        duration = None

        if isinstance(validation, dict):
            all_passed = validation.get("all_passed", False)
            status = TimelineEventStatus.COMPLETED if all_passed else TimelineEventStatus.FAILED

            total_duration = validation.get("total_duration", 0)
            if total_duration:
                duration = total_duration

            results = validation.get("results", [])
            passed_count = sum(1 for r in results if r.get("success", False))
            total_count = len(results)

            if all_passed:
                description = f"Todas as {total_count} validações passaram."
            else:
                description = f"{passed_count}/{total_count} validações passaram."

        event = RunTimelineEvent(
            event_type=TimelineEventType.VALIDATION,
            status=status,
            iteration_number=iter_num,
            description=description,
            duration_seconds=duration,
        )

        if isinstance(validation, dict):
            results = validation.get("results", [])

            # Add command results
            for result in results:
                if isinstance(result, dict):
                    cmd = result.get("command", "")
                    success = result.get("success", False)
                    icon = "✓" if success else "✗"

                    event.commands_run.append(cmd)

                    # Add detail for failed commands
                    if not success:
                        stderr = result.get("stderr", "")
                        event.details.append(TimelineEventDetail(
                            label=f"{icon} {cmd}",
                            content=stderr[:1000] if stderr else "Comando falhou",
                            detail_type="logs"
                        ))
                        event.errors.append(f"{cmd}: falhou")
                    else:
                        event.details.append(TimelineEventDetail(
                            label=f"{icon} {cmd}",
                            content="Sucesso",
                            detail_type="text"
                        ))
        else:
            event.status = TimelineEventStatus.COMPLETED

        timeline.add_event(event)

    def _add_checkpoint_event(self, timeline: RunTimeline, state_data: dict):
        """Add checkpoint event if present."""
        checkpoint = state_data.get("checkpoint")
        if not checkpoint or not isinstance(checkpoint, dict):
            return

        resolved = checkpoint.get("resolved", False)
        resolution = checkpoint.get("resolution", "")

        if resolved:
            status = TimelineEventStatus.COMPLETED
            description = f"Checkpoint resolvido: {resolution}"
        else:
            status = TimelineEventStatus.IN_PROGRESS
            description = f"Aguardando aprovação: {checkpoint.get('description', '')}"

        timestamp = None
        if checkpoint.get("created_at"):
            try:
                timestamp = datetime.fromisoformat(
                    checkpoint["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        event = RunTimelineEvent(
            event_type=TimelineEventType.CHECKPOINT,
            status=status,
            timestamp=timestamp,
            description=description,
            checkpoint_reason=checkpoint.get("reason", ""),
            checkpoint_resolved=resolved,
            checkpoint_resolution=resolution,
        )

        # Add details
        event.details.append(TimelineEventDetail(
            label="Motivo",
            content=checkpoint.get("description", event.checkpoint_reason),
            detail_type="text"
        ))

        details = checkpoint.get("details", {})
        if details and isinstance(details, dict):
            for key, value in details.items():
                event.details.append(TimelineEventDetail(
                    label=key.replace("_", " ").title(),
                    content=str(value),
                    detail_type="text"
                ))

        timeline.add_event(event)

    def _add_git_event(self, timeline: RunTimeline, state_data: dict):
        """Add git event if present."""
        git_result = state_data.get("git_result_final")
        status_str = state_data.get("status", "")

        if status_str == "committing" and not git_result:
            event = RunTimelineEvent(
                event_type=TimelineEventType.GIT,
                status=TimelineEventStatus.IN_PROGRESS,
                description="Registrando alterações no Git...",
            )
            timeline.add_event(event)
            return

        if not git_result or not isinstance(git_result, dict):
            return

        success = git_result.get("success", False)
        status = TimelineEventStatus.COMPLETED if success else TimelineEventStatus.FAILED

        operation = git_result.get("operation", "")
        commit_hash = git_result.get("commit_hash", "")
        message = git_result.get("message", "")

        if success and commit_hash:
            description = f"Commit criado: {commit_hash[:8]}"
        elif success:
            description = f"Operação Git concluída: {operation}"
        else:
            description = f"Falha no Git: {git_result.get('error', 'erro desconhecido')}"

        event = RunTimelineEvent(
            event_type=TimelineEventType.GIT,
            status=status,
            description=description,
        )

        if not success:
            event.errors.append(git_result.get("error", ""))

        # Add details
        if operation:
            event.details.append(TimelineEventDetail(
                label="Operação",
                content=operation,
                detail_type="text"
            ))
        if commit_hash:
            event.details.append(TimelineEventDetail(
                label="Commit Hash",
                content=commit_hash,
                detail_type="text"
            ))
        if message:
            event.details.append(TimelineEventDetail(
                label="Mensagem",
                content=message,
                detail_type="text"
            ))

        timeline.add_event(event)

    def _add_finalization_event(self, timeline: RunTimeline, state_data: dict):
        """Add finalization event."""
        status_str = state_data.get("status", "")

        if status_str not in ("completed", "failed", "cancelled"):
            return

        if status_str == "completed":
            status = TimelineEventStatus.COMPLETED
            description = "Run finalizada com sucesso."
        elif status_str == "failed":
            status = TimelineEventStatus.FAILED
            description = "Run finalizada com erros."
        elif status_str == "cancelled":
            status = TimelineEventStatus.SKIPPED
            description = "Run cancelada pelo usuário."
        else:
            status = TimelineEventStatus.COMPLETED
            description = "Run finalizada."

        event = RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=status,
            timestamp=timeline.completed_at,
            description=description,
        )

        if status_str == "failed":
            error_msg = state_data.get("error_message", "")
            if error_msg:
                event.errors.append(error_msg)
                event.details.append(TimelineEventDetail(
                    label="Erro",
                    content=error_msg,
                    detail_type="text"
                ))

        # Check for artifacts
        run_dir = self.runs_dir / timeline.run_id
        if run_dir.exists():
            artifacts = []
            final_dir = run_dir / "final"
            if final_dir.exists():
                for f in final_dir.iterdir():
                    artifacts.append(f.name)

            if artifacts:
                event.details.append(TimelineEventDetail(
                    label="Artefatos",
                    content="\n".join(artifacts),
                    detail_type="files"
                ))

        if timeline.total_duration_seconds:
            mins = int(timeline.total_duration_seconds // 60)
            secs = int(timeline.total_duration_seconds % 60)
            event.details.append(TimelineEventDetail(
                label="Duração Total",
                content=f"{mins}m {secs}s" if mins else f"{secs}s",
                detail_type="text"
            ))

        timeline.add_event(event)


def get_timeline_builder(workspace_path: Path) -> TimelineBuilder:
    """Factory function to create a TimelineBuilder."""
    return TimelineBuilder(workspace_path)
