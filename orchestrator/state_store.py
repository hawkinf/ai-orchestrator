"""State persistence for the orchestrator."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import RunState, TaskRequest, TaskStatus
from .paths import OrchestratorPaths
from .utils import generate_run_id


class StateStore:
    """
    Persistent state storage for runs.

    All state is stored as JSON files in the state directory.
    This allows resumption after crashes or interruptions.
    """

    def __init__(self, paths: OrchestratorPaths):
        self.paths = paths
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure state directories exist."""
        self.paths.state_dir.mkdir(parents=True, exist_ok=True)

    def _state_file(self, run_id: str) -> Path:
        """Get path to state file for a run."""
        return self.paths.state_dir / f"{run_id}.json"

    def _index_file(self) -> Path:
        """Get path to runs index file."""
        return self.paths.state_dir / "index.json"

    def create_run(self, task: TaskRequest) -> RunState:
        """
        Create a new run with initial state.

        Args:
            task: Task request to start

        Returns:
            New RunState instance
        """
        run_id = generate_run_id()
        state = RunState(
            run_id=run_id,
            status=TaskStatus.PENDING,
            task=task,
        )
        self.save_state(state)
        self._update_index(run_id, task.description)
        return state

    def save_state(self, state: RunState) -> None:
        """
        Save run state to disk.

        Args:
            state: RunState to save
        """
        state.updated_at = datetime.now()
        state_file = self._state_file(state.run_id)
        state_file.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8"
        )

    def load_state(self, run_id: str) -> Optional[RunState]:
        """
        Load run state from disk.

        Args:
            run_id: Run identifier

        Returns:
            RunState if found, None otherwise
        """
        state_file = self._state_file(run_id)
        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return RunState.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return None

    def update_status(self, run_id: str, status: TaskStatus) -> Optional[RunState]:
        """
        Update run status.

        Args:
            run_id: Run identifier
            status: New status

        Returns:
            Updated RunState if found
        """
        state = self.load_state(run_id)
        if state:
            state.status = status
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                state.completed_at = datetime.now()
            self.save_state(state)
        return state

    def set_error(self, run_id: str, error_message: str) -> Optional[RunState]:
        """
        Set error message and mark as failed.

        Args:
            run_id: Run identifier
            error_message: Error description

        Returns:
            Updated RunState if found
        """
        state = self.load_state(run_id)
        if state:
            state.error_message = error_message
            state.status = TaskStatus.FAILED
            state.completed_at = datetime.now()
            self.save_state(state)
        return state

    def _update_index(self, run_id: str, description: str) -> None:
        """Update runs index with new run."""
        index_file = self._index_file()
        index: dict = {}

        if index_file.exists():
            try:
                index = json.loads(index_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                index = {}

        if "runs" not in index:
            index["runs"] = []

        index["runs"].append({
            "run_id": run_id,
            "description": description[:100],
            "created_at": datetime.now().isoformat(),
        })

        # Keep only last 100 runs in index
        index["runs"] = index["runs"][-100:]

        index_file.write_text(
            json.dumps(index, indent=2),
            encoding="utf-8"
        )

    def list_runs(self, limit: int = 20) -> list[dict]:
        """
        List recent runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run info dicts
        """
        index_file = self._index_file()
        if not index_file.exists():
            return []

        try:
            index = json.loads(index_file.read_text(encoding="utf-8"))
            runs = index.get("runs", [])
            # Return most recent first
            return list(reversed(runs[-limit:]))
        except json.JSONDecodeError:
            return []

    def get_active_runs(self) -> list[RunState]:
        """
        Get all runs that are not completed/failed/cancelled.

        Returns:
            List of active RunState objects
        """
        active = []
        for run_info in self.list_runs(limit=50):
            state = self.load_state(run_info["run_id"])
            if state and state.status not in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ):
                active.append(state)
        return active

    def get_checkpoint_runs(self) -> list[RunState]:
        """
        Get runs waiting for checkpoint approval.

        Returns:
            List of RunState objects at checkpoint
        """
        checkpoint_runs = []
        for run_info in self.list_runs(limit=50):
            state = self.load_state(run_info["run_id"])
            if state and state.status == TaskStatus.CHECKPOINT:
                checkpoint_runs.append(state)
        return checkpoint_runs

    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run's state file.

        Args:
            run_id: Run identifier

        Returns:
            True if deleted, False if not found
        """
        state_file = self._state_file(run_id)
        if state_file.exists():
            state_file.unlink()
            return True
        return False

    def archive_run(self, run_id: str) -> bool:
        """
        Archive a run by moving it to archive directory.

        Args:
            run_id: Run identifier

        Returns:
            True if archived, False if not found
        """
        state_file = self._state_file(run_id)
        if not state_file.exists():
            return False

        archive_dir = self.paths.state_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_file = archive_dir / f"{run_id}.json"
        state_file.rename(archive_file)
        return True
