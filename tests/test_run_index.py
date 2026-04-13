"""Tests for run index module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from orchestrator.run_index import (
    RunIndex,
    RunStatus,
    RunSummary,
    RunMetrics,
    RunFilter,
    get_run_index,
)


class TestRunStatus:
    """Tests for RunStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert RunStatus.UNKNOWN.value == "unknown"
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.CHECKPOINT.value == "checkpoint"
        assert RunStatus.BLOCKED.value == "blocked"
        assert RunStatus.CANCELLED.value == "cancelled"
        assert RunStatus.INCOMPLETE.value == "incomplete"


class TestRunSummary:
    """Tests for RunSummary dataclass."""

    def test_create_summary(self):
        """Test creating a run summary."""
        summary = RunSummary(
            run_id="test-001",
            task_summary="Test task",
            status=RunStatus.COMPLETED,
        )

        assert summary.run_id == "test-001"
        assert summary.status == RunStatus.COMPLETED

    def test_to_dict(self):
        """Test converting to dictionary."""
        summary = RunSummary(
            run_id="test-001",
            status=RunStatus.FAILED,
            task_summary="Failed task",
            last_error_summary="Some error",
        )

        d = summary.to_dict()
        assert d["run_id"] == "test-001"
        assert d["status"] == "failed"
        assert d["last_error_summary"] == "Some error"


class TestRunMetrics:
    """Tests for RunMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating metrics."""
        metrics = RunMetrics(
            total_runs=10,
            completed_runs=5,
            failed_runs=2,
        )

        assert metrics.total_runs == 10
        assert metrics.completed_runs == 5

    def test_to_dict(self):
        """Test converting to dictionary."""
        metrics = RunMetrics(
            total_runs=10,
            running_runs=2,
            last_success_at=datetime(2026, 1, 1, 12, 0, 0),
        )

        d = metrics.to_dict()
        assert d["total_runs"] == 10
        assert d["running_runs"] == 2
        assert "2026-01-01" in d["last_success_at"]


class TestRunFilter:
    """Tests for RunFilter."""

    def test_empty_filter_matches_all(self):
        """Test empty filter matches everything."""
        f = RunFilter()
        run = RunSummary(run_id="test", status=RunStatus.COMPLETED)

        assert f.matches(run) is True

    def test_search_text_filter(self):
        """Test search text filtering."""
        f = RunFilter(search_text="login")

        run1 = RunSummary(run_id="test", task_summary="Fix login bug", status=RunStatus.COMPLETED)
        run2 = RunSummary(run_id="test", task_summary="Add feature", status=RunStatus.COMPLETED)

        assert f.matches(run1) is True
        assert f.matches(run2) is False

    def test_status_filter(self):
        """Test status filtering."""
        f = RunFilter(status_filter=[RunStatus.FAILED, RunStatus.BLOCKED])

        run1 = RunSummary(run_id="test", status=RunStatus.FAILED)
        run2 = RunSummary(run_id="test", status=RunStatus.COMPLETED)
        run3 = RunSummary(run_id="test", status=RunStatus.BLOCKED)

        assert f.matches(run1) is True
        assert f.matches(run2) is False
        assert f.matches(run3) is True

    def test_profile_filter(self):
        """Test profile filtering."""
        f = RunFilter(profile_filter="flutter")

        run1 = RunSummary(run_id="test", status=RunStatus.COMPLETED, project_type="flutter")
        run2 = RunSummary(run_id="test", status=RunStatus.COMPLETED, project_type="python")

        assert f.matches(run1) is True
        assert f.matches(run2) is False

    def test_checkpoint_filter(self):
        """Test checkpoint filtering."""
        f = RunFilter(has_checkpoint=True)

        run1 = RunSummary(run_id="test", status=RunStatus.CHECKPOINT, has_checkpoint=True)
        run2 = RunSummary(run_id="test", status=RunStatus.COMPLETED, has_checkpoint=False)

        assert f.matches(run1) is True
        assert f.matches(run2) is False

    def test_error_filter(self):
        """Test error filtering."""
        f = RunFilter(has_error=True)

        run1 = RunSummary(run_id="test", status=RunStatus.FAILED, last_error_summary="Error!")
        run2 = RunSummary(run_id="test", status=RunStatus.COMPLETED, last_error_summary="")

        assert f.matches(run1) is True
        assert f.matches(run2) is False

    def test_date_filter(self):
        """Test date range filtering."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)

        f = RunFilter(date_from=yesterday)

        run1 = RunSummary(run_id="test", status=RunStatus.COMPLETED, created_at=now)
        run2 = RunSummary(run_id="test", status=RunStatus.COMPLETED, created_at=last_week)

        assert f.matches(run1) is True
        assert f.matches(run2) is False


class TestRunIndex:
    """Tests for RunIndex class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()
            (workspace / "logs").mkdir()
            yield workspace

    @pytest.fixture
    def sample_state(self):
        """Create sample state data."""
        return {
            "run_id": "test-001",
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:30:00",
            "completed_at": "2026-01-15T10:30:00",
            "status": "completed",
            "current_iteration": 2,
            "max_iterations": 3,
            "task": {
                "description": "Fix the login validation bug",
                "profile": "flutter",
            },
            "plan": {
                "objective": "Improve login flow",
            },
            "iterations": [
                {
                    "execution_report": {
                        "summary": "Added validation",
                        "files_changed": ["lib/login.dart"],
                        "risks": ["Breaking change"],
                    },
                    "review_response": {
                        "status": "approved",
                    },
                }
            ],
            "git_result_final": {
                "commit_hash": "abc123def",
            },
        }

    def test_create_index(self, temp_workspace):
        """Test creating a run index."""
        index = RunIndex(temp_workspace)
        assert index is not None

    def test_get_all_runs_empty(self, temp_workspace):
        """Test getting runs from empty workspace."""
        index = RunIndex(temp_workspace)
        runs = index.get_all_runs()

        assert runs == []

    def test_get_all_runs(self, temp_workspace, sample_state):
        """Test getting all runs."""
        # Create state file
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state, f)

        index = RunIndex(temp_workspace)
        runs = index.get_all_runs()

        assert len(runs) == 1
        assert runs[0].run_id == "test-001"
        assert runs[0].status == RunStatus.COMPLETED

    def test_get_run(self, temp_workspace, sample_state):
        """Test getting a specific run."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state, f)

        index = RunIndex(temp_workspace)
        run = index.get_run("test-001")

        assert run is not None
        assert run.run_id == "test-001"
        assert run.task_summary == "Fix the login validation bug"

    def test_get_run_not_found(self, temp_workspace):
        """Test getting non-existent run."""
        index = RunIndex(temp_workspace)
        run = index.get_run("nonexistent")

        assert run is None

    def test_filter_runs(self, temp_workspace, sample_state):
        """Test filtering runs."""
        # Create multiple runs
        for i, status in enumerate(["completed", "failed", "running"]):
            state = sample_state.copy()
            state["run_id"] = f"test-{i:03d}"
            state["status"] = status

            state_file = temp_workspace / "state" / f"test-{i:03d}.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

        index = RunIndex(temp_workspace)

        # Filter by status
        filter_criteria = RunFilter(status_filter=[RunStatus.FAILED])
        filtered = index.filter_runs(filter_criteria)

        assert len(filtered) == 1
        assert filtered[0].status == RunStatus.FAILED

    def test_get_metrics(self, temp_workspace, sample_state):
        """Test getting metrics."""
        # Create runs with different statuses
        statuses = ["completed", "completed", "failed", "running", "checkpoint"]
        for i, status in enumerate(statuses):
            state = sample_state.copy()
            state["run_id"] = f"test-{i:03d}"
            state["status"] = status
            if status == "checkpoint":
                state["checkpoint"] = {"resolved": False, "reason": "test"}

            state_file = temp_workspace / "state" / f"test-{i:03d}.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

        index = RunIndex(temp_workspace)
        metrics = index.get_metrics()

        assert metrics.total_runs == 5
        assert metrics.completed_runs == 2
        assert metrics.failed_runs == 1
        assert metrics.running_runs == 1
        assert metrics.checkpoint_runs == 1

    def test_get_profiles(self, temp_workspace, sample_state):
        """Test getting unique profiles."""
        profiles = ["flutter", "python", "flutter", "generic"]
        for i, profile in enumerate(profiles):
            state = sample_state.copy()
            state["run_id"] = f"test-{i:03d}"
            state["task"]["profile"] = profile

            state_file = temp_workspace / "state" / f"test-{i:03d}.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

        index = RunIndex(temp_workspace)
        profiles_list = index.get_profiles()

        assert "flutter" in profiles_list
        assert "python" in profiles_list
        assert "generic" in profiles_list
        assert len(profiles_list) == 3  # Unique profiles

    def test_export_to_json(self, temp_workspace, sample_state):
        """Test exporting to JSON."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state, f)

        index = RunIndex(temp_workspace)
        output_path = temp_workspace / "logs" / "export.json"
        result = index.export_to_json(output_path)

        assert result.exists()

        with open(result) as f:
            data = json.load(f)

        assert "metrics" in data
        assert "runs" in data
        assert len(data["runs"]) == 1

    def test_export_to_markdown(self, temp_workspace, sample_state):
        """Test exporting to Markdown."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state, f)

        index = RunIndex(temp_workspace)
        output_path = temp_workspace / "logs" / "export.md"
        result = index.export_to_markdown(output_path)

        assert result.exists()

        content = result.read_text()
        assert "Dashboard" in content
        assert "Metrics" in content
        assert "test-001" in content

    def test_corrupted_state_file(self, temp_workspace):
        """Test handling corrupted state file."""
        # Create invalid JSON
        state_file = temp_workspace / "state" / "corrupted.json"
        state_file.write_text("{ invalid json")

        index = RunIndex(temp_workspace)
        runs = index.get_all_runs()

        assert len(runs) == 1
        assert runs[0].is_corrupted is True
        assert runs[0].status == RunStatus.INCOMPLETE

    def test_partial_state_file(self, temp_workspace):
        """Test handling partial state file."""
        # Create minimal state
        state = {"run_id": "partial", "status": "running"}
        state_file = temp_workspace / "state" / "partial.json"
        with open(state_file, "w") as f:
            json.dump(state, f)

        index = RunIndex(temp_workspace)
        runs = index.get_all_runs()

        assert len(runs) == 1
        assert runs[0].run_id == "partial"
        assert runs[0].status == RunStatus.RUNNING

    def test_refresh(self, temp_workspace, sample_state):
        """Test cache refresh clears and reloads data."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state, f)

        index = RunIndex(temp_workspace)
        runs1 = index.get_all_runs()
        assert len(runs1) == 1

        # Add another run
        sample_state["run_id"] = "test-002"
        state_file2 = temp_workspace / "state" / "test-002.json"
        with open(state_file2, "w") as f:
            json.dump(sample_state, f)

        # Index scans for new files each time
        runs2 = index.get_all_runs()
        assert len(runs2) == 2

        # refresh() clears cache and forces fresh read
        index.refresh()
        assert len(index._cache) == 0

        # After refresh, data is reloaded
        runs3 = index.get_all_runs()
        assert len(runs3) == 2

    def test_sorting(self, temp_workspace, sample_state):
        """Test sorting runs."""
        # Create runs at different times
        for i in range(3):
            state = sample_state.copy()
            state["run_id"] = f"test-{i:03d}"
            state["created_at"] = f"2026-01-{15-i:02d}T10:00:00"

            state_file = temp_workspace / "state" / f"test-{i:03d}.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

        index = RunIndex(temp_workspace)

        # Sort descending (newest first)
        runs_desc = index.get_all_runs(sort_by="created_at", sort_desc=True)
        assert runs_desc[0].run_id == "test-000"  # Jan 15
        assert runs_desc[2].run_id == "test-002"  # Jan 13

        # Sort ascending (oldest first)
        runs_asc = index.get_all_runs(sort_by="created_at", sort_desc=False)
        assert runs_asc[0].run_id == "test-002"  # Jan 13

    def test_limit(self, temp_workspace, sample_state):
        """Test limiting results."""
        for i in range(10):
            state = sample_state.copy()
            state["run_id"] = f"test-{i:03d}"

            state_file = temp_workspace / "state" / f"test-{i:03d}.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

        index = RunIndex(temp_workspace)
        runs = index.get_all_runs(limit=5)

        assert len(runs) == 5


class TestGetRunIndex:
    """Tests for get_run_index factory function."""

    def test_creates_index(self):
        """Test factory creates index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()

            index = get_run_index(workspace)
            assert isinstance(index, RunIndex)


class TestStatusMapping:
    """Tests for status mapping."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()
            yield workspace

    def test_map_running_statuses(self, temp_workspace):
        """Test mapping running statuses."""
        for status_str in ["running", "executing", "planning", "reviewing"]:
            state = {"run_id": "test", "status": status_str}
            state_file = temp_workspace / "state" / "test.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

            index = RunIndex(temp_workspace)
            index.refresh()
            run = index.get_run("test")
            assert run.status == RunStatus.RUNNING

    def test_map_completed_statuses(self, temp_workspace):
        """Test mapping completed statuses."""
        for status_str in ["completed", "finalized", "done"]:
            state = {"run_id": "test", "status": status_str}
            state_file = temp_workspace / "state" / "test.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

            index = RunIndex(temp_workspace)
            index.refresh()
            run = index.get_run("test")
            assert run.status == RunStatus.COMPLETED

    def test_map_failed_statuses(self, temp_workspace):
        """Test mapping failed statuses."""
        for status_str in ["failed", "error"]:
            state = {"run_id": "test", "status": status_str}
            state_file = temp_workspace / "state" / "test.json"
            with open(state_file, "w") as f:
                json.dump(state, f)

            index = RunIndex(temp_workspace)
            index.refresh()
            run = index.get_run("test")
            assert run.status == RunStatus.FAILED

    def test_checkpoint_detection(self, temp_workspace):
        """Test checkpoint detection from state."""
        state = {
            "run_id": "test",
            "status": "awaiting_approval",
            "checkpoint": {"resolved": False, "reason": "migration"},
        }
        state_file = temp_workspace / "state" / "test.json"
        with open(state_file, "w") as f:
            json.dump(state, f)

        index = RunIndex(temp_workspace)
        run = index.get_run("test")

        assert run.status == RunStatus.CHECKPOINT
        assert run.has_checkpoint is True
        assert run.checkpoint_reason == "migration"
