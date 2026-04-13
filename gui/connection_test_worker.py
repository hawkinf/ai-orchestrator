"""Background worker for connection testing.

Runs OpenAI connection tests in a separate thread to avoid blocking the UI.
"""

import logging
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool

logger = logging.getLogger("ai_orchestrator.connection_test")


class ConnectionTestSignals(QObject):
    """Signals for connection test worker communication."""

    # Emitted when test starts
    started = Signal()

    # Emitted with progress updates (stage_name, message)
    progress = Signal(str, str)

    # Emitted when test completes successfully (result_dict)
    success = Signal(dict)

    # Emitted when test fails (result_dict)
    failure = Signal(dict)

    # Emitted on unexpected error (error_message)
    error = Signal(str)


class ConnectionTestWorker(QRunnable):
    """
    Worker that runs OpenAI connection test in background.

    Usage:
        worker = ConnectionTestWorker()
        worker.signals.started.connect(on_started)
        worker.signals.success.connect(on_success)
        worker.signals.failure.connect(on_failure)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        skip_network_test: bool = False,
        timeout_seconds: int = 10
    ):
        super().__init__()
        self.project_root = project_root
        self.skip_network_test = skip_network_test
        self.timeout_seconds = timeout_seconds
        self.signals = ConnectionTestSignals()
        self._cancelled = False

    def run(self):
        """Execute the connection test in background thread."""
        logger.info("ConnectionTestWorker starting")

        try:
            # Signal start
            self.signals.started.emit()
            self.signals.progress.emit("inicio", "Iniciando teste de conexao...")

            # Import here to avoid circular imports
            from orchestrator.engine_health import (
                check_openai_connection,
                check_key_resolution,
                check_client_initialization,
                check_network_connection,
                get_env_resolution,
            )

            # Check for cancellation
            if self._cancelled:
                logger.info("Test cancelled before starting")
                return

            # Stage A: Key resolution
            self.signals.progress.emit("key_resolution", "Verificando chave API...")

            key_result = check_key_resolution(self.project_root)

            if not key_result.success:
                logger.warning(f"Key resolution failed: {key_result.message}")
                self.signals.failure.emit(key_result.to_dict())
                return

            if self._cancelled:
                return

            # Stage B: Client initialization
            self.signals.progress.emit("client_init", "Inicializando cliente OpenAI...")

            resolution = get_env_resolution(
                "OPENAI_API_KEY",
                self.project_root / ".env" if self.project_root else None
            )
            api_key = resolution.value

            client_result = check_client_initialization(api_key)

            if not client_result.success:
                # Merge details
                client_result.source = key_result.source
                logger.warning(f"Client init failed: {client_result.message}")
                self.signals.failure.emit(client_result.to_dict())
                return

            if self._cancelled:
                return

            # Stage C: Network test (optional)
            if self.skip_network_test:
                self.signals.progress.emit("completed", "Teste concluido (sem rede)")

                # Build final result
                from orchestrator.engine_health import ConnectionTestResult, ConnectionStage, ConnectionStatus
                import time

                final_result = ConnectionTestResult(
                    success=True,
                    stage=ConnectionStage.COMPLETED,
                    status=ConnectionStatus.SUCCESS,
                    source=key_result.source,
                    key_preview=client_result.key_preview,
                    client_initialized=True,
                    network_test_executed=False,
                    message="Cliente inicializado; teste de rede nao executado.",
                    details=key_result.details + ["---"] + client_result.details,
                )
                self.signals.success.emit(final_result.to_dict())
                return

            self.signals.progress.emit("connection_test", "Testando conexao de rede...")

            network_result = check_network_connection(api_key, self.timeout_seconds)

            # Merge all details
            all_details = key_result.details + ["---"] + client_result.details + ["---"] + network_result.details
            network_result.source = key_result.source
            network_result.details = all_details

            if network_result.success:
                from orchestrator.engine_health import ConnectionStage
                network_result.stage = ConnectionStage.COMPLETED
                self.signals.progress.emit("completed", "Teste concluido com sucesso!")
                logger.info(f"Connection test passed in {network_result.duration_ms}ms")
                self.signals.success.emit(network_result.to_dict())
            else:
                self.signals.progress.emit("failed", f"Falha: {network_result.message}")
                logger.warning(f"Connection test failed: {network_result.message}")
                self.signals.failure.emit(network_result.to_dict())

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ConnectionTestWorker error: {error_msg}")
            logger.debug(traceback.format_exc())

            # Sanitize error message
            import re
            error_msg = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***', error_msg)

            self.signals.error.emit(error_msg)

    def cancel(self):
        """Cancel the test."""
        self._cancelled = True
        logger.info("ConnectionTestWorker cancelled")


class ConnectionTestManager:
    """
    Manager for running connection tests with proper thread handling.

    Usage:
        manager = ConnectionTestManager()
        manager.run_test(
            on_started=lambda: print("Started"),
            on_success=lambda r: print(f"Success: {r}"),
            on_failure=lambda r: print(f"Failure: {r}"),
        )
    """

    def __init__(self):
        self._thread_pool = QThreadPool.globalInstance()
        self._current_worker: Optional[ConnectionTestWorker] = None

    @property
    def is_running(self) -> bool:
        """Check if a test is currently running."""
        return self._current_worker is not None

    def run_test(
        self,
        project_root: Optional[Path] = None,
        skip_network_test: bool = False,
        timeout_seconds: int = 10,
        on_started: Optional[callable] = None,
        on_progress: Optional[callable] = None,
        on_success: Optional[callable] = None,
        on_failure: Optional[callable] = None,
        on_error: Optional[callable] = None,
    ) -> bool:
        """
        Start a connection test in the background.

        Args:
            project_root: Optional project root for .env lookup
            skip_network_test: Skip network connectivity test
            timeout_seconds: Timeout for network test
            on_started: Callback when test starts
            on_progress: Callback with (stage, message) updates
            on_success: Callback with result dict on success
            on_failure: Callback with result dict on failure
            on_error: Callback with error message on unexpected error

        Returns:
            True if test started, False if test already running
        """
        if self.is_running:
            logger.warning("Connection test already running")
            return False

        # Create worker
        worker = ConnectionTestWorker(
            project_root=project_root,
            skip_network_test=skip_network_test,
            timeout_seconds=timeout_seconds,
        )

        # Connect signals
        if on_started:
            worker.signals.started.connect(on_started)

        if on_progress:
            worker.signals.progress.connect(on_progress)

        if on_success:
            worker.signals.success.connect(on_success)

        if on_failure:
            worker.signals.failure.connect(on_failure)

        if on_error:
            worker.signals.error.connect(on_error)

        # Track completion
        def on_finished():
            self._current_worker = None

        worker.signals.success.connect(on_finished)
        worker.signals.failure.connect(on_finished)
        worker.signals.error.connect(on_finished)

        # Start worker
        self._current_worker = worker
        self._thread_pool.start(worker)

        logger.info("Connection test worker started")
        return True

    def cancel(self):
        """Cancel the current test if running."""
        if self._current_worker:
            self._current_worker.cancel()
            self._current_worker = None
            logger.info("Connection test cancelled")
