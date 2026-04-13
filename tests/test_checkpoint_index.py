"""Tests for checkpoint index module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from orchestrator.checkpoint_index import (
    CheckpointDecisionStatus,
    CheckpointDetail,
    CheckpointFilter,
    CheckpointIndex,
    CheckpointMetrics,
    CheckpointSeverity,
    CheckpointSummary,
    REASON_DISPLAY_MAP,
    REASON_SEVERITY_MAP,
    get_checkpoint_index,
)


class TestCheckpointSeverity:
    """Tests for CheckpointSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert CheckpointSeverity.INFO.value == "info"
        assert CheckpointSeverity.WARNING.value == "warning"
        assert CheckpointSeverity.HIGH_RISK.value == "high_risk"
        assert CheckpointSeverity.CRITICAL.value == "critical"


class TestCheckpointDecisionStatus:
    """Tests for CheckpointDecisionStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert CheckpointDecisionStatus.PENDING.value == "pending"
        assert CheckpointDecisionStatus.APPROVED.value == "approved"
        assert CheckpointDecisionStatus.REJECTED.value == "rejected"


class TestCheckpointSummary:
    """Tests for CheckpointSummary dataclass."""

    def test_create_summary(self):
        """Test creating a checkpoint summary."""
        summary = CheckpointSummary(
            checkpoint_id="run-001_20260101120000",
            run_id="run-001",
            reason="destructive_operation",
            reason_display="Operacao Destrutiva",
            description="Delete all data",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.HIGH_RISK,
        )

        assert summary.checkpoint_id == "run-001_20260101120000"
        assert summary.run_id == "run-001"
        assert summary.status == CheckpointDecisionStatus.PENDING
        assert summary.severity == CheckpointSeverity.HIGH_RISK

    def test_to_dict(self):
        """Test converting to dictionary."""
        summary = CheckpointSummary(
            checkpoint_id="run-001_20260101120000",
            run_id="run-001",
            reason="migration",
            reason_display="Migracao",
            description="Database migration",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.HIGH_RISK,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            resolved_at=datetime(2026, 1, 1, 12, 30, 0),
            resolution="approved",
        )

        d = summary.to_dict()
        assert d["checkpoint_id"] == "run-001_20260101120000"
        assert d["status"] == "approved"
        assert d["severity"] == "high_risk"
        assert d["created_at"] == "2026-01-01T12:00:00"


class TestCheckpointMetrics:
    """Tests for CheckpointMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating metrics."""
        metrics = CheckpointMetrics(
            total_checkpoints=10,
            pending_checkpoints=3,
            approved_checkpoints=5,
            rejected_checkpoints=2,
            critical_pending=1,
            high_risk_pending=2,
        )

        assert metrics.total_checkpoints == 10
        assert metrics.pending_checkpoints == 3
        assert metrics.critical_pending == 1

    def test_to_dict(self):
        """Test converting to dictionary."""
        metrics = CheckpointMetrics(
            total_checkpoints=5,
            pending_checkpoints=2,
        )

        d = metrics.to_dict()
        assert d["total_checkpoints"] == 5
        assert d["pending_checkpoints"] == 2


class TestCheckpointFilter:
    """Tests for CheckpointFilter dataclass."""

    def test_empty_filter_matches_all(self):
        """Test empty filter matches everything."""
        f = CheckpointFilter()
        summary = CheckpointSummary(
            checkpoint_id="test",
            run_id="run-001",
            reason="migration",
            reason_display="Migracao",
            description="Test",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.WARNING,
        )
        assert f.matches(summary) is True

    def test_status_filter(self):
        """Test filtering by status."""
        f = CheckpointFilter(status_filter=[CheckpointDecisionStatus.PENDING])

        pending = CheckpointSummary(
            checkpoint_id="test1",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )

        approved = CheckpointSummary(
            checkpoint_id="test2",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.INFO,
        )

        assert f.matches(pending) is True
        assert f.matches(approved) is False

    def test_severity_filter(self):
        """Test filtering by severity."""
        f = CheckpointFilter(severity_filter=[CheckpointSeverity.CRITICAL])

        critical = CheckpointSummary(
            checkpoint_id="test1",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.CRITICAL,
        )

        warning = CheckpointSummary(
            checkpoint_id="test2",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.WARNING,
        )

        assert f.matches(critical) is True
        assert f.matches(warning) is False

    def test_search_text_filter(self):
        """Test filtering by search text."""
        f = CheckpointFilter(search_text="migration")

        match = CheckpointSummary(
            checkpoint_id="test1",
            run_id="run-001",
            reason="migration",
            reason_display="Migracao",
            description="Database migration",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )

        no_match = CheckpointSummary(
            checkpoint_id="test2",
            run_id="run-002",
            reason="delete",
            reason_display="Delete",
            description="Delete data",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )

        assert f.matches(match) is True
        assert f.matches(no_match) is False

    def test_run_id_filter(self):
        """Test filtering by run_id."""
        f = CheckpointFilter(run_id_filter="run-001")

        match = CheckpointSummary(
            checkpoint_id="test1",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )

        no_match = CheckpointSummary(
            checkpoint_id="test2",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )

        assert f.matches(match) is True
        assert f.matches(no_match) is False

    def test_date_filter(self):
        """Test filtering by date range."""
        now = datetime.now()
        f = CheckpointFilter(
            date_from=now - timedelta(days=7),
            date_to=now,
        )

        recent = CheckpointSummary(
            checkpoint_id="test1",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
            created_at=now - timedelta(days=3),
        )

        old = CheckpointSummary(
            checkpoint_id="test2",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
            created_at=now - timedelta(days=30),
        )

        assert f.matches(recent) is True
        assert f.matches(old) is False


class TestCheckpointIndex:
    """Tests for CheckpointIndex class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()
            yield workspace

    @pytest.fixture
    def sample_state_with_checkpoint(self):
        """Sample state data with checkpoint."""
        return {
            "run_id": "test-001",
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:30:00",
            "status": "checkpoint",
            "task": {
                "description": "Fix the bug",
                "profile": "python",
            },
            "checkpoint": {
                "run_id": "test-001",
                "reason": "destructive_operation",
                "description": "About to delete files",
                "created_at": "2026-01-15T10:30:00",
                "resolved": False,
                "options": ["approve", "reject"],
            },
            "plan": {
                "objective": "Fix the critical bug",
                "risks": ["Data loss", "Downtime"],
            },
        }

    def test_create_index(self, temp_workspace):
        """Test creating index."""
        index = CheckpointIndex(temp_workspace)
        assert index is not None
        assert index.workspace_path == temp_workspace

    def test_get_all_checkpoints_empty(self, temp_workspace):
        """Test getting checkpoints from empty workspace."""
        index = CheckpointIndex(temp_workspace)
        checkpoints = index.get_all_checkpoints()
        assert checkpoints == []

    def test_get_all_checkpoints(self, temp_workspace, sample_state_with_checkpoint):
        """Test getting all checkpoints."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        checkpoints = index.get_all_checkpoints()

        assert len(checkpoints) == 1
        assert checkpoints[0].run_id == "test-001"
        assert checkpoints[0].status == CheckpointDecisionStatus.PENDING
        assert checkpoints[0].reason == "destructive_operation"

    def test_get_pending_checkpoints(self, temp_workspace, sample_state_with_checkpoint):
        """Test getting only pending checkpoints."""
        # Create pending checkpoint
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        # Create resolved checkpoint
        resolved_state = sample_state_with_checkpoint.copy()
        resolved_state["run_id"] = "test-002"
        resolved_state["checkpoint"] = {
            "run_id": "test-002",
            "reason": "migration",
            "description": "Migration complete",
            "created_at": "2026-01-14T10:00:00",
            "resolved": True,
            "resolved_at": "2026-01-14T10:30:00",
            "resolution": "approved",
        }
        state_file2 = temp_workspace / "state" / "test-002.json"
        with open(state_file2, "w") as f:
            json.dump(resolved_state, f)

        index = CheckpointIndex(temp_workspace)
        pending = index.get_pending_checkpoints()

        assert len(pending) == 1
        assert pending[0].run_id == "test-001"

    def test_filter_checkpoints(self, temp_workspace, sample_state_with_checkpoint):
        """Test filtering checkpoints."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)

        # Filter by status
        f = CheckpointFilter(status_filter=[CheckpointDecisionStatus.APPROVED])
        filtered = index.filter_checkpoints(f)
        assert len(filtered) == 0

        # Filter by pending
        f = CheckpointFilter(status_filter=[CheckpointDecisionStatus.PENDING])
        filtered = index.filter_checkpoints(f)
        assert len(filtered) == 1

    def test_get_metrics(self, temp_workspace, sample_state_with_checkpoint):
        """Test calculating metrics."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        metrics = index.get_metrics()

        assert metrics.total_checkpoints == 1
        assert metrics.pending_checkpoints == 1
        assert metrics.approved_checkpoints == 0

    def test_get_checkpoint_by_run(self, temp_workspace, sample_state_with_checkpoint):
        """Test getting checkpoint by run ID."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        checkpoint = index.get_checkpoint_by_run("test-001")

        assert checkpoint is not None
        assert checkpoint.run_id == "test-001"

        # Non-existent run
        checkpoint = index.get_checkpoint_by_run("test-999")
        assert checkpoint is None

    def test_get_checkpoint_detail(self, temp_workspace, sample_state_with_checkpoint):
        """Test getting checkpoint detail."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        index._scan_checkpoints()

        # Get checkpoint ID from cache
        checkpoints = index.get_all_checkpoints()
        assert len(checkpoints) == 1
        checkpoint_id = checkpoints[0].checkpoint_id

        detail = index.get_checkpoint_detail(checkpoint_id)

        assert detail is not None
        assert detail.run_id == "test-001"
        assert detail.plan_objective == "Fix the critical bug"
        assert "Data loss" in detail.risks

    def test_refresh(self, temp_workspace, sample_state_with_checkpoint):
        """Test cache refresh."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        checkpoints1 = index.get_all_checkpoints()
        assert len(checkpoints1) == 1

        # Clear cache
        index.refresh()
        assert len(index._cache) == 0

        # Reload
        checkpoints2 = index.get_all_checkpoints()
        assert len(checkpoints2) == 1

    def test_export_to_json(self, temp_workspace, sample_state_with_checkpoint):
        """Test exporting to JSON."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        output_path = temp_workspace / "logs" / "checkpoints.json"

        result = index.export_to_json(output_path)

        assert result == output_path
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert "metrics" in data
        assert "checkpoints" in data
        assert len(data["checkpoints"]) == 1

    def test_export_to_markdown(self, temp_workspace, sample_state_with_checkpoint):
        """Test exporting to Markdown."""
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(sample_state_with_checkpoint, f)

        index = CheckpointIndex(temp_workspace)
        output_path = temp_workspace / "logs" / "checkpoints.md"

        result = index.export_to_markdown(output_path)

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "# AI Orchestrator" in content
        assert "Metrics Summary" in content

    def test_corrupted_state_file(self, temp_workspace):
        """Test handling corrupted state file."""
        state_file = temp_workspace / "state" / "corrupted.json"
        state_file.write_text("not valid json")

        index = CheckpointIndex(temp_workspace)
        checkpoints = index.get_all_checkpoints()

        # Should not crash, just skip corrupted file
        assert checkpoints == []

    def test_state_without_checkpoint(self, temp_workspace):
        """Test handling state file without checkpoint."""
        state = {
            "run_id": "test-001",
            "status": "completed",
            "task": {"description": "Test"},
        }
        state_file = temp_workspace / "state" / "test-001.json"
        with open(state_file, "w") as f:
            json.dump(state, f)

        index = CheckpointIndex(temp_workspace)
        checkpoints = index.get_all_checkpoints()

        # Should not include runs without checkpoints
        assert checkpoints == []

    def test_severity_mapping(self):
        """Test severity mapping by reason."""
        assert REASON_SEVERITY_MAP["git_destructive"] == CheckpointSeverity.CRITICAL
        assert REASON_SEVERITY_MAP["infrastructure_change"] == CheckpointSeverity.CRITICAL
        assert REASON_SEVERITY_MAP["migration"] == CheckpointSeverity.HIGH_RISK
        assert REASON_SEVERITY_MAP["repeated_failures"] == CheckpointSeverity.WARNING
        assert REASON_SEVERITY_MAP["manual_request"] == CheckpointSeverity.INFO

    def test_reason_display_mapping(self):
        """Test reason display text mapping."""
        assert REASON_DISPLAY_MAP["destructive_operation"] == "Operacao Destrutiva"
        assert REASON_DISPLAY_MAP["migration"] == "Migracao"
        assert REASON_DISPLAY_MAP["git_destructive"] == "Git Destrutivo"


class TestGetCheckpointIndex:
    """Tests for factory function."""

    def test_creates_index(self):
        """Test factory creates index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()

            index = get_checkpoint_index(workspace)

            assert isinstance(index, CheckpointIndex)
            assert index.workspace_path == workspace


class TestCheckpointIndexIntegration:
    """Integration tests for checkpoint index."""

    @pytest.fixture
    def workspace_with_checkpoints(self):
        """Create workspace with multiple checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()

            # Create multiple checkpoints with different statuses
            checkpoints_data = [
                {
                    "run_id": "run-001",
                    "status": "checkpoint",
                    "created_at": "2026-01-15T10:00:00",
                    "task": {"description": "Task 1", "profile": "python"},
                    "checkpoint": {
                        "reason": "destructive_operation",
                        "description": "Delete operation",
                        "created_at": "2026-01-15T10:30:00",
                        "resolved": False,
                    },
                },
                {
                    "run_id": "run-002",
                    "status": "completed",
                    "created_at": "2026-01-14T10:00:00",
                    "task": {"description": "Task 2", "profile": "flutter"},
                    "checkpoint": {
                        "reason": "migration",
                        "description": "Migration",
                        "created_at": "2026-01-14T10:00:00",
                        "resolved": True,
                        "resolved_at": "2026-01-14T10:30:00",
                        "resolution": "approved",
                    },
                },
                {
                    "run_id": "run-003",
                    "status": "cancelled",
                    "created_at": "2026-01-13T10:00:00",
                    "task": {"description": "Task 3", "profile": "python"},
                    "checkpoint": {
                        "reason": "git_destructive",
                        "description": "Force push",
                        "created_at": "2026-01-13T10:00:00",
                        "resolved": True,
                        "resolved_at": "2026-01-13T10:15:00",
                        "resolution": "rejected: too risky",
                    },
                },
            ]

            for cp in checkpoints_data:
                state_file = workspace / "state" / f"{cp['run_id']}.json"
                with open(state_file, "w") as f:
                    json.dump(cp, f)

            yield workspace

    def test_full_workflow(self, workspace_with_checkpoints):
        """Test full workflow of loading and filtering checkpoints."""
        index = CheckpointIndex(workspace_with_checkpoints)

        # Load all
        all_checkpoints = index.get_all_checkpoints()
        assert len(all_checkpoints) == 3

        # Get pending
        pending = index.get_pending_checkpoints()
        assert len(pending) == 1
        assert pending[0].run_id == "run-001"

        # Filter by status
        approved_filter = CheckpointFilter(status_filter=[CheckpointDecisionStatus.APPROVED])
        approved = index.filter_checkpoints(approved_filter)
        assert len(approved) == 1
        assert approved[0].run_id == "run-002"

        # Get metrics
        metrics = index.get_metrics()
        assert metrics.total_checkpoints == 3
        assert metrics.pending_checkpoints == 1
        assert metrics.approved_checkpoints == 1
        assert metrics.rejected_checkpoints == 1

    def test_sorting(self, workspace_with_checkpoints):
        """Test sorting checkpoints."""
        index = CheckpointIndex(workspace_with_checkpoints)

        # Sort by created_at descending (default)
        checkpoints = index.get_all_checkpoints(sort_by="created_at", sort_desc=True)
        assert checkpoints[0].run_id == "run-001"  # Most recent

        # Sort by created_at ascending
        checkpoints = index.get_all_checkpoints(sort_by="created_at", sort_desc=False)
        assert checkpoints[0].run_id == "run-003"  # Oldest

        # Sort by severity - most severe first
        checkpoints = index.get_all_checkpoints(sort_by="severity", sort_desc=False)
        # run-003 has git_destructive (CRITICAL), should be first
        # However, since severities are: CRITICAL, HIGH_RISK x2
        # First should be either CRITICAL or any HIGH_RISK depending on stable sort
        # Check that severities are in correct order: CRITICAL before HIGH_RISK
        severities = [cp.severity for cp in checkpoints]
        # Find position of CRITICAL
        critical_positions = [i for i, s in enumerate(severities) if s == CheckpointSeverity.CRITICAL]
        high_risk_positions = [i for i, s in enumerate(severities) if s == CheckpointSeverity.HIGH_RISK]
        # All CRITICAL should come before all HIGH_RISK
        if critical_positions and high_risk_positions:
            assert max(critical_positions) < min(high_risk_positions)

    def test_limit(self, workspace_with_checkpoints):
        """Test limiting results."""
        index = CheckpointIndex(workspace_with_checkpoints)

        checkpoints = index.get_all_checkpoints(limit=2)
        assert len(checkpoints) == 2
