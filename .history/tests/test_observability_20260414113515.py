"""Tests for structured observability support."""

import json
import logging
from datetime import datetime
from zipfile import ZipFile

from orchestrator.diagnostics import (
    CheckCategory,
    DiagnosticCheckResult,
    DiagnosticReport,
    DiagnosticStatus,
)
from orchestrator.observability import AppObservability


def _read_jsonl(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_observability_creates_structured_logs(tmp_path):
    service = AppObservability(tmp_path)

    service.record_app_event("gui_ready", "GUI initialized")
    service.record_run_event("run-123", "run_started", "Run started", iteration=1, phase="planning")
    service.record_user_action("navigate", {"target": "diagnostics"})

    app_logs = _read_jsonl(service.app_log_path)
    run_logs = _read_jsonl(service.runs_log_path)
    user_logs = _read_jsonl(service.user_actions_log_path)

    assert app_logs[-1]["event"] == "gui_ready"
    assert run_logs[-1]["run_id"] == "run-123"
    assert run_logs[-1]["phase"] == "planning"
    assert user_logs[-1]["action"] == "navigate"


def test_record_error_updates_failure_summary(tmp_path):
    service = AppObservability(tmp_path)

    error_id = service.record_error(
        error_type="RunExecutionFailed",
        message="Validation command failed",
        context={"command": "pytest"},
        run_id="run-456",
        phase="validating",
    )

    summary = service.get_failure_summary()
    errors = _read_jsonl(service.error_log_path)

    assert error_id
    assert summary["by_type"]["RunExecutionFailed"] == 1
    assert summary["recent_errors"][0]["message"] == "Validation command failed"
    assert errors[-1]["run_id"] == "run-456"


def test_logging_handler_mirrors_standard_logging(tmp_path):
    service = AppObservability(tmp_path, debug_mode=True)
    service.attach_logging_handler()

    logger = logging.getLogger("tests.observability")
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.error("Structured handler failure")

    service.detach_logging_handler()
    logger.setLevel(previous_level)

    app_logs = _read_jsonl(service.app_log_path)
    error_logs = _read_jsonl(service.error_log_path)

    assert any(entry.get("logger") == "tests.observability" for entry in app_logs)
    assert any(entry.get("message") == "Structured handler failure" for entry in error_logs)


def test_create_diagnostic_package_includes_logs_and_report(tmp_path):
    service = AppObservability(tmp_path, debug_mode=True)
    config_path = tmp_path / "config.yaml"
    prefs_path = tmp_path / "gui_preferences.json"
    version_path = tmp_path / "version.json"

    config_path.write_text("workspace_path: ./workspace\n", encoding="utf-8")
    prefs_path.write_text(json.dumps({"debug_mode": True}), encoding="utf-8")
    version_path.write_text(json.dumps({"version": "0.2.0"}), encoding="utf-8")

    service.record_app_event("diagnostics_completed", "Diagnostics finished")
    report = DiagnosticReport(
        started_at=datetime.now(),
        overall_status=DiagnosticStatus.WARNING,
        checks=[
            DiagnosticCheckResult(
                key="workspace",
                title="Workspace",
                category=CheckCategory.WORKSPACE,
                status=DiagnosticStatus.WARNING,
                summary="Workspace partially configured",
            )
        ],
    )

    archive_path = service.create_diagnostic_package(
        report=report,
        config_path=config_path,
        preferences_path=prefs_path,
        version_path=version_path,
        metadata={"origin": "test"},
    )

    assert archive_path.exists()

    with ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())

    assert "diagnostic_summary.json" in names
    assert "diagnostics/report.json" in names
    assert "diagnostics/report.md" in names
    assert "logs/app.log" in names
    assert "config/config.yaml" in names
    assert "config/gui_preferences.json" in names
    assert "config/version.json" in names