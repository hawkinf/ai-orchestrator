"""Checkpoint management for human approval gates."""

from datetime import datetime
from typing import Optional

from .models import (
    CheckpointReason,
    CheckpointRequest,
    RunState,
    TaskStatus,
)
from .state_store import StateStore
from .config import OrchestratorConfig


class CheckpointManager:
    """
    Manages human approval checkpoints.

    Checkpoints pause execution and require human approval before continuing.
    This is essential for destructive operations, migrations, etc.
    """

    def __init__(self, store: StateStore, config: OrchestratorConfig):
        self.store = store
        self.config = config

    def requires_checkpoint(self, text: str) -> tuple[bool, Optional[CheckpointReason]]:
        """
        Check if text requires a checkpoint.

        Args:
            text: Text to analyze (command, plan, etc.)

        Returns:
            Tuple of (requires_checkpoint, reason)
        """
        text_lower = text.lower()

        # Check for destructive git operations
        git_destructive = [
            "force push", "--force", "-f push",
            "reset --hard", "clean -f", "checkout .",
            "branch -D", "branch -d"
        ]
        for pattern in git_destructive:
            if pattern in text_lower:
                return True, CheckpointReason.GIT_DESTRUCTIVE

        # Check for migrations
        if "migration" in text_lower or "migrate" in text_lower:
            return True, CheckpointReason.MIGRATION

        # Check for deletions
        delete_patterns = ["delete", "remove", "rm -rf", "drop table", "truncate"]
        for pattern in delete_patterns:
            if pattern in text_lower:
                return True, CheckpointReason.DESTRUCTIVE_OPERATION

        # Check for infrastructure
        infra_patterns = ["infrastructure", "terraform", "cloudformation", "deploy"]
        for pattern in infra_patterns:
            if pattern in text_lower:
                return True, CheckpointReason.INFRASTRUCTURE_CHANGE

        # Check for architecture changes
        arch_patterns = ["rewrite", "refactor entire", "restructure", "redesign"]
        for pattern in arch_patterns:
            if pattern in text_lower:
                return True, CheckpointReason.ARCHITECTURE_REWRITE

        # Check config triggers
        if self.config.needs_checkpoint(text):
            return True, CheckpointReason.MANUAL_REQUEST

        return False, None

    def create_checkpoint(
        self,
        state: RunState,
        reason: CheckpointReason,
        description: str,
        details: Optional[dict] = None,
    ) -> CheckpointRequest:
        """
        Create a checkpoint and pause the run.

        Args:
            state: Current run state
            reason: Reason for checkpoint
            description: Human-readable description
            details: Additional context

        Returns:
            Created CheckpointRequest
        """
        checkpoint = CheckpointRequest(
            run_id=state.run_id,
            reason=reason,
            description=description,
            details=details or {},
        )

        state.checkpoint = checkpoint
        state.status = TaskStatus.CHECKPOINT
        self.store.save_state(state)

        return checkpoint

    def approve_checkpoint(
        self,
        run_id: str,
        resolution_note: Optional[str] = None,
    ) -> Optional[RunState]:
        """
        Approve a pending checkpoint.

        Args:
            run_id: Run identifier
            resolution_note: Optional note about approval

        Returns:
            Updated RunState if found
        """
        state = self.store.load_state(run_id)
        if not state or not state.checkpoint:
            return None

        state.checkpoint.resolved = True
        state.checkpoint.resolution = resolution_note or "approved"
        state.checkpoint.resolved_at = datetime.now()
        state.status = TaskStatus.EXECUTING  # Resume execution
        self.store.save_state(state)

        return state

    def reject_checkpoint(
        self,
        run_id: str,
        reason: Optional[str] = None,
    ) -> Optional[RunState]:
        """
        Reject a pending checkpoint.

        Args:
            run_id: Run identifier
            reason: Reason for rejection

        Returns:
            Updated RunState if found
        """
        state = self.store.load_state(run_id)
        if not state or not state.checkpoint:
            return None

        state.checkpoint.resolved = True
        state.checkpoint.resolution = f"rejected: {reason}" if reason else "rejected"
        state.checkpoint.resolved_at = datetime.now()
        state.status = TaskStatus.CANCELLED
        state.error_message = f"Checkpoint rejected: {reason or 'No reason given'}"
        self.store.save_state(state)

        return state

    def get_pending_checkpoints(self) -> list[RunState]:
        """
        Get all runs with pending checkpoints.

        Returns:
            List of RunState objects waiting for approval
        """
        return self.store.get_checkpoint_runs()

    def has_pending_checkpoint(self, run_id: str) -> bool:
        """
        Check if a run has a pending checkpoint.

        Args:
            run_id: Run identifier

        Returns:
            True if checkpoint is pending
        """
        state = self.store.load_state(run_id)
        return (
            state is not None
            and state.status == TaskStatus.CHECKPOINT
            and state.checkpoint is not None
            and not state.checkpoint.resolved
        )

    def create_failure_checkpoint(
        self,
        state: RunState,
        failure_count: int,
        last_error: str,
    ) -> CheckpointRequest:
        """
        Create checkpoint due to repeated failures.

        Args:
            state: Current run state
            failure_count: Number of failures
            last_error: Last error message

        Returns:
            Created CheckpointRequest
        """
        return self.create_checkpoint(
            state=state,
            reason=CheckpointReason.REPEATED_FAILURES,
            description=f"Execution failed {failure_count} times. Last error: {last_error}",
            details={
                "failure_count": failure_count,
                "last_error": last_error,
            },
        )

    def create_command_checkpoint(
        self,
        state: RunState,
        command: str,
    ) -> CheckpointRequest:
        """
        Create checkpoint for command not in allowlist.

        Args:
            state: Current run state
            command: Command that needs approval

        Returns:
            Created CheckpointRequest
        """
        return self.create_checkpoint(
            state=state,
            reason=CheckpointReason.COMMAND_NOT_ALLOWED,
            description=f"Command requires approval: {command}",
            details={
                "command": command,
            },
        )
