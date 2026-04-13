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
from .worker import WorkerManager, RunWorker, RunWorkerSignals
from .help_panel import HelpPanel
from .diagnostics_panel import DiagnosticsPanel
from .dashboard_panel import DashboardPanel
from .checkpoints_panel import CheckpointsPanel
from .policy_panel import PolicyPanel
from .replay_panel import ReplayPanel


class Sidebar(QFrame):
    """Sidebar navigation widget - Modern compact design."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(184)
        self._buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 12, 8, 12)

        title = QLabel("AI Orchestrator")
        title.setStyleSheet("""
            color: #e6edf3;
            font-size: 14px;
            font-weight: 600;
            padding: 4px 8px 4px 8px;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Fluxo guiado")
        subtitle.setStyleSheet("color: #6b7280; font-size: 11px; padding: 0 8px 12px 8px;")
        layout.addWidget(subtitle)

        # Navigation sections with compact buttons
        # Main section
        self._add_section_label(layout, "PRINCIPAL")
        nav_main = [
            ("new_task", "Nova Tarefa"),
            ("dashboard", "Dashboard"),
            ("checkpoints", "Checkpoints"),
        ]
        for key, label in nav_main:
            self._add_nav_button(layout, key, label)

        layout.addSpacing(12)

        # Tools section
        self._add_section_label(layout, "FERRAMENTAS")
        nav_tools = [
            ("policies", "Políticas"),
            ("replay", "Replay"),
            ("runs", "Execuções"),
        ]
        for key, label in nav_tools:
            self._add_nav_button(layout, key, label)

        layout.addSpacing(12)

        # System section
        self._add_section_label(layout, "SISTEMA")
        nav_system = [
            ("diagnostics", "Diagnóstico"),
            ("logs", "Logs"),
            ("settings", "Config"),
            ("help", "Ajuda"),
        ]
        for key, label in nav_system:
            self._add_nav_button(layout, key, label)

        layout.addStretch()

        # Version - subtle
        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet("color: #4b5563; font-size: 11px; padding: 6px 8px;")
        layout.addWidget(version_label)

    def _add_section_label(self, layout, text: str):
        """Add a section label."""
        label = QLabel(text)
        label.setStyleSheet("""
            color: #6b7280;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.5px;
            padding: 4px 8px 2px 8px;
        """)
        layout.addWidget(label)

    def _add_nav_button(self, layout, key: str, label: str):
        """Add a navigation button."""
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setProperty("nav_key", key)
        self._buttons[key] = btn
        layout.addWidget(btn)

    def get_button(self, key: str) -> Optional[QPushButton]:
        """Get a navigation button by key."""
        return self._buttons.get(key)

    def set_active(self, key: str):
        """Set the active navigation item."""
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)


class StatusWidget(QFrame):
    """Status bar widget showing current run status - Clean minimal design."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(12)

        # Run ID - compact
        self.run_label = QLabel("Pronto")
        self.run_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.run_label)

        # Separator
        sep = QLabel("•")
        sep.setStyleSheet("color: #3d4451;")
        layout.addWidget(sep)
        self._sep1 = sep

        # Status badge
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Phase - subtle
        self.phase_label = QLabel("")
        self.phase_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.phase_label)

        # Iteration - subtle
        self.iter_label = QLabel("")
        self.iter_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.iter_label)

        layout.addStretch()

        # Progress - minimal
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar.setFixedWidth(80)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Last update - very subtle
        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #4b5563; font-size: 11px;")
        layout.addWidget(self.update_label)

    def set_run(self, run_id: str, status: str, phase: str, iteration: int):
        """Update run status."""
        # Truncate run_id for display
        short_id = run_id[:12] if len(run_id) > 12 else run_id
        self.run_label.setText(short_id)
        self.run_label.setStyleSheet("color: #9da7b3; font-size: 12px;")

        # Status with color
        color = get_status_color(status)
        self.status_label.setText(status.lower())
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-weight: 500;
            font-size: 12px;
            background-color: {color}20;
            padding: 1px 6px;
            border-radius: 3px;
        """)
        self.status_label.setVisible(True)
        self._sep1.setVisible(True)

        # Phase and iteration - compact
        self.phase_label.setText(phase)
        if iteration > 0:
            self.iter_label.setText(f"#{iteration}")
        self.update_label.setText(datetime.now().strftime("%H:%M"))

    def set_loading(self, loading: bool):
        """Show/hide loading indicator."""
        self.progress_bar.setVisible(loading)

    def clear(self):
        """Clear status."""
        self.run_label.setText("Pronto")
        self.run_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.status_label.setVisible(False)
        self._sep1.setVisible(False)
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
        self._mock_executor = False  # Set to True for testing without real API calls
        self._project_path: Optional[Path] = None
        self._config_path: Optional[Path] = None

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

        self.diagnostics_panel = DiagnosticsPanel()
        self.stack.addWidget(self.diagnostics_panel)

        self.dashboard_panel = DashboardPanel()
        self.stack.addWidget(self.dashboard_panel)

        self.checkpoints_panel = CheckpointsPanel()
        self.stack.addWidget(self.checkpoints_panel)

        # Policy panel placeholder - initialized in _load_initial_data
        self.policy_panel = None
        self._policy_placeholder = QWidget()
        self.stack.addWidget(self._policy_placeholder)

        # Replay panel placeholder - initialized in _load_initial_data
        self.replay_panel = None
        self._replay_placeholder = QWidget()
        self.stack.addWidget(self._replay_placeholder)

        content_layout.addWidget(self.stack)

        main_layout.addWidget(content_widget)

        # Status bar
        self.status_widget = StatusWidget()
        self.setStatusBar(QStatusBar())
        self.statusBar().addPermanentWidget(self.status_widget, 1)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Sidebar navigation
        for key in ["new_task", "dashboard", "checkpoints", "policies", "replay", "runs", "diagnostics", "logs", "settings", "help"]:
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

        # Diagnostics panel
        self.diagnostics_panel.open_config.connect(lambda: self._navigate("settings"))
        self.diagnostics_panel.open_logs.connect(self._open_logs_folder)

        # Dashboard panel
        self.dashboard_panel.run_selected.connect(self._on_dashboard_run_selected)
        self.dashboard_panel.run_resume.connect(self._on_resume_run)
        self.dashboard_panel.open_folder.connect(self._open_run_folder)
        self.dashboard_panel.open_diagnostics.connect(lambda: self._navigate("diagnostics"))
        self.dashboard_panel.navigate_to_new_task.connect(lambda: self._navigate("new_task"))

        # Checkpoints panel
        self.checkpoints_panel.checkpoint_approved.connect(self._on_checkpoint_approved_from_center)
        self.checkpoints_panel.checkpoint_rejected.connect(self._on_checkpoint_rejected_from_center)
        self.checkpoints_panel.open_run.connect(self._on_checkpoint_open_run)

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

        # Set workspace for log viewer and run panel
        if self.paths:
            self.log_viewer.set_workspace_path(self.paths.workspace_root)
            self.run_panel.set_workspace_path(self.paths.workspace_root)

        # Check for pending checkpoints
        self._check_checkpoints()

        # Set diagnostics panel config
        self.diagnostics_panel.set_config(self.config, self.paths, self._project_path)

        # Set dashboard workspace
        if self.paths:
            self.dashboard_panel.set_workspace(self.paths.workspace_root)

        # Set checkpoints panel config
        if self.paths:
            self.checkpoints_panel.set_workspace(self.paths.workspace_root)
        if self.config:
            self.checkpoints_panel.set_config(self.config)

        # Initialize policy panel
        if self.paths:
            self._init_policy_panel()

        # Initialize replay panel
        if self.paths:
            self._init_replay_panel()

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

            self.engine = IntegratedTaskEngine(self.config, self.paths, mock_executor=self._mock_executor)
            self.store = StateStore(self.paths)

            # Store paths for workers
            self._project_path = self.paths.project_root
            self._config_path = self.paths.workspace_root / "config.yaml"

            self.logger.info("Engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize engine: {e}")
            self.logger.debug(traceback.format_exc())
            QMessageBox.warning(
                self,
                "Aviso",
                f"Erro ao inicializar engine: {e}\n\nVerifique se OPENAI_API_KEY esta configurada."
            )

    def _init_policy_panel(self):
        """Initialize the policy panel."""
        if not self.paths:
            return

        try:
            self.policy_panel = PolicyPanel(self.paths.workspace_root)

            # Replace placeholder
            idx = self.stack.indexOf(self._policy_placeholder)
            if idx >= 0:
                self.stack.removeWidget(self._policy_placeholder)
                self._policy_placeholder.deleteLater()
                self.stack.insertWidget(idx, self.policy_panel)

            self.logger.info("Policy panel initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize policy panel: {e}")

    def _init_replay_panel(self):
        """Initialize the replay panel."""
        if not self.paths:
            return

        try:
            self.replay_panel = ReplayPanel(self.paths.workspace_root)

            # Replace placeholder
            idx = self.stack.indexOf(self._replay_placeholder)
            if idx >= 0:
                self.stack.removeWidget(self._replay_placeholder)
                self._replay_placeholder.deleteLater()
                self.stack.insertWidget(idx, self.replay_panel)

            self.logger.info("Replay panel initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize replay panel: {e}")

    def _navigate(self, key: str):
        """Navigate to a page."""
        page_map = {
            "new_task": 0,
            "runs": 1,
            "logs": 2,
            "settings": 3,
            "help": 4,
            "diagnostics": 5,
            "dashboard": 6,
            "checkpoints": 7,
            "policies": 8,
            "replay": 9,
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

        # Check if a run is already active
        if self.worker_manager.has_active_run:
            QMessageBox.warning(
                self,
                "Aviso",
                "Ja existe uma run em execucao. Aguarde a conclusao ou cancele."
            )
            return

        # Validate task description
        if not config.task_description or not config.task_description.strip():
            QMessageBox.warning(self, "Aviso", "Descricao da tarefa e obrigatoria.")
            return

        try:
            # Update status
            self.status_widget.set_loading(True)
            self.status_widget.set_run("...", "iniciando", "preparando", 0)

            # Disable submit button
            self.task_panel.set_submitting(True)

            # Start worker using the new RunWorker
            worker = self.worker_manager.start_run(
                task_config=config,
                project_path=self._project_path,
                config_path=self._config_path,
                mock_executor=self._mock_executor,
            )

            # Connect signals for detailed progress
            worker.signals.run_started.connect(self._on_run_started)
            worker.signals.progress.connect(self._on_run_progress)
            worker.signals.phase_changed.connect(self._on_phase_changed)
            worker.signals.iteration_changed.connect(self._on_iteration_changed)
            worker.signals.checkpoint_pending.connect(self._on_checkpoint_pending)
            worker.signals.run_completed.connect(self._on_run_completed)
            worker.signals.run_failed.connect(self._on_run_failed)

            self.logger.info("RunWorker started")

            # Save to recent
            if self.settings_store:
                self.settings_store.add_recent_task(config.task_description)

        except Exception as e:
            self.logger.error(f"Error submitting task: {e}")
            self.logger.debug(traceback.format_exc())
            self.status_widget.set_loading(False)
            self.task_panel.set_submitting(False)
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar tarefa:\n\n{e}")

    # --- New RunWorker signal handlers ---

    @Slot(str)
    def _on_run_started(self, run_id: str):
        """Handle run started."""
        self._current_run_id = run_id
        self.status_widget.set_run(run_id, "executando", "iniciado", 1)
        self.logger.info(f"Run started: {run_id}")

    @Slot(dict)
    def _on_run_progress(self, event_dict: dict):
        """Handle run progress update."""
        run_id = event_dict.get("run_id", self._current_run_id or "")
        phase = event_dict.get("phase", "executando")
        message = event_dict.get("message", "")
        iteration = event_dict.get("iteration", 1)
        max_iterations = event_dict.get("max_iterations", 3)
        is_error = event_dict.get("is_error", False)

        # Update status bar
        self.status_widget.set_run(run_id, "executando", phase, iteration)

        # Log progress
        if is_error:
            self.logger.warning(f"Run progress [{phase}]: {message}")
        else:
            self.logger.debug(f"Run progress [{phase}]: {message}")

        # Optionally update run panel with live progress
        # This could be extended to show real-time logs

    @Slot(str, str)
    def _on_phase_changed(self, run_id: str, phase: str):
        """Handle phase change."""
        self.status_widget.set_run(run_id, "executando", phase, self._get_current_iteration())
        self.logger.info(f"Phase changed: {phase}")

    @Slot(str, int, int)
    def _on_iteration_changed(self, run_id: str, current: int, max_iter: int):
        """Handle iteration change."""
        phase = "executando"
        self.status_widget.set_run(run_id, "executando", phase, current)
        self.status_widget.iter_label.setText(f"Iteracao: {current}/{max_iter}")
        self.logger.info(f"Iteration changed: {current}/{max_iter}")

    @Slot(str, str, str)
    def _on_checkpoint_pending(self, run_id: str, reason: str, description: str):
        """Handle checkpoint pending notification."""
        self.logger.info(f"Checkpoint pending: {reason} - {description}")
        self.status_widget.set_run(run_id, "checkpoint", "aguardando", self._get_current_iteration())
        self.status_widget.set_loading(False)

        # Check for checkpoints and show notification
        self._check_checkpoints()

        # Re-enable submit
        self.task_panel.set_submitting(False)

        # Refresh runs list
        self._refresh_runs()

    @Slot(str, dict)
    def _on_run_completed(self, run_id: str, summary: dict):
        """Handle run completed."""
        self.logger.info(f"Run completed: {run_id}")
        self.status_widget.set_loading(False)
        self.status_widget.set_run(run_id, "concluido", "finalizado", 0)

        # Re-enable submit
        self.task_panel.set_submitting(False)

        # Build completion message
        message_parts = ["Tarefa concluida com sucesso!"]
        if summary.get("objective"):
            message_parts.append(f"\nObjetivo: {summary['objective'][:100]}")
        if summary.get("iterations"):
            message_parts.append(f"\nIteracoes: {summary['iterations']}")
        if summary.get("commit_hash"):
            message_parts.append(f"\nCommit: {summary['commit_hash'][:8]}")

        QMessageBox.information(self, "Sucesso", "\n".join(message_parts))

        # Refresh and navigate
        self._refresh_runs()
        self._check_checkpoints()
        self._navigate("runs")

        # Select the completed run
        self._on_run_selected(run_id)

    @Slot(str, str)
    def _on_run_failed(self, run_id: str, error: str):
        """Handle run failed."""
        self.logger.error(f"Run failed: {run_id} - {error}")
        self.status_widget.set_loading(False)
        self.status_widget.set_run(run_id or "erro", "falhou", "erro", 0)

        # Re-enable submit
        self.task_panel.set_submitting(False)

        # Show error
        QMessageBox.critical(self, "Erro", f"Erro na execucao:\n\n{error}")

        # Refresh
        self._refresh_runs()

    def _get_current_iteration(self) -> int:
        """Get current iteration from the active run."""
        if self._current_run_id and self.store:
            try:
                state = self.store.load_state(self._current_run_id)
                if state:
                    return state.current_iteration or 1
            except Exception:
                pass
        return 1

    # --- Legacy worker handlers (kept for backwards compatibility) ---

    @Slot(str)
    def _on_worker_started(self, run_id: str):
        """Handle worker started (legacy)."""
        self._current_run_id = run_id
        self.status_widget.set_run(run_id, "executando", "iniciado", 1)

    @Slot(ProgressEvent)
    def _on_worker_progress(self, event: ProgressEvent):
        """Handle worker progress (legacy)."""
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
        """Handle worker finished (legacy)."""
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
        """Handle worker error (legacy)."""
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
        if self.worker_manager.has_active_run:
            QMessageBox.warning(
                self,
                "Aviso",
                "Ja existe uma run em execucao. Aguarde a conclusao."
            )
            return

        self.status_widget.set_loading(True)
        self._current_run_id = run_id

        # Use new ResumeRunWorker
        worker = self.worker_manager.resume_run(
            run_id=run_id,
            project_path=self._project_path,
            config_path=self._config_path,
            mock_executor=self._mock_executor,
        )

        # Connect signals
        worker.signals.progress.connect(self._on_run_progress)
        worker.signals.phase_changed.connect(self._on_phase_changed)
        worker.signals.iteration_changed.connect(self._on_iteration_changed)
        worker.signals.checkpoint_pending.connect(self._on_checkpoint_pending)
        worker.signals.run_completed.connect(self._on_run_completed)
        worker.signals.run_failed.connect(self._on_run_failed)

        self.logger.info(f"Resume worker started for: {run_id}")

    @Slot(str, str)
    def _on_checkpoint_approve(self, run_id: str, note: str):
        """Handle checkpoint approval."""
        # Show dialog
        state = self.store.load_state(run_id) if self.store else None
        reason = state.checkpoint.reason.value if state and state.checkpoint else "checkpoint"
        desc = state.checkpoint.description if state and state.checkpoint else ""

        dialog = CheckpointDialog(run_id, reason, desc, self)
        if dialog.exec():
            approve = dialog.was_approved()
            note = dialog.get_note()

            # Use new CheckpointActionWorker
            worker = self.worker_manager.handle_checkpoint(
                run_id=run_id,
                approve=approve,
                note=note,
                project_path=self._project_path,
                config_path=self._config_path,
                mock_executor=self._mock_executor,
            )

            worker.signals.status_changed.connect(
                lambda rid, status: self._on_checkpoint_status_changed(rid, status, approve)
            )
            worker.signals.run_failed.connect(self._on_run_failed)

            self.logger.info(f"Checkpoint {'approved' if approve else 'rejected'} for: {run_id}")

    @Slot(str, str)
    def _on_checkpoint_reject(self, run_id: str, reason: str):
        """Handle checkpoint rejection."""
        self._on_checkpoint_approve(run_id, reason)  # Use same dialog

    def _on_checkpoint_status_changed(self, run_id: str, status: str, was_approved: bool):
        """Handle checkpoint status change."""
        action = "aprovado" if was_approved else "rejeitado"
        self.logger.info(f"Checkpoint {action} for {run_id}, new status: {status}")

        self._refresh_runs()
        self._check_checkpoints()

        QMessageBox.information(
            self,
            "Checkpoint",
            f"Checkpoint {action}.\nNovo status: {status}"
        )

    @Slot(str, bool, str)
    def _on_checkpoint_processed(self, run_id: str, success: bool, message: str):
        """Handle checkpoint processed (legacy)."""
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

    def _on_dashboard_run_selected(self, run_id: str):
        """Handle run selection from dashboard."""
        self._navigate("runs")
        self._on_run_selected(run_id)

    def _on_checkpoint_approved_from_center(self, run_id: str):
        """Handle checkpoint approved from checkpoint center."""
        self.logger.info(f"Checkpoint approved from center: {run_id}")
        self._refresh_runs()
        self._check_checkpoints()
        # Auto-resume the run
        self._on_resume_run(run_id)

    def _on_checkpoint_rejected_from_center(self, run_id: str):
        """Handle checkpoint rejected from checkpoint center."""
        self.logger.info(f"Checkpoint rejected from center: {run_id}")
        self._refresh_runs()
        self._check_checkpoints()

    def _on_checkpoint_open_run(self, run_id: str):
        """Handle open run from checkpoint center."""
        self._navigate("runs")
        self._on_run_selected(run_id)

    def _open_logs_folder(self):
        """Open logs folder in file explorer."""
        if not self.paths:
            return

        logs_path = self.paths.workspace_root / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(logs_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(logs_path)])
        else:
            subprocess.run(["xdg-open", str(logs_path)])

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
