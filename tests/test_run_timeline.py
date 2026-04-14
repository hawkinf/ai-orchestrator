"""Tests for run timeline models and builder."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from orchestrator.run_timeline import (
    RunTimeline,
    RunTimelineEvent,
    TimelineEventStatus,
    TimelineEventType,
    TimelineEventDetail,
    TimelineBuilder,
    EVENT_EXPLANATIONS,
    EVENT_DISPLAY_NAMES,
)


class TestRunTimelineEvent:
    """Tests for RunTimelineEvent dataclass."""

    def test_event_creates_with_defaults(self):
        event = RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.PENDING,
        )

        assert event.event_type == TimelineEventType.PLANNING
        assert event.status == TimelineEventStatus.PENDING
        assert event.title == "Planejamento"
        assert event.explanation != ""

    def test_event_auto_fills_title_and_explanation(self):
        event = RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.IN_PROGRESS,
        )

        assert event.title == EVENT_DISPLAY_NAMES[TimelineEventType.EXECUTION]
        assert event.explanation == EVENT_EXPLANATIONS[TimelineEventType.EXECUTION]

    def test_event_preserves_custom_title(self):
        event = RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
            title="Custom Title",
        )

        assert event.title == "Custom Title"

    def test_event_to_dict(self):
        timestamp = datetime.now()
        event = RunTimelineEvent(
            event_type=TimelineEventType.VALIDATION,
            status=TimelineEventStatus.COMPLETED,
            timestamp=timestamp,
            duration_seconds=45.5,
            description="All tests passed",
            files_affected=["file1.py", "file2.py"],
            commands_run=["pytest"],
        )

        data = event.to_dict()

        assert data["event_type"] == "validation"
        assert data["status"] == "completed"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["duration_seconds"] == 45.5
        assert data["description"] == "All tests passed"
        assert data["files_affected"] == ["file1.py", "file2.py"]
        assert data["commands_run"] == ["pytest"]

    def test_event_with_details(self):
        detail = TimelineEventDetail(
            label="Output",
            content="Test output content",
            detail_type="logs"
        )
        event = RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
            details=[detail],
        )

        data = event.to_dict()

        assert len(data["details"]) == 1
        assert data["details"][0]["label"] == "Output"
        assert data["details"][0]["content"] == "Test output content"
        assert data["details"][0]["detail_type"] == "logs"

    def test_checkpoint_event_fields(self):
        event = RunTimelineEvent(
            event_type=TimelineEventType.CHECKPOINT,
            status=TimelineEventStatus.IN_PROGRESS,
            checkpoint_reason="destructive_operation",
            checkpoint_resolved=False,
        )

        assert event.checkpoint_reason == "destructive_operation"
        assert event.checkpoint_resolved is False


class TestRunTimeline:
    """Tests for RunTimeline dataclass."""

    def test_timeline_creates_empty(self):
        timeline = RunTimeline(run_id="test-run-123")

        assert timeline.run_id == "test-run-123"
        assert timeline.events == []
        assert timeline.is_complete is False
        assert timeline.has_errors is False

    def test_timeline_add_event(self):
        timeline = RunTimeline(run_id="test-run")
        event = RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        )

        timeline.add_event(event)

        assert len(timeline.events) == 1
        assert timeline.events[0] == event

    def test_timeline_tracks_errors(self):
        timeline = RunTimeline(run_id="test-run")
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.FAILED,
        ))

        assert timeline.has_errors is True

    def test_timeline_get_current_event(self):
        timeline = RunTimeline(run_id="test-run")
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.IN_PROGRESS,
        ))

        current = timeline.get_current_event()

        assert current is not None
        assert current.event_type == TimelineEventType.EXECUTION

    def test_timeline_get_current_event_none(self):
        timeline = RunTimeline(run_id="test-run")
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))

        assert timeline.get_current_event() is None

    def test_timeline_to_dict(self):
        timeline = RunTimeline(
            run_id="test-run",
            current_stage="executing",
            is_complete=False,
            total_duration_seconds=120.5,
            created_at=datetime.now(),
        )
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))

        data = timeline.to_dict()

        assert data["run_id"] == "test-run"
        assert data["current_stage"] == "executing"
        assert data["is_complete"] is False
        assert data["total_duration_seconds"] == 120.5
        assert len(data["events"]) == 1


class TestTimelineBuilder:
    """Tests for TimelineBuilder."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a workspace with state directory."""
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        return tmp_path

    def test_builder_returns_none_for_missing_run(self, workspace):
        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline("nonexistent-run")

        assert timeline is None

    def test_builder_parses_pending_run(self, workspace):
        run_id = "test-pending-run"
        state_data = {
            "run_id": run_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "task": {
                "description": "Test task",
                "profile": "python"
            }
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        assert timeline is not None
        assert timeline.run_id == run_id
        assert timeline.is_complete is False
        assert len(timeline.events) >= 1
        assert timeline.events[0].event_type == TimelineEventType.PLANNING
        assert timeline.events[0].status == TimelineEventStatus.PENDING

    def test_builder_parses_planning_run(self, workspace):
        run_id = "test-planning-run"
        state_data = {
            "run_id": run_id,
            "status": "planning",
            "created_at": datetime.now().isoformat(),
            "task": {"description": "Test task"}
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        assert timeline.events[0].status == TimelineEventStatus.IN_PROGRESS

    def test_builder_parses_completed_plan(self, workspace):
        run_id = "test-with-plan"
        state_data = {
            "run_id": run_id,
            "status": "executing",
            "created_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {
                "objective": "Test objective",
                "scope": "Test scope",
                "files_likely_affected": ["file1.py", "file2.py"],
                "risks": ["Risk 1", "Risk 2"],
                "constraints": ["Constraint 1"]
            }
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        planning_event = timeline.events[0]
        assert planning_event.status == TimelineEventStatus.COMPLETED
        assert "Test objective" in planning_event.description
        assert len(planning_event.details) > 0
        assert planning_event.files_affected == ["file1.py", "file2.py"]

    def test_builder_parses_iterations(self, workspace):
        run_id = "test-with-iterations"
        state_data = {
            "run_id": run_id,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"},
            "iterations": [
                {
                    "iteration_number": 1,
                    "started_at": datetime.now().isoformat(),
                    "execution_result": {
                        "success": True,
                        "duration_seconds": 30.5,
                        "files_changed": ["file1.py"],
                        "commands_run": ["pytest"]
                    },
                    "execution_report": {
                        "summary": "Made changes successfully",
                        "files_changed": ["file1.py"],
                        "tests_run": ["test_main"],
                        "tests_passed": 5,
                        "tests_failed": 0
                    },
                    "review_response": {
                        "status": "approved",
                        "findings": ["Code looks good"],
                        "suggestions": ["Consider adding type hints"]
                    },
                    "validation_summary": {
                        "all_passed": True,
                        "results": [
                            {"command": "pytest", "success": True}
                        ]
                    }
                }
            ]
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        # Should have: planning, execution, review, validation, finalization
        event_types = [e.event_type for e in timeline.events]
        assert TimelineEventType.PLANNING in event_types
        assert TimelineEventType.EXECUTION in event_types
        assert TimelineEventType.REVIEW in event_types
        assert TimelineEventType.VALIDATION in event_types
        assert TimelineEventType.FINALIZATION in event_types

    def test_builder_parses_checkpoint(self, workspace):
        run_id = "test-with-checkpoint"
        state_data = {
            "run_id": run_id,
            "status": "checkpoint",
            "created_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"},
            "checkpoint": {
                "reason": "destructive_operation",
                "description": "About to delete files",
                "resolved": False,
                "created_at": datetime.now().isoformat()
            }
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        checkpoint_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.CHECKPOINT
        ]
        assert len(checkpoint_events) == 1
        assert checkpoint_events[0].status == TimelineEventStatus.IN_PROGRESS
        assert checkpoint_events[0].checkpoint_reason == "destructive_operation"

    def test_builder_parses_git_result(self, workspace):
        run_id = "test-with-git"
        state_data = {
            "run_id": run_id,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"},
            "git_result_final": {
                "operation": "commit",
                "success": True,
                "commit_hash": "abc123def456",
                "message": "Fix: resolved issue"
            }
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        git_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.GIT
        ]
        assert len(git_events) == 1
        assert git_events[0].status == TimelineEventStatus.COMPLETED
        assert "abc123de" in git_events[0].description

    def test_builder_parses_failed_run(self, workspace):
        run_id = "test-failed"
        state_data = {
            "run_id": run_id,
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"},
            "error_message": "Something went wrong"
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        assert timeline.is_complete is True
        assert timeline.has_errors is True

        finalization = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.FINALIZATION
        ][0]
        assert finalization.status == TimelineEventStatus.FAILED
        assert "Something went wrong" in finalization.errors

    def test_builder_calculates_duration(self, workspace):
        run_id = "test-duration"
        created = datetime.now() - timedelta(minutes=5)
        completed = datetime.now()

        state_data = {
            "run_id": run_id,
            "status": "completed",
            "created_at": created.isoformat(),
            "completed_at": completed.isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"}
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        # Should be approximately 300 seconds (5 minutes)
        assert 290 < timeline.total_duration_seconds < 310

    def test_builder_handles_corrupted_json(self, workspace):
        run_id = "test-corrupted"
        (workspace / "state" / f"{run_id}.json").write_text(
            "{ invalid json", encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        assert timeline is None

    def test_builder_handles_multiple_iterations(self, workspace):
        run_id = "test-multi-iter"
        state_data = {
            "run_id": run_id,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "task": {"description": "Test task"},
            "plan": {"objective": "Test"},
            "iterations": [
                {
                    "iteration_number": 1,
                    "execution_report": {"summary": "First attempt"},
                    "review_response": {"status": "needs_followup"}
                },
                {
                    "iteration_number": 2,
                    "execution_report": {"summary": "Second attempt"},
                    "review_response": {"status": "approved"}
                }
            ]
        }

        (workspace / "state" / f"{run_id}.json").write_text(
            json.dumps(state_data), encoding="utf-8"
        )

        builder = TimelineBuilder(workspace)
        timeline = builder.build_timeline(run_id)

        # Should have iteration start event for iteration 2
        iter_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.ITERATION_START
        ]
        assert len(iter_events) == 1
        assert iter_events[0].iteration_number == 2


class TestTimelineEventDetail:
    """Tests for TimelineEventDetail."""

    def test_detail_creates_with_defaults(self):
        detail = TimelineEventDetail(
            label="Test Label",
            content="Test content"
        )

        assert detail.label == "Test Label"
        assert detail.content == "Test content"
        assert detail.detail_type == "text"

    def test_detail_with_custom_type(self):
        detail = TimelineEventDetail(
            label="Logs",
            content="log output",
            detail_type="logs"
        )

        assert detail.detail_type == "logs"


class TestEventConstants:
    """Tests for event display names and explanations."""

    def test_all_event_types_have_display_names(self):
        for event_type in TimelineEventType:
            assert event_type in EVENT_DISPLAY_NAMES
            assert len(EVENT_DISPLAY_NAMES[event_type]) > 0

    def test_all_event_types_have_explanations(self):
        for event_type in TimelineEventType:
            assert event_type in EVENT_EXPLANATIONS
            assert len(EVENT_EXPLANATIONS[event_type]) > 0

    def test_display_names_are_in_portuguese(self):
        # Check a few known translations
        assert EVENT_DISPLAY_NAMES[TimelineEventType.PLANNING] == "Planejamento"
        assert EVENT_DISPLAY_NAMES[TimelineEventType.EXECUTION] == "Execução"
        assert EVENT_DISPLAY_NAMES[TimelineEventType.REVIEW] == "Revisão"
        assert EVENT_DISPLAY_NAMES[TimelineEventType.VALIDATION] == "Validação"
