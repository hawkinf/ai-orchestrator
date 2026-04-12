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
        assert prefs.last_tab == "new_task"


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


class TestWorkerManager:
    """Test WorkerManager."""

    def test_worker_manager_creation(self):
        """Test WorkerManager creation."""
        from gui.worker import WorkerManager

        manager = WorkerManager()
        assert manager is not None
        assert manager.thread_pool is not None
