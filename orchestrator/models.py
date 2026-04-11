"""Pydantic models for the orchestrator."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task/run."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    VALIDATING = "validating"
    CHECKPOINT = "checkpoint"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckpointReason(str, Enum):
    """Reasons for checkpoint."""
    DESTRUCTIVE_OPERATION = "destructive_operation"
    MIGRATION = "migration"
    INFRASTRUCTURE_CHANGE = "infrastructure_change"
    ARCHITECTURE_REWRITE = "architecture_rewrite"
    GIT_DESTRUCTIVE = "git_destructive"
    COMMAND_NOT_ALLOWED = "command_not_allowed"
    REPEATED_FAILURES = "repeated_failures"
    MANUAL_REQUEST = "manual_request"


class ReviewStatus(str, Enum):
    """Review decision status."""
    APPROVED = "approved"
    NEEDS_FOLLOWUP = "needs_followup"
    BLOCKED = "blocked"


# ============================================================
# Input/Request Models
# ============================================================

class TaskRequest(BaseModel):
    """Initial task request from user."""
    description: str = Field(..., description="Task description from user")
    project_path: Optional[str] = Field(None, description="Path to project")
    profile: Optional[str] = Field(None, description="Project profile (flutter, python, etc)")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    priority: Optional[str] = Field(None, description="Priority level")
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# Planner Models
# ============================================================

class PlanResponse(BaseModel):
    """Structured response from planner."""
    objective: str = Field(..., description="Clear objective statement")
    scope: str = Field(..., description="Scope of changes")
    constraints: list[str] = Field(default_factory=list, description="Constraints to follow")
    files_likely_affected: list[str] = Field(default_factory=list, description="Files to modify")
    risks: list[str] = Field(default_factory=list, description="Identified risks")
    validation_steps: list[str] = Field(default_factory=list, description="How to validate")
    checkpoints: list[str] = Field(default_factory=list, description="Points requiring human review")
    execution_prompt: str = Field(..., description="Prompt for executor")
    estimated_complexity: Optional[str] = Field(None, description="Complexity estimate")


# ============================================================
# Execution Models
# ============================================================

class ExecutionResult(BaseModel):
    """Result of executor run."""
    success: bool = Field(..., description="Whether execution succeeded")
    exit_code: int = Field(0, description="Process exit code")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    duration_seconds: float = Field(0.0, description="Execution duration")
    files_changed: list[str] = Field(default_factory=list, description="Files modified")
    commands_run: list[str] = Field(default_factory=list, description="Commands executed")
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


class ExecutionReport(BaseModel):
    """Parsed execution report."""
    summary: str = Field("", description="Summary of what was done")
    files_changed: list[str] = Field(default_factory=list)
    commands_executed: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    tests_passed: int = Field(0)
    tests_failed: int = Field(0)
    pending_items: list[str] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    needs_checkpoint: bool = Field(False)
    checkpoint_reason: Optional[str] = None
    raw_output: str = Field("")


# ============================================================
# Review Models
# ============================================================

class ReviewResponse(BaseModel):
    """Structured response from reviewer."""
    status: ReviewStatus = Field(..., description="Review decision")
    findings: list[str] = Field(default_factory=list, description="Review findings")
    regression_risks: list[str] = Field(default_factory=list, description="Regression risks")
    next_prompt: Optional[str] = Field(None, description="Prompt for next iteration")
    commit_allowed: bool = Field(False, description="Whether commit is allowed")
    human_review_required: bool = Field(False, description="Needs human review")
    suggestions: list[str] = Field(default_factory=list)


# ============================================================
# Validation Models
# ============================================================

class ValidationResult(BaseModel):
    """Result of validation commands."""
    command: str = Field(..., description="Command that was run")
    success: bool = Field(..., description="Whether validation passed")
    exit_code: int = Field(0)
    stdout: str = Field("")
    stderr: str = Field("")
    duration_seconds: float = Field(0.0)


class ValidationSummary(BaseModel):
    """Summary of all validations."""
    all_passed: bool = Field(False)
    results: list[ValidationResult] = Field(default_factory=list)
    total_duration: float = Field(0.0)


# ============================================================
# Git Models
# ============================================================

class GitStatus(BaseModel):
    """Git repository status."""
    is_repo: bool = Field(False)
    branch: str = Field("")
    is_clean: bool = Field(True)
    staged_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    ahead: int = Field(0)
    behind: int = Field(0)


class GitResult(BaseModel):
    """Result of git operation."""
    operation: str = Field(..., description="Git operation performed")
    success: bool = Field(...)
    message: str = Field("")
    commit_hash: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# Checkpoint Models
# ============================================================

class CheckpointRequest(BaseModel):
    """Checkpoint requiring human approval."""
    run_id: str = Field(...)
    reason: CheckpointReason = Field(...)
    description: str = Field(...)
    details: dict = Field(default_factory=dict)
    options: list[str] = Field(default_factory=lambda: ["approve", "reject", "modify"])
    created_at: datetime = Field(default_factory=datetime.now)
    resolved: bool = Field(False)
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


# ============================================================
# State Models
# ============================================================

class IterationState(BaseModel):
    """State of a single iteration."""
    iteration_number: int = Field(...)
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    plan_prompt: Optional[str] = None
    execution_result: Optional[ExecutionResult] = None
    execution_report: Optional[ExecutionReport] = None
    review_response: Optional[ReviewResponse] = None
    validation_summary: Optional[ValidationSummary] = None


class RunState(BaseModel):
    """Complete state of a run for persistence."""
    run_id: str = Field(...)
    status: TaskStatus = Field(TaskStatus.PENDING)
    task: TaskRequest = Field(...)
    plan: Optional[PlanResponse] = None
    current_iteration: int = Field(0)
    iterations: list[IterationState] = Field(default_factory=list)
    checkpoint: Optional[CheckpointRequest] = None
    git_status_initial: Optional[GitStatus] = None
    git_result_final: Optional[GitResult] = None
    validation_final: Optional[ValidationSummary] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ============================================================
# Final Report Model
# ============================================================

class FinalReport(BaseModel):
    """Final report for a completed run."""
    run_id: str = Field(...)
    objective: str = Field(...)
    status: TaskStatus = Field(...)
    plan_summary: Optional[str] = None
    total_iterations: int = Field(0)
    files_changed: list[str] = Field(default_factory=list)
    commands_executed: list[str] = Field(default_factory=list)
    validations: list[dict] = Field(default_factory=list)
    commit_hash: Optional[str] = None
    duration_seconds: float = Field(0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    artifacts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
