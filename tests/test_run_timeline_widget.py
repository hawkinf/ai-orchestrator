"""Tests for run timeline widget."""

import json
import pytest
from datetime import datetime
from pathlib import Path

pytest.importorskip("PySide6")


def test_timeline_widget_creates(qapp):
    from gui.run_timeline_widget import RunTimelineWidget

    widget = RunTimelineWidget()
    widget.show()
    qapp.processEvents()

    assert widget.title_label.text() == "Timeline da Run"


def test_timeline_widget_with_workspace(qapp, tmp_path):
    from gui.run_timeline_widget import RunTimelineWidget

    widget = RunTimelineWidget(workspace_path=tmp_path)
    widget.show()
    qapp.processEvents()

    assert widget.workspace_path == tmp_path


def test_timeline_widget_set_workspace(qapp, tmp_path):
    from gui.run_timeline_widget import RunTimelineWidget

    widget = RunTimelineWidget()
    widget.set_workspace(tmp_path)

    assert widget.workspace_path == tmp_path


def test_timeline_widget_load_timeline(qapp, tmp_path):
    from gui.run_timeline_widget import RunTimelineWidget

    # Create test state
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    run_id = "test-run-123"
    state_data = {
        "run_id": run_id,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "task": {"description": "Test task"},
        "plan": {"objective": "Test objective"}
    }
    (state_dir / f"{run_id}.json").write_text(
        json.dumps(state_data), encoding="utf-8"
    )

    widget = RunTimelineWidget(workspace_path=tmp_path)
    widget.show()
    widget.load_timeline(run_id)
    qapp.processEvents()

    assert widget._timeline is not None
    assert widget._timeline.run_id == run_id


def test_timeline_widget_clear(qapp, tmp_path):
    from gui.run_timeline_widget import RunTimelineWidget
    from orchestrator.run_timeline import RunTimeline, RunTimelineEvent, TimelineEventType, TimelineEventStatus

    widget = RunTimelineWidget(workspace_path=tmp_path)
    widget.show()

    # Set a timeline
    timeline = RunTimeline(run_id="test")
    timeline.add_event(RunTimelineEvent(
        event_type=TimelineEventType.PLANNING,
        status=TimelineEventStatus.COMPLETED
    ))
    widget.set_timeline(timeline)
    qapp.processEvents()

    # Clear it
    widget.clear_timeline()
    qapp.processEvents()

    assert widget._timeline is None


def test_timeline_widget_set_timeline(qapp):
    from gui.run_timeline_widget import RunTimelineWidget
    from orchestrator.run_timeline import RunTimeline, RunTimelineEvent, TimelineEventType, TimelineEventStatus

    widget = RunTimelineWidget()
    widget.show()

    timeline = RunTimeline(run_id="test-run")
    timeline.add_event(RunTimelineEvent(
        event_type=TimelineEventType.PLANNING,
        status=TimelineEventStatus.COMPLETED
    ))
    timeline.add_event(RunTimelineEvent(
        event_type=TimelineEventType.EXECUTION,
        status=TimelineEventStatus.IN_PROGRESS
    ))

    widget.set_timeline(timeline)
    qapp.processEvents()

    assert widget._timeline == timeline
    # Should show timeline header with run_id
    assert "test-run" in widget.title_label.text()


def test_timeline_widget_shows_complete_status(qapp):
    from gui.run_timeline_widget import RunTimelineWidget
    from orchestrator.run_timeline import RunTimeline, RunTimelineEvent, TimelineEventType, TimelineEventStatus

    widget = RunTimelineWidget()
    widget.show()

    timeline = RunTimeline(run_id="test-run", is_complete=True)
    timeline.add_event(RunTimelineEvent(
        event_type=TimelineEventType.FINALIZATION,
        status=TimelineEventStatus.COMPLETED
    ))

    widget.set_timeline(timeline)
    qapp.processEvents()

    assert "sucesso" in widget.status_label.text().lower()


def test_timeline_widget_shows_error_status(qapp):
    from gui.run_timeline_widget import RunTimelineWidget
    from orchestrator.run_timeline import RunTimeline, RunTimelineEvent, TimelineEventType, TimelineEventStatus

    widget = RunTimelineWidget()
    widget.show()

    timeline = RunTimeline(run_id="test-run", is_complete=True, has_errors=True)
    timeline.add_event(RunTimelineEvent(
        event_type=TimelineEventType.FINALIZATION,
        status=TimelineEventStatus.FAILED
    ))

    widget.set_timeline(timeline)
    qapp.processEvents()

    assert "erro" in widget.status_label.text().lower()


def test_timeline_event_widget_creates(qapp):
    from gui.run_timeline_widget import TimelineEventWidget
    from orchestrator.run_timeline import RunTimelineEvent, TimelineEventType, TimelineEventStatus

    event = RunTimelineEvent(
        event_type=TimelineEventType.PLANNING,
        status=TimelineEventStatus.COMPLETED,
        description="Planning completed",
    )

    widget = TimelineEventWidget(event)
    widget.show()
    qapp.processEvents()

    # Should display the event
    assert widget.timeline_event == event


def test_timeline_event_widget_shows_status_color(qapp):
    from gui.run_timeline_widget import TimelineEventWidget, STATUS_COLORS
    from orchestrator.run_timeline import RunTimelineEvent, TimelineEventType, TimelineEventStatus

    event = RunTimelineEvent(
        event_type=TimelineEventType.EXECUTION,
        status=TimelineEventStatus.IN_PROGRESS,
    )

    widget = TimelineEventWidget(event)
    widget.show()
    qapp.processEvents()

    # Status dot should have the correct color in stylesheet
    expected_color = STATUS_COLORS[TimelineEventStatus.IN_PROGRESS]
    assert expected_color in widget.status_dot.styleSheet()


def test_timeline_event_widget_toggle_details(qapp):
    from gui.run_timeline_widget import TimelineEventWidget
    from orchestrator.run_timeline import (
        RunTimelineEvent, TimelineEventType, TimelineEventStatus, TimelineEventDetail
    )

    detail = TimelineEventDetail(label="Test", content="Content")
    event = RunTimelineEvent(
        event_type=TimelineEventType.EXECUTION,
        status=TimelineEventStatus.COMPLETED,
        details=[detail],
    )

    widget = TimelineEventWidget(event)
    widget.show()
    qapp.processEvents()

    # Initially details should be hidden
    assert not widget.details_container.isVisible()

    # Toggle details
    widget._toggle_details()
    qapp.processEvents()

    assert widget.details_container.isVisible()


def test_timeline_detail_widget_creates(qapp):
    from gui.run_timeline_widget import TimelineDetailWidget
    from orchestrator.run_timeline import TimelineEventDetail

    detail = TimelineEventDetail(
        label="Output",
        content="Test output content",
        detail_type="logs"
    )

    widget = TimelineDetailWidget(detail)
    widget.show()
    qapp.processEvents()

    assert widget.detail == detail


def test_timeline_detail_widget_expand_collapse(qapp):
    from gui.run_timeline_widget import TimelineDetailWidget
    from orchestrator.run_timeline import TimelineEventDetail

    detail = TimelineEventDetail(
        label="Logs",
        content="Log content here",
    )

    widget = TimelineDetailWidget(detail)
    widget.show()
    qapp.processEvents()

    # Initially collapsed
    assert not widget.content_widget.isVisible()

    # Expand
    widget._toggle_expand()
    qapp.processEvents()

    assert widget.content_widget.isVisible()
    assert widget.expand_btn.text() == "▼"

    # Collapse
    widget._toggle_expand()
    qapp.processEvents()

    assert not widget.content_widget.isVisible()
    assert widget.expand_btn.text() == "▶"
