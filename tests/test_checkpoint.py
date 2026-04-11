"""Tests for checkpoint management."""

import pytest
import tempfile
from pathlib import Path

from orchestrator.checkpoint import CheckpointManager
from orchestrator.config import OrchestratorConfig
from orchestrator.models import (
    CheckpointReason,
    TaskRequest,
    TaskStatus,
)
from orchestrator.paths import OrchestratorPaths
from orchestrator.state_store import StateStore


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config():
    """Create test config."""
    return OrchestratorConfig()


@pytest.fixture
def checkpoint_manager(temp_workspace, config):
    """Create checkpoint manager."""
    paths = OrchestratorPaths(temp_workspace)
    store = StateStore(paths)
    return CheckpointManager(store, config), store


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    def test_requires_checkpoint_force_push(self, checkpoint_manager):
        """Test checkpoint detection for force push."""
        mgr, _ = checkpoint_manager

        needs, reason = mgr.requires_checkpoint("git push --force origin main")

        assert needs is True
        assert reason == CheckpointReason.GIT_DESTRUCTIVE

    def test_requires_checkpoint_migration(self, checkpoint_manager):
        """Test checkpoint detection for migration."""
        mgr, _ = checkpoint_manager

        needs, reason = mgr.requires_checkpoint("Running database migration")

        assert needs is True
        assert reason == CheckpointReason.MIGRATION

    def test_requires_checkpoint_delete(self, checkpoint_manager):
        """Test checkpoint detection for delete."""
        mgr, _ = checkpoint_manager

        needs, reason = mgr.requires_checkpoint("Delete all user data")

        assert needs is True
        assert reason == CheckpointReason.DESTRUCTIVE_OPERATION

    def test_requires_checkpoint_infrastructure(self, checkpoint_manager):
        """Test checkpoint detection for infrastructure."""
        mgr, _ = checkpoint_manager

        needs, reason = mgr.requires_checkpoint("Deploy infrastructure changes")

        assert needs is True
        assert reason == CheckpointReason.INFRASTRUCTURE_CHANGE

    def test_requires_checkpoint_safe(self, checkpoint_manager):
        """Test no checkpoint for safe operations."""
        mgr, _ = checkpoint_manager

        needs, reason = mgr.requires_checkpoint("Add new feature to login page")

        assert needs is False
        assert reason is None

    def test_create_checkpoint(self, checkpoint_manager):
        """Test creating a checkpoint."""
        mgr, store = checkpoint_manager

        # Create a run
        task = TaskRequest(description="Test task")
        state = store.create_run(task)

        # Create checkpoint
        checkpoint = mgr.create_checkpoint(
            state,
            CheckpointReason.MIGRATION,
            "Migration requires approval",
        )

        assert checkpoint is not None
        assert checkpoint.reason == CheckpointReason.MIGRATION
        assert checkpoint.resolved is False

        # Verify state updated
        loaded = store.load_state(state.run_id)
        assert loaded.status == TaskStatus.CHECKPOINT
        assert loaded.checkpoint is not None

    def test_approve_checkpoint(self, checkpoint_manager):
        """Test approving a checkpoint."""
        mgr, store = checkpoint_manager

        # Create run and checkpoint
        task = TaskRequest(description="Test task")
        state = store.create_run(task)
        mgr.create_checkpoint(
            state,
            CheckpointReason.MIGRATION,
            "Migration requires approval",
        )

        # Approve
        updated = mgr.approve_checkpoint(state.run_id, "Approved by test")

        assert updated is not None
        assert updated.status == TaskStatus.EXECUTING
        assert updated.checkpoint.resolved is True
        assert "approved" in updated.checkpoint.resolution.lower()

    def test_reject_checkpoint(self, checkpoint_manager):
        """Test rejecting a checkpoint."""
        mgr, store = checkpoint_manager

        # Create run and checkpoint
        task = TaskRequest(description="Test task")
        state = store.create_run(task)
        mgr.create_checkpoint(
            state,
            CheckpointReason.MIGRATION,
            "Migration requires approval",
        )

        # Reject
        updated = mgr.reject_checkpoint(state.run_id, "Not safe")

        assert updated is not None
        assert updated.status == TaskStatus.CANCELLED
        assert updated.checkpoint.resolved is True
        assert "rejected" in updated.checkpoint.resolution.lower()

    def test_get_pending_checkpoints(self, checkpoint_manager):
        """Test getting pending checkpoints."""
        mgr, store = checkpoint_manager

        # Create runs with checkpoints
        task1 = TaskRequest(description="Task 1")
        state1 = store.create_run(task1)
        mgr.create_checkpoint(state1, CheckpointReason.MIGRATION, "Test 1")

        task2 = TaskRequest(description="Task 2")
        state2 = store.create_run(task2)
        mgr.create_checkpoint(state2, CheckpointReason.DESTRUCTIVE_OPERATION, "Test 2")

        # Get pending
        pending = mgr.get_pending_checkpoints()

        assert len(pending) == 2

    def test_has_pending_checkpoint(self, checkpoint_manager):
        """Test checking for pending checkpoint."""
        mgr, store = checkpoint_manager

        # Create run with checkpoint
        task = TaskRequest(description="Test task")
        state = store.create_run(task)
        mgr.create_checkpoint(state, CheckpointReason.MIGRATION, "Test")

        assert mgr.has_pending_checkpoint(state.run_id) is True

        # Approve and check again
        mgr.approve_checkpoint(state.run_id)

        assert mgr.has_pending_checkpoint(state.run_id) is False
