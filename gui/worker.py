"""Background worker for async task execution."""

from datetime import datetime
from typing import Optional
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, QRunnable, QThreadPool

from .ui_models import ProgressEvent, ProgressEventType, TaskConfig


class TaskWorkerSignals(QObject):
    """Signals for task worker communication."""
    started = Signal(str)  # run_id
    progress = Signal(ProgressEvent)
    finished = Signal(str, bool, str)  # run_id, success, message
    error = Signal(str, str)  # run_id, error_message


class TaskWorker(QRunnable):
    """Background worker for running tasks."""

    def __init__(self, engine, task_config: TaskConfig):
        super().__init__()
        self.engine = engine
        self.task_config = task_config
        self.signals = TaskWorkerSignals()
        self._cancelled = False

    def run(self):
        """Execute the task in background thread."""
        run_id = None
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
    """Manages background workers."""

    def __init__(self):
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers = {}

    def start_task(self, engine, task_config: TaskConfig) -> TaskWorker:
        """Start a new task worker."""
        worker = TaskWorker(engine, task_config)
        self.thread_pool.start(worker)
        return worker

    def resume_task(self, engine, run_id: str) -> ResumeWorker:
        """Start a resume worker."""
        worker = ResumeWorker(engine, run_id)
        self.thread_pool.start(worker)
        return worker

    def process_checkpoint(
        self, engine, run_id: str, approve: bool, note: Optional[str] = None
    ) -> CheckpointWorker:
        """Start a checkpoint worker."""
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
