"""Settings and preferences persistence for GUI."""

import json
from pathlib import Path
from typing import Optional

from .ui_models import UIPreferences, SettingsViewModel


class SettingsStore:
    """Manages GUI settings and preferences persistence."""

    DEFAULT_PREFS_FILE = "gui_preferences.json"
    MAX_RECENT_ITEMS = 10

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.prefs_file = workspace_path / self.DEFAULT_PREFS_FILE
        self._preferences: Optional[UIPreferences] = None

    def _ensure_workspace(self):
        """Ensure workspace directory exists."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def load_preferences(self) -> UIPreferences:
        """Load UI preferences from disk."""
        if self._preferences is not None:
            return self._preferences

        self._ensure_workspace()

        if self.prefs_file.exists():
            try:
                data = json.loads(self.prefs_file.read_text(encoding="utf-8"))
                self._preferences = UIPreferences(
                    window_width=data.get("window_width", 1200),
                    window_height=data.get("window_height", 800),
                    window_x=data.get("window_x", 100),
                    window_y=data.get("window_y", 100),
                    window_maximized=data.get("window_maximized", False),
                    last_tab=data.get("last_tab", "new_task"),
                    last_project_path=data.get("last_project_path", "."),
                    last_profile=data.get("last_profile", "generic"),
                    interface_mode=data.get("interface_mode", "simple"),
                    onboarding_completed=data.get("onboarding_completed", False),
                    sidebar_collapsed=data.get("sidebar_collapsed", False),
                    show_advanced_options=data.get("show_advanced_options", False),
                    first_task_completed=data.get("first_task_completed", False),
                    first_task_run_id=data.get("first_task_run_id"),
                    show_first_run_hints=data.get("show_first_run_hints", True),
                    recent_projects=data.get("recent_projects", []),
                    recent_tasks=data.get("recent_tasks", []),
                )
            except (json.JSONDecodeError, KeyError):
                self._preferences = UIPreferences()
        else:
            self._preferences = UIPreferences()

        return self._preferences

    def save_preferences(self, prefs: UIPreferences):
        """Save UI preferences to disk."""
        self._ensure_workspace()
        self._preferences = prefs

        data = {
            "window_width": prefs.window_width,
            "window_height": prefs.window_height,
            "window_x": prefs.window_x,
            "window_y": prefs.window_y,
            "window_maximized": prefs.window_maximized,
            "last_tab": prefs.last_tab,
            "last_project_path": prefs.last_project_path,
            "last_profile": prefs.last_profile,
            "interface_mode": prefs.interface_mode,
            "onboarding_completed": prefs.onboarding_completed,
            "sidebar_collapsed": prefs.sidebar_collapsed,
            "show_advanced_options": prefs.show_advanced_options,
            "first_task_completed": prefs.first_task_completed,
            "first_task_run_id": prefs.first_task_run_id,
            "show_first_run_hints": prefs.show_first_run_hints,
            "recent_projects": prefs.recent_projects[:self.MAX_RECENT_ITEMS],
            "recent_tasks": prefs.recent_tasks[:self.MAX_RECENT_ITEMS],
        }

        self.prefs_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_recent_project(self, path: str):
        """Add a project to recent list."""
        prefs = self.load_preferences()

        # Remove if already exists
        if path in prefs.recent_projects:
            prefs.recent_projects.remove(path)

        # Add to front
        prefs.recent_projects.insert(0, path)

        # Trim to max
        prefs.recent_projects = prefs.recent_projects[:self.MAX_RECENT_ITEMS]

        self.save_preferences(prefs)

    def add_recent_task(self, task: str):
        """Add a task to recent list."""
        prefs = self.load_preferences()

        # Truncate long tasks
        task_short = task[:200] if len(task) > 200 else task

        # Remove if already exists
        if task_short in prefs.recent_tasks:
            prefs.recent_tasks.remove(task_short)

        # Add to front
        prefs.recent_tasks.insert(0, task_short)

        # Trim to max
        prefs.recent_tasks = prefs.recent_tasks[:self.MAX_RECENT_ITEMS]

        self.save_preferences(prefs)

    def update_window_geometry(self, x: int, y: int, width: int, height: int, maximized: bool):
        """Update window geometry in preferences."""
        prefs = self.load_preferences()
        prefs.window_x = x
        prefs.window_y = y
        prefs.window_width = width
        prefs.window_height = height
        prefs.window_maximized = maximized
        self.save_preferences(prefs)

    def update_last_tab(self, tab: str):
        """Update last active tab."""
        prefs = self.load_preferences()
        prefs.last_tab = tab
        self.save_preferences(prefs)

    def update_last_profile(self, profile: str):
        """Update last used profile."""
        prefs = self.load_preferences()
        prefs.last_profile = profile
        self.save_preferences(prefs)

    def update_interface_mode(self, mode: str):
        """Update the preferred interface mode."""
        prefs = self.load_preferences()
        prefs.interface_mode = mode
        self.save_preferences(prefs)

    def mark_onboarding_completed(self, completed: bool = True):
        """Mark onboarding completion state."""
        prefs = self.load_preferences()
        prefs.onboarding_completed = completed
        self.save_preferences(prefs)

    def mark_first_task_completed(self, run_id: str):
        """Mark that the user has completed their first task."""
        prefs = self.load_preferences()
        prefs.first_task_completed = True
        prefs.first_task_run_id = run_id
        self.save_preferences(prefs)

    def set_show_first_run_hints(self, show: bool):
        """Set whether to show first run hints."""
        prefs = self.load_preferences()
        prefs.show_first_run_hints = show
        self.save_preferences(prefs)

    def is_first_task_pending(self) -> bool:
        """Check if the user has not yet completed their first task."""
        prefs = self.load_preferences()
        return prefs.onboarding_completed and not prefs.first_task_completed


def config_to_settings(config) -> SettingsViewModel:
    """Convert OrchestratorConfig to SettingsViewModel."""
    flutter_profile = config.profiles.get("flutter")
    python_profile = config.profiles.get("python")

    return SettingsViewModel(
        project_path=str(config.project_path),
        workspace_path=str(config.workspace_path),
        active_profile=config.active_profile,
        max_iterations=config.max_iterations,
        planner_model=config.planner.model_name,
        reviewer_model=config.reviewer.model_name,
        planner_timeout=config.planner.timeout_seconds,
        reviewer_timeout=config.reviewer.timeout_seconds,
        executor_command=config.executor.command,
        executor_timeout=config.executor.timeout_seconds,
        flutter_commands=list(getattr(flutter_profile, "validation_commands", [])),
        python_commands=list(getattr(python_profile, "validation_commands", [])),
        allow_auto_commit=config.allow_auto_commit,
        allow_auto_push=config.auto_push_on_complete,
        git_remote=config.git.remote,
        git_branch=config.git.branch,
        protected_branches=config.git.protected_branches,
        require_human_on_destructive=config.require_human_on_destructive,
        checkpoint_triggers=config.checkpoint_triggers,
    )
