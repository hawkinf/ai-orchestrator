"""Background worker for dashboard data loading.

Runs data loading in a separate thread to avoid blocking the UI.
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool, QTimer

from orchestrator.run_index import (
    RunIndex,
    RunSummary,
    RunMetrics,
    RunFilter,
    get_run_index,
)

logger = logging.getLogger("ai_orchestrator.dashboard_worker")


class DashboardWorkerSignals(QObject):
    """Signals for dashboard worker communication."""

    # Emitted when data loading starts
    loading_started = Signal()

    # Emitted when data loading completes
    data_loaded = Signal(object, object, object)  # runs, metrics, profiles

    # Emitted on error
    loading_failed = Signal(str)  # error message


class DashboardLoadWorker(QRunnable):
    """
    Worker that loads dashboard data in background.

    Usage:
        worker = DashboardLoadWorker(workspace_path)
        worker.signals.data_loaded.connect(on_data_loaded)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        workspace_path: Path,
        filter_criteria: Optional[RunFilter] = None,
        limit: Optional[int] = None,
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.filter_criteria = filter_criteria
        self.limit = limit
        self.signals = DashboardWorkerSignals()

    def run(self):
        """Execute data loading in background thread."""
        logger.debug("DashboardLoadWorker starting")

        try:
            self.signals.loading_started.emit()

            # Create index
            index = get_run_index(self.workspace_path)
            index.refresh()  # Force fresh read

            # Get runs
            if self.filter_criteria:
                runs = index.filter_runs(self.filter_criteria, limit=self.limit)
            else:
                runs = index.get_all_runs(limit=self.limit)

            # Get metrics
            metrics = index.get_metrics()

            # Get profiles
            profiles = index.get_profiles()

            logger.debug(f"Loaded {len(runs)} runs, metrics calculated")
            self.signals.data_loaded.emit(runs, metrics, profiles)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"DashboardLoadWorker error: {error_msg}")
            logger.debug(traceback.format_exc())
            self.signals.loading_failed.emit(error_msg)


class ExportWorker(QRunnable):
    """Worker that exports dashboard data in background."""

    def __init__(
        self,
        workspace_path: Path,
        output_dir: Path,
        format: str = "both",  # json, markdown, or both
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.output_dir = output_dir
        self.format = format
        self.signals = DashboardWorkerSignals()

    def run(self):
        """Execute export in background thread."""
        logger.debug("ExportWorker starting")

        try:
            self.signals.loading_started.emit()

            index = get_run_index(self.workspace_path)
            index.refresh()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paths = {}

            if self.format in ("json", "both"):
                json_path = self.output_dir / f"dashboard_{timestamp}.json"
                index.export_to_json(json_path)
                paths["json"] = json_path

            if self.format in ("markdown", "both"):
                md_path = self.output_dir / f"dashboard_{timestamp}.md"
                index.export_to_markdown(md_path)
                paths["markdown"] = md_path

            logger.info(f"Export completed: {paths}")
            # Signal completion with paths info
            self.signals.data_loaded.emit(paths, None, None)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ExportWorker error: {error_msg}")
            self.signals.loading_failed.emit(error_msg)


class DashboardManager:
    """
    Manager for dashboard data loading with auto-refresh support.

    Usage:
        manager = DashboardManager(workspace_path)
        manager.start_auto_refresh(
            on_data=lambda runs, metrics, profiles: print(f"Got {len(runs)} runs"),
            interval_ms=5000
        )
    """

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = workspace_path
        self._thread_pool = QThreadPool.globalInstance()
        self._auto_refresh_timer: Optional[QTimer] = None
        self._is_loading = False
        self._on_data_callback = None
        self._on_error_callback = None
        self._filter: Optional[RunFilter] = None
        self._limit: Optional[int] = 100

    def set_workspace(self, workspace_path: Path):
        """Set workspace path."""
        self.workspace_path = workspace_path

    def set_filter(self, filter_criteria: Optional[RunFilter]):
        """Set filter for data loading."""
        self._filter = filter_criteria

    def set_limit(self, limit: Optional[int]):
        """Set limit for data loading."""
        self._limit = limit

    @property
    def is_loading(self) -> bool:
        """Check if data is currently loading."""
        return self._is_loading

    def load_data(
        self,
        on_data: Optional[callable] = None,
        on_error: Optional[callable] = None,
    ) -> bool:
        """
        Load dashboard data once.

        Args:
            on_data: Callback(runs, metrics, profiles) when data loads
            on_error: Callback(error_msg) on error

        Returns:
            True if started, False if already loading or no workspace
        """
        if self._is_loading:
            logger.debug("Already loading, skipping")
            return False

        if not self.workspace_path:
            logger.warning("No workspace path set")
            return False

        self._is_loading = True

        worker = DashboardLoadWorker(
            workspace_path=self.workspace_path,
            filter_criteria=self._filter,
            limit=self._limit,
        )

        def on_loaded(runs, metrics, profiles):
            self._is_loading = False
            if on_data:
                on_data(runs, metrics, profiles)

        def on_failed(error_msg):
            self._is_loading = False
            if on_error:
                on_error(error_msg)

        worker.signals.data_loaded.connect(on_loaded)
        worker.signals.loading_failed.connect(on_failed)

        self._thread_pool.start(worker)
        return True

    def start_auto_refresh(
        self,
        on_data: callable,
        on_error: Optional[callable] = None,
        interval_ms: int = 5000,
    ):
        """
        Start auto-refresh timer.

        Args:
            on_data: Callback for data updates
            on_error: Callback for errors
            interval_ms: Refresh interval in milliseconds
        """
        self.stop_auto_refresh()

        self._on_data_callback = on_data
        self._on_error_callback = on_error

        self._auto_refresh_timer = QTimer()
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)
        self._auto_refresh_timer.start(interval_ms)

        # Do initial load
        self.load_data(on_data, on_error)

        logger.info(f"Auto-refresh started with interval {interval_ms}ms")

    def stop_auto_refresh(self):
        """Stop auto-refresh timer."""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()
            self._auto_refresh_timer = None
            logger.info("Auto-refresh stopped")

    def _on_auto_refresh(self):
        """Handle auto-refresh timer tick."""
        self.load_data(self._on_data_callback, self._on_error_callback)

    def export_data(
        self,
        output_dir: Path,
        format: str = "both",
        on_complete: Optional[callable] = None,
        on_error: Optional[callable] = None,
    ) -> bool:
        """
        Export dashboard data.

        Args:
            output_dir: Directory for output files
            format: "json", "markdown", or "both"
            on_complete: Callback with paths dict
            on_error: Callback on error

        Returns:
            True if started
        """
        if not self.workspace_path:
            logger.warning("No workspace path set")
            return False

        worker = ExportWorker(
            workspace_path=self.workspace_path,
            output_dir=output_dir,
            format=format,
        )

        if on_complete:
            worker.signals.data_loaded.connect(
                lambda paths, _, __: on_complete(paths)
            )
        if on_error:
            worker.signals.loading_failed.connect(on_error)

        self._thread_pool.start(worker)
        return True

    def get_clipboard_summary(self) -> str:
        """Get summary text for clipboard."""
        if not self.workspace_path:
            return "No workspace configured"

        try:
            index = get_run_index(self.workspace_path)
            metrics = index.get_metrics()
            runs = index.get_all_runs(limit=10)

            lines = [
                "=== AI Orchestrator Dashboard ===",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "--- Metrics ---",
                f"Total: {metrics.total_runs}",
                f"Running: {metrics.running_runs}",
                f"Completed: {metrics.completed_runs}",
                f"Failed: {metrics.failed_runs}",
                f"Checkpoint: {metrics.checkpoint_runs}",
                "",
                "--- Recent Runs ---",
            ]

            for run in runs[:5]:
                status = run.status.value.upper()
                task = run.task_summary[:50]
                lines.append(f"[{status}] {run.run_id[:12]} - {task}")

            return "\n".join(lines)

        except Exception as e:
            return f"Error generating summary: {e}"
