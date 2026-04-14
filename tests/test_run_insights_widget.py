"""Tests for run insights widget."""

import json
import pytest
from datetime import datetime
from pathlib import Path

pytest.importorskip("PySide6")


def test_insights_widget_creates(qapp):
    from gui.run_insights_widget import RunInsightsWidget

    widget = RunInsightsWidget()
    widget.show()
    qapp.processEvents()

    # Should show empty state initially
    assert widget.empty_label.isVisible()
    assert not widget.summary_widget.isVisible()


def test_insights_widget_with_workspace(qapp, tmp_path):
    from gui.run_insights_widget import RunInsightsWidget

    widget = RunInsightsWidget(workspace_path=tmp_path)
    widget.show()
    qapp.processEvents()

    assert widget.workspace_path == tmp_path


def test_insights_widget_set_workspace(qapp, tmp_path):
    from gui.run_insights_widget import RunInsightsWidget

    widget = RunInsightsWidget()
    widget.set_workspace(tmp_path)

    assert widget.workspace_path == tmp_path


def test_insights_widget_set_report(qapp):
    from gui.run_insights_widget import RunInsightsWidget
    from orchestrator.run_insights import (
        RunInsightReport, RunInsight, RunOutcome,
        InsightSeverity, InsightCategory,
    )

    widget = RunInsightsWidget()
    widget.show()

    # Create a test report
    insight = RunInsight(
        id="test-1",
        category=InsightCategory.VALIDATION,
        severity=InsightSeverity.SUCCESS,
        title="Test Insight",
        message="Test message",
    )
    report = RunInsightReport(
        run_id="test-run",
        outcome=RunOutcome.SUCCESS,
        executive_summary="Run completed successfully.",
        short_label="Tudo OK",
        insights=[insight],
    )

    widget.set_report(report)
    qapp.processEvents()

    # Should hide empty state and show content
    assert not widget.empty_label.isVisible()
    assert widget.summary_widget.isVisible()
    assert widget.insights_container.isVisible()
    assert widget.insight_count_label.text() == "1 insight(s)"


def test_insights_widget_clear_insights(qapp):
    from gui.run_insights_widget import RunInsightsWidget
    from orchestrator.run_insights import RunInsightReport, RunOutcome

    widget = RunInsightsWidget()
    widget.show()

    # Set a report first
    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.SUCCESS,
        executive_summary="Done",
        short_label="OK",
    )
    widget.set_report(report)
    qapp.processEvents()

    # Clear it
    widget.clear_insights()
    qapp.processEvents()

    assert widget.empty_label.isVisible()
    assert not widget.summary_widget.isVisible()
    assert widget._report is None


def test_insights_widget_get_report(qapp):
    from gui.run_insights_widget import RunInsightsWidget
    from orchestrator.run_insights import RunInsightReport, RunOutcome

    widget = RunInsightsWidget()

    # No report initially
    assert widget.get_report() is None

    # Set and get report
    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.SUCCESS,
        executive_summary="Done",
        short_label="OK",
    )
    widget.set_report(report)

    assert widget.get_report() == report


def test_insights_widget_get_short_label(qapp):
    from gui.run_insights_widget import RunInsightsWidget
    from orchestrator.run_insights import RunInsightReport, RunOutcome

    widget = RunInsightsWidget()

    # No report - empty label
    assert widget.get_short_label() == ""

    # With report
    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.SUCCESS,
        executive_summary="Done",
        short_label="Tudo OK",
    )
    widget.set_report(report)

    assert widget.get_short_label() == "Tudo OK"


def test_insight_card_creates(qapp):
    from gui.run_insights_widget import InsightCard, SEVERITY_COLORS
    from orchestrator.run_insights import (
        RunInsight, InsightSeverity, InsightCategory
    )

    insight = RunInsight(
        id="test-1",
        category=InsightCategory.EXECUTION,
        severity=InsightSeverity.WARNING,
        title="Test Warning",
        message="Warning message here",
        recommendation="Do something about it",
    )

    card = InsightCard(insight)
    card.show()
    qapp.processEvents()

    assert card.insight == insight
    # Border should have warning color
    expected_color = SEVERITY_COLORS[InsightSeverity.WARNING]
    assert expected_color in card.styleSheet()


def test_insight_card_without_recommendation(qapp):
    from gui.run_insights_widget import InsightCard
    from orchestrator.run_insights import (
        RunInsight, InsightSeverity, InsightCategory
    )

    insight = RunInsight(
        id="test-1",
        category=InsightCategory.VALIDATION,
        severity=InsightSeverity.SUCCESS,
        title="Success",
        message="All good",
    )

    card = InsightCard(insight)
    card.show()
    qapp.processEvents()

    # Should still work without recommendation
    assert card.insight == insight


def test_executive_summary_widget_creates(qapp):
    from gui.run_insights_widget import ExecutiveSummaryWidget

    widget = ExecutiveSummaryWidget()
    widget.show()
    qapp.processEvents()

    assert widget.outcome_label.text() == "Resultado"


def test_executive_summary_widget_set_report(qapp):
    from gui.run_insights_widget import ExecutiveSummaryWidget, OUTCOME_COLORS
    from orchestrator.run_insights import RunInsightReport, RunOutcome

    widget = ExecutiveSummaryWidget()
    widget.show()

    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.SUCCESS,
        executive_summary="Run completed successfully.",
        short_label="Tudo OK",
        total_duration_seconds=90,
        iteration_count=1,
        checkpoint_count=0,
        validation_passed=True,
    )

    widget.set_report(report)
    qapp.processEvents()

    assert widget.outcome_label.text() == "Sucesso"
    assert widget.short_label.text() == "Tudo OK"
    assert widget.summary_label.text() == "Run completed successfully."


def test_executive_summary_widget_failed_outcome(qapp):
    from gui.run_insights_widget import ExecutiveSummaryWidget
    from orchestrator.run_insights import RunInsightReport, RunOutcome

    widget = ExecutiveSummaryWidget()
    widget.show()

    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.FAILED,
        executive_summary="Run failed.",
        short_label="Falhou",
        validation_passed=False,
    )

    widget.set_report(report)
    qapp.processEvents()

    assert widget.outcome_label.text() == "Falhou"
    assert widget.short_label.text() == "Falhou"


def test_insights_widget_sections_by_severity(qapp):
    from gui.run_insights_widget import RunInsightsWidget
    from orchestrator.run_insights import (
        RunInsightReport, RunInsight, RunOutcome,
        InsightSeverity, InsightCategory,
    )

    widget = RunInsightsWidget()
    widget.show()

    # Create insights of different severities
    error_insight = RunInsight(
        id="1", category=InsightCategory.VALIDATION,
        severity=InsightSeverity.ERROR, title="Error", message="M"
    )
    warning_insight = RunInsight(
        id="2", category=InsightCategory.EXECUTION,
        severity=InsightSeverity.WARNING, title="Warning", message="M"
    )
    info_insight = RunInsight(
        id="3", category=InsightCategory.PERFORMANCE,
        severity=InsightSeverity.INFO, title="Info", message="M"
    )
    success_insight = RunInsight(
        id="4", category=InsightCategory.GIT,
        severity=InsightSeverity.SUCCESS, title="Success", message="M"
    )

    report = RunInsightReport(
        run_id="test",
        outcome=RunOutcome.FAILED,
        executive_summary="Mixed results",
        short_label="Falhou",
        insights=[error_insight, warning_insight, info_insight, success_insight],
    )

    widget.set_report(report)
    qapp.processEvents()

    # Should have 4 insights displayed
    assert widget.insight_count_label.text() == "4 insight(s)"


def test_insights_widget_load_insights(qapp, tmp_path):
    from gui.run_insights_widget import RunInsightsWidget

    # Create state directory with run data
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    run_id = "test-insights-123"
    state_data = {
        "run_id": run_id,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "task": {"description": "Test task"},
        "plan": {"objective": "Test objective"},
    }
    (state_dir / f"{run_id}.json").write_text(
        json.dumps(state_data), encoding="utf-8"
    )

    widget = RunInsightsWidget(workspace_path=tmp_path)
    widget.show()
    widget.load_insights(run_id)
    qapp.processEvents()

    # Should have loaded and analyzed the run
    assert widget._report is not None
    assert widget._report.run_id == run_id


def test_get_short_insight_label(tmp_path):
    from gui.run_insights_widget import get_short_insight_label

    # Create state directory with run data
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    run_id = "test-label-run"
    state_data = {
        "run_id": run_id,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "task": {"description": "Test"},
        "plan": {"objective": "Test"},
    }
    (state_dir / f"{run_id}.json").write_text(
        json.dumps(state_data), encoding="utf-8"
    )

    label = get_short_insight_label(tmp_path, run_id)

    # Should return a non-empty label
    assert isinstance(label, str)


def test_get_short_insight_label_invalid_run(tmp_path):
    from gui.run_insights_widget import get_short_insight_label

    # No state directory
    label = get_short_insight_label(tmp_path, "nonexistent")

    assert label == ""
