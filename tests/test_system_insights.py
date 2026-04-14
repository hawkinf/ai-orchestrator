"""Tests for aggregate system insights."""

from __future__ import annotations

import json
from pathlib import Path

from orchestrator.system_insights import SystemHealthStatus, SystemInsightsAnalyzer


def _write_run(
    workspace: Path,
    run_id: str,
    *,
    status: str,
    profile: str,
    created_at: str,
    completed_at: str | None = None,
    checkpoint: bool = False,
    git_failed: bool = False,
    validation_failed: bool = False,
    iterations: int = 1,
) -> None:
    state = {
        "run_id": run_id,
        "created_at": created_at,
        "completed_at": completed_at,
        "status": status,
        "task": {"description": f"Tarefa {run_id}", "profile": profile},
        "plan": {"objective": f"Objetivo {run_id}"},
        "current_iteration": iterations,
        "max_iterations": max(iterations, 3),
    }
    if checkpoint:
        state["checkpoint"] = {"reason": "Aprovação necessária", "status": "pending"}
    if git_failed:
        state["git"] = {"status": "failed", "error": "push blocked"}
    elif status == "completed":
        state["git"] = {"status": "completed", "commit_hash": "abc123"}
    if validation_failed:
        state["validation"] = {"status": "failed", "commands": [{"command": "pytest", "exit_code": 1, "output": "failed"}]}
    else:
        state["validation"] = {"status": "completed", "commands": [{"command": "pytest", "exit_code": 0, "output": "ok"}]}
    (workspace / "state" / f"{run_id}.json").write_text(json.dumps(state), encoding="utf-8")


def test_system_insights_detect_recurrent_validation_failures(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_run(tmp_path, "run-001", status="failed", profile="python", created_at="2026-04-10T10:00:00", completed_at="2026-04-10T10:05:00", validation_failed=True)
    _write_run(tmp_path, "run-002", status="failed", profile="python", created_at="2026-04-09T10:00:00", completed_at="2026-04-09T10:06:00", validation_failed=True)
    _write_run(tmp_path, "run-003", status="completed", profile="python", created_at="2026-04-08T10:00:00", completed_at="2026-04-08T10:04:00")

    report = SystemInsightsAnalyzer(tmp_path).analyze(limit=10)

    validation = report.get_by_category("validation")
    assert validation
    assert "validação" in validation[0].title.lower() or "validação" in validation[0].message.lower()


def test_system_insights_duration_trend_and_profile_breakdown(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_run(tmp_path, "run-101", status="completed", profile="flutter", created_at="2026-04-10T10:00:00", completed_at="2026-04-10T10:15:00")
    _write_run(tmp_path, "run-102", status="completed", profile="flutter", created_at="2026-04-09T10:00:00", completed_at="2026-04-09T10:14:00")
    _write_run(tmp_path, "run-103", status="completed", profile="python", created_at="2026-04-08T10:00:00", completed_at="2026-04-08T10:03:00")
    _write_run(tmp_path, "run-104", status="completed", profile="python", created_at="2026-04-07T10:00:00", completed_at="2026-04-07T10:02:30")

    report = SystemInsightsAnalyzer(tmp_path).analyze(limit=10)

    avg_duration = next(metric for metric in report.metrics if metric.key == "avg_duration")
    assert avg_duration.display_value != "-"
    assert report.profile_breakdown["flutter"]["avg_duration_seconds"] > report.profile_breakdown["python"]["avg_duration_seconds"]


def test_system_insights_success_rate_by_profile_and_health(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_run(tmp_path, "run-201", status="completed", profile="flutter", created_at="2026-04-10T10:00:00", completed_at="2026-04-10T10:03:00")
    _write_run(tmp_path, "run-202", status="completed", profile="flutter", created_at="2026-04-09T10:00:00", completed_at="2026-04-09T10:03:20")
    _write_run(tmp_path, "run-203", status="failed", profile="python", created_at="2026-04-08T10:00:00", completed_at="2026-04-08T10:05:00", validation_failed=True)
    _write_run(tmp_path, "run-204", status="failed", profile="python", created_at="2026-04-07T10:00:00", completed_at="2026-04-07T10:05:30", git_failed=True)

    report = SystemInsightsAnalyzer(tmp_path).analyze(limit=10)

    assert report.profile_breakdown["flutter"]["success_rate"] == 100.0
    assert report.profile_breakdown["python"]["success_rate"] == 0.0
    assert report.health_status in {SystemHealthStatus.DEGRADED, SystemHealthStatus.RECURRING_FAILURES}


def test_system_insights_export_report(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()
    _write_run(tmp_path, "run-301", status="completed", profile="generic", created_at="2026-04-10T10:00:00", completed_at="2026-04-10T10:01:00")

    analyzer = SystemInsightsAnalyzer(tmp_path)
    report = analyzer.analyze(limit=10)
    paths = analyzer.export_report(report)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["actions"].exists()
    assert "Insights do Sistema" in paths["markdown"].read_text(encoding="utf-8")
