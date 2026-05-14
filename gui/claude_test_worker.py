"""Background worker for Claude Code CLI detection/testing.

Runs the (timeout-bounded) ``claude --version`` probe off the UI thread so the
window never freezes while the executable is being validated.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

logger = logging.getLogger("ai_orchestrator.claude_test")


class ClaudeTestSignals(QObject):
    """Signals emitted by :class:`ClaudeTestWorker`."""

    started = Signal()
    finished = Signal(dict)  # ClaudeDetectionResult.to_dict()
    error = Signal(str)


class ClaudeTestWorker(QRunnable):
    """Worker that probes the Claude CLI in a background thread."""

    def __init__(
        self,
        command: str,
        project_root: Optional[Path] = None,
        timeout: int = 15,
    ):
        super().__init__()
        self.command = command
        self.project_root = project_root
        self.timeout = timeout
        self.signals = ClaudeTestSignals()

    def run(self):
        """Execute the Claude probe and emit the result."""
        try:
            self.signals.started.emit()
            from orchestrator.claude_detector import ClaudeExecutorDetector

            detector = ClaudeExecutorDetector(self.command, self.project_root)
            result = detector.test(timeout=self.timeout)
            self.signals.finished.emit(result.to_dict())
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("ClaudeTestWorker error: %s", exc)
            logger.debug(traceback.format_exc())
            self.signals.error.emit(str(exc))


class ClaudeTestManager:
    """Convenience runner that keeps one Claude test in flight at a time."""

    def __init__(self):
        self._thread_pool = QThreadPool.globalInstance()
        self._current_worker: Optional[ClaudeTestWorker] = None

    @property
    def is_running(self) -> bool:
        return self._current_worker is not None

    def run_test(
        self,
        command: str,
        project_root: Optional[Path] = None,
        timeout: int = 15,
        on_started: Optional[Callable[[], None]] = None,
        on_finished: Optional[Callable[[dict], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Start a Claude test in the background. Returns False if one is running."""
        if self.is_running:
            logger.warning("Claude test already running")
            return False

        worker = ClaudeTestWorker(command=command, project_root=project_root, timeout=timeout)

        if on_started:
            worker.signals.started.connect(on_started)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        if on_error:
            worker.signals.error.connect(on_error)

        def _clear(*_args):
            self._current_worker = None

        worker.signals.finished.connect(_clear)
        worker.signals.error.connect(_clear)

        self._current_worker = worker
        self._thread_pool.start(worker)
        return True
