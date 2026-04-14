"""Tests for recommended actions widget."""

import pytest

pytest.importorskip("PySide6")

from orchestrator.recommended_actions import ActionPriority, ActionTarget, RecommendedAction, RecommendedActionGroup


def test_recommended_actions_widget_renders_actions(qapp):
    from gui.recommended_actions_widget import RecommendedActionsWidget

    widget = RecommendedActionsWidget()
    group = RecommendedActionGroup(
        title="Ações",
        summary="Resumo",
        actions=[
            RecommendedAction(
                id="a1",
                title="Abrir diagnóstico",
                description="Teste o ambiente.",
                priority=ActionPriority.IMMEDIATE,
                source_type="system_insight",
                source_id="sys-1",
                target=ActionTarget.DIAGNOSTICS,
                action_type="navigate",
            )
        ],
    )

    widget.set_group(group)
    widget.show()
    qapp.processEvents()

    assert widget.title_label.text() == "Ações"
    assert widget.count_label.text() == "1 ação(ões)"
    assert not widget.empty_label.isVisible()
