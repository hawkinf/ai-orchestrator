"""Tests for engine_health module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from orchestrator.engine_health import (
    ConnectionStage,
    ConnectionStatus,
    ConnectionTestResult,
    check_key_resolution,
    check_client_initialization,
    check_network_connection,
    check_openai_connection,
    _sanitize_error,
)


class TestConnectionTestResult:
    """Test ConnectionTestResult dataclass."""

    def test_create_success_result(self):
        """Test creating a success result."""
        result = ConnectionTestResult(
            success=True,
            stage=ConnectionStage.COMPLETED,
            status=ConnectionStatus.SUCCESS,
            source="system",
            key_preview="sk-abc1...",
            client_initialized=True,
            network_test_executed=True,
            message="Connection validated",
            details=["Step 1 OK", "Step 2 OK"],
        )

        assert result.success is True
        assert result.stage == ConnectionStage.COMPLETED
        assert result.status == ConnectionStatus.SUCCESS
        assert result.source == "system"
        assert result.client_initialized is True
        assert result.network_test_executed is True

    def test_create_failure_result(self):
        """Test creating a failure result."""
        result = ConnectionTestResult(
            success=False,
            stage=ConnectionStage.KEY_RESOLUTION,
            status=ConnectionStatus.FAILURE,
            message="Key not found",
            details=["Error: Key missing"],
        )

        assert result.success is False
        assert result.stage == ConnectionStage.KEY_RESOLUTION
        assert result.client_initialized is False
        assert result.network_test_executed is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ConnectionTestResult(
            success=True,
            stage=ConnectionStage.COMPLETED,
            status=ConnectionStatus.SUCCESS,
            source="dotenv",
            message="OK",
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["stage"] == "completed"
        assert d["status"] == "success"
        assert d["source"] == "dotenv"
        assert "timestamp" in d
        assert "duration_ms" in d


class TestSanitizeError:
    """Test error sanitization."""

    def test_sanitize_api_key(self):
        """Test that API keys are masked."""
        error = "Invalid API key: sk-abcdefghij1234567890abcd"
        result = _sanitize_error(Exception(error))

        assert "sk-abcdefghij1234567890abcd" not in result
        assert "sk-***" in result

    def test_sanitize_api_key_pattern(self):
        """Test api_key= pattern is masked."""
        error = "api_key=my-secret-key"
        result = _sanitize_error(Exception(error))

        assert "my-secret-key" not in result
        assert "api_key=***" in result

    def test_safe_error_unchanged(self):
        """Test that safe errors pass through."""
        error = "Connection timeout"
        result = _sanitize_error(Exception(error))

        assert result == "Connection timeout"


class TestKeyResolution:
    """Test check_key_resolution function."""

    def test_key_present_in_environment(self):
        """Test when key is in environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890"}, clear=True):
            result = check_key_resolution()

            assert result.success is True
            assert result.stage == ConnectionStage.KEY_RESOLUTION
            assert result.source == "system"
            assert "sk-test1" in result.key_preview
            assert "..." in result.key_preview  # Masked

    def test_key_missing(self):
        """Test when key is not found."""
        with patch.dict(os.environ, {}, clear=True):
            result = check_key_resolution()

            assert result.success is False
            assert result.stage == ConnectionStage.KEY_RESOLUTION
            assert "nao encontrada" in result.message.lower()

    def test_key_empty(self):
        """Test when key is empty."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "   "}, clear=True):
            result = check_key_resolution()

            assert result.success is False
            assert "vazia" in result.message.lower()

    def test_key_from_dotenv(self):
        """Test when key is from .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("OPENAI_API_KEY=sk-fromdotenv123\n")

            with patch.dict(os.environ, {}, clear=True):
                result = check_key_resolution(Path(tmpdir))

                assert result.success is True
                assert result.source == "dotenv"


class TestClientInitialization:
    """Test check_client_initialization function."""

    def test_client_init_success(self):
        """Test successful client initialization."""
        with patch("openai.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()

            result = check_client_initialization("sk-test123")

            assert result.success is True
            assert result.client_initialized is True
            assert result.stage == ConnectionStage.CLIENT_INIT

    def test_client_init_exception(self):
        """Test when initialization raises exception."""
        with patch("openai.OpenAI", side_effect=Exception("Init failed")):
            result = check_client_initialization("sk-test123")

            assert result.success is False
            assert result.client_initialized is False


class TestNetworkConnection:
    """Test check_network_connection function."""

    def test_network_success(self):
        """Test successful network connection."""
        mock_client = MagicMock()
        mock_client.models.list.return_value = [MagicMock(), MagicMock()]

        with patch("openai.OpenAI", return_value=mock_client):
            result = check_network_connection("sk-test123")

            assert result.success is True
            assert result.network_test_executed is True
            assert result.client_initialized is True
            assert "sucesso" in result.message.lower()

    def test_network_auth_error(self):
        """Test authentication error."""
        from openai import AuthenticationError

        mock_client = MagicMock()
        mock_error = MagicMock()
        mock_error.status_code = 401
        mock_client.models.list.side_effect = AuthenticationError(
            message="Invalid API Key",
            response=mock_error,
            body=None
        )

        with patch("openai.OpenAI", return_value=mock_client):
            result = check_network_connection("sk-invalid")

            assert result.success is False
            assert result.network_test_executed is True
            assert "autenticacao" in result.message.lower()

    def test_network_rate_limit(self):
        """Test rate limit error."""
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_error = MagicMock()
        mock_error.status_code = 429
        mock_client.models.list.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_error,
            body=None
        )

        with patch("openai.OpenAI", return_value=mock_client):
            result = check_network_connection("sk-test123")

            assert result.success is False
            assert "limite" in result.message.lower()

    def test_network_connection_error(self):
        """Test connection error."""
        from openai import APIConnectionError

        mock_client = MagicMock()
        mock_client.models.list.side_effect = APIConnectionError(
            request=MagicMock()
        )

        with patch("openai.OpenAI", return_value=mock_client):
            result = check_network_connection("sk-test123")

            assert result.success is False
            assert "rede" in result.message.lower() or "conexao" in result.message.lower()


class TestFullConnectionCheck:
    """Test check_openai_connection full pipeline."""

    def test_full_check_success(self):
        """Test full connection check success."""
        mock_client = MagicMock()
        mock_client.models.list.return_value = [MagicMock()]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890"}, clear=True):
            with patch("openai.OpenAI", return_value=mock_client):
                result = check_openai_connection()

                assert result.success is True
                assert result.stage == ConnectionStage.COMPLETED
                assert result.client_initialized is True
                assert result.network_test_executed is True

    def test_full_check_skip_network(self):
        """Test full check with network skip."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890"}, clear=True):
            with patch("openai.OpenAI", return_value=MagicMock()):
                result = check_openai_connection(skip_network_test=True)

                assert result.success is True
                assert result.client_initialized is True
                assert result.network_test_executed is False
                assert "nao executado" in result.message.lower()

    def test_full_check_key_missing(self):
        """Test full check when key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = check_openai_connection()

            assert result.success is False
            assert result.stage == ConnectionStage.KEY_RESOLUTION
            assert result.client_initialized is False

    def test_full_check_auth_failure(self):
        """Test full check with authentication failure."""
        from openai import AuthenticationError

        mock_client = MagicMock()
        mock_error = MagicMock()
        mock_error.status_code = 401
        mock_client.models.list.side_effect = AuthenticationError(
            message="Invalid",
            response=mock_error,
            body=None
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-invalid123456"}, clear=True):
            with patch("openai.OpenAI", return_value=mock_client):
                result = check_openai_connection()

                assert result.success is False
                assert result.network_test_executed is True
                assert "autenticacao" in result.message.lower()


class TestResultDetails:
    """Test result details are properly populated."""

    def test_details_on_success(self):
        """Test details are populated on success."""
        mock_client = MagicMock()
        mock_client.models.list.return_value = [MagicMock(), MagicMock(), MagicMock()]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890"}, clear=True):
            with patch("openai.OpenAI", return_value=mock_client):
                result = check_openai_connection()

                assert len(result.details) > 0
                # Should have details from all stages
                details_text = "\n".join(result.details)
                assert "---" in details_text  # Separators between stages

    def test_details_on_failure(self):
        """Test details are populated on failure."""
        with patch.dict(os.environ, {}, clear=True):
            result = check_openai_connection()

            assert len(result.details) > 0
            details_text = "\n".join(result.details)
            assert "OPENAI_API_KEY" in details_text

    def test_duration_tracked(self):
        """Test duration is tracked."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1234567890"}, clear=True):
            with patch("openai.OpenAI", return_value=MagicMock()):
                result = check_openai_connection(skip_network_test=True)

                assert result.duration_ms >= 0
