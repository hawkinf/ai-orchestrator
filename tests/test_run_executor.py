"""Tests for gui/run_executor module."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from gui.run_executor import (
    RunPhase,
    RunProgressEvent,
    RunExecutorSignals,
    RunExecutor,
)


class TestRunPhase:
    """Test RunPhase enum."""

    def test_all_phases_exist(self):
        """Test all expected phases exist."""
        phases = [
            RunPhase.INITIALIZING,
            RunPhase.PLANNING,
            RunPhase.EXECUTING,
            RunPhase.REVIEWING,
            RunPhase.VALIDATING,
            RunPhase.COMMITTING,
            RunPhase.PUSHING,
            RunPhase.FINALIZING,
            RunPhase.COMPLETED,
            RunPhase.FAILED,
            RunPhase.CHECKPOINT,
        ]
        assert len(phases) == 11

    def test_phase_values(self):
        """Test phase values are strings."""
        assert RunPhase.INITIALIZING.value == "initializing"
        assert RunPhase.COMPLETED.value == "completed"
        assert RunPhase.FAILED.value == "failed"


class TestRunProgressEvent:
    """Test RunProgressEvent dataclass."""

    def test_create_basic_event(self):
        """Test creating a basic progress event."""
        event = RunProgressEvent(
            run_id="test-run-123",
            phase=RunPhase.PLANNING,
            message="Planning started",
        )

        assert event.run_id == "test-run-123"
        assert event.phase == RunPhase.PLANNING
        assert event.message == "Planning started"
        assert event.iteration == 0
        assert event.max_iterations == 3
        assert event.is_error is False

    def test_create_event_with_all_fields(self):
        """Test creating event with all fields."""
        event = RunProgressEvent(
            run_id="run-456",
            phase=RunPhase.EXECUTING,
            message="Executing iteration 2",
            iteration=2,
            max_iterations=5,
            details={"files": ["a.py", "b.py"]},
            is_error=False,
            checkpoint_reason="review_required",
        )

        assert event.iteration == 2
        assert event.max_iterations == 5
        assert event.details == {"files": ["a.py", "b.py"]}
        assert event.checkpoint_reason == "review_required"

    def test_timestamp_auto_set(self):
        """Test timestamp is auto-set when not provided."""
        event = RunProgressEvent(
            run_id="test",
            phase=RunPhase.INITIALIZING,
            message="Test",
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        event = RunProgressEvent(
            run_id="run-789",
            phase=RunPhase.COMPLETED,
            message="Done",
            iteration=3,
            max_iterations=3,
        )

        d = event.to_dict()

        assert d["run_id"] == "run-789"
        assert d["phase"] == "completed"
        assert d["message"] == "Done"
        assert d["iteration"] == 3
        assert d["max_iterations"] == 3
        assert d["is_error"] is False
        assert "timestamp" in d


class TestRunExecutorSignals:
    """Test RunExecutorSignals."""

    def test_signals_exist(self):
        """Test all expected signals exist."""
        signals = RunExecutorSignals()

        # Verify signals exist
        assert hasattr(signals, "run_started")
        assert hasattr(signals, "progress")
        assert hasattr(signals, "phase_changed")
        assert hasattr(signals, "iteration_changed")
        assert hasattr(signals, "checkpoint_pending")
        assert hasattr(signals, "run_completed")
        assert hasattr(signals, "run_failed")
        assert hasattr(signals, "status_changed")


class TestRunExecutor:
    """Test RunExecutor class."""

    def test_init(self):
        """Test RunExecutor initialization."""
        executor = RunExecutor(
            project_path=Path("/test/project"),
            config_path=Path("/test/config.yaml"),
            mock_executor=True,
        )

        assert executor.project_path == Path("/test/project")
        assert executor.config_path == Path("/test/config.yaml")
        assert executor.mock_executor is True
        assert executor.signals is not None

    def test_init_default_values(self):
        """Test RunExecutor with default values."""
        executor = RunExecutor()

        assert executor.project_path == Path.cwd()
        assert executor.config_path is None
        assert executor.mock_executor is False

    def test_cancel(self):
        """Test cancel method."""
        executor = RunExecutor()

        assert executor._cancelled is False
        executor.cancel()
        assert executor._cancelled is True

    @patch("orchestrator.integrated_engine.IntegratedTaskEngine")
    @patch("orchestrator.state_store.StateStore")
    @patch("orchestrator.config.load_config")
    @patch("orchestrator.paths.OrchestratorPaths")
    def test_init_engine(
        self,
        mock_paths_class,
        mock_load_config,
        mock_store_class,
        mock_engine_class
    ):
        """Test lazy engine initialization."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_paths = MagicMock()
        mock_paths_class.return_value = mock_paths

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        # Create executor and init engine
        executor = RunExecutor(project_path=Path("/test"))
        executor._init_engine()

        # Verify engine was created
        assert executor._engine is not None
        mock_engine_class.assert_called_once()

    @patch("orchestrator.integrated_engine.IntegratedTaskEngine")
    @patch("orchestrator.state_store.StateStore")
    @patch("orchestrator.config.load_config")
    @patch("orchestrator.paths.OrchestratorPaths")
    def test_engine_only_initialized_once(
        self,
        mock_paths_class,
        mock_load_config,
        mock_store_class,
        mock_engine_class
    ):
        """Test engine is only initialized once."""
        executor = RunExecutor(project_path=Path("/test"))

        # Init twice
        executor._init_engine()
        executor._init_engine()

        # Should only be called once
        assert mock_engine_class.call_count == 1


class TestRunExecutorProgress:
    """Test RunExecutor progress emission."""

    def test_emit_progress(self):
        """Test _emit_progress creates and emits event."""
        executor = RunExecutor()

        # Track emitted events
        emitted = []
        executor.signals.progress.connect(lambda e: emitted.append(e))

        # Emit progress
        executor._emit_progress(
            run_id="test-run",
            phase=RunPhase.PLANNING,
            message="Planning...",
            iteration=1,
            max_iterations=3,
        )

        # Verify
        assert len(emitted) == 1
        event = emitted[0]
        assert event.run_id == "test-run"
        assert event.phase == RunPhase.PLANNING
        assert event.message == "Planning..."

    def test_emit_progress_with_error(self):
        """Test emitting error progress."""
        executor = RunExecutor()

        emitted = []
        executor.signals.progress.connect(lambda e: emitted.append(e))

        executor._emit_progress(
            run_id="test-run",
            phase=RunPhase.FAILED,
            message="Something went wrong",
            is_error=True,
        )

        assert emitted[0].is_error is True

    def test_emit_progress_with_checkpoint(self):
        """Test emitting checkpoint progress."""
        executor = RunExecutor()

        emitted = []
        executor.signals.progress.connect(lambda e: emitted.append(e))

        executor._emit_progress(
            run_id="test-run",
            phase=RunPhase.CHECKPOINT,
            message="Checkpoint needed",
            checkpoint_reason="destructive_operation",
        )

        assert emitted[0].checkpoint_reason == "destructive_operation"


class TestRunExecutorBuildSummary:
    """Test RunExecutor._build_summary method."""

    def test_build_basic_summary(self):
        """Test building a basic summary."""
        executor = RunExecutor()

        # Create mock state
        mock_state = MagicMock()
        mock_state.run_id = "test-run-123"
        mock_state.status.value = "completed"
        mock_state.current_iteration = 2
        mock_state.task.description = "Test task description"
        mock_state.plan = None
        mock_state.git_result_final = None
        mock_state.validation_final = None

        summary = executor._build_summary(mock_state)

        assert summary["run_id"] == "test-run-123"
        assert summary["status"] == "completed"
        assert summary["iterations"] == 2
        assert "Test task" in summary["task"]

    def test_build_summary_with_plan(self):
        """Test building summary with plan."""
        executor = RunExecutor()

        mock_state = MagicMock()
        mock_state.run_id = "run-456"
        mock_state.status.value = "completed"
        mock_state.current_iteration = 1
        mock_state.task.description = "Task"
        mock_state.plan.objective = "Fix the bug"
        mock_state.git_result_final = None
        mock_state.validation_final = None

        summary = executor._build_summary(mock_state)

        assert summary["objective"] == "Fix the bug"

    def test_build_summary_with_git(self):
        """Test building summary with git result."""
        executor = RunExecutor()

        mock_state = MagicMock()
        mock_state.run_id = "run-789"
        mock_state.status.value = "completed"
        mock_state.current_iteration = 3
        mock_state.task.description = "Task"
        mock_state.plan = None
        mock_state.git_result_final.commit_hash = "abc123def"
        mock_state.validation_final = None

        summary = executor._build_summary(mock_state)

        assert summary["commit_hash"] == "abc123def"

    def test_build_summary_with_validation(self):
        """Test building summary with validation result."""
        executor = RunExecutor()

        mock_state = MagicMock()
        mock_state.run_id = "run-101"
        mock_state.status.value = "completed"
        mock_state.current_iteration = 1
        mock_state.task.description = "Task"
        mock_state.plan = None
        mock_state.git_result_final = None
        mock_state.validation_final.all_passed = True

        summary = executor._build_summary(mock_state)

        assert summary["validation_passed"] is True
