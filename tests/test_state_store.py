"""Tests for state persistence."""

import pytest
import tempfile
from pathlib import Path

from orchestrator.models import TaskRequest, TaskStatus
from orchestrator.paths import OrchestratorPaths
from orchestrator.state_store import StateStore


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def state_store(temp_workspace):
    """Create a state store with temp workspace."""
    paths = OrchestratorPaths(temp_workspace)
    return StateStore(paths)


class TestStateStore:
    """Tests for StateStore class."""

    def test_create_run(self, state_store):
        """Test creating a new run."""
        task = TaskRequest(description="Test task")
        state = state_store.create_run(task)

        assert state.run_id is not None
        assert state.status == TaskStatus.PENDING
        assert state.task.description == "Test task"

    def test_save_and_load_state(self, state_store):
        """Test saving and loading state."""
        task = TaskRequest(description="Test task")
        state = state_store.create_run(task)
        run_id = state.run_id

        # Modify state
        state.status = TaskStatus.EXECUTING
        state.current_iteration = 2
        state_store.save_state(state)

        # Load and verify
        loaded = state_store.load_state(run_id)
        assert loaded is not None
        assert loaded.status == TaskStatus.EXECUTING
        assert loaded.current_iteration == 2

    def test_update_status(self, state_store):
        """Test updating run status."""
        task = TaskRequest(description="Test task")
        state = state_store.create_run(task)
        run_id = state.run_id

        # Update status
        updated = state_store.update_status(run_id, TaskStatus.COMPLETED)

        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None

    def test_set_error(self, state_store):
        """Test setting error state."""
        task = TaskRequest(description="Test task")
        state = state_store.create_run(task)
        run_id = state.run_id

        # Set error
        updated = state_store.set_error(run_id, "Something went wrong")

        assert updated is not None
        assert updated.status == TaskStatus.FAILED
        assert updated.error_message == "Something went wrong"
        assert updated.completed_at is not None

    def test_list_runs(self, state_store):
        """Test listing runs."""
        # Create multiple runs
        for i in range(5):
            task = TaskRequest(description=f"Task {i}")
            state_store.create_run(task)

        runs = state_store.list_runs(limit=10)
        assert len(runs) == 5

    def test_load_nonexistent_run(self, state_store):
        """Test loading a nonexistent run."""
        result = state_store.load_state("nonexistent-run-id")
        assert result is None

    def test_get_active_runs(self, state_store):
        """Test getting active runs."""
        import time

        # Create runs with different statuses
        task1 = TaskRequest(description="Active task")
        state1 = state_store.create_run(task1)
        state1.status = TaskStatus.EXECUTING
        state_store.save_state(state1)

        # Small delay to ensure different run_id
        time.sleep(1.1)

        task2 = TaskRequest(description="Completed task")
        state2 = state_store.create_run(task2)
        state2.status = TaskStatus.COMPLETED
        state_store.save_state(state2)

        active = state_store.get_active_runs()
        # Check that at least the active one is present
        active_ids = [s.run_id for s in active]
        assert state1.run_id in active_ids

    def test_delete_run(self, state_store):
        """Test deleting a run."""
        task = TaskRequest(description="Test task")
        state = state_store.create_run(task)
        run_id = state.run_id

        # Verify exists
        assert state_store.load_state(run_id) is not None

        # Delete
        result = state_store.delete_run(run_id)
        assert result is True

        # Verify deleted
        assert state_store.load_state(run_id) is None

    def test_delete_nonexistent_run(self, state_store):
        """Test deleting a nonexistent run."""
        result = state_store.delete_run("nonexistent-run-id")
        assert result is False
