"""Background worker for async task execution.

Provides QRunnable workers for running pipeline tasks in background threads.
Uses RunExecutor to wrap IntegratedTaskEngine with progress events.
"""

import logging
import traceback
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, QRunnable, QThreadPool

from .ui_models import ProgressEvent, ProgressEventType, TaskConfig
from .run_executor import RunExecutor, RunPhase, RunProgressEvent

logger = logging.getLogger("ai_orchestrator.worker")


class TaskWorkerSignals(QObject):
    """Signals for task worker communication."""
    started = Signal(str)  # run_id
    progress = Signal(ProgressEvent)
    finished = Signal(str, bool, str)  # run_id, success, message
    error = Signal(str, str)  # run_id, error_message


class RunWorkerSignals(QObject):
    """Signals for RunWorker communication with detailed progress."""

    # Emitted when run starts
    run_started = Signal(str)  # run_id

    # Emitted with progress updates (RunProgressEvent converted to dict)
    progress = Signal(dict)

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


class RunWorker(QRunnable):
    """
    Background worker for running pipeline tasks using RunExecutor.

    This worker provides detailed progress events during pipeline execution.
    Use this instead of TaskWorker for full pipeline execution with real-time updates.

    Usage:
        worker = RunWorker(task_config, project_path)
        worker.signals.run_started.connect(on_started)
        worker.signals.progress.connect(on_progress)
        worker.signals.run_completed.connect(on_completed)
        worker.signals.checkpoint_pending.connect(on_checkpoint)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        task_config: TaskConfig,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ):
        super().__init__()
        self.task_config = task_config
        self.project_path = project_path
        self.config_path = config_path
        self.mock_executor = mock_executor
        self.signals = RunWorkerSignals()
        self._executor: Optional[RunExecutor] = None
        self._cancelled = False

    def run(self):
        """Execute the pipeline in background thread."""
        logger.info(f"RunWorker starting: {self.task_config.task_description[:50]}...")

        try:
            # Create executor
            self._executor = RunExecutor(
                project_path=self.project_path,
                config_path=self.config_path,
                mock_executor=self.mock_executor,
            )

            # Connect executor signals to our signals
            self._connect_executor_signals()

            # Start the run
            run_id = self._executor.start_run(
                task_description=self.task_config.task_description,
                profile=self.task_config.profile,
                auto_commit=self.task_config.auto_commit,
                auto_push=self.task_config.auto_push,
                max_iterations=self.task_config.max_iterations,
            )

            if run_id is None:
                logger.warning("RunWorker: start_run returned None")
                # Error already emitted by executor

        except Exception as e:
            error_msg = str(e)
            logger.error(f"RunWorker error: {error_msg}")
            logger.debug(traceback.format_exc())
            self.signals.run_failed.emit("unknown", error_msg)

    def _connect_executor_signals(self):
        """Connect RunExecutor signals to our signals."""
        # Forward run_started
        self._executor.signals.run_started.connect(self.signals.run_started.emit)

        # Convert RunProgressEvent to dict and forward
        def on_progress(event: RunProgressEvent):
            self.signals.progress.emit(event.to_dict())

        self._executor.signals.progress.connect(on_progress)

        # Forward other signals
        self._executor.signals.phase_changed.connect(self.signals.phase_changed.emit)
        self._executor.signals.iteration_changed.connect(self.signals.iteration_changed.emit)
        self._executor.signals.checkpoint_pending.connect(self.signals.checkpoint_pending.emit)
        self._executor.signals.run_completed.connect(self.signals.run_completed.emit)
        self._executor.signals.run_failed.connect(self.signals.run_failed.emit)
        self._executor.signals.status_changed.connect(self.signals.status_changed.emit)

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
        if self._executor:
            self._executor.cancel()
        logger.info("RunWorker cancelled")


class ResumeRunWorker(QRunnable):
    """
    Background worker for resuming pipeline runs using RunExecutor.

    Usage:
        worker = ResumeRunWorker(run_id, project_path)
        worker.signals.run_completed.connect(on_completed)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        run_id: str,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ):
        super().__init__()
        self.run_id = run_id
        self.project_path = project_path
        self.config_path = config_path
        self.mock_executor = mock_executor
        self.signals = RunWorkerSignals()
        self._executor: Optional[RunExecutor] = None

    def run(self):
        """Resume the pipeline in background thread."""
        logger.info(f"ResumeRunWorker resuming: {self.run_id}")

        try:
            # Create executor
            self._executor = RunExecutor(
                project_path=self.project_path,
                config_path=self.config_path,
                mock_executor=self.mock_executor,
            )

            # Connect signals
            self._executor.signals.run_started.connect(self.signals.run_started.emit)
            self._executor.signals.progress.connect(
                lambda e: self.signals.progress.emit(e.to_dict())
            )
            self._executor.signals.phase_changed.connect(self.signals.phase_changed.emit)
            self._executor.signals.iteration_changed.connect(self.signals.iteration_changed.emit)
            self._executor.signals.checkpoint_pending.connect(self.signals.checkpoint_pending.emit)
            self._executor.signals.run_completed.connect(self.signals.run_completed.emit)
            self._executor.signals.run_failed.connect(self.signals.run_failed.emit)
            self._executor.signals.status_changed.connect(self.signals.status_changed.emit)

            # Resume
            result = self._executor.resume_run(self.run_id)

            if result is None:
                logger.warning(f"ResumeRunWorker: resume returned None for {self.run_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ResumeRunWorker error: {error_msg}")
            logger.debug(traceback.format_exc())
            self.signals.run_failed.emit(self.run_id, error_msg)


class CheckpointActionWorker(QRunnable):
    """
    Background worker for checkpoint approve/reject using RunExecutor.

    Usage:
        worker = CheckpointActionWorker(run_id, approve=True, note="Approved")
        worker.signals.status_changed.connect(on_status)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        run_id: str,
        approve: bool,
        note: Optional[str] = None,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ):
        super().__init__()
        self.run_id = run_id
        self.approve = approve
        self.note = note
        self.project_path = project_path
        self.config_path = config_path
        self.mock_executor = mock_executor
        self.signals = RunWorkerSignals()

    def run(self):
        """Process checkpoint action in background thread."""
        action = "approve" if self.approve else "reject"
        logger.info(f"CheckpointActionWorker: {action} checkpoint for {self.run_id}")

        try:
            executor = RunExecutor(
                project_path=self.project_path,
                config_path=self.config_path,
                mock_executor=self.mock_executor,
            )

            # Connect signals
            executor.signals.status_changed.connect(self.signals.status_changed.emit)
            executor.signals.run_completed.connect(self.signals.run_completed.emit)
            executor.signals.run_failed.connect(self.signals.run_failed.emit)

            if self.approve:
                success = executor.approve_checkpoint(self.run_id, self.note)
            else:
                success = executor.reject_checkpoint(self.run_id, self.note)

            if not success:
                self.signals.run_failed.emit(
                    self.run_id,
                    f"Falha ao {action} checkpoint"
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"CheckpointActionWorker error: {error_msg}")
            self.signals.run_failed.emit(self.run_id, error_msg)


# Legacy workers below - kept for backwards compatibility


class TaskWorker(QRunnable):
    """Background worker for running tasks (legacy - use RunWorker instead)."""

    def __init__(self, engine, task_config: TaskConfig):
        super().__init__()
        self.engine = engine
        self.task_config = task_config
        self.signals = TaskWorkerSignals()
        self._cancelled = False

    def run(self):
        """Execute the task in background thread."""
        run_id = None
        logger.info(f"TaskWorker starting: {self.task_config.task_description[:50]}...")
        try:
            # Emit start
            self.signals.progress.emit(ProgressEvent(
                event_type=ProgressEventType.RUN_STARTED,
                message="Iniciando tarefa...",
                phase="starting",
            ))

            # Start the task
            state = self.engine.start(
                self.task_config.task_description,
                self.task_config.profile,
            )
            run_id = state.run_id
            logger.info(f"Task started with run_id: {run_id}")
            self.signals.started.emit(run_id)

            # Emit completion
            if state.status.value == "completed":
                self.signals.progress.emit(ProgressEvent(
                    event_type=ProgressEventType.RUN_COMPLETED,
                    message="Tarefa concluida com sucesso!",
                    run_id=run_id,
                    phase="completed",
                ))
                self.signals.finished.emit(run_id, True, "Tarefa concluida com sucesso!")
            elif state.status.value == "checkpoint":
                self.signals.progress.emit(ProgressEvent(
                    event_type=ProgressEventType.CHECKPOINT_PENDING,
                    message="Aguardando aprovacao de checkpoint",
                    run_id=run_id,
                    phase="checkpoint",
                ))
                self.signals.finished.emit(run_id, True, "Checkpoint pendente")
            elif state.status.value == "failed":
                error_msg = state.error_message or "Erro desconhecido"
                self.signals.progress.emit(ProgressEvent(
                    event_type=ProgressEventType.RUN_FAILED,
                    message=f"Falha: {error_msg}",
                    run_id=run_id,
                    phase="failed",
                ))
                self.signals.finished.emit(run_id, False, error_msg)
            else:
                # Still in progress or other state
                self.signals.finished.emit(run_id, True, f"Status: {state.status.value}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"TaskWorker error: {error_msg}")
            logger.debug(traceback.format_exc())
            self.signals.progress.emit(ProgressEvent(
                event_type=ProgressEventType.ERROR,
                message=f"Erro: {error_msg}",
                run_id=run_id,
            ))
            self.signals.error.emit(run_id or "unknown", error_msg)

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True


class ResumeWorker(QRunnable):
    """Background worker for resuming tasks."""

    def __init__(self, engine, run_id: str):
        super().__init__()
        self.engine = engine
        self.run_id = run_id
        self.signals = TaskWorkerSignals()

    def run(self):
        """Resume the task in background thread."""
        try:
            self.signals.progress.emit(ProgressEvent(
                event_type=ProgressEventType.STATUS_UPDATE,
                message=f"Retomando run {self.run_id}...",
                run_id=self.run_id,
                phase="resuming",
            ))

            state = self.engine.resume(self.run_id)

            if not state:
                self.signals.error.emit(self.run_id, "Run nao encontrado")
                return

            if state.status.value == "completed":
                self.signals.finished.emit(self.run_id, True, "Run concluido!")
            elif state.status.value == "checkpoint":
                self.signals.finished.emit(self.run_id, True, "Checkpoint pendente")
            elif state.status.value == "failed":
                self.signals.finished.emit(self.run_id, False, state.error_message or "Falha")
            else:
                self.signals.finished.emit(self.run_id, True, f"Status: {state.status.value}")

        except Exception as e:
            self.signals.error.emit(self.run_id, str(e))


class CheckpointWorker(QRunnable):
    """Background worker for checkpoint operations."""

    def __init__(self, engine, run_id: str, approve: bool, note: Optional[str] = None):
        super().__init__()
        self.engine = engine
        self.run_id = run_id
        self.approve = approve
        self.note = note
        self.signals = TaskWorkerSignals()

    def run(self):
        """Process checkpoint decision."""
        try:
            if self.approve:
                self.signals.progress.emit(ProgressEvent(
                    event_type=ProgressEventType.STATUS_UPDATE,
                    message="Aprovando checkpoint...",
                    run_id=self.run_id,
                ))
                state = self.engine.approve_checkpoint(self.run_id, self.note)
            else:
                self.signals.progress.emit(ProgressEvent(
                    event_type=ProgressEventType.STATUS_UPDATE,
                    message="Rejeitando checkpoint...",
                    run_id=self.run_id,
                ))
                state = self.engine.reject_checkpoint(self.run_id, self.note)

            if state:
                action = "aprovado" if self.approve else "rejeitado"
                self.signals.finished.emit(self.run_id, True, f"Checkpoint {action}")
            else:
                self.signals.error.emit(self.run_id, "Falha ao processar checkpoint")

        except Exception as e:
            self.signals.error.emit(self.run_id, str(e))


class ValidationWorker(QRunnable):
    """Background worker for running validations."""

    def __init__(self, validator, run_id: str):
        super().__init__()
        self.validator = validator
        self.run_id = run_id
        self.signals = TaskWorkerSignals()

    def run(self):
        """Run validations."""
        try:
            self.signals.progress.emit(ProgressEvent(
                event_type=ProgressEventType.VALIDATION_STARTED,
                message="Executando validacoes...",
                run_id=self.run_id,
            ))

            summary = self.validator.run_all()

            self.signals.progress.emit(ProgressEvent(
                event_type=ProgressEventType.VALIDATION_COMPLETED,
                message="Validacoes concluidas",
                run_id=self.run_id,
                data={"passed": summary.all_passed, "results": len(summary.results)},
            ))

            if summary.all_passed:
                self.signals.finished.emit(self.run_id, True, "Todas validacoes passaram!")
            else:
                failed = [r.command for r in summary.results if not r.success]
                self.signals.finished.emit(
                    self.run_id, False,
                    f"Falhas: {', '.join(failed)}"
                )

        except Exception as e:
            self.signals.error.emit(self.run_id, str(e))


class WorkerManager:
    """
    Manages background workers for pipeline execution.

    Provides methods to start runs, resume runs, and handle checkpoints
    using the new RunWorker-based workers that provide detailed progress events.
    """

    def __init__(self):
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers: dict[str, QRunnable] = {}
        self._current_run_worker: Optional[RunWorker] = None

    # --- New RunExecutor-based methods ---

    def start_run(
        self,
        task_config: TaskConfig,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ) -> RunWorker:
        """
        Start a new pipeline run with detailed progress events.

        Args:
            task_config: Task configuration
            project_path: Project root path
            config_path: Optional config file path
            mock_executor: Use mock executor for testing

        Returns:
            RunWorker instance with connected signals
        """
        worker = RunWorker(
            task_config=task_config,
            project_path=project_path,
            config_path=config_path,
            mock_executor=mock_executor,
        )

        # Track the worker
        def on_started(run_id: str):
            self.active_workers[run_id] = worker

        def on_finished(run_id: str, *args):
            self.active_workers.pop(run_id, None)
            if self._current_run_worker == worker:
                self._current_run_worker = None

        worker.signals.run_started.connect(on_started)
        worker.signals.run_completed.connect(on_finished)
        worker.signals.run_failed.connect(on_finished)

        self._current_run_worker = worker
        self.thread_pool.start(worker)
        return worker

    def resume_run(
        self,
        run_id: str,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ) -> ResumeRunWorker:
        """
        Resume an existing pipeline run.

        Args:
            run_id: The run to resume
            project_path: Project root path
            config_path: Optional config file path
            mock_executor: Use mock executor for testing

        Returns:
            ResumeRunWorker instance with connected signals
        """
        worker = ResumeRunWorker(
            run_id=run_id,
            project_path=project_path,
            config_path=config_path,
            mock_executor=mock_executor,
        )

        # Track
        def on_finished(rid: str, *args):
            self.active_workers.pop(rid, None)

        self.active_workers[run_id] = worker
        worker.signals.run_completed.connect(on_finished)
        worker.signals.run_failed.connect(on_finished)

        self.thread_pool.start(worker)
        return worker

    def handle_checkpoint(
        self,
        run_id: str,
        approve: bool,
        note: Optional[str] = None,
        project_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        mock_executor: bool = False,
    ) -> CheckpointActionWorker:
        """
        Handle a checkpoint decision (approve or reject).

        Args:
            run_id: The run with pending checkpoint
            approve: True to approve, False to reject
            note: Optional note/reason
            project_path: Project root path
            config_path: Optional config file path
            mock_executor: Use mock executor for testing

        Returns:
            CheckpointActionWorker instance
        """
        worker = CheckpointActionWorker(
            run_id=run_id,
            approve=approve,
            note=note,
            project_path=project_path,
            config_path=config_path,
            mock_executor=mock_executor,
        )
        self.thread_pool.start(worker)
        return worker

    def cancel_current_run(self):
        """Cancel the currently running pipeline."""
        if self._current_run_worker:
            self._current_run_worker.cancel()
            self._current_run_worker = None

    def is_run_active(self, run_id: str) -> bool:
        """Check if a run is currently active."""
        return run_id in self.active_workers

    @property
    def has_active_run(self) -> bool:
        """Check if any run is currently active."""
        return self._current_run_worker is not None

    # --- Legacy methods for backwards compatibility ---

    def start_task(self, engine, task_config: TaskConfig) -> TaskWorker:
        """Start a new task worker (legacy - use start_run instead)."""
        worker = TaskWorker(engine, task_config)
        self.thread_pool.start(worker)
        return worker

    def resume_task(self, engine, run_id: str) -> ResumeWorker:
        """Start a resume worker (legacy - use resume_run instead)."""
        worker = ResumeWorker(engine, run_id)
        self.thread_pool.start(worker)
        return worker

    def process_checkpoint(
        self, engine, run_id: str, approve: bool, note: Optional[str] = None
    ) -> CheckpointWorker:
        """Start a checkpoint worker (legacy - use handle_checkpoint instead)."""
        worker = CheckpointWorker(engine, run_id, approve, note)
        self.thread_pool.start(worker)
        return worker

    def run_validation(self, validator, run_id: str) -> ValidationWorker:
        """Start a validation worker."""
        worker = ValidationWorker(validator, run_id)
        self.thread_pool.start(worker)
        return worker

    def wait_for_done(self):
        """Wait for all workers to finish."""
        self.thread_pool.waitForDone()
