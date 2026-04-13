"""Background workers for checkpoint center panel.

Handles data loading, checkpoint actions, and export in background threads.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from orchestrator.checkpoint_index import (
    CheckpointDecisionStatus,
    CheckpointDetail,
    CheckpointFilter,
    CheckpointIndex,
    CheckpointMetrics,
    CheckpointSummary,
    get_checkpoint_index,
)
from orchestrator.checkpoint import CheckpointManager
from orchestrator.state_store import StateStore
from orchestrator.paths import OrchestratorPaths
from orchestrator.config import OrchestratorConfig

logger = logging.getLogger("ai_orchestrator.checkpoints_worker")


class CheckpointWorkerSignals(QObject):
    """Signals for checkpoint workers."""
    loading_started = Signal()
    data_loaded = Signal(list, object, list)  # checkpoints, metrics, reasons
    detail_loaded = Signal(object)  # CheckpointDetail
    loading_failed = Signal(str)
    action_completed = Signal(str, bool, str)  # action, success, message
    export_completed = Signal(str, bool, str)  # format, success, path/error


class CheckpointLoadWorker(QRunnable):
    """Worker for loading checkpoint data in background."""

    def __init__(
        self,
        workspace_path: Path,
        filter_criteria: Optional[CheckpointFilter] = None,
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.filter_criteria = filter_criteria
        self.signals = CheckpointWorkerSignals()

    def run(self):
        """Load checkpoint data."""
        try:
            self.signals.loading_started.emit()

            index = get_checkpoint_index(self.workspace_path)
            index.refresh()

            if self.filter_criteria:
                checkpoints = index.filter_checkpoints(self.filter_criteria)
            else:
                checkpoints = index.get_all_checkpoints()

            metrics = index.get_metrics()
            reasons = index.get_reasons()

            self.signals.data_loaded.emit(checkpoints, metrics, reasons)

        except Exception as e:
            logger.exception("Error loading checkpoint data")
            self.signals.loading_failed.emit(str(e))


class CheckpointDetailWorker(QRunnable):
    """Worker for loading checkpoint details in background."""

    def __init__(self, workspace_path: Path, checkpoint_id: str):
        super().__init__()
        self.workspace_path = workspace_path
        self.checkpoint_id = checkpoint_id
        self.signals = CheckpointWorkerSignals()

    def run(self):
        """Load checkpoint detail."""
        try:
            index = get_checkpoint_index(self.workspace_path)
            detail = index.get_checkpoint_detail(self.checkpoint_id)
            self.signals.detail_loaded.emit(detail)

        except Exception as e:
            logger.exception(f"Error loading checkpoint detail: {self.checkpoint_id}")
            self.signals.loading_failed.emit(str(e))


class CheckpointActionWorker(QRunnable):
    """Worker for executing checkpoint actions (approve/reject) in background."""

    def __init__(
        self,
        workspace_path: Path,
        config: OrchestratorConfig,
        run_id: str,
        action: str,  # "approve" or "reject"
        note: str = "",
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.config = config
        self.run_id = run_id
        self.action = action
        self.note = note
        self.signals = CheckpointWorkerSignals()

    def run(self):
        """Execute checkpoint action."""
        try:
            paths = OrchestratorPaths(workspace_root=self.workspace_path)
            store = StateStore(paths)
            manager = CheckpointManager(store, self.config)

            if self.action == "approve":
                result = manager.approve_checkpoint(self.run_id, self.note)
                if result:
                    self.signals.action_completed.emit(
                        "approve", True, f"Checkpoint aprovado para run {self.run_id}"
                    )
                else:
                    self.signals.action_completed.emit(
                        "approve", False, f"Run {self.run_id} nao encontrada ou sem checkpoint"
                    )
            elif self.action == "reject":
                result = manager.reject_checkpoint(self.run_id, self.note)
                if result:
                    self.signals.action_completed.emit(
                        "reject", True, f"Checkpoint rejeitado para run {self.run_id}"
                    )
                else:
                    self.signals.action_completed.emit(
                        "reject", False, f"Run {self.run_id} nao encontrada ou sem checkpoint"
                    )
            else:
                self.signals.action_completed.emit(
                    self.action, False, f"Acao desconhecida: {self.action}"
                )

        except Exception as e:
            logger.exception(f"Error executing checkpoint action: {self.action}")
            self.signals.action_completed.emit(self.action, False, str(e))


class CheckpointExportWorker(QRunnable):
    """Worker for exporting checkpoint data in background."""

    def __init__(
        self,
        workspace_path: Path,
        output_dir: Path,
        format: str,  # "json", "markdown", or "both"
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.output_dir = output_dir
        self.format = format
        self.signals = CheckpointWorkerSignals()

    def run(self):
        """Export checkpoint data."""
        try:
            index = get_checkpoint_index(self.workspace_path)
            index.refresh()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paths = []

            if self.format in ("json", "both"):
                json_path = self.output_dir / f"checkpoints_{timestamp}.json"
                index.export_to_json(json_path)
                paths.append(str(json_path))

            if self.format in ("markdown", "both"):
                md_path = self.output_dir / f"checkpoints_{timestamp}.md"
                index.export_to_markdown(md_path)
                paths.append(str(md_path))

            self.signals.export_completed.emit(
                self.format, True, ", ".join(paths)
            )

        except Exception as e:
            logger.exception("Error exporting checkpoint data")
            self.signals.export_completed.emit(self.format, False, str(e))


class CheckpointManager:
    """Manager for checkpoint center operations.

    Provides high-level API for the checkpoint panel:
    - Loading data with optional filtering
    - Auto-refresh functionality
    - Checkpoint actions
    - Export operations
    """

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        config: Optional[OrchestratorConfig] = None,
    ):
        self.workspace_path = workspace_path
        self.config = config
        self.thread_pool = QThreadPool.globalInstance()
        self._filter: Optional[CheckpointFilter] = None
        self._auto_refresh_timer: Optional[QTimer] = None
        self._is_loading = False

        # Callbacks
        self._on_data_loaded: Optional[Callable] = None
        self._on_detail_loaded: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_action_completed: Optional[Callable] = None
        self._on_export_completed: Optional[Callable] = None

    @property
    def is_loading(self) -> bool:
        """Check if currently loading data."""
        return self._is_loading

    def set_workspace(self, workspace_path: Path):
        """Set workspace path."""
        self.workspace_path = workspace_path

    def set_config(self, config: OrchestratorConfig):
        """Set config."""
        self.config = config

    def set_filter(self, filter_criteria: Optional[CheckpointFilter]):
        """Set filter criteria for loading."""
        self._filter = filter_criteria

    def set_callbacks(
        self,
        on_data_loaded: Optional[Callable] = None,
        on_detail_loaded: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_action_completed: Optional[Callable] = None,
        on_export_completed: Optional[Callable] = None,
    ):
        """Set callback functions."""
        self._on_data_loaded = on_data_loaded
        self._on_detail_loaded = on_detail_loaded
        self._on_error = on_error
        self._on_action_completed = on_action_completed
        self._on_export_completed = on_export_completed

    def load_data(self):
        """Load checkpoint data in background."""
        if not self.workspace_path:
            if self._on_error:
                self._on_error("Workspace nao configurado")
            return

        self._is_loading = True
        worker = CheckpointLoadWorker(self.workspace_path, self._filter)

        if self._on_data_loaded:
            worker.signals.data_loaded.connect(self._handle_data_loaded)
        if self._on_error:
            worker.signals.loading_failed.connect(self._on_error)

        self.thread_pool.start(worker)

    def _handle_data_loaded(self, checkpoints, metrics, reasons):
        """Handle data loaded callback."""
        self._is_loading = False
        if self._on_data_loaded:
            self._on_data_loaded(checkpoints, metrics, reasons)

    def load_detail(self, checkpoint_id: str):
        """Load checkpoint detail in background."""
        if not self.workspace_path:
            return

        worker = CheckpointDetailWorker(self.workspace_path, checkpoint_id)

        if self._on_detail_loaded:
            worker.signals.detail_loaded.connect(self._on_detail_loaded)
        if self._on_error:
            worker.signals.loading_failed.connect(self._on_error)

        self.thread_pool.start(worker)

    def approve_checkpoint(self, run_id: str, note: str = ""):
        """Approve a checkpoint."""
        if not self.workspace_path or not self.config:
            if self._on_error:
                self._on_error("Configuracao incompleta")
            return

        worker = CheckpointActionWorker(
            self.workspace_path, self.config, run_id, "approve", note
        )

        if self._on_action_completed:
            worker.signals.action_completed.connect(self._on_action_completed)
        if self._on_error:
            worker.signals.loading_failed.connect(self._on_error)

        self.thread_pool.start(worker)

    def reject_checkpoint(self, run_id: str, note: str = ""):
        """Reject a checkpoint."""
        if not self.workspace_path or not self.config:
            if self._on_error:
                self._on_error("Configuracao incompleta")
            return

        worker = CheckpointActionWorker(
            self.workspace_path, self.config, run_id, "reject", note
        )

        if self._on_action_completed:
            worker.signals.action_completed.connect(self._on_action_completed)
        if self._on_error:
            worker.signals.loading_failed.connect(self._on_error)

        self.thread_pool.start(worker)

    def export_data(self, format: str = "both"):
        """Export checkpoint data."""
        if not self.workspace_path:
            if self._on_error:
                self._on_error("Workspace nao configurado")
            return

        output_dir = self.workspace_path / "logs"
        worker = CheckpointExportWorker(self.workspace_path, output_dir, format)

        if self._on_export_completed:
            worker.signals.export_completed.connect(self._on_export_completed)
        if self._on_error:
            worker.signals.loading_failed.connect(self._on_error)

        self.thread_pool.start(worker)

    def start_auto_refresh(self, interval_ms: int = 5000):
        """Start auto-refresh timer."""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()

        self._auto_refresh_timer = QTimer()
        self._auto_refresh_timer.timeout.connect(self.load_data)
        self._auto_refresh_timer.start(interval_ms)

    def stop_auto_refresh(self):
        """Stop auto-refresh timer."""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()
            self._auto_refresh_timer = None

    def get_clipboard_summary(self) -> str:
        """Generate summary text for clipboard."""
        if not self.workspace_path:
            return "Workspace nao configurado"

        try:
            index = get_checkpoint_index(self.workspace_path)
            index.refresh()
            metrics = index.get_metrics()
            pending = index.get_pending_checkpoints()

            lines = [
                "=== AI Orchestrator - Checkpoint Center ===",
                "",
                f"Total: {metrics.total_checkpoints}",
                f"Pendentes: {metrics.pending_checkpoints}",
                f"Aprovados: {metrics.approved_checkpoints}",
                f"Rejeitados: {metrics.rejected_checkpoints}",
                "",
            ]

            if pending:
                lines.append("--- Checkpoints Pendentes ---")
                for cp in pending[:10]:
                    created = cp.created_at.strftime("%d/%m %H:%M") if cp.created_at else "-"
                    lines.append(
                        f"[{cp.severity.value.upper()}] {cp.run_id[:16]} - "
                        f"{cp.reason_display} ({created})"
                    )
                if len(pending) > 10:
                    lines.append(f"... e mais {len(pending) - 10} checkpoints")
            else:
                lines.append("Nenhum checkpoint pendente")

            lines.extend([
                "",
                f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ])

            return "\n".join(lines)

        except Exception as e:
            logger.exception("Error generating clipboard summary")
            return f"Erro ao gerar resumo: {e}"
