"""Main application window."""

import logging
import os
import subprocess
import sys
import traceback
from functools import partial
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import yaml
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QStatusBar, QMessageBox,
    QProgressBar, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QIcon

from orchestrator.config import OrchestratorConfig, load_config
from orchestrator.observability import configure_observability, get_observability
from orchestrator.recommended_actions import ActionTarget, RecommendedAction
from orchestrator.setup_validator import SetupValidationResult, SetupValidator
from orchestrator.updater import ReleaseInfo, UpdateConfig, UpdateResult, UpdateStatus, get_updater
from orchestrator.version import ReleaseChannel, get_recent_changelog_markdown, get_version_info

from .about_dialog import AboutDialog
from .mode_manager import InterfaceModeManager, MODE_SIMPLE
from .onboarding_wizard import OnboardingWizard
from .first_task_wizard import FirstTaskWizard, FirstRunCompletionDialog
from .styles import MAIN_STYLESHEET, get_status_color
from .ui_models import (
    RunListItem, RunDetailViewModel, TaskConfig, ProgressEvent,
    ProgressEventType, UIPreferences,
)
from .settings_store import SettingsStore, config_to_settings
from .task_panel import TaskPanel
from .update_dialog import UpdateDialog, UpdateTaskThread
from .run_panel import RunPanel
from .config_panel import ConfigPanel
from .log_viewer import LogViewer
from .checkpoint_dialog import CheckpointDialog, CheckpointNotification
from .worker import WorkerManager, RunWorker, RunWorkerSignals
from .help_panel import HelpPanel
from .feedback_dialog import FeedbackDialog
from .diagnostics_panel import DiagnosticsPanel
from .dashboard_panel import DashboardPanel
from .openai_config_dialog import OpenAIConfigRequiredDialog
from .checkpoints_panel import CheckpointsPanel
from .policy_panel import PolicyPanel
from .replay_panel import ReplayPanel
from .command_center_panel import CommandCenterPanel


class Sidebar(QFrame):
    """Sidebar navigation widget - Modern compact design."""

    def __init__(self, app_name: str, version_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(184)
        self._buttons = {}
        self._app_name = app_name
        self._version_text = version_text
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 12, 8, 12)

        title = QLabel(self._app_name)
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
            ("command_center", "Command Center"),
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
        self.version_label = QLabel(self._version_text)
        self.version_label.setStyleSheet("color: #4b5563; font-size: 11px; padding: 6px 8px;")
        layout.addWidget(self.version_label)

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
        self.version_info = get_version_info()
        self.app_root = Path(__file__).resolve().parent.parent
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
        self._interface_mode = MODE_SIMPLE
        self._update_thread: Optional[UpdateTaskThread] = None
        self.observability = get_observability()

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
        self.setWindowTitle(f"{self.version_info.app_name} v{self.version_info.version}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        icon_path = self.app_root / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Load preferences
        if self.paths:
            self.settings_store = SettingsStore(self.paths.workspace_root)
            prefs = self.settings_store.load_preferences()
            self.observability = configure_observability(self.paths.workspace_root, prefs.debug_mode)
            self.resize(prefs.window_width, prefs.window_height)
            self.move(prefs.window_x, prefs.window_y)
            if prefs.window_maximized:
                self.showMaximized()
            self._interface_mode = InterfaceModeManager.normalize(prefs.interface_mode)

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
        sidebar_version = f"v{self.version_info.version}"
        self.sidebar = Sidebar(self.version_info.app_name, sidebar_version)
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
        self.command_center_panel = CommandCenterPanel()
        self.stack.addWidget(self.command_center_panel)

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
        self._apply_interface_mode(self._interface_mode)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Sidebar navigation
        for key in ["command_center", "new_task", "dashboard", "checkpoints", "policies", "replay", "runs", "diagnostics", "logs", "settings", "help"]:
            btn = self.sidebar.get_button(key)
            if btn:
                btn.clicked.connect(lambda checked, k=key: self._navigate(k))

        # Command center
        self.command_center_panel.navigate_to_new_task.connect(lambda: self._navigate("new_task"))
        self.command_center_panel.start_first_task.connect(self._run_first_task_wizard)
        self.command_center_panel.open_checkpoints.connect(lambda: self._navigate("checkpoints"))
        self.command_center_panel.open_diagnostics.connect(lambda: self._navigate("diagnostics"))
        self.command_center_panel.open_system_insights.connect(self._open_system_insights_from_command_center)
        self.command_center_panel.open_runs.connect(lambda: self._navigate("runs"))
        self.command_center_panel.open_feedback.connect(self._open_feedback_dialog)
        self.command_center_panel.run_selected.connect(self._on_dashboard_run_selected)
        self.command_center_panel.recommended_action_requested.connect(self._execute_recommended_action)

        # Task panel
        self.task_panel.task_submitted.connect(self._on_task_submitted)

        # Run panel
        self.run_panel.run_refresh.connect(self._refresh_runs)
        self.run_panel.run_resume.connect(self._on_resume_run)
        self.run_panel.checkpoint_approve.connect(self._on_checkpoint_approve)
        self.run_panel.checkpoint_reject.connect(self._on_checkpoint_reject)
        self.run_panel.open_folder.connect(self._open_run_folder)
        self.run_panel.get_list_panel().run_selected.connect(self._on_run_selected)
        self.run_panel.action_requested.connect(self._execute_recommended_action)

        # Log viewer
        self.log_viewer.open_folder.connect(self._open_run_folder)

        # Config panel
        self.config_panel.settings_saved.connect(self._on_settings_saved)
        self.config_panel.mode_changed.connect(self._on_interface_mode_changed)
        self.config_panel.onboarding_requested.connect(self._run_onboarding)
        self.config_panel.complete_setup_requested.connect(self._validate_minimum_setup)

        # Diagnostics panel
        self.diagnostics_panel.open_config.connect(lambda: self._navigate("settings"))
        self.diagnostics_panel.open_logs.connect(self._open_logs_folder)
        self.diagnostics_panel.debug_mode_changed.connect(self._on_debug_mode_changed)
        self.help_panel.about_requested.connect(self._open_about_dialog)
        self.help_panel.updates_requested.connect(self._open_update_dialog)

        # Dashboard panel
        self.dashboard_panel.run_selected.connect(self._on_dashboard_run_selected)
        self.dashboard_panel.run_resume.connect(self._on_resume_run)
        self.dashboard_panel.open_folder.connect(self._open_run_folder)
        self.dashboard_panel.open_diagnostics.connect(lambda: self._navigate("diagnostics"))
        self.dashboard_panel.navigate_to_new_task.connect(lambda: self._navigate("new_task"))
        self.dashboard_panel.recommended_action_requested.connect(self._execute_recommended_action)

        # Checkpoints panel
        self.checkpoints_panel.checkpoint_approved.connect(self._on_checkpoint_approved_from_center)
        self.checkpoints_panel.checkpoint_rejected.connect(self._on_checkpoint_rejected_from_center)
        self.checkpoints_panel.open_run.connect(self._on_checkpoint_open_run)

        # Set initial page
        self._navigate("command_center")

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
            self.command_center_panel.set_workspace(self.paths.workspace_root)

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
            self.command_center_panel.set_runtime_context(
                config=self.config,
                project_path=self._project_path,
                first_task_pending=self.settings_store.is_first_task_pending() if self.settings_store else False,
            )

        # Initialize policy panel
        if self.paths:
            self._init_policy_panel()

        # Initialize replay panel
        if self.paths:
            self._init_replay_panel()

        if self.settings_store:
            prefs = self.settings_store.load_preferences()
            self.task_panel.apply_preferences(prefs.show_advanced_options)
            self.diagnostics_panel.set_debug_mode(prefs.debug_mode)
            last_tab = prefs.last_tab or "command_center"
            if last_tab in InterfaceModeManager.visible_sections(self._interface_mode):
                self._navigate(last_tab)

        QTimer.singleShot(0, self._maybe_run_onboarding)
        QTimer.singleShot(1200, self._maybe_check_for_updates)

    def _build_update_config(self) -> UpdateConfig:
        """Build the effective update configuration using defaults plus user prefs."""
        base = UpdateConfig.load(self.app_root)
        if not self.settings_store:
            return base

        prefs = self.settings_store.load_preferences()
        try:
            channel = ReleaseChannel(prefs.update_channel)
        except ValueError:
            channel = base.channel

        base.auto_check_on_startup = prefs.auto_check_updates
        base.channel = channel
        base.include_prereleases = channel != ReleaseChannel.STABLE
        base.release_url = prefs.release_url or base.release_url
        return base

    def _save_update_preferences(self, auto_check_updates: bool, update_channel: str, release_url: str):
        """Persist update preferences without opening settings."""
        if self.settings_store:
            self.settings_store.update_update_preferences(auto_check_updates, update_channel, release_url)

    def _open_about_dialog(self):
        """Open the product about dialog."""
        prefs = self.settings_store.load_preferences() if self.settings_store else None
        config = self._build_update_config()
        dialog = AboutDialog(
            version_info=self.version_info,
            release_url=config.release_url,
            changelog_markdown=get_recent_changelog_markdown(self.app_root, max_entries=2),
            auto_check_updates=prefs.auto_check_updates if prefs else config.auto_check_on_startup,
            update_channel=prefs.update_channel if prefs else config.channel.value,
            parent=self,
        )
        dialog.preferences_changed.connect(self._save_update_preferences)
        dialog.check_updates_requested.connect(self._open_update_dialog)
        dialog.exec()

    def _open_update_dialog(self, initial_result: Optional[UpdateResult] = None):
        """Open the update dialog and optionally seed it with a known result."""
        prefs = self.settings_store.load_preferences() if self.settings_store else None
        config = self._build_update_config()
        dialog = UpdateDialog(
            current_version=str(self.version_info.version),
            release_url=config.release_url,
            auto_check_updates=prefs.auto_check_updates if prefs else config.auto_check_on_startup,
            parent=self,
        )
        dialog.preferences_changed.connect(
            lambda checked: self._save_update_preferences(checked, config.channel.value, config.release_url)
        )
        dialog.check_requested.connect(partial(self._start_update_check, dialog, False))
        dialog.update_requested.connect(lambda release: self._start_update_install(dialog, release))
        if initial_result is not None:
            dialog.present_result(initial_result)
        else:
            self._start_update_check(dialog, False)
        dialog.exec()

    def _maybe_check_for_updates(self):
        """Run a silent update check on startup when enabled."""
        config = self._build_update_config()
        if not config.auto_check_on_startup:
            return

        updater = get_updater(config=config, root_path=self.app_root)
        if not updater.should_check_for_updates():
            return

        self._start_update_check(None, True)

    def _start_update_check(self, dialog: Optional[UpdateDialog], silent: bool):
        """Check for updates in the background."""
        if self._update_thread and self._update_thread.isRunning():
            return

        if dialog is not None:
            dialog.set_checking()

        updater = get_updater(config=self._build_update_config(), root_path=self.app_root)
        self._update_thread = UpdateTaskThread(updater, mode="check", parent=self)
        self._update_thread.progress_changed.connect(self._on_update_progress)
        self._update_thread.result_ready.connect(lambda result: self._finish_update_check(result, dialog, silent))
        self._update_thread.start()

    def _start_update_install(self, dialog: UpdateDialog, release: ReleaseInfo):
        """Download and prepare an update installation."""
        if self._update_thread and self._update_thread.isRunning():
            return

        dialog.set_progress(0.0, "Preparando download...")
        updater = get_updater(config=self._build_update_config(), root_path=self.app_root)
        self._update_thread = UpdateTaskThread(updater, mode="install", release=release, parent=self)
        self._update_thread.progress_changed.connect(lambda progress, message: dialog.set_progress(progress, message))
        self._update_thread.result_ready.connect(lambda result: self._finish_update_install(result, dialog))
        self._update_thread.start()

    @Slot(float, str)
    def _on_update_progress(self, progress: float, message: str):
        """Mirror startup update progress to logs only."""
        self.logger.debug("Update progress %.2f: %s", progress, message)

    def _finish_update_check(self, result: UpdateResult, dialog: Optional[UpdateDialog], silent: bool):
        """Handle update check completion."""
        self._update_thread = None
        if dialog is not None:
            dialog.present_result(result)
            return

        if silent and result.status == UpdateStatus.UPDATE_AVAILABLE:
            self._open_update_dialog(result)

    def _open_feedback_dialog(self):
        """Open the feedback dialog."""
        if not self.paths:
            QMessageBox.warning(self, "Aviso", "Workspace indisponível para salvar feedback.")
            return

        preferences_path = self.paths.workspace_root / SettingsStore.DEFAULT_PREFS_FILE
        dialog = FeedbackDialog(
            paths=self.paths,
            version_info=self.version_info,
            config_path=self._config_path,
            preferences_path=preferences_path,
            parent=self,
        )
        self.observability.record_user_action("open_feedback_dialog")
        dialog.exec()

    def _finish_update_install(self, result: UpdateResult, dialog: UpdateDialog):
        """Handle update install preparation completion."""
        self._update_thread = None
        should_restart = dialog.present_install_result(result)
        if should_restart:
            get_updater(config=self._build_update_config(), root_path=self.app_root).apply_update_and_restart()

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
            self._config_path = self.paths.project_root / "config.yaml"

            self.logger.info("Engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize engine: {e}")
            self.logger.debug(traceback.format_exc())
            if self._is_openai_configuration_error(e):
                self._show_openai_configuration_dialog()
            else:
                QMessageBox.warning(
                    self,
                    "Inicialização incompleta",
                    "Não foi possível iniciar todos os recursos da aplicação.\n\n"
                    "Verifique os logs para mais detalhes técnicos."
                )

    def _is_openai_configuration_error(self, error: Exception) -> bool:
        """Check whether an exception is caused by missing OpenAI configuration."""
        error_text = str(error)
        markers = [
            "OPENAI_API_KEY",
            "OpenAI API key not configured",
            "OpenAI API key",
        ]
        return any(marker in error_text for marker in markers)

    def _show_openai_configuration_dialog(self):
        """Show a compact dialog guiding the user to configure OpenAI."""
        dialog = OpenAIConfigRequiredDialog(self)
        if dialog.exec():
            self._open_openai_settings()

    def _open_openai_settings(self):
        """Navigate to the correct settings area for OpenAI configuration."""
        self._navigate("settings")
        self.config_panel.focus_openai_configuration()

    def _init_policy_panel(self):
        """Initialize the policy panel."""
        if not self.paths:
            return

        try:
            current = self.policy_panel or self._policy_placeholder
            idx = self.stack.indexOf(current)
            self.policy_panel = PolicyPanel(self.paths.workspace_root)

            if idx >= 0:
                self.stack.removeWidget(current)
                current.deleteLater()
                self.stack.insertWidget(idx, self.policy_panel)

            self.logger.info("Policy panel initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize policy panel: {e}")

    def _init_replay_panel(self):
        """Initialize the replay panel."""
        if not self.paths:
            return

        try:
            current = self.replay_panel or self._replay_placeholder
            idx = self.stack.indexOf(current)
            self.replay_panel = ReplayPanel(self.paths.workspace_root)

            if idx >= 0:
                self.stack.removeWidget(current)
                current.deleteLater()
                self.stack.insertWidget(idx, self.replay_panel)

            self.logger.info("Replay panel initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize replay panel: {e}")

    def _navigate(self, key: str):
        """Navigate to a page."""
        if key not in InterfaceModeManager.visible_sections(self._interface_mode):
            key = "settings"

        page_map = {
            "command_center": 0,
            "new_task": 1,
            "runs": 2,
            "logs": 3,
            "settings": 4,
            "help": 5,
            "diagnostics": 6,
            "dashboard": 7,
            "checkpoints": 8,
            "policies": 9,
            "replay": 10,
        }

        if key in page_map:
            self.stack.setCurrentIndex(page_map[key])
            self.sidebar.set_active(key)

            # Save preference
            if self.settings_store:
                prefs = self.settings_store.load_preferences()
                prefs.last_tab = key
                self.settings_store.save_preferences(prefs)

            self.observability.record_user_action("navigate", {"target": key})

    @Slot(TaskConfig)
    def _on_task_submitted(self, config: TaskConfig):
        """Handle task submission."""
        self.logger.info(f"Task submitted: {config.task_description[:50]}...")
        self.observability.record_user_action(
            "submit_task",
            {
                "profile": config.profile,
                "auto_validate": config.auto_validate,
                "auto_commit": config.auto_commit,
                "auto_push": config.auto_push,
            },
        )

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
        self.observability.record_run_event(run_id, "run_started", "Run started from UI", iteration=1, phase="initializing")

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

        self.observability.record_run_event(
            run_id,
            "run_progress",
            message,
            iteration=iteration,
            phase=phase,
            context={"max_iterations": max_iterations, "is_error": is_error},
            level="warning" if is_error else "debug",
            debug_only=not is_error,
        )

        # Optionally update run panel with live progress
        # This could be extended to show real-time logs

    @Slot(str, str)
    def _on_phase_changed(self, run_id: str, phase: str):
        """Handle phase change."""
        self.status_widget.set_run(run_id, "executando", phase, self._get_current_iteration())
        self.logger.info(f"Phase changed: {phase}")
        self.observability.record_run_event(run_id, "phase_changed", f"Phase changed to {phase}", phase=phase)

    @Slot(str, int, int)
    def _on_iteration_changed(self, run_id: str, current: int, max_iter: int):
        """Handle iteration change."""
        phase = "executando"
        self.status_widget.set_run(run_id, "executando", phase, current)
        self.status_widget.iter_label.setText(f"Iteracao: {current}/{max_iter}")
        self.logger.info(f"Iteration changed: {current}/{max_iter}")
        self.observability.record_run_event(
            run_id,
            "iteration_changed",
            f"Iteration {current} of {max_iter}",
            iteration=current,
            phase=phase,
        )

    @Slot(str, str, str)
    def _on_checkpoint_pending(self, run_id: str, reason: str, description: str):
        """Handle checkpoint pending notification."""
        self.logger.info(f"Checkpoint pending: {reason} - {description}")
        self.observability.record_run_event(
            run_id,
            "checkpoint_pending",
            description or reason,
            iteration=self._get_current_iteration(),
            phase="checkpoint",
            context={"reason": reason},
            level="warning",
        )
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
        self.observability.record_run_event(
            run_id,
            "run_completed",
            "Run completed successfully",
            iteration=summary.get("iterations"),
            phase="completed",
            context=summary,
        )
        self.status_widget.set_loading(False)
        self.status_widget.set_run(run_id, "concluido", "finalizado", 0)

        # Re-enable submit
        self.task_panel.set_submitting(False)

        # Refresh and navigate
        self._refresh_runs()
        self._check_checkpoints()

        # Check if this is the first task
        is_first_task = False
        if self.settings_store:
            prefs = self.settings_store.load_preferences()
            is_first_task = not prefs.first_task_completed

        if is_first_task:
            # Show first run completion dialog
            summary_text = summary.get("objective", "Tarefa concluída com sucesso!")
            self._show_first_run_completion(run_id, True, summary_text)
        else:
            # Build completion message
            message_parts = ["Tarefa concluida com sucesso!"]
            if summary.get("objective"):
                message_parts.append(f"\nObjetivo: {summary['objective'][:100]}")
            if summary.get("iterations"):
                message_parts.append(f"\nIteracoes: {summary['iterations']}")
            if summary.get("commit_hash"):
                message_parts.append(f"\nCommit: {summary['commit_hash'][:8]}")

            QMessageBox.information(self, "Sucesso", "\n".join(message_parts))
            self._navigate("runs")

        # Select the completed run
        self._on_run_selected(run_id)

    @Slot(str, str)
    def _on_run_failed(self, run_id: str, error: str):
        """Handle run failed."""
        self.logger.error(f"Run failed: {run_id} - {error}")
        self.observability.record_error(
            error_type="RunExecutionFailed",
            message=error,
            context={"source": "main_window"},
            run_id=run_id,
            phase="run_failed",
        )
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
            self.command_center_panel.refresh()
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
            self.command_center_panel.refresh()
            self.logger.debug(f"Loaded {len(runs)} runs")
        except Exception as e:
            self.logger.error(f"Error refreshing runs: {e}")
            self.logger.debug(traceback.format_exc())
            self.run_panel.set_runs([])  # Show empty list on error
            self.command_center_panel.refresh()

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
        self.observability.record_user_action("resume_run", {"run_id": run_id})

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
            self.observability.record_user_action(
                "checkpoint_decision",
                {"run_id": run_id, "approved": approve, "note_present": bool(note)},
            )

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

    @Slot(object)
    def _on_settings_saved(self, settings):
        """Handle settings saved."""
        self._apply_and_persist_settings(settings)
        self.observability.record_user_action(
            "save_settings",
            {"project_path": settings.project_path, "profile": settings.active_profile},
        )
        result = self._validate_minimum_setup()
        message = "Configurações salvas."
        if result and result.is_ready:
            message += "\nA configuração mínima recomendada está pronta."
        else:
            message += "\nAinda faltam alguns itens no checklist mínimo."
        QMessageBox.information(self, "Configurações", message)

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

    def _open_system_insights_from_command_center(self):
        """Open full system insights from the command center."""
        self._navigate("dashboard")
        self.dashboard_panel._open_system_insights_panel()

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
        self.observability.record_user_action("open_logs_folder", {"path": str(logs_path)})

    def _execute_recommended_action(self, action: RecommendedAction):
        """Execute a recommended action emitted by the GUI."""
        if not action:
            return

        action_type = action.action_type
        payload = action.payload or {}

        if action_type == "navigate":
            self._navigate(action.target.value)
            return

        if action_type == "navigate_new_task":
            self._navigate("new_task")
            return

        if action_type == "open_settings_tab":
            self._navigate("settings")
            tab_name = payload.get("tab", "")
            if tab_name.lower() == "ambiente":
                self.config_panel.focus_openai_configuration()
            elif tab_name.lower() == "executor":
                self.config_panel.focus_executor_configuration()
            elif tab_name.lower() == "git":
                self.config_panel.focus_git_configuration()
            else:
                self.config_panel.open_tab(tab_name)
            return

        if action_type == "filter_dashboard":
            self._navigate("dashboard")
            self.dashboard_panel.apply_quick_filter(
                status=payload.get("status"),
                profile=payload.get("profile"),
                has_checkpoint=payload.get("has_checkpoint"),
                has_error=payload.get("has_error"),
                search_text=payload.get("search_text", ""),
            )
            return

        if action_type == "open_run_tab":
            run_id = payload.get("run_id") or action.context.run_id
            if run_id:
                self._navigate("runs")
                self._on_run_selected(run_id)
                self.run_panel.open_tab(payload.get("tab", "Visao Geral"))
            return

        if action_type == "navigate_replay":
            self._navigate("replay")
            run_id = payload.get("run_id") or action.context.run_id
            if self.replay_panel and run_id:
                self.replay_panel.select_run(run_id)
            return

        if action_type == "open_system_insights":
            self._navigate("dashboard")
            self.dashboard_panel._open_system_insights_panel()
            return

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
            prefs.show_advanced_options = self.task_panel.settings_section.isVisible()
            prefs.interface_mode = self._interface_mode
            self.settings_store.save_preferences(prefs)

        self.observability.record_app_event(
            event="window_closed",
            message="Main window closed",
            context={"current_run_id": self._current_run_id, "interface_mode": self._interface_mode},
        )

        event.accept()

    @Slot(bool)
    def _on_debug_mode_changed(self, enabled: bool):
        """Handle debug mode changes from diagnostics UI."""
        if self.settings_store:
            self.settings_store.update_debug_mode(enabled)
        self.observability = configure_observability(self.paths.workspace_root, enabled) if self.paths else get_observability()
        self.observability.record_app_event(
            event="debug_mode_changed_from_ui",
            message="Debug mode updated from diagnostics panel",
            context={"enabled": enabled},
        )

    def set_engine(self, engine):
        """Set the orchestration engine."""
        self.engine = engine

    def set_store(self, store):
        """Set the state store."""
        self.store = store
        self._refresh_runs()
        self._check_checkpoints()

    def _apply_interface_mode(self, mode: str):
        """Apply interface mode across the shell and pages."""
        self._interface_mode = InterfaceModeManager.normalize(mode)
        self.command_center_panel.set_interface_mode(self._interface_mode)
        self.task_panel.set_interface_mode(self._interface_mode)
        self.config_panel.set_interface_mode(self._interface_mode)
        visible_sections = InterfaceModeManager.visible_sections(self._interface_mode)

        for key in ["command_center", "new_task", "dashboard", "checkpoints", "policies", "replay", "runs", "diagnostics", "logs", "settings", "help"]:
            btn = self.sidebar.get_button(key)
            if btn:
                btn.setVisible(key in visible_sections)

    @Slot(str)
    def _on_interface_mode_changed(self, mode: str):
        """Persist and apply interface mode changes."""
        self._apply_interface_mode(mode)
        if self.settings_store:
            self.settings_store.update_interface_mode(self._interface_mode)

    def _validate_minimum_setup(self) -> Optional[SetupValidationResult]:
        """Validate the minimum recommended setup."""
        settings = self.config_panel.get_settings()
        validator = SetupValidator(Path(settings.project_path or Path.cwd()))
        result = validator.validate_minimum_configuration(
            project_path=Path(settings.project_path or "."),
            workspace_path=Path(settings.workspace_path or "./workspace"),
            profile=settings.active_profile,
            executor_command=settings.executor_command,
        )
        self.config_panel.set_setup_validation(result)
        return result

    def _maybe_run_onboarding(self):
        """Trigger onboarding when setup is missing or incomplete."""
        if not self.settings_store:
            return

        prefs = self.settings_store.load_preferences()
        result = self._validate_minimum_setup()
        if not prefs.onboarding_completed or (result and not result.is_ready):
            self._run_onboarding()

    def _run_onboarding(self):
        """Launch the first-run onboarding wizard."""
        wizard = OnboardingWizard(self._project_path or Path.cwd(), self)
        if self.config:
            settings = config_to_settings(self.config)
            wizard.project_page.project_edit.setText(settings.project_path)
            wizard.project_page.profile_combo.setCurrentText(settings.active_profile)
            wizard.executor_page.command_edit.setText(settings.executor_command)
            wizard.workspace_page.workspace_edit.setText(settings.workspace_path)

        if wizard.exec():
            wizard.save_openai_key_if_needed()
            self._apply_and_persist_settings(wizard.build_settings())
            if self.settings_store:
                self.settings_store.mark_onboarding_completed(True)
                self.command_center_panel.set_runtime_context(
                    config=self.config,
                    project_path=self._project_path,
                    first_task_pending=self.settings_store.is_first_task_pending(),
                )
            self._validate_minimum_setup()

            destination = wizard.selected_destination()
            if destination == "first_task":
                self._run_first_task_wizard()
            else:
                self._navigate(destination)

    def _settings_to_config_payload(self, settings) -> dict:
        """Build a config payload suitable for config.yaml."""
        base = (
            self.config.model_dump(mode="json")
            if isinstance(self.config, OrchestratorConfig)
            else OrchestratorConfig().model_dump(mode="json")
        )
        base["project_path"] = settings.project_path
        base["workspace_path"] = settings.workspace_path
        base["active_profile"] = settings.active_profile
        base["max_iterations"] = settings.max_iterations
        base["allow_auto_commit"] = settings.allow_auto_commit
        base["auto_push_on_complete"] = settings.allow_auto_push
        base["require_human_on_destructive"] = settings.require_human_on_destructive
        base["checkpoint_triggers"] = settings.checkpoint_triggers
        base["planner"]["model_name"] = settings.planner_model
        base["planner"]["timeout_seconds"] = settings.planner_timeout
        base["reviewer"]["model_name"] = settings.reviewer_model
        base["reviewer"]["timeout_seconds"] = settings.reviewer_timeout
        base["executor"]["command"] = settings.executor_command
        base["executor"]["timeout_seconds"] = settings.executor_timeout
        base["git"]["remote"] = settings.git_remote
        base["git"]["branch"] = settings.git_branch
        base["git"]["protected_branches"] = settings.protected_branches
        base["profiles"]["flutter"]["validation_commands"] = settings.flutter_commands
        base["profiles"]["python"]["validation_commands"] = settings.python_commands
        return base

    def _apply_and_persist_settings(self, settings):
        """Write config.yaml and refresh runtime state."""
        project_path = Path(settings.project_path or ".").resolve()
        project_path.mkdir(parents=True, exist_ok=True)
        config_payload = self._settings_to_config_payload(settings)
        config_path = project_path / "config.yaml"
        config_path.write_text(
            yaml.safe_dump(config_payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        self.config = load_config(config_path)
        from orchestrator.paths import OrchestratorPaths

        self.paths = OrchestratorPaths(self.config.workspace_path, self.config.project_path)
        self._project_path = self.paths.project_root
        self._config_path = config_path
        self.settings_store = SettingsStore(self.paths.workspace_root)
        prefs = self.settings_store.load_preferences()
        self.observability = configure_observability(self.paths.workspace_root, prefs.debug_mode)

        self.config_panel.set_settings(config_to_settings(self.config))
        self.config_panel.set_interface_mode(self._interface_mode)
        self.task_panel.path_edit.setText(settings.project_path or ".")
        self.task_panel.profile_combo.setCurrentText(settings.active_profile)
        self.log_viewer.set_workspace_path(self.paths.workspace_root)
        self.run_panel.set_workspace_path(self.paths.workspace_root)
        self.dashboard_panel.set_workspace(self.paths.workspace_root)
        self.command_center_panel.set_workspace(self.paths.workspace_root)
        self.checkpoints_panel.set_workspace(self.paths.workspace_root)
        self.checkpoints_panel.set_config(self.config)
        self.diagnostics_panel.set_config(self.config, self.paths, self._project_path)
        self.diagnostics_panel.set_debug_mode(prefs.debug_mode)
        self.command_center_panel.set_runtime_context(
            config=self.config,
            project_path=self._project_path,
            first_task_pending=self.settings_store.is_first_task_pending() if self.settings_store else False,
        )
        self._init_engine()
        self._init_policy_panel()
        self._init_replay_panel()
        self._refresh_runs()
        self._check_checkpoints()

        prefs.last_project_path = settings.project_path
        prefs.last_profile = settings.active_profile
        prefs.interface_mode = self._interface_mode
        prefs.show_advanced_options = self.task_panel.settings_section.isVisible()
        self.settings_store.save_preferences(prefs)
        self.observability.record_app_event(
            event="settings_applied",
            message="Configuration persisted and runtime refreshed",
            context={
                "project_path": settings.project_path,
                "profile": settings.active_profile,
                "workspace_root": str(self.paths.workspace_root),
                "debug_mode": prefs.debug_mode,
            },
        )

    def _run_first_task_wizard(self):
        """Launch the first task wizard for guided first run."""
        wizard = FirstTaskWizard(self._project_path or Path.cwd(), self)
        wizard.task_submitted.connect(self._on_first_task_submitted)

        if wizard.exec():
            # Task was submitted through the wizard
            pass
        else:
            # User skipped, go to new task panel
            self._navigate("new_task")

    @Slot(str, str)
    def _on_first_task_submitted(self, task_text: str, profile: str):
        """Handle task submission from first task wizard."""
        # Pre-fill the task panel
        self.task_panel.set_task_text(task_text)
        self.task_panel.profile_combo.setCurrentText(profile)

        # Navigate to task panel and submit
        self._navigate("new_task")

        # Create the task config and submit
        config = TaskConfig(
            task_description=task_text,
            project_path=str(self._project_path or "."),
            profile=profile,
            max_iterations=3,
            auto_validate=True,
            auto_commit=False,
            auto_push=False,
            require_approval_destructive=True,
        )

        self._on_task_submitted(config)

    def _show_first_run_completion(self, run_id: str, success: bool, summary: str):
        """Show completion dialog after first run."""
        if not self.settings_store:
            return

        prefs = self.settings_store.load_preferences()
        if prefs.first_task_completed:
            return  # Already completed before

        # Mark first task as completed
        self.settings_store.mark_first_task_completed(run_id)
        self.command_center_panel.set_runtime_context(
            config=self.config,
            project_path=self._project_path,
            first_task_pending=False,
        )

        # Show completion dialog
        dialog = FirstRunCompletionDialog(run_id, success, summary, self)
        dialog.open_dashboard.connect(lambda: self._navigate("dashboard"))
        dialog.create_new_task.connect(lambda: self._navigate("new_task"))
        dialog.open_artifacts.connect(self._open_run_folder)
        dialog.open_manual.connect(lambda: self._navigate("help"))
        dialog.exec()
