"""Controller for the interactive in-app demo."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from orchestrator.demo_run_builder import build_demo_scenarios

from .demo_overlay import DemoOverlay
from .demo_scenarios import DemoStep, build_demo_steps


class DemoController(QObject):
    """Drive the interactive demo on top of the real UI shell."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.scenarios = build_demo_scenarios()
        self.steps = build_demo_steps()
        self.current_index = -1
        self.overlay = DemoOverlay(main_window)
        self.overlay.next_requested.connect(self.next_step)
        self.overlay.back_requested.connect(self.previous_step)
        self.overlay.skip_requested.connect(self.stop)
        self.overlay.close_requested.connect(self.stop)

    def start(self):
        """Start or restart the demo."""
        self.current_index = 0
        self._apply_current_step()

    def stop(self):
        """Close the demo overlay."""
        self.current_index = -1
        self.overlay.clear()

    def next_step(self):
        """Advance to the next step or close the demo."""
        if self.current_index < 0:
            self.start()
            return
        if self.current_index >= len(self.steps) - 1:
            self.stop()
            return
        self.current_index += 1
        self._apply_current_step()

    def previous_step(self):
        """Go back one step."""
        if self.current_index <= 0:
            return
        self.current_index -= 1
        self._apply_current_step()

    def current_step(self) -> Optional[DemoStep]:
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def _apply_current_step(self):
        step = self.current_step()
        if step is None:
            self.stop()
            return

        self._run_setup(step.setup_key)
        target = self._resolve_target(step.target_key)
        self.overlay.set_step(index=self.current_index + 1, total=len(self.steps), step=step, target_widget=target)

    def _run_setup(self, setup_key: Optional[str]):
        if setup_key == "show_command_center":
            self.main_window._navigate("command_center")
        elif setup_key == "show_dashboard":
            self.main_window._navigate("dashboard")
        elif setup_key == "show_checkpoints":
            self.main_window._navigate("checkpoints")
        elif setup_key == "show_diagnostics":
            self.main_window._navigate("diagnostics")
        elif setup_key == "show_help":
            self.main_window._navigate("help")
            self.main_window.help_panel.set_current_section("interactive_demo")
        elif setup_key == "show_config_example":
            self.main_window._navigate("settings")
            self.main_window.config_panel.open_tab("Geral")
            self.main_window.config_panel.project_path_edit.setText("C:/demo/projects/flutter-shop")
            self.main_window.config_panel.workspace_path_edit.setText("C:/demo/workspace")
            self.main_window.config_panel.profile_combo.setCurrentText("flutter")
            self.main_window.config_panel.open_tab("Ambiente")
            self.main_window.config_panel.api_key_input.setText("sk-demo-only")
            self.main_window.config_panel.open_tab("Executor")
            self.main_window.config_panel.executor_cmd_edit.setText("claude-demo")
            self.main_window.config_panel.open_tab("Geral")
        elif setup_key == "show_task_example_simple":
            self.main_window._navigate("new_task")
            self.main_window.task_panel.set_interface_mode("simple")
            self.main_window.task_panel.apply_preferences(False)
            self.main_window.task_panel.set_task_text(self.scenarios["success"].task_text)
        elif setup_key == "show_task_example_advanced":
            self.main_window._navigate("new_task")
            self.main_window.task_panel.set_interface_mode("advanced")
            self.main_window.task_panel.apply_preferences(True)
            self.main_window.task_panel.profile_combo.setCurrentText("flutter")
            self.main_window.task_panel.max_iter_spin.setValue(3)
            self.main_window.task_panel.auto_validate_cb.setChecked(True)
            self.main_window.task_panel.require_approval_cb.setChecked(True)
            self.main_window.task_panel.auto_commit_cb.setChecked(False)
            self.main_window.task_panel.auto_push_cb.setChecked(False)
        elif setup_key == "show_success_run":
            self.main_window._navigate("runs")
            self.main_window.run_panel.open_tab("Timeline")
        elif setup_key == "show_success_results":
            self.main_window._navigate("runs")
            self.main_window.run_panel.open_tab("Insights")
        elif setup_key == "show_failure_run":
            self.main_window._navigate("runs")
            self.main_window.run_panel.open_tab("Insights")

    def _resolve_target(self, target_key: Optional[str]) -> Optional[QWidget]:
        if not target_key:
            return None

        lookup = {
            "sidebar.dashboard": self.main_window.sidebar.get_button("dashboard"),
            "sidebar.checkpoints": self.main_window.sidebar.get_button("checkpoints"),
            "sidebar.diagnostics": self.main_window.sidebar.get_button("diagnostics"),
            "command_center.overview": self.main_window.command_center_panel.overview_frame,
            "command_center.primary_action": self.main_window.command_center_panel.primary_action_card,
            "task.task_edit": self.main_window.task_panel.task_edit,
            "task.settings": self.main_window.task_panel.settings_section,
            "config.setup_card": self.main_window.config_panel.setup_card,
            "help.section_list": self.main_window.help_panel.section_list,
            "run.timeline": self.main_window.run_panel.detail_panel.timeline_widget,
            "run.insights": self.main_window.run_panel.detail_panel.insights_widget,
            "run.recommended_actions": self.main_window.run_panel.detail_panel.recommended_actions,
        }
        return lookup.get(target_key)
