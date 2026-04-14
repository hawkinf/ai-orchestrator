"""Tests for end-user feedback capture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from orchestrator.feedback_store import FeedbackEntry, FeedbackStore
from orchestrator.observability import configure_observability
from orchestrator.paths import OrchestratorPaths
from orchestrator.version import ReleaseChannel, Version, VersionInfo


@pytest.fixture
def version_info():
    return VersionInfo(
        version=Version(0, 2, 0),
        channel=ReleaseChannel.STABLE,
        build_date="2026-04-14T12:00:00",
        app_name="AI Orchestrator",
    )


def test_feedback_store_creates_feedback_file(tmp_path, version_info):
    paths = OrchestratorPaths(tmp_path)
    configure_observability(tmp_path)
    store = FeedbackStore(paths, version_info)

    entry = store.build_feedback(
        feedback_type="bug",
        description="A tela travou ao abrir uma run.",
        timestamp="2026-04-14T12:30:00Z",
    )
    output_path = store.save_feedback(entry)

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["tipo"] == "bug"
    assert data["descricao"] == "A tela travou ao abrir uma run."
    assert data["versao_app"] == "0.2.0"
    assert data["diagnostico"] is None


def test_feedback_store_persists_diagnostic_path(tmp_path, version_info):
    paths = OrchestratorPaths(tmp_path)
    configure_observability(tmp_path)
    store = FeedbackStore(paths, version_info)
    diagnostic_path = paths.diagnostics_dir / "diagnostic_20260414_123000.zip"
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_path.write_text("zip-placeholder", encoding="utf-8")

    entry = store.build_feedback(
        feedback_type="sugestão",
        description="Seria útil destacar runs pausadas.",
        timestamp="2026-04-14T12:31:00Z",
        diagnostic_path=diagnostic_path,
    )
    output_path = store.save_feedback(entry)
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["tipo"] == "sugestão"
    assert data["diagnostico"] == str(diagnostic_path)


@pytest.mark.usefixtures("qapp")
def test_feedback_dialog_generates_diagnostic_and_persists(tmp_path, version_info, monkeypatch):
    from gui.feedback_dialog import FeedbackDialog

    paths = OrchestratorPaths(tmp_path)
    configure_observability(tmp_path)
    (tmp_path / "config.yaml").write_text("workspace_path: ./workspace\n", encoding="utf-8")
    (tmp_path / "gui_preferences.json").write_text(json.dumps({"debug_mode": False}), encoding="utf-8")

    info_messages = []
    monkeypatch.setattr("gui.feedback_dialog.QMessageBox.information", lambda *args: info_messages.append(args[2]))
    monkeypatch.setattr("gui.feedback_dialog.QMessageBox.warning", lambda *args: None)

    dialog = FeedbackDialog(
        paths=paths,
        version_info=version_info,
        config_path=tmp_path / "config.yaml",
        preferences_path=tmp_path / "gui_preferences.json",
    )
    dialog.type_combo.setCurrentText("bug")
    dialog.description_edit.setPlainText("A execução ficou presa na fase de validação.")
    dialog.attach_diagnostic_checkbox.setChecked(True)

    dialog._save_feedback()

    saved_files = list(paths.feedback_dir.glob("feedback_*.json"))
    diagnostic_files = list(paths.diagnostics_dir.glob("diagnostic_*.zip"))
    assert len(saved_files) == 1
    assert len(diagnostic_files) == 1

    payload = json.loads(saved_files[0].read_text(encoding="utf-8"))
    assert payload["tipo"] == "bug"
    assert payload["diagnostico"] == str(diagnostic_files[0])
    assert info_messages


@pytest.mark.usefixtures("qapp")
def test_feedback_dialog_copy_content(tmp_path, version_info, monkeypatch):
    from gui.feedback_dialog import FeedbackDialog

    paths = OrchestratorPaths(tmp_path)
    configure_observability(tmp_path)

    monkeypatch.setattr("gui.feedback_dialog.QMessageBox.information", lambda *args: None)
    monkeypatch.setattr("gui.feedback_dialog.QMessageBox.warning", lambda *args: None)

    dialog = FeedbackDialog(paths=paths, version_info=version_info)
    dialog.type_combo.setCurrentText("dúvida")
    dialog.description_edit.setPlainText("Onde vejo o histórico completo das runs?")
    dialog.attach_diagnostic_checkbox.setChecked(False)

    dialog._copy_feedback()

    clipboard_text = dialog._last_feedback_json
    assert "dúvida" in clipboard_text
    assert "histórico completo" in clipboard_text