"""Run executor that wraps IntegratedTaskEngine with progress events.

Provides a GUI-friendly wrapper that emits structured progress events
during pipeline execution without duplicating core logic.
"""

import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, List

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("ai_orchestrator.run_executor")


class RunPhase(Enum):
    """Phases of a pipeline run."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    VALIDATING = "validating"
    COMMITTING = "committing"
    PUSHING = "pushing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINT = "checkpoint"


@dataclass
class RunProgressEvent:
    """Structured progress event from run execution."""
    run_id: str
    phase: RunPhase
    message: str
    iteration: int = 0
    max_iterations: int = 3
    timestamp: datetime = None
    details: Optional[dict] = None
    is_error: bool = False
    checkpoint_reason: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "message": self.message,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "is_error": self.is_error,
            "checkpoint_reason": self.checkpoint_reason,
        }


class RunExecutorSignals(QObject):
    """Signals emitted by RunExecutor."""

    # Emitted when run starts
    run_started = Signal(str)  # run_id

    # Emitted with progress updates
    progress = Signal(object)  # RunProgressEvent

    # Emitted when phase changes
    phase_changed = Signal(str, str)  # run_id, phase_name

    # Emitted when iteration changes
    iteration_changed = Signal(str, int, int)  # run_id, current, max

    # Emitted when checkpoint is needed
    checkpoint_pending = Signal(str, str, str)  # run_id, reason, description

    # Emitted when run completes successfully
    run_completed = Signal(str, dict)  # run_id, summary dict

    # Emitted when run fails
    run_failed = Signal(str, str)  # run_id, error message

    # Emitted for any status change
    status_changed = Signal(str, str)  # run_id, new status


class RunExecutor:
    """
    Executes pipeline runs with progress reporting.

    Wraps IntegratedTaskEngine and emits structured events during execution.
    Does NOT run in a thread - use with QRunnable or ThreadPoolExecutor.
    """

    def __init__(
        self,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ):
        self.project_path = project_path or Path.cwd()
        self.config_path = config_path
        self.mock_executor = mock_executor
        self.signals = RunExecutorSignals()

        self._engine = None
        self._current_run_id: Optional[str] = None
        self._cancelled = False

    def _emit_progress(
        self,
        run_id: str,
        phase: RunPhase,
        message: str,
        iteration: int = 0,
        max_iterations: int = 3,
        details: Optional[dict] = None,
        is_error: bool = False,
        checkpoint_reason: Optional[str] = None,
    ):
        """Emit a progress event."""
        event = RunProgressEvent(
            run_id=run_id,
            phase=phase,
            message=message,
            iteration=iteration,
            max_iterations=max_iterations,
            details=details,
            is_error=is_error,
            checkpoint_reason=checkpoint_reason,
        )
        self.signals.progress.emit(event)
        logger.debug(f"Progress: {phase.value} - {message}")

    def _init_engine(self):
        """Initialize the engine lazily."""
        if self._engine is not None:
            return

        from orchestrator.config import load_config
        from orchestrator.paths import OrchestratorPaths
        from orchestrator.integrated_engine import IntegratedTaskEngine

        # Load config
        if self.config_path and self.config_path.exists():
            config = load_config(self.config_path)
        else:
            config = load_config(self.project_path / "config.yaml")

        # Setup paths
        paths = OrchestratorPaths(self.project_path)

        # Create engine
        self._engine = IntegratedTaskEngine(
            config=config,
            paths=paths,
            mock_executor=self.mock_executor,
        )

        logger.info(f"Engine initialized for project: {self.project_path}")

    def start_run(
        self,
        task_description: str,
        profile: Optional[str] = None,
        auto_commit: bool = False,
        auto_push: bool = False,
        max_iterations: int = 3,
    ) -> Optional[str]:
        """
        Start a new pipeline run.

        Args:
            task_description: The task to execute
            profile: Project profile (flutter, python, etc.)
            auto_commit: Whether to auto-commit changes
            auto_push: Whether to auto-push after commit
            max_iterations: Maximum execution iterations

        Returns:
            run_id if started, None if failed
        """
        self._cancelled = False

        try:
            # Initialize engine
            self._emit_progress(
                run_id="pending",
                phase=RunPhase.INITIALIZING,
                message="Inicializando engine...",
            )

            self._init_engine()

            if self._cancelled:
                return None

            # Start the run
            self._emit_progress(
                run_id="pending",
                phase=RunPhase.INITIALIZING,
                message="Criando nova run...",
            )

            # The engine's start() method runs the entire pipeline
            # We need to intercept and report progress
            state = self._execute_pipeline(
                task_description=task_description,
                profile=profile,
                max_iterations=max_iterations,
            )

            if state is None:
                return None

            self._current_run_id = state.run_id

            # Check final status
            from orchestrator.models import TaskStatus

            if state.status == TaskStatus.COMPLETED:
                summary = self._build_summary(state)
                self.signals.run_completed.emit(state.run_id, summary)
                return state.run_id

            elif state.status == TaskStatus.CHECKPOINT:
                reason = state.checkpoint.reason.value if state.checkpoint else "unknown"
                description = state.checkpoint.description if state.checkpoint else ""
                self.signals.checkpoint_pending.emit(state.run_id, reason, description)
                return state.run_id

            elif state.status == TaskStatus.FAILED:
                error = state.error_message or "Unknown error"
                self.signals.run_failed.emit(state.run_id, error)
                return state.run_id

            else:
                # Still in progress or other state
                self.signals.status_changed.emit(state.run_id, state.status.value)
                return state.run_id

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Run failed: {error_msg}")
            logger.debug(traceback.format_exc())

            run_id = self._current_run_id or "unknown"
            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.FAILED,
                message=f"Erro: {error_msg}",
                is_error=True,
            )
            self.signals.run_failed.emit(run_id, error_msg)
            return None

    def _execute_pipeline(
        self,
        task_description: str,
        profile: Optional[str],
        max_iterations: int,
    ):
        """Execute the pipeline with progress reporting."""
        from orchestrator.models import TaskStatus, TaskRequest
        from orchestrator.state_store import StateStore

        # Create task request
        task = TaskRequest(
            description=task_description,
            profile=profile,
            max_iterations=max_iterations,
        )

        # Create run via state store
        store = StateStore(self._engine.paths)
        state = store.create_run(task)
        run_id = state.run_id

        self._current_run_id = run_id
        self.signals.run_started.emit(run_id)
        self.signals.phase_changed.emit(run_id, "initializing")

        logger.info(f"Created run: {run_id}")

        # Phase 1: Planning
        if self._cancelled:
            return state

        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.PLANNING,
            message="Gerando plano com OpenAI...",
            max_iterations=max_iterations,
        )
        self.signals.phase_changed.emit(run_id, "planning")

        state = self._engine._phase_planning(state)
        store.save_state(state)

        if state.status == TaskStatus.CHECKPOINT:
            return state
        if state.status == TaskStatus.FAILED:
            return state

        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.PLANNING,
            message=f"Plano criado: {state.plan.objective[:50] if state.plan else 'N/A'}...",
            max_iterations=max_iterations,
        )

        # Phase 2-3: Execute/Review loop
        for iteration in range(1, max_iterations + 1):
            if self._cancelled:
                return state

            state.current_iteration = iteration
            self.signals.iteration_changed.emit(run_id, iteration, max_iterations)

            # Execution
            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.EXECUTING,
                message=f"Executando com Claude (iteracao {iteration})...",
                iteration=iteration,
                max_iterations=max_iterations,
            )
            self.signals.phase_changed.emit(run_id, "executing")

            state = self._engine._phase_execution(state)
            store.save_state(state)

            if state.status == TaskStatus.CHECKPOINT:
                self._emit_progress(
                    run_id=run_id,
                    phase=RunPhase.CHECKPOINT,
                    message="Checkpoint: aguardando aprovacao",
                    iteration=iteration,
                    max_iterations=max_iterations,
                    checkpoint_reason=state.checkpoint.reason.value if state.checkpoint else None,
                )
                return state

            if state.status == TaskStatus.FAILED:
                return state

            # Review
            if self._cancelled:
                return state

            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.REVIEWING,
                message=f"Revisando com OpenAI (iteracao {iteration})...",
                iteration=iteration,
                max_iterations=max_iterations,
            )
            self.signals.phase_changed.emit(run_id, "reviewing")

            state = self._engine._phase_review(state)
            store.save_state(state)

            if state.status == TaskStatus.CHECKPOINT:
                return state
            if state.status == TaskStatus.FAILED:
                return state

            # Check if review approved
            from orchestrator.models import ReviewStatus
            last_iter = state.iterations[-1] if state.iterations else None
            if last_iter and last_iter.review_response:
                if last_iter.review_response.status == ReviewStatus.APPROVED:
                    self._emit_progress(
                        run_id=run_id,
                        phase=RunPhase.REVIEWING,
                        message="Review aprovado!",
                        iteration=iteration,
                        max_iterations=max_iterations,
                    )
                    break
                elif last_iter.review_response.status == ReviewStatus.BLOCKED:
                    self._emit_progress(
                        run_id=run_id,
                        phase=RunPhase.FAILED,
                        message="Review bloqueado",
                        iteration=iteration,
                        max_iterations=max_iterations,
                        is_error=True,
                    )
                    state.status = TaskStatus.FAILED
                    state.error_message = "Review blocked execution"
                    store.save_state(state)
                    return state

        # Phase 4: Validation
        if self._cancelled:
            return state

        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.VALIDATING,
            message="Executando validacoes...",
            iteration=state.current_iteration,
            max_iterations=max_iterations,
        )
        self.signals.phase_changed.emit(run_id, "validating")

        state = self._engine._phase_validation(state)
        store.save_state(state)

        if state.status == TaskStatus.FAILED:
            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.VALIDATING,
                message="Validacao falhou",
                is_error=True,
            )
            return state

        # Phase 5: Commit
        if self._cancelled:
            return state

        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.COMMITTING,
            message="Commitando alteracoes...",
            iteration=state.current_iteration,
            max_iterations=max_iterations,
        )
        self.signals.phase_changed.emit(run_id, "committing")

        state = self._engine._phase_commit(state)
        store.save_state(state)

        if state.status == TaskStatus.CHECKPOINT:
            return state

        # Phase 6: Finalize
        if self._cancelled:
            return state

        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.FINALIZING,
            message="Finalizando e gerando relatorio...",
            iteration=state.current_iteration,
            max_iterations=max_iterations,
        )
        self.signals.phase_changed.emit(run_id, "finalizing")

        state = self._engine._phase_finalize(state)
        store.save_state(state)

        # Completed
        self._emit_progress(
            run_id=run_id,
            phase=RunPhase.COMPLETED,
            message="Run concluida com sucesso!",
            iteration=state.current_iteration,
            max_iterations=max_iterations,
        )
        self.signals.phase_changed.emit(run_id, "completed")

        return state

    def resume_run(self, run_id: str) -> Optional[str]:
        """
        Resume an existing run.

        Args:
            run_id: The run to resume

        Returns:
            run_id if resumed, None if failed
        """
        self._cancelled = False

        try:
            self._init_engine()

            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.INITIALIZING,
                message="Retomando run...",
            )

            # Use engine's resume
            state = self._engine.resume(run_id)

            if state is None:
                self.signals.run_failed.emit(run_id, "Run not found")
                return None

            self._current_run_id = run_id

            # Report final status
            from orchestrator.models import TaskStatus

            if state.status == TaskStatus.COMPLETED:
                summary = self._build_summary(state)
                self.signals.run_completed.emit(run_id, summary)
            elif state.status == TaskStatus.CHECKPOINT:
                reason = state.checkpoint.reason.value if state.checkpoint else "unknown"
                description = state.checkpoint.description if state.checkpoint else ""
                self.signals.checkpoint_pending.emit(run_id, reason, description)
            elif state.status == TaskStatus.FAILED:
                self.signals.run_failed.emit(run_id, state.error_message or "Unknown error")
            else:
                self.signals.status_changed.emit(run_id, state.status.value)

            return run_id

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Resume failed: {error_msg}")
            self.signals.run_failed.emit(run_id, error_msg)
            return None

    def approve_checkpoint(self, run_id: str, note: Optional[str] = None) -> bool:
        """Approve a pending checkpoint."""
        try:
            self._init_engine()

            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.INITIALIZING,
                message="Aprovando checkpoint...",
            )

            state = self._engine.approve_checkpoint(run_id, note)

            if state is None:
                self.signals.run_failed.emit(run_id, "Checkpoint approval failed")
                return False

            self.signals.status_changed.emit(run_id, state.status.value)
            return True

        except Exception as e:
            logger.error(f"Checkpoint approval failed: {e}")
            self.signals.run_failed.emit(run_id, str(e))
            return False

    def reject_checkpoint(self, run_id: str, reason: Optional[str] = None) -> bool:
        """Reject a pending checkpoint."""
        try:
            self._init_engine()

            self._emit_progress(
                run_id=run_id,
                phase=RunPhase.INITIALIZING,
                message="Rejeitando checkpoint...",
            )

            state = self._engine.reject_checkpoint(run_id, reason)

            if state is None:
                self.signals.run_failed.emit(run_id, "Checkpoint rejection failed")
                return False

            self.signals.status_changed.emit(run_id, state.status.value)
            return True

        except Exception as e:
            logger.error(f"Checkpoint rejection failed: {e}")
            self.signals.run_failed.emit(run_id, str(e))
            return False

    def _build_summary(self, state) -> dict:
        """Build a summary dict from run state."""
        summary = {
            "run_id": state.run_id,
            "status": state.status.value,
            "iterations": state.current_iteration,
            "task": state.task.description[:100] if state.task else "",
        }

        if state.plan:
            summary["objective"] = state.plan.objective

        if state.git_result_final:
            summary["commit_hash"] = state.git_result_final.commit_hash

        if state.validation_final:
            summary["validation_passed"] = state.validation_final.all_passed

        return summary

    def cancel(self):
        """Cancel the current execution."""
        self._cancelled = True
        logger.info("Run execution cancelled")
