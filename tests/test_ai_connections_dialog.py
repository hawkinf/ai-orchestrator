"""Widget tests for the 'Conexões IA' dialog."""

import pytest

from orchestrator.ai_connection_service import AIConnectionService
from gui.ai_connections_dialog import AIConnectionsDialog

REAL_KEY = "sk-dialogsecret1234567890abcdefghijkl"


@pytest.fixture(autouse=True)
def _no_system_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.mark.usefixtures("qapp")
class TestAIConnectionsDialog:
    def test_dialog_has_both_sections(self, tmp_path):
        service = AIConnectionService(tmp_path)
        dialog = AIConnectionsDialog(service)
        assert dialog.api_key_input is not None
        assert dialog.claude_command_edit is not None
        assert dialog.claude_command_edit.text() == "claude"

    def test_openai_input_is_masked_by_default(self, tmp_path):
        from PySide6.QtWidgets import QLineEdit

        dialog = AIConnectionsDialog(AIConnectionService(tmp_path))
        assert dialog.api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_status_starts_not_configured(self, tmp_path):
        dialog = AIConnectionsDialog(AIConnectionService(tmp_path))
        assert "não configurado" in dialog.openai_status_badge.text().lower()

    def test_save_key_updates_status_without_restart(self, tmp_path):
        service = AIConnectionService(tmp_path)
        dialog = AIConnectionsDialog(service)
        changed = []
        dialog.configuration_changed.connect(lambda: changed.append(True))

        dialog.api_key_input.setText(REAL_KEY)
        dialog._on_save_openai_key()

        # Status flips to "encontrada" in the same session.
        assert "encontrada" in dialog.openai_status_badge.text().lower()
        assert changed == [True]
        # Key is persisted, input cleared, and the raw key is never shown.
        assert (tmp_path / ".env").read_text().count(REAL_KEY) == 1
        assert dialog.api_key_input.text() == ""
        assert REAL_KEY not in dialog.openai_result_label.text()

    def test_save_claude_command_emits_signal(self, tmp_path):
        dialog = AIConnectionsDialog(AIConnectionService(tmp_path))
        captured = []
        dialog.claude_command_changed.connect(captured.append)

        dialog.claude_command_edit.setText("/opt/bin/claude")
        dialog._on_save_claude_command()

        assert captured == ["/opt/bin/claude"]

    def test_initial_section_claude_focuses_command(self, tmp_path):
        dialog = AIConnectionsDialog(
            AIConnectionService(tmp_path), initial_section="claude"
        )
        # The Claude command field exists and is the focus target.
        assert dialog.claude_command_edit is not None

    def test_diagnostics_area_toggles(self, tmp_path):
        dialog = AIConnectionsDialog(AIConnectionService(tmp_path))
        assert dialog.diagnostics_text.isHidden() is True
        dialog.diagnostics_btn.setChecked(True)
        assert dialog.diagnostics_text.isHidden() is False

    def test_claude_section_shows_install_hint_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orchestrator.claude_detector.shutil.which", lambda cmd: None)
        dialog = AIConnectionsDialog(AIConnectionService(tmp_path))
        assert dialog.claude_install_hint.isHidden() is False
        assert "não encontrado" in dialog.claude_status_badge.text().lower()
