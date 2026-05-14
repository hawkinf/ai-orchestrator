"""Tests for the actionable 'Configuração mínima recomendada' card."""

import pytest
from PySide6.QtWidgets import QPushButton

from gui.config_panel import ConfigPanel
from orchestrator.setup_validator import SetupCheckResult, SetupValidationResult


def _check(key, title, ok, required=True, action_hint=""):
    return SetupCheckResult(
        key=key,
        title=title,
        ok=ok,
        required=required,
        summary=f"{title} summary",
        details=[],
        action_hint=action_hint,
    )


def _result(openai_ok=True, executor_ok=True):
    return SetupValidationResult(
        checks=[
            _check("project_path", "Projeto", True),
            _check("profile", "Perfil", True),
            _check("openai", "OpenAI", openai_ok, action_hint="Configure a chave."),
            _check("executor", "Claude Executor", executor_ok, action_hint="Instale o Claude."),
            _check("workspace", "Workspace", True),
            _check("git", "Git", True, required=False),
        ]
    )


@pytest.mark.usefixtures("qapp")
class TestSetupCard:
    def test_shows_configure_openai_button_when_openai_missing(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(openai_ok=False))
        fix_btn = panel.findChild(QPushButton, "fix_openai")
        assert fix_btn is not None
        assert "OpenAI" in fix_btn.text()

    def test_shows_configure_claude_button_when_executor_missing(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(executor_ok=False))
        fix_btn = panel.findChild(QPushButton, "fix_executor")
        assert fix_btn is not None
        assert "Claude" in fix_btn.text()

    def test_no_fix_button_for_passing_check(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(openai_ok=True, executor_ok=True))
        assert panel.findChild(QPushButton, "fix_openai") is None
        assert panel.findChild(QPushButton, "fix_executor") is None

    def test_complete_button_disabled_until_required_ok(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(openai_ok=False))
        assert panel.complete_setup_btn.isEnabled() is False

    def test_complete_button_enabled_when_all_required_ok(self):
        panel = ConfigPanel()
        # Git failing but optional -> still ready.
        result = _result(openai_ok=True, executor_ok=True)
        result.checks[-1] = _check("git", "Git", False, required=False)
        panel.set_setup_validation(result)
        assert panel.complete_setup_btn.isEnabled() is True

    def test_fix_openai_emits_signal_with_section(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(openai_ok=False))
        captured = []
        panel.open_ai_connections_requested.connect(captured.append)
        panel.findChild(QPushButton, "fix_openai").click()
        assert captured == ["openai"]

    def test_fix_executor_emits_claude_section(self):
        panel = ConfigPanel()
        panel.set_setup_validation(_result(executor_ok=False))
        captured = []
        panel.open_ai_connections_requested.connect(captured.append)
        panel.findChild(QPushButton, "fix_executor").click()
        assert captured == ["claude"]

    def test_action_row_buttons_emit_signals(self):
        panel = ConfigPanel()
        captured = []
        panel.open_ai_connections_requested.connect(captured.append)
        panel.configure_openai_btn.click()
        panel.configure_claude_btn.click()
        assert captured == ["openai", "claude"]

    def test_header_ai_connections_button_emits_empty_section(self):
        panel = ConfigPanel()
        captured = []
        panel.open_ai_connections_requested.connect(captured.append)
        panel.ai_connections_btn.click()
        assert captured == [""]

    def test_open_diagnostics_button(self):
        panel = ConfigPanel()
        captured = []
        panel.open_diagnostics_requested.connect(lambda: captured.append(True))
        panel.open_diagnostics_btn.click()
        assert captured == [True]

    def test_revalidate_after_set_validation_updates_rows(self):
        """Status updates without recreating the panel (no restart needed)."""
        panel = ConfigPanel()
        panel.set_setup_validation(_result(openai_ok=False))
        assert panel.findChild(QPushButton, "fix_openai") is not None
        panel.set_setup_validation(_result(openai_ok=True))
        assert panel.findChild(QPushButton, "fix_openai") is None
        assert panel.complete_setup_btn.isEnabled() is True
