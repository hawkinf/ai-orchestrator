import pytest

pytest.importorskip("PySide6")

from datetime import datetime

from orchestrator.recommended_actions import (
    ActionPriority,
    ActionTarget,
    RecommendedAction,
)
from orchestrator.run_index import RunMetrics, RunStatus, RunSummary
from orchestrator.setup_validator import SetupCheckResult, SetupValidationResult
from orchestrator.system_insights import SystemHealthStatus, SystemInsightReport


def _make_report():
    return SystemInsightReport(
        report_id="sys-1",
        generated_at=datetime.now(),
        health_status=SystemHealthStatus.USABLE_WITH_ALERTS,
        executive_summary="As últimas runs mostram alertas, mas o sistema segue utilizável.",
        analysis_window={"label": "Últimas 10 runs"},
        total_runs=3,
    )


def _make_action():
    return RecommendedAction(
        id="action-1",
        title="Abrir runs com falha",
        description="Veja as falhas recentes para agir primeiro onde há mais risco.",
        priority=ActionPriority.IMMEDIATE,
        source_type="system_insight",
        source_id="sys-1",
        target=ActionTarget.DASHBOARD,
        action_type="filter_dashboard",
        payload={"status": "failed"},
        recommendation_reason="Houve aumento recente de falhas.",
        confidence=0.92,
    )


def _make_setup():
    return SetupValidationResult(
        checks=[
            SetupCheckResult("project_path", "Projeto", True, True, "Projeto pronto."),
            SetupCheckResult("profile", "Perfil", True, True, "Perfil ativo: python"),
            SetupCheckResult("openai", "OpenAI", True, True, "Chave configurada."),
            SetupCheckResult("executor", "Executor", True, True, "Executor disponível."),
            SetupCheckResult("workspace", "Workspace", True, True, "Workspace acessível."),
            SetupCheckResult("git", "Git", False, False, "Projeto sem repositório Git."),
        ]
    )


def test_command_center_renders_snapshot(qapp):
    from gui.command_center_panel import CommandCenterPanel, CommandCenterSnapshot

    panel = CommandCenterPanel()
    snapshot = CommandCenterSnapshot(
        runs=[
            RunSummary(
                run_id="run-001",
                task_summary="Corrigir falha de validação",
                status=RunStatus.FAILED,
                current_stage="validation",
                duration_seconds=125,
                project_type="python",
                created_at=datetime.now(),
            )
        ],
        metrics=RunMetrics(total_runs=3, failed_runs=1, checkpoint_runs=1),
        pending_checkpoints=[],
        system_report=_make_report(),
        setup_result=_make_setup(),
        primary_action=_make_action(),
        recommended_actions_count=3,
    )

    panel._render_snapshot(snapshot)
    qapp.processEvents()

    assert "alertas" in panel.executive_summary.text().lower()
    assert panel.primary_action_card.title_label.text() == "Abrir runs com falha"
    assert panel.summary_cards["runs"].value_label.text() == "3"
    assert panel.actions_widget.get_group() is not None


def test_command_center_simple_vs_advanced(qapp):
    from gui.command_center_panel import CommandCenterPanel
    from gui.mode_manager import MODE_ADVANCED, MODE_SIMPLE

    panel = CommandCenterPanel()
    panel.set_interface_mode(MODE_SIMPLE)
    qapp.processEvents()
    assert not panel.health_frame.isVisible()

    panel.set_interface_mode(MODE_ADVANCED)
    panel.show()
    qapp.processEvents()
    assert panel.health_frame.isVisible()


def test_command_center_empty_workspace_state(qapp):
    from gui.command_center_panel import CommandCenterPanel

    panel = CommandCenterPanel()
    panel.refresh()
    qapp.processEvents()

    assert "histórico suficiente" in panel.executive_summary.text().lower()


def test_command_center_feedback_button_emits_signal(qapp):
    from gui.command_center_panel import CommandCenterPanel

    panel = CommandCenterPanel()
    emitted = []
    panel.open_feedback.connect(lambda: emitted.append(True))

    panel.feedback_btn.click()
    qapp.processEvents()

    assert emitted == [True]
