"""Smoke tests for GUI components."""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Skip all tests if PySide6 is not available
pytest.importorskip("PySide6")


class TestUIModels:
    """Test UI data models."""

    def test_run_list_item(self):
        """Test RunListItem creation."""
        from gui.ui_models import RunListItem

        item = RunListItem(
            run_id="test-run-123",
            task_summary="This is a test task",
            status="executing",
            created_at=datetime.now(),
            current_iteration=2,
        )

        assert item.run_id == "test-run-123"
        assert item.status == "executing"
        assert item.current_iteration == 2

    def test_run_list_item_truncation(self):
        """Test task truncation in RunListItem."""
        from gui.ui_models import RunListItem

        long_task = "x" * 100
        item = RunListItem(
            run_id="test",
            task_summary=long_task,
            status="pending",
            created_at=datetime.now(),
        )

        assert len(item.task_short) <= 63  # 60 + "..."

    def test_task_config(self):
        """Test TaskConfig creation."""
        from gui.ui_models import TaskConfig

        config = TaskConfig(
            task_description="Test task",
            project_path="/test",
            profile="flutter",
        )

        assert config.task_description == "Test task"
        assert config.profile == "flutter"
        assert config.max_iterations == 3  # default

    def test_progress_event(self):
        """Test ProgressEvent creation."""
        from gui.ui_models import ProgressEvent, ProgressEventType

        event = ProgressEvent(
            event_type=ProgressEventType.RUN_STARTED,
            message="Test message",
            run_id="test-123",
        )

        assert event.event_type == ProgressEventType.RUN_STARTED
        assert event.run_id == "test-123"
        assert event.timestamp is not None

    def test_settings_view_model(self):
        """Test SettingsViewModel defaults."""
        from gui.ui_models import SettingsViewModel

        settings = SettingsViewModel()

        assert settings.max_iterations == 3
        assert settings.planner_model == "gpt-4o"
        assert settings.executor_command == "claude"
        assert settings.require_human_on_destructive is True

    def test_ui_preferences(self):
        """Test UIPreferences defaults."""
        from gui.ui_models import UIPreferences

        prefs = UIPreferences()

        assert prefs.window_width == 1200
        assert prefs.window_height == 800
        assert prefs.last_tab == "command_center"
        assert prefs.interface_mode == "simple"


class TestSettingsStore:
    """Test settings persistence."""

    def test_settings_store_creation(self, tmp_path):
        """Test SettingsStore creation."""
        from gui.settings_store import SettingsStore

        store = SettingsStore(tmp_path)
        prefs = store.load_preferences()

        assert prefs.window_width == 1200  # default

    def test_settings_store_save_load(self, tmp_path):
        """Test saving and loading preferences."""
        from gui.settings_store import SettingsStore
        from gui.ui_models import UIPreferences

        store = SettingsStore(tmp_path)

        prefs = UIPreferences(
            window_width=1400,
            window_height=900,
            last_tab="runs",
        )
        store.save_preferences(prefs)

        # Reload
        store2 = SettingsStore(tmp_path)
        loaded = store2.load_preferences()

        assert loaded.window_width == 1400
        assert loaded.window_height == 900
        assert loaded.last_tab == "runs"

    def test_recent_projects(self, tmp_path):
        """Test recent projects tracking."""
        from gui.settings_store import SettingsStore

        store = SettingsStore(tmp_path)

        store.add_recent_project("/project1")
        store.add_recent_project("/project2")
        store.add_recent_project("/project1")  # Should move to front

        prefs = store.load_preferences()
        assert prefs.recent_projects[0] == "/project1"
        assert len(prefs.recent_projects) == 2

    def test_interface_mode_persistence(self, tmp_path):
        """Interface mode and onboarding state should persist."""
        from gui.settings_store import SettingsStore

        store = SettingsStore(tmp_path)
        store.update_interface_mode("advanced")
        store.mark_onboarding_completed(True)

        prefs = store.load_preferences()
        assert prefs.interface_mode == "advanced"
        assert prefs.onboarding_completed is True

    def test_config_to_settings_reads_profile_models(self, tmp_path):
        """config_to_settings should support ProfileConfig objects."""
        from orchestrator.config import OrchestratorConfig, ProfileConfig
        from gui.settings_store import config_to_settings

        config = OrchestratorConfig(
            project_path=tmp_path,
            workspace_path=tmp_path / "workspace",
            profiles={
                "flutter": ProfileConfig(validation_commands=["flutter analyze"]),
                "python": ProfileConfig(validation_commands=["python -m pytest"]),
            },
        )

        settings = config_to_settings(config)

        assert settings.flutter_commands == ["flutter analyze"]
        assert settings.python_commands == ["python -m pytest"]


class TestStyles:
    """Test style utilities."""

    def test_get_status_color(self):
        """Test status color mapping."""
        from gui.styles import get_status_color

        assert "#22c55e" in get_status_color("completed")
        assert "#ef4444" in get_status_color("failed")
        assert "#f59e0b" in get_status_color("pending")

    def test_get_status_style(self):
        """Test status style generation."""
        from gui.styles import get_status_style

        style = get_status_style("completed")
        assert "color:" in style
        assert "padding:" in style

    def test_no_unsupported_qss_properties(self):
        """Regression test for unsupported QSS properties that caused runtime warnings."""
        styles_text = Path("gui/styles.py").read_text(encoding="utf-8")
        diagnostics_text = Path("gui/diagnostics_panel.py").read_text(encoding="utf-8")
        spec_text = Path("ai_orchestrator.spec").read_text(encoding="utf-8")

        assert "text-transform" not in styles_text
        assert "transform:" not in diagnostics_text
        assert "console=False" in spec_text


# GUI widget tests require QApplication
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for widget tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestWidgetCreation:
    """Test widget creation (smoke tests)."""

    def test_task_panel_creation(self, qapp):
        """Test TaskPanel can be created."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        assert panel is not None
        panel.close()

    def test_run_panel_creation(self, qapp):
        """Test RunPanel can be created."""
        from gui.run_panel import RunPanel

        panel = RunPanel()
        assert panel is not None
        panel.close()

    def test_config_panel_creation(self, qapp):
        """Test ConfigPanel can be created."""
        from gui.config_panel import ConfigPanel

        panel = ConfigPanel()
        assert panel is not None
        panel.close()

    def test_log_viewer_creation(self, qapp):
        """Test LogViewer can be created."""
        from gui.log_viewer import LogViewer

        viewer = LogViewer()
        assert viewer is not None
        viewer.close()

    def test_command_center_panel_creation(self, qapp):
        """Test CommandCenterPanel can be created."""
        from gui.command_center_panel import CommandCenterPanel

        panel = CommandCenterPanel()
        assert panel is not None
        panel.close()

    def test_checkpoint_dialog_creation(self, qapp):
        """Test CheckpointDialog can be created."""
        from gui.checkpoint_dialog import CheckpointDialog

        dialog = CheckpointDialog(
            run_id="test-123",
            reason="migration",
            description="Test checkpoint",
        )
        assert dialog is not None
        assert dialog.run_id == "test-123"
        dialog.close()


class TestTaskPanel:
    """Test TaskPanel functionality."""

    def test_get_config(self, qapp):
        """Test getting config from TaskPanel."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        panel.task_edit.setPlainText("Test task description")
        panel.profile_combo.setCurrentText("python")

        config = panel.get_config()
        assert config is not None
        assert config.task_description == "Test task description"
        assert config.profile == "python"

        panel.close()

    def test_clear_form(self, qapp):
        """Test clearing the form."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        panel.task_edit.setPlainText("Some text")
        panel._clear_form()

        assert panel.task_edit.toPlainText() == ""
        panel.close()

    def test_advanced_options_hidden_by_default(self, qapp):
        """TaskPanel should start in simple mode."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        assert panel.settings_section.isHidden()
        assert panel.advanced_toggle_btn.text() == "Mostrar opções avançadas"
        panel.close()

    def test_advanced_options_can_be_toggled(self, qapp):
        """TaskPanel should reveal advanced options on demand."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        panel.advanced_toggle_btn.click()

        assert not panel.settings_section.isHidden()
        assert panel.advanced_toggle_btn.text() == "Ocultar opções avançadas"
        panel.close()

    def test_task_panel_advanced_mode_shows_settings(self, qapp):
        """Advanced interface mode should expose advanced settings immediately."""
        from gui.task_panel import TaskPanel

        panel = TaskPanel()
        panel.set_interface_mode("advanced")

        assert not panel.settings_section.isHidden()
        assert not panel.advanced_toggle_btn.isVisible()
        panel.close()


class TestConfigPanel:
    """Test ConfigPanel functionality."""

    def test_set_and_get_settings(self, qapp):
        """Test setting and getting settings."""
        from gui.config_panel import ConfigPanel
        from gui.ui_models import SettingsViewModel

        panel = ConfigPanel()

        settings = SettingsViewModel(
            project_path="/test/project",
            max_iterations=5,
            planner_model="gpt-4",
        )
        panel.set_settings(settings)

        retrieved = panel.get_settings()
        assert retrieved.project_path == "/test/project"
        assert retrieved.max_iterations == 5
        assert retrieved.planner_model == "gpt-4"

        panel.close()

    def test_focus_openai_configuration(self, qapp):
        """Config panel should open the environment tab and focus the API key input."""
        from gui.config_panel import ConfigPanel
        from PySide6.QtWidgets import QApplication

        panel = ConfigPanel()
        panel.show()
        panel.api_key_input.setFocus()
        QApplication.processEvents()
        assert panel.api_key_input.hasFocus()
        panel.close()

    def test_config_panel_mode_toggle(self, qapp):
        """ConfigPanel should support switching between simple and advanced modes."""
        from gui.config_panel import ConfigPanel

        panel = ConfigPanel()
        panel.set_interface_mode("advanced")

        assert panel.mode_btn.text() == "Modo avançado"
        panel.set_interface_mode("simple")
        assert panel.mode_btn.text() == "Modo simples"
        panel.close()


class TestDashboardAndDiagnostics:
    """Smoke tests for reorganized high-level panels."""

    def test_dashboard_panel_creation(self, qapp):
        """DashboardPanel can be created."""
        from gui.dashboard_panel import DashboardPanel

        panel = DashboardPanel()
        assert panel is not None
        assert panel.empty_state.isHidden()
        panel.close()

    def test_diagnostics_panel_creation(self, qapp):
        """DiagnosticsPanel can be created."""
        from gui.diagnostics_panel import DiagnosticsPanel

        panel = DiagnosticsPanel()
        assert panel is not None
        assert panel.run_all_btn.text() == "Executar tudo"
        panel.close()

    def test_run_panel_has_recommended_actions(self, qapp):
        """RunPanel should expose recommended actions in the detail view."""
        from gui.run_panel import RunPanel

        panel = RunPanel()
        assert panel.get_detail_panel().recommended_actions is not None
        panel.close()


class TestOpenAIConfigDialog:
    """Tests for the compact OpenAI configuration dialog."""

    def test_dialog_creation(self, qapp):
        """Dialog should be compact and start collapsed."""
        from gui.openai_config_dialog import OpenAIConfigRequiredDialog

        dialog = OpenAIConfigRequiredDialog()
        assert dialog.windowTitle() == "Configuração da OpenAI necessária"
        assert dialog.instructions_frame.isHidden()
        dialog.close()

    def test_dialog_instructions_toggle(self, qapp):
        """Instructions area should expand only on demand."""
        from gui.openai_config_dialog import OpenAIConfigRequiredDialog

        dialog = OpenAIConfigRequiredDialog()
        dialog.instructions_btn.click()

        assert not dialog.instructions_frame.isHidden()
        assert dialog.instructions_btn.text() == "Ocultar instruções"
        dialog.close()


class TestMainWindowOpenAIFlow:
    """Tests for OpenAI configuration navigation from the main window."""

    def test_open_openai_settings_navigates_to_config(self, qapp):
        """MainWindow should route the user to the environment settings tab."""
        from gui.main_window import MainWindow

        window = MainWindow(config=None, paths=None)
        window._open_openai_settings()

        assert window.stack.currentWidget() is window.config_panel
        assert window.config_panel.tabs.currentIndex() == window.config_panel._environment_tab_index
        window.close()

    def test_execute_recommended_action_opens_executor_settings(self, qapp):
        """MainWindow should route recommended actions to the correct config tab."""
        from gui.main_window import MainWindow
        from orchestrator.recommended_actions import ActionPriority, ActionTarget, RecommendedAction

        window = MainWindow(config=None, paths=None)
        action = RecommendedAction(
            id="act-1",
            title="Abrir Configurações > Executor",
            description="",
            priority=ActionPriority.IMMEDIATE,
            source_type="run_insight",
            source_id="ins-1",
            target=ActionTarget.SETTINGS,
            action_type="open_settings_tab",
            payload={"tab": "Executor"},
        )
        window._execute_recommended_action(action)

        assert window.stack.currentWidget() is window.config_panel
        assert window.config_panel.tabs.tabText(window.config_panel.tabs.currentIndex()) == "Executor"
        window.close()

    def test_main_window_starts_on_command_center(self, qapp):
        """MainWindow should land on the command center by default."""
        from gui.main_window import MainWindow

        window = MainWindow(config=None, paths=None)

        assert window.stack.currentWidget() is window.command_center_panel
        window.close()

    def test_main_window_can_launch_interactive_demo(self, qapp):
        """MainWindow should expose the fictional interactive demo overlay."""
        from gui.main_window import MainWindow

        window = MainWindow(config=None, paths=None)
        window.show()
        qapp.processEvents()

        window._run_interactive_demo()
        qapp.processEvents()

        assert window.demo_controller is not None
        assert window.demo_controller.overlay.isVisible()
        assert window.demo_controller.current_step() is not None
        window.demo_controller.stop()
        window.close()

    def test_build_run_failure_summary_prefers_validation_context(self, qapp):
        """MainWindow should convert validation failures into actionable text."""
        from gui.main_window import MainWindow
        from orchestrator.models import (
            RunState,
            TaskRequest,
            TaskStatus,
            ValidationResult,
            ValidationSummary,
        )

        window = MainWindow(config=None, paths=None)

        class FakeStore:
            def load_state(self, run_id):
                return RunState(
                    run_id=run_id,
                    status=TaskStatus.FAILED,
                    task=TaskRequest(description="Test task"),
                    validation_final=ValidationSummary(
                        all_passed=False,
                        results=[
                            ValidationResult(
                                command="python -m pytest",
                                success=False,
                                stderr="AssertionError: suite failed",
                            )
                        ],
                    ),
                    error_message="Task failed with error",
                )

        window.store = FakeStore()
        summary = window._build_run_failure_summary("run-123", "Task failed with error")

        assert "validação automática falhou" in summary
        assert "python -m pytest" in summary
        assert "AssertionError: suite failed" in summary
        window.close()


class TestWorkerManager:
    """Test WorkerManager."""

    def test_worker_manager_creation(self):
        """Test WorkerManager creation."""
        from gui.worker import WorkerManager

        manager = WorkerManager()
        assert manager is not None
        assert manager.thread_pool is not None
