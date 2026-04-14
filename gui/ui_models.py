"""UI data models and view models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any


class ProgressEventType(Enum):
    """Types of progress events."""
    RUN_STARTED = "run_started"
    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"
    EXECUTOR_STARTED = "executor_started"
    EXECUTOR_COMPLETED = "executor_completed"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    CHECKPOINT_PENDING = "checkpoint_pending"
    GIT_STARTED = "git_started"
    GIT_COMPLETED = "git_completed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    STATUS_UPDATE = "status_update"
    LOG_MESSAGE = "log_message"
    ERROR = "error"


@dataclass
class ProgressEvent:
    """Progress event for UI updates."""
    event_type: ProgressEventType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[dict] = None
    run_id: Optional[str] = None
    iteration: Optional[int] = None
    phase: Optional[str] = None


@dataclass
class RunListItem:
    """Simplified run item for list display."""
    run_id: str
    task_summary: str
    status: str
    created_at: datetime
    current_iteration: int = 1
    phase: str = "pending"
    has_checkpoint: bool = False
    error_message: Optional[str] = None

    @property
    def task_short(self) -> str:
        """Get truncated task description."""
        max_len = 60
        if len(self.task_summary) > max_len:
            return self.task_summary[:max_len] + "..."
        return self.task_summary


@dataclass
class RunDetailViewModel:
    """Detailed run view model."""
    run_id: str
    task_description: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    current_iteration: int = 1
    max_iterations: int = 3
    profile: str = "generic"

    # Plan
    plan_objective: Optional[str] = None
    plan_scope: Optional[str] = None
    plan_steps: List[str] = field(default_factory=list)

    # Execution
    files_changed: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    execution_summary: Optional[str] = None

    # Review
    review_status: Optional[str] = None
    review_findings: Optional[str] = None
    review_approved: bool = False

    # Validation
    validation_passed: bool = False
    validation_results: List[dict] = field(default_factory=list)

    # Git
    commit_hash: Optional[str] = None
    git_branch: Optional[str] = None
    diff_summary: Optional[str] = None

    # Checkpoint
    checkpoint_reason: Optional[str] = None
    checkpoint_description: Optional[str] = None
    checkpoint_pending: bool = False

    # Errors
    error_message: Optional[str] = None
    risks: List[str] = field(default_factory=list)
    pending_items: List[str] = field(default_factory=list)


@dataclass
class TaskConfig:
    """Configuration for a new task."""
    task_description: str
    project_path: str = "."
    profile: str = "generic"
    mode: str = "full"  # full, plan_only, plan_execute, review

    # Options
    auto_validate: bool = True
    auto_commit: bool = False
    auto_push: bool = False
    require_approval_destructive: bool = True
    max_iterations: int = 3


@dataclass
class CheckpointDecision:
    """Checkpoint approval/rejection decision."""
    run_id: str
    approved: bool
    note: Optional[str] = None
    decided_at: datetime = field(default_factory=datetime.now)
    decided_by: str = "user"


@dataclass
class SettingsViewModel:
    """Settings view model."""
    # General
    project_path: str = "."
    workspace_path: str = "./workspace"
    active_profile: str = "generic"
    max_iterations: int = 3

    # Models
    planner_model: str = "gpt-4o"
    reviewer_model: str = "gpt-4o"
    planner_timeout: int = 120
    reviewer_timeout: int = 120

    # Executor
    executor_command: str = "claude"
    executor_timeout: int = 600

    # Validation
    flutter_commands: List[str] = field(default_factory=lambda: ["flutter analyze", "flutter test"])
    python_commands: List[str] = field(default_factory=lambda: ["python -m pytest", "ruff check ."])

    # Git
    allow_auto_commit: bool = False
    allow_auto_push: bool = False
    git_remote: str = "origin"
    git_branch: str = "main"
    protected_branches: List[str] = field(default_factory=lambda: ["main", "master"])

    # Security
    require_human_on_destructive: bool = True
    checkpoint_triggers: List[str] = field(default_factory=lambda: ["delete", "migration", "force push"])


@dataclass
class UIPreferences:
    """User interface preferences."""
    window_width: int = 1200
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100
    window_maximized: bool = False

    last_tab: str = "command_center"
    last_project_path: str = "."
    last_profile: str = "generic"
    interface_mode: str = "simple"
    onboarding_completed: bool = False

    sidebar_collapsed: bool = False
    show_advanced_options: bool = False

    # First task tracking
    first_task_completed: bool = False
    first_task_run_id: Optional[str] = None
    show_first_run_hints: bool = True

    # Recent items
    recent_projects: List[str] = field(default_factory=list)
    recent_tasks: List[str] = field(default_factory=list)

    # Updates
    auto_check_updates: bool = True
    update_channel: str = "stable"
    release_url: str = "https://github.com/hawkinf/ai-orchestrator/releases"
