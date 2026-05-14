"""Tests for AIConnectionService and OpenAIConnectionTester.

OpenAI connectivity is exercised with simulated engine-health results so the
suite never makes a real network call.
"""

import pytest

from orchestrator.ai_connection_service import AIConnectionService, OpenAIConnectionTester
from orchestrator.engine_health import (
    ConnectionStage,
    ConnectionStatus,
    ConnectionTestResult,
)

REAL_KEY = "sk-secretvalue1234567890abcdefghijklmn"


@pytest.fixture(autouse=True)
def _no_system_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _result(success, message, status=ConnectionStatus.SUCCESS, details=None):
    return ConnectionTestResult(
        success=success,
        stage=ConnectionStage.COMPLETED,
        status=status,
        message=message,
        details=details or [],
    )


class TestOpenAIConnectionTester:
    def test_test_delegates_to_engine_health(self, tmp_path, monkeypatch):
        captured = {}

        def fake_check(project_root, skip_network_test, timeout_seconds):
            captured["project_root"] = project_root
            captured["skip"] = skip_network_test
            return _result(True, "ok simulado")

        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_openai_connection", fake_check
        )
        tester = OpenAIConnectionTester(tmp_path)
        result = tester.test(skip_network=True)
        assert result.success is True
        assert captured["project_root"] == tmp_path
        assert captured["skip"] is True

    def test_empty_key_fails_without_network(self, monkeypatch):
        """An empty key never reaches the network stage."""
        called = {"network": False}

        def fake_init(api_key):
            assert api_key == ""
            return _result(False, "chave vazia", ConnectionStatus.FAILURE)

        def fake_network(api_key, timeout):
            called["network"] = True
            return _result(True, "should not happen")

        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_client_initialization", fake_init
        )
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_network_connection", fake_network
        )
        tester = OpenAIConnectionTester()
        result = tester.test_key("", skip_network=False)
        assert result.success is False
        assert called["network"] is False

    def test_simulated_auth_error(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_client_initialization",
            lambda key: _result(True, "cliente ok"),
        )
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_network_connection",
            lambda key, timeout: _result(
                False, "Falha de autenticacao: chave invalida.", ConnectionStatus.FAILURE
            ),
        )
        result = OpenAIConnectionTester().test_key(REAL_KEY)
        assert result.success is False
        assert "autentica" in result.message.lower()

    def test_simulated_network_error(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_client_initialization",
            lambda key: _result(True, "cliente ok"),
        )
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_network_connection",
            lambda key, timeout: _result(
                False, "Falha de conexao de rede.", ConnectionStatus.FAILURE
            ),
        )
        result = OpenAIConnectionTester().test_key(REAL_KEY)
        assert result.success is False
        assert "rede" in result.message.lower()

    def test_simulated_success(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_client_initialization",
            lambda key: _result(True, "cliente ok"),
        )
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_network_connection",
            lambda key, timeout: _result(True, "Conexao com OpenAI validada com sucesso."),
        )
        result = OpenAIConnectionTester().test_key(REAL_KEY)
        assert result.success is True

    def test_key_never_appears_in_result(self, monkeypatch):
        """Whatever engine-health returns, the tester must not echo the raw key."""
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_client_initialization",
            lambda key: _result(True, "cliente ok", details=["preview: sk-secre..."]),
        )
        monkeypatch.setattr(
            "orchestrator.ai_connection_service.check_network_connection",
            lambda key, timeout: _result(True, "ok", details=["preview: sk-secre..."]),
        )
        result = OpenAIConnectionTester().test_key(REAL_KEY)
        blob = " ".join([result.message, *result.details])
        assert REAL_KEY not in blob


class TestAIConnectionService:
    def test_bundles_all_three_surfaces(self, tmp_path):
        service = AIConnectionService(tmp_path, claude_command="claude")
        assert service.env is not None
        assert service.claude is not None
        assert service.openai is not None

    def test_openai_status_passthrough(self, tmp_path):
        service = AIConnectionService(tmp_path)
        assert service.openai_status().state.value == "not_configured"
        service.save_openai_key(REAL_KEY)
        assert service.openai_status().state.value == "found_in_env"

    def test_set_claude_command_updates_detector(self, tmp_path):
        service = AIConnectionService(tmp_path, claude_command="claude")
        service.set_claude_command("/custom/claude")
        assert service.claude.command == "/custom/claude"

    def test_detect_claude_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orchestrator.claude_detector.shutil.which", lambda cmd: None)
        service = AIConnectionService(tmp_path, claude_command="claude")
        result = service.detect_claude()
        assert result.found is False

    def test_claude_install_instructions(self, tmp_path):
        service = AIConnectionService(tmp_path)
        assert "npm install" in service.claude_install_instructions()
