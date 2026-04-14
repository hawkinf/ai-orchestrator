"""Tests for system insights widgets."""

import json

import pytest

pytest.importorskip("PySide6")


def _write_state(tmp_path, run_id: str, status: str, created_at: str, completed_at: str):
    state = {
        "run_id": run_id,
        "created_at": created_at,
        "completed_at": completed_at,
        "status": status,
        "task": {"description": f"Tarefa {run_id}", "profile": "python"},
        "plan": {"objective": "Objetivo"},
        "validation": {"status": "completed", "commands": [{"command": "pytest", "exit_code": 0}]},
        "git": {"status": "completed", "commit_hash": "abc123"},
    }
    (tmp_path / "state" / f"{run_id}.json").write_text(json.dumps(state), encoding="utf-8")


def test_system_insights_widget_loads_report(qapp, tmp_path):
    from gui.system_insights_widget import SystemInsightsWidget

    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_state(tmp_path, "run-001", "completed", "2026-04-10T10:00:00", "2026-04-10T10:01:30")
    _write_state(tmp_path, "run-002", "completed", "2026-04-09T10:00:00", "2026-04-09T10:02:10")

    widget = SystemInsightsWidget(tmp_path)
    widget.load_report(limit=10)

    report = widget.get_report()
    assert report is not None
    assert "runs" in report.executive_summary.lower()


def test_system_insights_panel_refresh(qapp, tmp_path):
    from gui.system_insights_panel import SystemInsightsPanel

    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_state(tmp_path, "run-010", "completed", "2026-04-10T10:00:00", "2026-04-10T10:01:30")

    panel = SystemInsightsPanel(tmp_path)
    panel.refresh()

    report = panel.get_report()
    assert report is not None
    assert panel.health_label.text()
