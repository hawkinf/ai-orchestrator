"""Main application window."""

import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QStatusBar, QMessageBox,
    QProgressBar, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent

from .styles import MAIN_STYLESHEET, get_status_color
from .ui_models import (
    RunListItem, RunDetailViewModel, TaskConfig, ProgressEvent,
    ProgressEventType, UIPreferences,
)
from .settings_store import SettingsStore, config_to_settings
from .task_panel import TaskPanel
from .run_panel import RunPanel
from .config_panel import ConfigPanel
from .log_viewer import LogViewer
from .checkpoint_dialog import CheckpointDialog, CheckpointNotification
from .worker import WorkerManager, TaskWorker
from .help_panel import HelpPanel


class Sidebar(QFrame):
    """Sidebar navigation widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 16, 8, 16)

        # Logo/title
        title = QLabel("AI Orchestrator")
        title.setStyleSheet("""
            color: #f8fafc;
            font-size: 16px;
            font-weight: 600;
            padding: 8px 12px;
            margin-bottom: 16px;
        """)
        layout.addWidget(title)

        # Navigation buttons
        nav_items = [
            ("new_task", "Nova Tarefa"),
            ("runs", "Execucoes"),
            ("logs", "Logs / Relatorios"),
            ("settings", "Configuracoes"),
            ("help", "Ajuda"),
        ]

        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("nav_key", key)
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Version
        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 8px;")
        layout.addWidget(version_label)

    def get_button(self, key: str) -> Optional[QPushButton]:
        """Get a navigation button by key."""
        return self._buttons.get(key)

    def set_active(self, key: str):
        """Set the active navigation item."""
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)


class StatusWidget(QFrame):
    """Status bar widget showing current run status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(16)

        # Run ID
        self.run_label = QLabel("Nenhuma run ativa")
        self.run_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.run_label)

        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Phase
        self.phase_label = QLabel("")
        self.phase_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.phase_label)

        # Iteration
        self.iter_label = QLabel("")
        self.iter_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.iter_label)

        layout.addStretch()

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Last update
        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.update_label)

    def set_run(self, run_id: str, status: str, phase: str, iteration: int):
        """Update run status."""
        self.run_label.setText(f"Run: {run_id}")
        color = get_status_color(status)
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.phase_label.setText(f"Fase: {phase}")
        self.iter_label.setText(f"Iteracao: {iteration}")
        self.update_label.setText(datetime.now().strftime("%H:%M:%S"))

    def set_loading(self, loading: bool):
        """Show/hide loading indicator."""
        self.progress_bar.setVisible(loading)

    def clear(self):
        """Clear status."""
        self.run_label.setText("Nenhuma run ativa")
        self.status_label.setText("")
        self.phase_label.setText("")
        self.iter_label.setText("")
        self.update_label.setText("")
        self.progress_bar.setVisible(False)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config=None, paths=None):
        super().__init__()

        self.logger = logging.getLogger("ai_orchestrator.gui")
        self.config = config
        self.paths = paths
        self.engine = None
        self.store = None
        self.settings_store = None
        self.worker_manager = WorkerManager()
        self._current_run_id: Optional[str] = None

        self.logger.info("Initializing MainWindow...")

        try:
            self._setup_window()
            self._setup_ui()
            self._connect_signals()
            self._load_initial_data()
            self.logger.info("MainWindow initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing MainWindow: {e}")
            self.logger.debug(traceback.format_exc())
            raise

    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("AI Orchestrator")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Load preferences
        if self.paths:
            self.settings_store = SettingsStore(self.paths.workspace_root)
            prefs = self.settings_store.load_preferences()
            self.resize(prefs.window_width, prefs.window_height)
            self.move(prefs.window_x, prefs.window_y)
            if prefs.window_maximized:
                self.showMaximized()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setStyleSheet(MAIN_STYLESHEET)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area
        content_widget = QWidget()
        content_widget.setObjectName("content_area")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Checkpoint notification area
        self.checkpoint_area = QVBoxLayout()
        self.checkpoint_area.setContentsMargins(16, 8, 16, 0)
        content_layout.addLayout(self.checkpoint_area)

        # Stacked widget for pages
        self.stack = QStackedWidget()

        # Pages
        self.task_panel = TaskPanel()
        self.stack.addWidget(self.task_panel)

        self.run_panel = RunPanel()
        self.stack.addWidget(self.run_panel)

        self.log_viewer = LogViewer()
        self.stack.addWidget(self.log_viewer)

        self.config_panel = ConfigPanel()
        self.stack.addWidget(self.config_panel)

        self.help_panel = HelpPanel()
        self.stack.addWidget(self.help_panel)

        content_layout.addWidget(self.stack)

        main_layout.addWidget(content_widget)

        # Status bar
        self.status_widget = StatusWidget()
        self.setStatusBar(QStatusBar())
        self.statusBar().addPermanentWidget(self.status_widget, 1)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Sidebar navigation
        for key in ["new_task", "runs", "logs", "settings", "help"]:
            btn = self.sidebar.get_button(key)
            if btn:
                btn.clicked.connect(lambda checked, k=key: self._navigate(k))

        # Task panel
        self.task_panel.task_submitted.connect(self._on_task_submitted)

        # Run panel
        self.run_panel.run_refresh.connect(self._refresh_runs)
        self.run_panel.run_resume.connect(self._on_resume_run)
        self.run_panel.checkpoint_approve.connect(self._on_checkpoint_approve)
        self.run_panel.checkpoint_reject.connect(self._on_checkpoint_reject)
        self.run_panel.open_folder.connect(self._open_run_folder)
        self.run_panel.get_list_panel().run_selected.connect(self._on_run_selected)

        # Log viewer
        self.log_viewer.open_folder.connect(self._open_run_folder)

        # Config panel
        self.config_panel.settings_saved.connect(self._on_settings_saved)

        # Set initial page
        self._navigate("new_task")

    def _load_initial_data(self):
        """Load initial data."""
        # Initialize engine
        self._init_engine()

        # Load settings
        if self.config:
            settings = config_to_settings(self.config)
            self.config_panel.set_settings(settings)

        # Load runs
        self._refresh_runs()

        # Set workspace for log viewer
        if self.paths:
            self.log_viewer.set_workspace_path(self.paths.workspace_root)

        # Check for pending checkpoints
        self._check_checkpoints()

    def _init_engine(self):
        """Initialize the orchestration engine."""
        if not self.config or not self.paths:
            self.logger.warning("Cannot initialize engine: config or paths is None")
            return

        try:
            self.logger.info("Initializing orchestration engine...")

            # Import here to avoid circular imports
            from orchestrator.integrated_engine import IntegratedTaskEngine
            from orchestrator.state_store import StateStore

            self.engine = IntegratedTaskEngine(self.config, self.paths, mock_executor=False)
            self.store = StateStore(self.paths)

            self.logger.info("Engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize engine: {e}")
            self.logger.debug(traceback.format_exc())
            QMessageBox.warning(
                self,
                "Aviso",
                f"Erro ao inicializar engine: {e}\n\nVerifique se OPENAI_API_KEY esta configurada."
            )

    def _navigate(self, key: str):
        """Navigate to a page."""
        page_map = {
            "new_task": 0,
            "runs": 1,
            "logs": 2,
            "settings": 3,
            "help": 4,
        }

        if key in page_map:
            self.stack.setCurrentIndex(page_map[key])
            self.sidebar.set_active(key)

            # Save preference
            if self.settings_store:
                prefs = self.settings_store.load_preferences()
                prefs.last_tab = key
                self.settings_store.save_preferences(prefs)

    @Slot(TaskConfig)
    def _on_task_submitted(self, config: TaskConfig):
        """Handle task submission."""
        self.logger.info(f"Task submitted: {config.task_description[:50]}...")

        if not self.engine:
            self.logger.error("Cannot submit task: engine not initialized")
            QMessageBox.warning(
                self,
                "Erro",
                "Engine nao inicializado. Verifique as configuracoes."
            )
            return

        try:
            # Update status
            self.status_widget.set_loading(True)
            self.status_widget.set_run("...", "iniciando", "preparando", 0)

            # Start worker
            worker = self.worker_manager.start_task(self.engine, config)
            if worker:
                worker.signals.started.connect(self._on_worker_started)
                worker.signals.progress.connect(self._on_worker_progress)
                worker.signals.finished.connect(self._on_worker_finished)
                worker.signals.error.connect(self._on_worker_error)
                self.logger.info("Task worker started")
            else:
                self.logger.error("Failed to create task worker")
                self.status_widget.set_loading(False)
                QMessageBox.warning(self, "Erro", "Falha ao iniciar tarefa.")
                return

            # Save to recent
            if self.settings_store:
                self.settings_store.add_recent_task(config.task_description)

        except Exception as e:
            self.logger.error(f"Error submitting task: {e}")
            self.logger.debug(traceback.format_exc())
            self.status_widget.set_loading(False)
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar tarefa:\n\n{e}")

    @Slot(str)
    def _on_worker_started(self, run_id: str):
        """Handle worker started."""
        self._current_run_id = run_id
        self.status_widget.set_run(run_id, "executando", "iniciado", 1)

    @Slot(ProgressEvent)
    def _on_worker_progress(self, event: ProgressEvent):
        """Handle worker progress."""
        # Update status
        if event.run_id:
            phase = event.phase or "executando"
            iteration = event.iteration or 1
            self.status_widget.set_run(event.run_id, "executando", phase, iteration)

        # Check for checkpoint
        if event.event_type == ProgressEventType.CHECKPOINT_PENDING:
            self._check_checkpoints()

    @Slot(str, bool, str)
    def _on_worker_finished(self, run_id: str, success: bool, message: str):
        """Handle worker finished."""
        self.status_widget.set_loading(False)

        if success:
            self.status_widget.set_run(run_id, "concluido", "finalizado", 0)
            QMessageBox.information(self, "Sucesso", message)
        else:
            self.status_widget.set_run(run_id, "falhou", "erro", 0)

        # Refresh runs
        self._refresh_runs()
        self._check_checkpoints()

        # Navigate to runs
        self._navigate("runs")

    @Slot(str, str)
    def _on_worker_error(self, run_id: str, error: str):
        """Handle worker error."""
        self.status_widget.set_loading(False)
        self.status_widget.set_run(run_id or "erro", "falhou", "erro", 0)
        QMessageBox.critical(self, "Erro", f"Erro na execucao:\n\n{error}")
        self._refresh_runs()

    def _refresh_runs(self):
        """Refresh the runs list."""
        if not self.store:
            self.logger.debug("Cannot refresh runs: store is None")
            self.run_panel.set_runs([])  # Show empty list
            return

        try:
            self.logger.debug("Refreshing runs list...")
            runs_data = self.store.list_runs(limit=50)
            runs = []

            for run_info in runs_data:
                try:
                    state = self.store.load_state(run_info["run_id"])
                    if state and state.task:
                        runs.append(RunListItem(
                            run_id=state.run_id,
                            task_summary=state.task.description or "(sem descricao)",
                            status=state.status.value if state.status else "unknown",
                            created_at=state.created_at,
                            current_iteration=state.current_iteration or 0,
                            phase=state.status.value if state.status else "unknown",
                            has_checkpoint=state.checkpoint is not None and not state.checkpoint.resolved,
                            error_message=state.error_message,
                        ))
                except Exception as run_error:
                    self.logger.warning(f"Error loading run {run_info.get('run_id')}: {run_error}")

            self.run_panel.set_runs(runs)
            self.logger.debug(f"Loaded {len(runs)} runs")
        except Exception as e:
            self.logger.error(f"Error refreshing runs: {e}")
            self.logger.debug(traceback.format_exc())
            self.run_panel.set_runs([])  # Show empty list on error

    @Slot(str)
    def _on_run_selected(self, run_id: str):
        """Handle run selection."""
        if not self.store:
            self.logger.warning("Cannot load run detail: store is None")
            return

        if not run_id:
            self.logger.warning("Cannot load run detail: run_id is empty")
            return

        try:
            self.logger.debug(f"Loading run detail: {run_id}")
            state = self.store.load_state(run_id)
            if not state:
                self.logger.warning(f"Run not found: {run_id}")
                return

            if not state.task:
                self.logger.warning(f"Run has no task: {run_id}")
                return

            # Build view model
            detail = RunDetailViewModel(
                run_id=state.run_id,
                task_description=state.task.description,
                status=state.status.value,
                created_at=state.created_at,
                completed_at=state.completed_at,
                current_iteration=state.current_iteration,
                max_iterations=self.config.max_iterations if self.config else 3,
                profile=state.task.profile or "generic",
            )

            # Plan
            if state.plan:
                detail.plan_objective = state.plan.objective
                detail.plan_scope = state.plan.scope
                detail.plan_steps = state.plan.steps or []

            # Iterations
            if state.iterations:
                last_iter = state.iterations[-1]
                if last_iter.execution_report:
                    detail.files_changed = last_iter.execution_report.files_changed
                    detail.execution_summary = last_iter.execution_report.summary
                    detail.risks = last_iter.execution_report.risks or []
                    detail.pending_items = last_iter.execution_report.pending_items or []
                if last_iter.review_response:
                    detail.review_status = last_iter.review_response.status.value
                    detail.review_findings = last_iter.review_response.findings
                    detail.review_approved = last_iter.review_response.status.value == "approved"

            # Validation
            if state.validation_final:
                detail.validation_passed = state.validation_final.all_passed
                detail.validation_results = [
                    {"command": r.command, "success": r.success}
                    for r in state.validation_final.results
                ]

            # Git
            if state.git_result_final:
                detail.commit_hash = state.git_result_final.commit_hash
            if state.git_status_initial:
                detail.git_branch = state.git_status_initial.branch

            # Checkpoint
            if state.checkpoint and not state.checkpoint.resolved:
                detail.checkpoint_pending = True
                detail.checkpoint_reason = state.checkpoint.reason.value
                detail.checkpoint_description = state.checkpoint.description

            # Error
            detail.error_message = state.error_message

            self.run_panel.set_run_detail(detail)
            self.logger.debug(f"Run detail loaded: {run_id}")

        except Exception as e:
            self.logger.error(f"Error loading run detail: {e}")
            self.logger.debug(traceback.format_exc())

    @Slot(str)
    def _on_resume_run(self, run_id: str):
        """Handle resume run request."""
        if not self.engine:
            return

        self.status_widget.set_loading(True)

        worker = self.worker_manager.resume_task(self.engine, run_id)
        worker.signals.progress.connect(self._on_worker_progress)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.error.connect(self._on_worker_error)

    @Slot(str, str)
    def _on_checkpoint_approve(self, run_id: str, note: str):
        """Handle checkpoint approval."""
        if not self.engine:
            return

        # Show dialog
        state = self.store.load_state(run_id) if self.store else None
        reason = state.checkpoint.reason.value if state and state.checkpoint else "checkpoint"
        desc = state.checkpoint.description if state and state.checkpoint else ""

        dialog = CheckpointDialog(run_id, reason, desc, self)
        if dialog.exec():
            if dialog.was_approved():
                worker = self.worker_manager.process_checkpoint(
                    self.engine, run_id, True, dialog.get_note()
                )
            else:
                worker = self.worker_manager.process_checkpoint(
                    self.engine, run_id, False, dialog.get_note()
                )
            worker.signals.finished.connect(self._on_checkpoint_processed)
            worker.signals.error.connect(self._on_worker_error)

    @Slot(str, str)
    def _on_checkpoint_reject(self, run_id: str, reason: str):
        """Handle checkpoint rejection."""
        self._on_checkpoint_approve(run_id, reason)  # Use same dialog

    @Slot(str, bool, str)
    def _on_checkpoint_processed(self, run_id: str, success: bool, message: str):
        """Handle checkpoint processed."""
        self._refresh_runs()
        self._check_checkpoints()
        if success:
            QMessageBox.information(self, "Checkpoint", message)
        else:
            QMessageBox.warning(self, "Checkpoint", message)

    def _check_checkpoints(self):
        """Check for pending checkpoints."""
        # Clear existing notifications
        while self.checkpoint_area.count():
            item = self.checkpoint_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.store:
            return

        try:
            checkpoint_runs = self.store.get_checkpoint_runs()
            for state in checkpoint_runs:
                if state.checkpoint and not state.checkpoint.resolved:
                    notif = CheckpointNotification(
                        state.run_id,
                        state.checkpoint.reason.value,
                    )
                    notif.action_btn.clicked.connect(
                        lambda checked, rid=state.run_id: self._show_checkpoint_dialog(rid)
                    )
                    self.checkpoint_area.addWidget(notif)
        except Exception as e:
            self.logger.error(f"Error checking checkpoints: {e}")
            self.logger.debug(traceback.format_exc())

    def _show_checkpoint_dialog(self, run_id: str):
        """Show checkpoint dialog for a run."""
        self._on_checkpoint_approve(run_id, "")

    @Slot(str)
    def _open_run_folder(self, run_id: str):
        """Open run folder in file explorer."""
        if not self.paths:
            return

        run_path = self.paths.run_dir(run_id)
        if run_path.exists():
            if sys.platform == "win32":
                os.startfile(run_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(run_path)])
            else:
                subprocess.run(["xdg-open", str(run_path)])

    def _on_settings_saved(self):
        """Handle settings saved."""
        QMessageBox.information(
            self,
            "Configuracoes",
            "Configuracoes salvas!\nAlgumas alteracoes podem requerer reinicio."
        )

    def closeEvent(self, event: QCloseEvent):
        """Handle window close."""
        # Save window geometry
        if self.settings_store:
            prefs = self.settings_store.load_preferences()
            if not self.isMaximized():
                prefs.window_width = self.width()
                prefs.window_height = self.height()
                prefs.window_x = self.x()
                prefs.window_y = self.y()
            prefs.window_maximized = self.isMaximized()
            self.settings_store.save_preferences(prefs)

        event.accept()

    def set_engine(self, engine):
        """Set the orchestration engine."""
        self.engine = engine

    def set_store(self, store):
        """Set the state store."""
        self.store = store
        self._refresh_runs()
        self._check_checkpoints()
