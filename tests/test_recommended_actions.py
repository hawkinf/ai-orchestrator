"""Tests for recommended actions mapping."""

from orchestrator.recommended_actions import ActionPriority, RecommendedActionsEngine
from orchestrator.run_insights import InsightCategory, InsightSeverity, RunInsight, RunInsightReport, RunOutcome
from orchestrator.system_insights import SystemHealthStatus, SystemInsight, SystemInsightReport


def test_run_validation_insight_maps_to_useful_actions():
    report = RunInsightReport(
        run_id="run-123",
        outcome=RunOutcome.FAILED,
        executive_summary="Falhou na validação.",
        short_label="Falhou",
        insights=[
            RunInsight(
                id="ins-1",
                category=InsightCategory.VALIDATION,
                severity=InsightSeverity.ERROR,
                title="Validação falhou",
                message="pytest falhou",
                recommendation_key="review_validation",
            )
        ],
    )

    group = RecommendedActionsEngine().from_run_report(report)

    titles = [action.title for action in group.actions]
    assert "Abrir validação da run" in titles
    assert "Abrir replay desta run" in titles
    assert any(action.priority == ActionPriority.IMMEDIATE for action in group.actions)


def test_system_git_insight_maps_to_git_actions():
    report = SystemInsightReport(
        report_id="system-1",
        generated_at=__import__("datetime").datetime.now(),
        health_status=SystemHealthStatus.DEGRADED,
        executive_summary="Falhas de Git em alta.",
        analysis_window={"label": "Últimas 10 runs"},
        insights=[
            SystemInsight(
                id="sys-1",
                category="git",
                severity="error",
                title="Falhas recorrentes em Git",
                message="Git falhou em 3 runs",
                recommendation="Revise Git",
            )
        ],
    )

    group = RecommendedActionsEngine().from_system_report(report)
    titles = [action.title for action in group.actions]
    assert "Abrir Configurações > Git" in titles
    assert "Abrir diagnóstico" in titles


def test_actions_are_deduplicated_and_sorted():
    report = RunInsightReport(
        run_id="run-456",
        outcome=RunOutcome.SUCCESS_WITH_WARNINGS,
        executive_summary="Com avisos.",
        short_label="Avisos",
        checkpoint_count=1,
        insights=[
            RunInsight(
                id="ins-1",
                category=InsightCategory.CHECKPOINT,
                severity=InsightSeverity.WARNING,
                title="Checkpoint 1",
                message="checkpoint",
                recommendation_key="wait_approval",
            ),
            RunInsight(
                id="ins-2",
                category=InsightCategory.CHECKPOINT,
                severity=InsightSeverity.WARNING,
                title="Checkpoint 2",
                message="checkpoint",
                recommendation_key="wait_approval",
            ),
        ],
    )

    group = RecommendedActionsEngine().from_run_report(report)
    titles = [action.title for action in group.actions]
    assert titles.count("Abrir Centro de Checkpoints") == 1
