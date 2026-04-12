"""Tests for environment validation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.env_validator import (
    EnvironmentValidator,
    EnvKeyStatus,
    EnvValidationResult,
    validate_environment,
    get_openai_key_or_raise,
)


class TestEnvKeyStatus:
    """Test EnvKeyStatus enum."""

    def test_status_values(self):
        """Test that all status values exist."""
        assert EnvKeyStatus.OK.value == "ok"
        assert EnvKeyStatus.MISSING.value == "missing"
        assert EnvKeyStatus.EMPTY.value == "empty"


class TestEnvValidationResult:
    """Test EnvValidationResult dataclass."""

    def test_is_valid_ok(self):
        """Test is_valid returns True for OK status."""
        result = EnvValidationResult(
            key_name="TEST_KEY",
            status=EnvKeyStatus.OK,
            value_preview="sk-abc...",
            source="system",
        )
        assert result.is_valid is True

    def test_is_valid_missing(self):
        """Test is_valid returns False for MISSING status."""
        result = EnvValidationResult(
            key_name="TEST_KEY",
            status=EnvKeyStatus.MISSING,
        )
        assert result.is_valid is False

    def test_is_valid_empty(self):
        """Test is_valid returns False for EMPTY status."""
        result = EnvValidationResult(
            key_name="TEST_KEY",
            status=EnvKeyStatus.EMPTY,
        )
        assert result.is_valid is False


class TestEnvironmentValidator:
    """Test EnvironmentValidator class."""

    def test_validate_key_present(self):
        """Test validation when key is present."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test12345678"}):
            validator = EnvironmentValidator()
            result = validator.validate_openai_key()

            assert result.status == EnvKeyStatus.OK
            assert result.is_valid is True
            assert result.value_preview is not None
            assert "sk-test1" in result.value_preview

    def test_validate_key_missing(self):
        """Test validation when key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Also clear the key if it exists
            os.environ.pop("OPENAI_API_KEY", None)

            validator = EnvironmentValidator()
            result = validator.validate_openai_key()

            assert result.status == EnvKeyStatus.MISSING
            assert result.is_valid is False

    def test_validate_key_empty(self):
        """Test validation when key is empty."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            validator = EnvironmentValidator()
            result = validator.validate_openai_key()

            assert result.status == EnvKeyStatus.EMPTY
            assert result.is_valid is False

    def test_validate_key_whitespace_only(self):
        """Test validation when key is whitespace only."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "   "}):
            validator = EnvironmentValidator()
            result = validator.validate_openai_key()

            assert result.status == EnvKeyStatus.EMPTY
            assert result.is_valid is False

    def test_load_dotenv_file(self):
        """Test loading .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .env file
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST_VAR=test_value\n")

            validator = EnvironmentValidator(Path(tmpdir))
            loaded, path = validator.load_dotenv()

            assert loaded is True
            assert path == env_path

    def test_load_dotenv_missing(self):
        """Test when .env file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = EnvironmentValidator(Path(tmpdir))
            loaded, path = validator.load_dotenv()

            assert loaded is False
            assert path is None

    def test_full_diagnostics(self):
        """Test full diagnostics."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test12345678"}):
            validator = EnvironmentValidator()
            diag = validator.run_full_diagnostics()

            assert diag.openai_key.is_valid is True
            assert diag.system_info is not None
            assert "Python" in diag.system_info
            assert diag.is_ready is True

    def test_full_diagnostics_not_ready(self):
        """Test diagnostics when not ready."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)

            validator = EnvironmentValidator()
            diag = validator.run_full_diagnostics()

            assert diag.openai_key.is_valid is False
            assert diag.is_ready is False

    def test_get_help_message_valid(self):
        """Test help message for valid key."""
        validator = EnvironmentValidator()
        result = EnvValidationResult(
            key_name="OPENAI_API_KEY",
            status=EnvKeyStatus.OK,
            source="system",
        )

        help_msg = validator.get_help_message(result)
        assert "configured correctly" in help_msg

    def test_get_help_message_missing(self):
        """Test help message for missing key."""
        validator = EnvironmentValidator()
        result = EnvValidationResult(
            key_name="OPENAI_API_KEY",
            status=EnvKeyStatus.MISSING,
        )

        help_msg = validator.get_help_message(result)
        assert "not found" in help_msg
        assert "PowerShell" in help_msg
        assert ".env" in help_msg
        assert "restart" in help_msg.lower()

    def test_get_help_message_empty(self):
        """Test help message for empty key."""
        validator = EnvironmentValidator()
        result = EnvValidationResult(
            key_name="OPENAI_API_KEY",
            status=EnvKeyStatus.EMPTY,
        )

        help_msg = validator.get_help_message(result)
        assert "empty" in help_msg


class TestValidateEnvironment:
    """Test validate_environment helper."""

    def test_validate_environment_helper(self):
        """Test the quick helper function."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test12345678"}):
            diag = validate_environment()

            assert diag is not None
            assert diag.openai_key.is_valid is True


class TestGetOpenaiKeyOrRaise:
    """Test get_openai_key_or_raise function."""

    def test_get_key_success(self):
        """Test getting key when present."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test12345678"}):
            key = get_openai_key_or_raise()
            assert key == "sk-test12345678"

    def test_get_key_missing_raises(self):
        """Test that missing key raises EnvironmentError."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)

            with pytest.raises(EnvironmentError) as exc_info:
                get_openai_key_or_raise()

            error_msg = str(exc_info.value)
            assert "not configured" in error_msg
            assert "PowerShell" in error_msg

    def test_get_key_empty_raises(self):
        """Test that empty key raises EnvironmentError."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with pytest.raises(EnvironmentError) as exc_info:
                get_openai_key_or_raise()

            assert "not configured" in str(exc_info.value)


class TestDotenvIntegration:
    """Test .env file integration."""

    def test_dotenv_loads_key(self):
        """Test that .env file is loaded and key is available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .env file with key
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("OPENAI_API_KEY=sk-from-dotenv-12345\n")

            # Clear existing key
            original = os.environ.pop("OPENAI_API_KEY", None)

            try:
                validator = EnvironmentValidator(Path(tmpdir))
                validator.load_dotenv()
                result = validator.validate_openai_key()

                assert result.is_valid is True
                # Source should indicate .env
                # (depends on dotenv behavior)
            finally:
                # Restore original
                if original:
                    os.environ["OPENAI_API_KEY"] = original
                else:
                    os.environ.pop("OPENAI_API_KEY", None)
