"""Background worker for diagnostics execution.

Runs diagnostic checks in a separate thread to avoid blocking the UI.
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool

from orchestrator.diagnostics import (
    SystemDiagnostics,
    DiagnosticReport,
    DiagnosticCheckResult,
    DiagnosticStatus,
)

logger = logging.getLogger("ai_orchestrator.diagnostics_worker")


class DiagnosticsWorkerSignals(QObject):
    """Signals for diagnostics worker communication."""

    # Emitted when diagnostics start
    diagnostics_started = Signal()

    # Emitted when a single check starts
    check_started = Signal(str)  # check_key

    # Emitted when a single check completes
    check_completed = Signal(object)  # DiagnosticCheckResult

    # Emitted when all diagnostics complete
    diagnostics_completed = Signal(object)  # DiagnosticReport

    # Emitted on unexpected error
    diagnostics_failed = Signal(str)  # error message


class DiagnosticsWorker(QRunnable):
    """
    Worker that runs all diagnostic checks in background.

    Usage:
        worker = DiagnosticsWorker(config, paths, project_path)
        worker.signals.diagnostics_started.connect(on_started)
        worker.signals.check_completed.connect(on_check_done)
        worker.signals.diagnostics_completed.connect(on_completed)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        config=None,
        paths=None,
        project_path: Optional[Path] = None,
    ):
        super().__init__()
        self.config = config
        self.paths = paths
        self.project_path = project_path
        self.signals = DiagnosticsWorkerSignals()
        self._cancelled = False
        self._diagnostics: Optional[SystemDiagnostics] = None

    def run(self):
        """Execute all diagnostic checks in background thread."""
        logger.info("DiagnosticsWorker starting")

        try:
            self.signals.diagnostics_started.emit()

            # Create diagnostics instance
            self._diagnostics = SystemDiagnostics(
                config=self.config,
                paths=self.paths,
                project_path=self.project_path,
            )

            # Run all checks with callbacks
            report = self._diagnostics.run_all(
                on_check_started=self._on_check_started,
                on_check_completed=self._on_check_completed,
            )

            if self._cancelled:
                logger.info("DiagnosticsWorker cancelled")
                return

            logger.info(f"Diagnostics completed: {report.overall_status.value}")
            self.signals.diagnostics_completed.emit(report)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"DiagnosticsWorker error: {error_msg}")
            logger.debug(traceback.format_exc())
            self.signals.diagnostics_failed.emit(error_msg)

    def _on_check_started(self, check_key: str):
        """Callback when a check starts."""
        if not self._cancelled:
            self.signals.check_started.emit(check_key)

    def _on_check_completed(self, result: DiagnosticCheckResult):
        """Callback when a check completes."""
        if not self._cancelled:
            self.signals.check_completed.emit(result)

    def cancel(self):
        """Cancel the diagnostics."""
        self._cancelled = True
        if self._diagnostics:
            self._diagnostics.cancel()
        logger.info("DiagnosticsWorker cancelled")


class SingleCheckWorker(QRunnable):
    """
    Worker that runs a single diagnostic check.

    Usage:
        worker = SingleCheckWorker("openai", config, paths)
        worker.signals.check_completed.connect(on_done)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        check_key: str,
        config=None,
        paths=None,
        project_path: Optional[Path] = None,
    ):
        super().__init__()
        self.check_key = check_key
        self.config = config
        self.paths = paths
        self.project_path = project_path
        self.signals = DiagnosticsWorkerSignals()

    def run(self):
        """Execute single diagnostic check."""
        logger.info(f"SingleCheckWorker running: {self.check_key}")

        try:
            self.signals.check_started.emit(self.check_key)

            diagnostics = SystemDiagnostics(
                config=self.config,
                paths=self.paths,
                project_path=self.project_path,
            )

            result = diagnostics.run_single(self.check_key)

            if result:
                logger.info(f"Check {self.check_key} completed: {result.status.value}")
                self.signals.check_completed.emit(result)
            else:
                logger.warning(f"Check {self.check_key} not found")
                self.signals.diagnostics_failed.emit(f"Check not found: {self.check_key}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"SingleCheckWorker error: {error_msg}")
            self.signals.diagnostics_failed.emit(error_msg)


class DiagnosticsManager:
    """
    Manager for running diagnostics with proper thread handling.

    Usage:
        manager = DiagnosticsManager(config, paths)
        manager.run_all(
            on_started=lambda: print("Started"),
            on_check_completed=lambda r: print(r.key),
            on_completed=lambda r: print(r.overall_status),
        )
    """

    def __init__(self, config=None, paths=None, project_path: Optional[Path] = None):
        self.config = config
        self.paths = paths
        self.project_path = project_path
        self._thread_pool = QThreadPool.globalInstance()
        self._current_worker: Optional[DiagnosticsWorker] = None

    @property
    def is_running(self) -> bool:
        """Check if diagnostics are currently running."""
        return self._current_worker is not None

    def run_all(
        self,
        on_started: Optional[callable] = None,
        on_check_started: Optional[callable] = None,
        on_check_completed: Optional[callable] = None,
        on_completed: Optional[callable] = None,
        on_failed: Optional[callable] = None,
    ) -> bool:
        """
        Start running all diagnostic checks.

        Args:
            on_started: Callback when diagnostics start
            on_check_started: Callback when a check starts (receives check_key)
            on_check_completed: Callback when a check completes (receives result)
            on_completed: Callback when all checks complete (receives report)
            on_failed: Callback on error (receives error message)

        Returns:
            True if started, False if already running
        """
        if self.is_running:
            logger.warning("Diagnostics already running")
            return False

        worker = DiagnosticsWorker(
            config=self.config,
            paths=self.paths,
            project_path=self.project_path,
        )

        # Connect signals
        if on_started:
            worker.signals.diagnostics_started.connect(on_started)
        if on_check_started:
            worker.signals.check_started.connect(on_check_started)
        if on_check_completed:
            worker.signals.check_completed.connect(on_check_completed)
        if on_completed:
            worker.signals.diagnostics_completed.connect(on_completed)
        if on_failed:
            worker.signals.diagnostics_failed.connect(on_failed)

        # Track completion
        def on_finished(*args):
            self._current_worker = None

        worker.signals.diagnostics_completed.connect(on_finished)
        worker.signals.diagnostics_failed.connect(on_finished)

        self._current_worker = worker
        self._thread_pool.start(worker)

        logger.info("Diagnostics worker started")
        return True

    def run_single(
        self,
        check_key: str,
        on_started: Optional[callable] = None,
        on_completed: Optional[callable] = None,
        on_failed: Optional[callable] = None,
    ) -> bool:
        """
        Run a single diagnostic check.

        Args:
            check_key: The check to run
            on_started: Callback when check starts
            on_completed: Callback when check completes (receives result)
            on_failed: Callback on error (receives error message)

        Returns:
            True if started
        """
        worker = SingleCheckWorker(
            check_key=check_key,
            config=self.config,
            paths=self.paths,
            project_path=self.project_path,
        )

        if on_started:
            worker.signals.check_started.connect(on_started)
        if on_completed:
            worker.signals.check_completed.connect(on_completed)
        if on_failed:
            worker.signals.diagnostics_failed.connect(on_failed)

        self._thread_pool.start(worker)
        logger.info(f"Single check worker started: {check_key}")
        return True

    def cancel(self):
        """Cancel current diagnostics if running."""
        if self._current_worker:
            self._current_worker.cancel()
            self._current_worker = None
            logger.info("Diagnostics cancelled")

    def export_report(
        self,
        report: DiagnosticReport,
        workspace_path: Path,
        format: str = "both"
    ) -> dict:
        """
        Export diagnostic report to files.

        Args:
            report: The report to export
            workspace_path: Workspace directory
            format: "json", "markdown", or "both"

        Returns:
            Dict with file paths: {"json": path, "markdown": path}
        """
        logs_dir = workspace_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = {}

        if format in ("json", "both"):
            json_path = logs_dir / f"diagnostics_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            paths["json"] = json_path
            logger.info(f"Exported JSON report: {json_path}")

        if format in ("markdown", "both"):
            md_path = logs_dir / f"diagnostics_{timestamp}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(report.to_markdown())
            paths["markdown"] = md_path
            logger.info(f"Exported Markdown report: {md_path}")

        return paths
