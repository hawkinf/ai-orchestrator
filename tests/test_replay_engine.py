"""Tests for the replay engine module."""

import pytest
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from orchestrator.replay_models import (
    ReplayMode,
    ReplayStage,
    ReplayStatus,
    ReplayConfig,
    ReplayResult,
    ReplayListItem,
    ReplayComparison,
    ComparisonResult,
    StageMetrics,
    StageComparison,
    FileDiff,
    CheckpointComparison,
)
from orchestrator.replay_engine import ReplayEngine
from orchestrator.models import (
    RunState,
    TaskStatus,
    TaskRequest,
    PlanResponse,
    IterationState,
    ExecutionReport,
    ReviewResponse,
    ReviewStatus,
    ValidationResult,
    ValidationSummary,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "state").mkdir()
    (workspace / "runs").mkdir()
    (workspace / "replays").mkdir()
    return workspace


@pytest.fixture
def replay_engine(temp_workspace):
    """Create a replay engine with temporary workspace."""
    return ReplayEngine(temp_workspace)


@pytest.fixture
def sample_run_state():
    """Create a sample run state for testing."""
    run_id = f"run-{uuid4().hex[:8]}"
    return RunState(
        run_id=run_id,
        status=TaskStatus.COMPLETED,
        task=TaskRequest(
            description="Test task description",
            profile="python",
        ),
        plan=PlanResponse(
            objective="Test objective",
            scope="Test scope",
            execution_prompt="Execute the test task",
            risks=["Risk 1"],
        ),
        iterations=[
            IterationState(
                iteration_number=1,
                execution_report=ExecutionReport(
                    summary="Execution completed successfully",
                    files_changed=["file1.py", "file2.py"],
                    risks=["Minor risk"],
                ),
                review_response=ReviewResponse(
                    status=ReviewStatus.APPROVED,
                    findings=["All good"],
                ),
            )
        ],
        validation_final=ValidationSummary(
            all_passed=True,
            results=[
                ValidationResult(command="pytest", success=True, stdout="OK"),
            ],
        ),
        created_at=datetime.now(),
        completed_at=datetime.now(),
        current_iteration=1,
    )


@pytest.fixture
def workspace_with_run(temp_workspace, sample_run_state):
    """Create workspace with a saved run state."""
    state_file = temp_workspace / "state" / f"{sample_run_state.run_id}.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(sample_run_state.model_dump(mode="json"), f, default=str)
    return temp_workspace, sample_run_state


# =============================================================================
# ReplayConfig Tests
# =============================================================================


class TestReplayConfig:
    def test_default_config(self):
        config = ReplayConfig()
        assert config.mode == ReplayMode.DRY_RUN
        assert ReplayStage.ALL in config.stages
        assert config.use_sandbox is False
        assert config.mock_executor is True
        assert config.auto_approve_checkpoints is True

    def test_to_dict(self):
        config = ReplayConfig(
            mode=ReplayMode.PARTIAL,
            stages=[ReplayStage.PLANNING, ReplayStage.EXECUTION],
            use_sandbox=True,
            timeout_seconds=300,
        )
        d = config.to_dict()
        assert d["mode"] == "partial"
        assert "planning" in d["stages"]
        assert d["use_sandbox"] is True
        assert d["timeout_seconds"] == 300

    def test_from_dict(self):
        data = {
            "mode": "full",
            "stages": ["planning", "review"],
            "use_sandbox": True,
            "mock_executor": False,
        }
        config = ReplayConfig.from_dict(data)
        assert config.mode == ReplayMode.FULL
        assert ReplayStage.PLANNING in config.stages
        assert config.use_sandbox is True
        assert config.mock_executor is False


# =============================================================================
# ReplayMode Tests
# =============================================================================


class TestReplayMode:
    def test_modes_exist(self):
        assert ReplayMode.DRY_RUN.value == "dry_run"
        assert ReplayMode.PARTIAL.value == "partial"
        assert ReplayMode.FULL.value == "full"


# =============================================================================
# ReplayStage Tests
# =============================================================================


class TestReplayStage:
    def test_stages_exist(self):
        assert ReplayStage.PLANNING.value == "planning"
        assert ReplayStage.EXECUTION.value == "execution"
        assert ReplayStage.REVIEW.value == "review"
        assert ReplayStage.VALIDATION.value == "validation"
        assert ReplayStage.COMMIT.value == "commit"
        assert ReplayStage.ALL.value == "all"


# =============================================================================
# StageMetrics Tests
# =============================================================================


class TestStageMetrics:
    def test_to_dict(self):
        metrics = StageMetrics(
            stage=ReplayStage.EXECUTION,
            started_at=datetime.now(),
            duration_seconds=10.5,
            success=True,
            files_affected=5,
        )
        d = metrics.to_dict()
        assert d["stage"] == "execution"
        assert d["duration_seconds"] == 10.5
        assert d["success"] is True
        assert d["files_affected"] == 5

    def test_from_dict(self):
        data = {
            "stage": "planning",
            "duration_seconds": 5.0,
            "success": True,
            "output_summary": "Plan created",
        }
        metrics = StageMetrics.from_dict(data)
        assert metrics.stage == ReplayStage.PLANNING
        assert metrics.duration_seconds == 5.0
        assert metrics.output_summary == "Plan created"


# =============================================================================
# FileDiff Tests
# =============================================================================


class TestFileDiff:
    def test_to_dict(self):
        diff = FileDiff(
            file_path="src/main.py",
            comparison=ComparisonResult.DIFFERENT,
            lines_added=10,
            lines_removed=5,
        )
        d = diff.to_dict()
        assert d["file_path"] == "src/main.py"
        assert d["comparison"] == "different"
        assert d["lines_added"] == 10

    def test_from_dict(self):
        data = {
            "file_path": "test.py",
            "comparison": "identical",
            "lines_changed": 0,
        }
        diff = FileDiff.from_dict(data)
        assert diff.file_path == "test.py"
        assert diff.comparison == ComparisonResult.IDENTICAL


# =============================================================================
# CheckpointComparison Tests
# =============================================================================


class TestCheckpointComparison:
    def test_to_dict(self):
        comp = CheckpointComparison(
            checkpoint_id="cp-123",
            checkpoint_type="manual_request",
            original_decision="approved",
            replay_decision="auto_approved",
            comparison=ComparisonResult.IDENTICAL,
        )
        d = comp.to_dict()
        assert d["checkpoint_id"] == "cp-123"
        assert d["original_decision"] == "approved"
        assert d["comparison"] == "identical"

    def test_from_dict(self):
        data = {
            "checkpoint_id": "cp-456",
            "checkpoint_type": "git_destructive",
            "original_decision": "rejected",
            "replay_decision": "rejected",
            "comparison": "identical",
        }
        comp = CheckpointComparison.from_dict(data)
        assert comp.checkpoint_id == "cp-456"
        assert comp.comparison == ComparisonResult.IDENTICAL


# =============================================================================
# ReplayResult Tests
# =============================================================================


class TestReplayResult:
    def test_auto_generate_id(self):
        result = ReplayResult(
            replay_id="",
            original_run_id="run-123",
            config=ReplayConfig(),
        )
        assert result.replay_id.startswith("replay-")

    def test_to_dict(self):
        result = ReplayResult(
            replay_id="replay-test",
            original_run_id="run-123",
            config=ReplayConfig(),
            status=ReplayStatus.COMPLETED,
            success=True,
            duration_seconds=15.5,
        )
        d = result.to_dict()
        assert d["replay_id"] == "replay-test"
        assert d["status"] == "completed"
        assert d["success"] is True
        assert d["duration_seconds"] == 15.5

    def test_from_dict(self):
        data = {
            "replay_id": "replay-abc",
            "original_run_id": "run-xyz",
            "config": {"mode": "dry_run"},
            "status": "completed",
            "success": True,
        }
        result = ReplayResult.from_dict(data)
        assert result.replay_id == "replay-abc"
        assert result.status == ReplayStatus.COMPLETED


# =============================================================================
# ReplayListItem Tests
# =============================================================================


class TestReplayListItem:
    def test_to_dict(self):
        item = ReplayListItem(
            replay_id="replay-001",
            original_run_id="run-001",
            mode=ReplayMode.DRY_RUN,
            status=ReplayStatus.COMPLETED,
            created_at=datetime.now(),
            duration_seconds=10.0,
            success=True,
            comparison_result=ComparisonResult.IDENTICAL,
        )
        d = item.to_dict()
        assert d["replay_id"] == "replay-001"
        assert d["mode"] == "dry_run"
        assert d["comparison_result"] == "identical"


# =============================================================================
# ReplayEngine Tests
# =============================================================================


class TestReplayEngine:
    def test_init(self, replay_engine, temp_workspace):
        assert replay_engine.workspace_path == temp_workspace
        assert replay_engine.replays_dir.exists()

    def test_replay_run_not_found(self, replay_engine):
        result = replay_engine.replay("nonexistent-run")
        assert result.status == ReplayStatus.FAILED
        assert "not found" in result.error.lower()

    def test_replay_dry_run(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        config = ReplayConfig(mode=ReplayMode.DRY_RUN)
        result = engine.replay(run_state.run_id, config)

        assert result.status == ReplayStatus.COMPLETED
        assert result.success is True
        assert len(result.stage_metrics) > 0
        assert result.comparison is not None

    def test_replay_partial(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        config = ReplayConfig(
            mode=ReplayMode.PARTIAL,
            stages=[ReplayStage.PLANNING, ReplayStage.REVIEW],
        )
        result = engine.replay(run_state.run_id, config)

        assert result.status == ReplayStatus.COMPLETED
        assert result.success is True

    def test_replay_creates_artifacts(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        result = engine.replay(run_state.run_id)

        assert result.replay_dir is not None
        assert result.replay_dir.exists()
        assert result.report_path is not None
        assert result.report_path.exists()
        assert result.metrics_path is not None

    def test_replay_comparison_generated(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        result = engine.replay(run_state.run_id)

        assert result.comparison is not None
        assert result.comparison.original_run_id == run_state.run_id
        assert result.comparison.replay_id == result.replay_id
        assert result.comparison.overall_result in ComparisonResult

    def test_list_replays(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        # Create a replay
        engine.replay(run_state.run_id)

        # List replays
        replays = engine.list_replays()
        assert len(replays) >= 1
        assert replays[0].original_run_id == run_state.run_id

    def test_get_replay(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        # Create a replay
        result = engine.replay(run_state.run_id)

        # Get the replay
        loaded = engine.get_replay(result.replay_id)
        assert loaded is not None
        assert loaded.replay_id == result.replay_id

    def test_delete_replay(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        # Create a replay
        result = engine.replay(run_state.run_id)

        # Delete it
        deleted = engine.delete_replay(result.replay_id)
        assert deleted is True

        # Verify it's gone
        loaded = engine.get_replay(result.replay_id)
        assert loaded is None

    def test_cancel_replay(self, replay_engine):
        # Cancel before starting
        replay_engine.cancel()
        assert replay_engine._cancel_requested is True


# =============================================================================
# Stage Simulation Tests
# =============================================================================


class TestStageSimulation:
    def test_simulate_planning(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        metrics = engine._simulate_stage(ReplayStage.PLANNING, run_state)
        assert metrics.stage == ReplayStage.PLANNING
        assert metrics.success is True
        assert "Objective" in metrics.output_summary

    def test_simulate_execution(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        metrics = engine._simulate_stage(ReplayStage.EXECUTION, run_state)
        assert metrics.stage == ReplayStage.EXECUTION
        assert metrics.success is True
        assert metrics.files_affected == 2  # file1.py, file2.py

    def test_simulate_review(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        metrics = engine._simulate_stage(ReplayStage.REVIEW, run_state)
        assert metrics.stage == ReplayStage.REVIEW
        assert metrics.success is True
        assert "approved" in metrics.output_summary.lower()

    def test_simulate_validation(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        metrics = engine._simulate_stage(ReplayStage.VALIDATION, run_state)
        assert metrics.stage == ReplayStage.VALIDATION
        assert metrics.success is True
        assert "passed" in metrics.output_summary.lower()


# =============================================================================
# Comparison Generation Tests
# =============================================================================


class TestComparisonGeneration:
    def test_compare_stages(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        result = ReplayResult(
            replay_id="test-replay",
            original_run_id=run_state.run_id,
            config=ReplayConfig(),
        )

        # Simulate stages
        result.stage_metrics = [
            engine._simulate_stage(ReplayStage.PLANNING, run_state),
            engine._simulate_stage(ReplayStage.EXECUTION, run_state),
        ]

        # Generate comparison
        comparison = engine._generate_comparison(run_state, result)

        assert len(comparison.stage_comparisons) >= 2

    def test_time_comparison(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        result = engine.replay(run_state.run_id)

        if result.comparison:
            # Original time should be calculated
            assert result.comparison.replay_total_time >= 0


# =============================================================================
# Sandbox Tests
# =============================================================================


class TestSandbox:
    def test_setup_sandbox(self, replay_engine, sample_run_state):
        config = ReplayConfig(use_sandbox=True)
        sandbox = replay_engine._setup_sandbox(config, sample_run_state)

        assert sandbox.exists()
        assert (sandbox / "project").exists()
        assert (sandbox / "workspace").exists()

        # Cleanup
        replay_engine._cleanup_sandbox(sandbox)
        assert not sandbox.exists()

    def test_custom_sandbox_path(self, replay_engine, sample_run_state, tmp_path):
        custom_path = tmp_path / "custom_sandbox"
        config = ReplayConfig(use_sandbox=True, sandbox_path=custom_path)

        sandbox = replay_engine._setup_sandbox(config, sample_run_state)
        assert sandbox == custom_path

        # Cleanup
        replay_engine._cleanup_sandbox(sandbox)


# =============================================================================
# Progress Callback Tests
# =============================================================================


class TestProgressCallback:
    def test_progress_callback_called(self, workspace_with_run):
        workspace, run_state = workspace_with_run
        engine = ReplayEngine(workspace)

        progress_messages = []

        def callback(message, percent):
            progress_messages.append((message, percent))

        engine.replay(run_state.run_id, progress_callback=callback)

        assert len(progress_messages) > 0
        # Should end at 100%
        assert progress_messages[-1][1] == 1.0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    def test_replay_with_no_plan(self, temp_workspace):
        # Create a minimal run without plan
        run_id = "run-no-plan"
        state = RunState(
            run_id=run_id,
            status=TaskStatus.COMPLETED,
            task=TaskRequest(description="Test"),
            plan=None,
            iterations=[],
        )

        state_file = temp_workspace / "state" / f"{run_id}.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, default=str)

        engine = ReplayEngine(temp_workspace)
        result = engine.replay(run_id)

        # Should still complete
        assert result.status == ReplayStatus.COMPLETED

    def test_replay_with_no_iterations(self, temp_workspace):
        run_id = "run-no-iter"
        state = RunState(
            run_id=run_id,
            status=TaskStatus.COMPLETED,
            task=TaskRequest(description="Test"),
            iterations=[],
        )

        state_file = temp_workspace / "state" / f"{run_id}.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, default=str)

        engine = ReplayEngine(temp_workspace)
        result = engine.replay(run_id)

        assert result.status == ReplayStatus.COMPLETED

    def test_delete_nonexistent_replay(self, replay_engine):
        deleted = replay_engine.delete_replay("nonexistent-replay")
        assert deleted is False
