"""Tests for run insights analyzer."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from orchestrator.run_insights import (
    InsightSeverity,
    InsightCategory,
    RunOutcome,
    RunInsight,
    RunInsightReport,
    InsightsAnalyzer,
    OUTCOME_DISPLAY,
    OUTCOME_SHORT_LABELS,
    get_insights_analyzer,
)
from orchestrator.run_timeline import (
    RunTimeline,
    RunTimelineEvent,
    TimelineEventType,
    TimelineEventStatus,
)


class TestInsightSeverity:
    """Tests for InsightSeverity enum."""

    def test_severity_values(self):
        assert InsightSeverity.INFO.value == "info"
        assert InsightSeverity.SUCCESS.value == "success"
        assert InsightSeverity.WARNING.value == "warning"
        assert InsightSeverity.ERROR.value == "error"


class TestInsightCategory:
    """Tests for InsightCategory enum."""

    def test_category_values(self):
        assert InsightCategory.VALIDATION.value == "validation"
        assert InsightCategory.EXECUTION.value == "execution"
        assert InsightCategory.REVIEW.value == "review"
        assert InsightCategory.CHECKPOINT.value == "checkpoint"
        assert InsightCategory.GIT.value == "git"
        assert InsightCategory.CONFIGURATION.value == "configuration"
        assert InsightCategory.PERFORMANCE.value == "performance"
        assert InsightCategory.RELIABILITY.value == "reliability"
        assert InsightCategory.SUMMARY.value == "summary"


class TestRunOutcome:
    """Tests for RunOutcome enum."""

    def test_outcome_values(self):
        assert RunOutcome.SUCCESS.value == "success"
        assert RunOutcome.SUCCESS_WITH_WARNINGS.value == "success_with_warnings"
        assert RunOutcome.FAILED.value == "failed"
        assert RunOutcome.INTERRUPTED.value == "interrupted"
        assert RunOutcome.NEEDS_ATTENTION.value == "needs_attention"
        assert RunOutcome.IN_PROGRESS.value == "in_progress"

    def test_outcome_display_names(self):
        assert OUTCOME_DISPLAY[RunOutcome.SUCCESS] == "Sucesso"
        assert OUTCOME_DISPLAY[RunOutcome.FAILED] == "Falhou"

    def test_outcome_short_labels(self):
        assert OUTCOME_SHORT_LABELS[RunOutcome.SUCCESS] == "Tudo OK"
        assert OUTCOME_SHORT_LABELS[RunOutcome.FAILED] == "Falhou"


class TestRunInsight:
    """Tests for RunInsight dataclass."""

    def test_create_insight(self):
        insight = RunInsight(
            id="test-1",
            category=InsightCategory.VALIDATION,
            severity=InsightSeverity.SUCCESS,
            title="Test Insight",
            message="Test message",
        )
        assert insight.id == "test-1"
        assert insight.category == InsightCategory.VALIDATION
        assert insight.severity == InsightSeverity.SUCCESS
        assert insight.title == "Test Insight"
        assert insight.message == "Test message"

    def test_insight_to_dict(self):
        insight = RunInsight(
            id="test-1",
            category=InsightCategory.VALIDATION,
            severity=InsightSeverity.SUCCESS,
            title="Test Insight",
            message="Test message",
            recommendation="Test recommendation",
            recommendation_key="test_key",
            related_event_types=[TimelineEventType.VALIDATION],
            related_stage="validation",
            confidence=0.9,
            data={"key": "value"},
        )
        data = insight.to_dict()

        assert data["id"] == "test-1"
        assert data["category"] == "validation"
        assert data["severity"] == "success"
        assert data["title"] == "Test Insight"
        assert data["message"] == "Test message"
        assert data["recommendation"] == "Test recommendation"
        assert data["recommendation_key"] == "test_key"
        assert data["related_event_types"] == ["validation"]
        assert data["related_stage"] == "validation"
        assert data["confidence"] == 0.9
        assert data["data"] == {"key": "value"}


class TestRunInsightReport:
    """Tests for RunInsightReport dataclass."""

    def test_create_report(self):
        report = RunInsightReport(
            run_id="test-run",
            outcome=RunOutcome.SUCCESS,
            executive_summary="Test summary",
            short_label="OK",
        )
        assert report.run_id == "test-run"
        assert report.outcome == RunOutcome.SUCCESS
        assert report.executive_summary == "Test summary"
        assert report.short_label == "OK"

    def test_get_by_category(self):
        insight1 = RunInsight(
            id="1", category=InsightCategory.VALIDATION,
            severity=InsightSeverity.SUCCESS, title="T1", message="M1"
        )
        insight2 = RunInsight(
            id="2", category=InsightCategory.EXECUTION,
            severity=InsightSeverity.INFO, title="T2", message="M2"
        )
        insight3 = RunInsight(
            id="3", category=InsightCategory.VALIDATION,
            severity=InsightSeverity.WARNING, title="T3", message="M3"
        )

        report = RunInsightReport(
            run_id="test",
            outcome=RunOutcome.SUCCESS,
            executive_summary="",
            short_label="",
            insights=[insight1, insight2, insight3],
        )

        validation_insights = report.get_by_category(InsightCategory.VALIDATION)
        assert len(validation_insights) == 2
        assert insight1 in validation_insights
        assert insight3 in validation_insights

    def test_get_by_severity(self):
        insight1 = RunInsight(
            id="1", category=InsightCategory.VALIDATION,
            severity=InsightSeverity.ERROR, title="T1", message="M1"
        )
        insight2 = RunInsight(
            id="2", category=InsightCategory.EXECUTION,
            severity=InsightSeverity.WARNING, title="T2", message="M2"
        )
        insight3 = RunInsight(
            id="3", category=InsightCategory.GIT,
            severity=InsightSeverity.ERROR, title="T3", message="M3"
        )

        report = RunInsightReport(
            run_id="test",
            outcome=RunOutcome.FAILED,
            executive_summary="",
            short_label="",
            insights=[insight1, insight2, insight3],
        )

        error_insights = report.get_by_severity(InsightSeverity.ERROR)
        assert len(error_insights) == 2
        assert insight1 in error_insights
        assert insight3 in error_insights

    def test_has_errors(self):
        report_with_error = RunInsightReport(
            run_id="test",
            outcome=RunOutcome.FAILED,
            executive_summary="",
            short_label="",
            insights=[
                RunInsight(id="1", category=InsightCategory.VALIDATION,
                          severity=InsightSeverity.ERROR, title="T", message="M")
            ],
        )
        assert report_with_error.has_errors() is True

        report_no_error = RunInsightReport(
            run_id="test",
            outcome=RunOutcome.SUCCESS,
            executive_summary="",
            short_label="",
            insights=[
                RunInsight(id="1", category=InsightCategory.VALIDATION,
                          severity=InsightSeverity.SUCCESS, title="T", message="M")
            ],
        )
        assert report_no_error.has_errors() is False

    def test_has_warnings(self):
        report_with_warning = RunInsightReport(
            run_id="test",
            outcome=RunOutcome.SUCCESS_WITH_WARNINGS,
            executive_summary="",
            short_label="",
            insights=[
                RunInsight(id="1", category=InsightCategory.VALIDATION,
                          severity=InsightSeverity.WARNING, title="T", message="M")
            ],
        )
        assert report_with_warning.has_warnings() is True

    def test_to_dict(self):
        report = RunInsightReport(
            run_id="test-run",
            outcome=RunOutcome.SUCCESS,
            executive_summary="Test summary",
            short_label="OK",
            total_duration_seconds=120.5,
            iteration_count=2,
            checkpoint_count=1,
            validation_passed=True,
        )
        data = report.to_dict()

        assert data["run_id"] == "test-run"
        assert data["outcome"] == "success"
        assert data["executive_summary"] == "Test summary"
        assert data["short_label"] == "OK"
        assert data["total_duration_seconds"] == 120.5
        assert data["iteration_count"] == 2
        assert data["checkpoint_count"] == 1
        assert data["validation_passed"] is True
        assert "created_at" in data

    def test_to_markdown(self):
        insight = RunInsight(
            id="1", category=InsightCategory.VALIDATION,
            severity=InsightSeverity.SUCCESS, title="Test", message="Message",
            recommendation="Do something"
        )
        report = RunInsightReport(
            run_id="test-run",
            outcome=RunOutcome.SUCCESS,
            executive_summary="Run completed successfully.",
            short_label="OK",
            total_duration_seconds=90,
            iteration_count=1,
            checkpoint_count=0,
            validation_passed=True,
            insights=[insight],
        )

        md = report.to_markdown()

        assert "# Insights da Run: test-run" in md
        assert "**Resultado:** Sucesso" in md
        assert "Run completed successfully." in md
        assert "**Duração:** 1m 30s" in md
        assert "**Iterações:** 1" in md
        assert "**Checkpoints:** 0" in md
        assert "**Validação:** Passou" in md
        assert "### ✅ Test" in md
        assert "Message" in md
        assert "**Recomendação:** Do something" in md


class TestInsightsAnalyzer:
    """Tests for InsightsAnalyzer class."""

    def test_create_analyzer(self):
        analyzer = InsightsAnalyzer()
        assert analyzer.workspace_path is None

        analyzer_with_path = InsightsAnalyzer(Path("/test"))
        assert analyzer_with_path.workspace_path == Path("/test")

    def test_analyze_empty_timeline(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test")

        report = analyzer.analyze(timeline)

        assert report.run_id == "test"
        assert report.outcome == RunOutcome.IN_PROGRESS

    def test_analyze_successful_run(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test", is_complete=True)

        # Add events for a successful run
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
            description="Planning done"
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
            description="Execution done"
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.VALIDATION,
            status=TimelineEventStatus.COMPLETED,
            description="Validation passed"
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.COMPLETED,
            description="Finalized"
        ))

        report = analyzer.analyze(timeline)

        assert report.outcome == RunOutcome.SUCCESS
        assert report.validation_passed is True
        assert "sucesso" in report.executive_summary.lower()

    def test_analyze_failed_validation(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test", is_complete=True, has_errors=True)

        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.VALIDATION,
            status=TimelineEventStatus.FAILED,
            errors=["Test failed"],
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.FAILED,
        ))

        report = analyzer.analyze(timeline)

        assert report.outcome == RunOutcome.FAILED
        assert report.validation_passed is False

        # Should have validation error insight
        error_insights = report.get_by_severity(InsightSeverity.ERROR)
        assert len(error_insights) > 0

    def test_analyze_with_checkpoint(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test", is_complete=False)

        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.CHECKPOINT,
            status=TimelineEventStatus.IN_PROGRESS,
            checkpoint_reason="Destructive action",
            checkpoint_resolved=False,
        ))

        report = analyzer.analyze(timeline)

        assert report.checkpoint_count == 1
        # Pending checkpoint means needs attention
        assert report.outcome == RunOutcome.NEEDS_ATTENTION

        # Should have checkpoint insight
        checkpoint_insights = report.get_by_category(InsightCategory.CHECKPOINT)
        assert len(checkpoint_insights) > 0

    def test_analyze_multiple_iterations(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test", is_complete=True)

        # Multiple execution events
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.ITERATION_START,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.COMPLETED,
        ))

        report = analyzer.analyze(timeline)

        assert report.iteration_count >= 2
        # Multiple iterations cause success_with_warnings
        assert report.outcome in (RunOutcome.SUCCESS, RunOutcome.SUCCESS_WITH_WARNINGS)

    def test_analyze_git_success(self):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test", is_complete=True)

        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.PLANNING,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.GIT,
            status=TimelineEventStatus.COMPLETED,
            description="Commit and push done",
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.COMPLETED,
        ))

        report = analyzer.analyze(timeline)

        git_insights = report.get_by_category(InsightCategory.GIT)
        assert len(git_insights) > 0
        assert any(i.severity == InsightSeverity.SUCCESS for i in git_insights)

    def test_analyze_performance_long_duration(self):
        analyzer = InsightsAnalyzer()
        # Create timeline with long duration
        timeline = RunTimeline(
            run_id="test",
            is_complete=True,
            total_duration_seconds=400,  # > 300 threshold
        )

        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.EXECUTION,
            status=TimelineEventStatus.COMPLETED,
            duration_seconds=350,
        ))
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.COMPLETED,
        ))

        report = analyzer.analyze(timeline)

        perf_insights = report.get_by_category(InsightCategory.PERFORMANCE)
        assert len(perf_insights) > 0

    def test_export_to_file(self, tmp_path):
        analyzer = InsightsAnalyzer()
        timeline = RunTimeline(run_id="test-export", is_complete=True)
        timeline.add_event(RunTimelineEvent(
            event_type=TimelineEventType.FINALIZATION,
            status=TimelineEventStatus.COMPLETED,
        ))

        report = analyzer.analyze(timeline)
        run_dir = tmp_path / "runs" / "test-export"
        run_dir.mkdir(parents=True)

        exported = analyzer.export_to_file(report, run_dir)

        assert "json" in exported
        assert "markdown" in exported
        assert exported["json"].exists()
        assert exported["markdown"].exists()

        # Verify JSON content
        with open(exported["json"], encoding="utf-8") as f:
            data = json.load(f)
        assert data["run_id"] == "test-export"

        # Verify Markdown content
        md_content = exported["markdown"].read_text(encoding="utf-8")
        assert "test-export" in md_content


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_insights_analyzer(self):
        analyzer = get_insights_analyzer()
        assert isinstance(analyzer, InsightsAnalyzer)
        assert analyzer.workspace_path is None

    def test_get_insights_analyzer_with_path(self, tmp_path):
        analyzer = get_insights_analyzer(tmp_path)
        assert isinstance(analyzer, InsightsAnalyzer)
        assert analyzer.workspace_path == tmp_path
