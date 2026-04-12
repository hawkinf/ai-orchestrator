"""Tests for env_file module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.env_file import (
    EnvLine,
    EnvResolution,
    mask_secret,
    parse_env_line,
    load_env_file,
    format_env_line,
    upsert_env_var,
    remove_env_var,
    get_env_resolution,
    create_env_file_if_missing,
)


class TestMaskSecret:
    """Test mask_secret function."""

    def test_mask_normal_key(self):
        """Test masking a normal API key."""
        key = "sk-test1234567890abcdef"
        result = mask_secret(key)
        assert result == "sk-test1..."
        assert len(result) == 11

    def test_mask_short_key(self):
        """Test masking a short key."""
        key = "abc"
        result = mask_secret(key)
        assert result == "ab..."

    def test_mask_very_short_key(self):
        """Test masking a very short key."""
        key = "ab"
        result = mask_secret(key)
        assert result == "***"

    def test_mask_empty_key(self):
        """Test masking empty string."""
        result = mask_secret("")
        assert result == ""

    def test_mask_custom_visible_chars(self):
        """Test with custom visible chars."""
        key = "sk-abcdefghij"
        result = mask_secret(key, visible_chars=4)
        assert result == "sk-a..."


class TestParseEnvLine:
    """Test parse_env_line function."""

    def test_parse_simple_var(self):
        """Test parsing simple KEY=value."""
        line = "API_KEY=sk-test123"
        result = parse_env_line(line)

        assert result.key == "API_KEY"
        assert result.value == "sk-test123"
        assert not result.is_comment
        assert not result.is_empty

    def test_parse_quoted_value(self):
        """Test parsing KEY="value with spaces"."""
        line = 'DATABASE_URL="postgres://localhost/db"'
        result = parse_env_line(line)

        assert result.key == "DATABASE_URL"
        assert result.value == "postgres://localhost/db"

    def test_parse_single_quoted_value(self):
        """Test parsing KEY='value'."""
        line = "SECRET='my secret'"
        result = parse_env_line(line)

        assert result.key == "SECRET"
        assert result.value == "my secret"

    def test_parse_empty_line(self):
        """Test parsing empty line."""
        result = parse_env_line("")
        assert result.is_empty
        assert result.key is None

    def test_parse_whitespace_line(self):
        """Test parsing whitespace-only line."""
        result = parse_env_line("   ")
        assert result.is_empty

    def test_parse_comment(self):
        """Test parsing comment line."""
        result = parse_env_line("# This is a comment")
        assert result.is_comment
        assert result.key is None

    def test_parse_comment_with_spaces(self):
        """Test parsing comment with leading spaces."""
        result = parse_env_line("  # Indented comment")
        assert result.is_comment

    def test_parse_empty_value(self):
        """Test parsing KEY= (empty value)."""
        line = "EMPTY_VAR="
        result = parse_env_line(line)

        assert result.key == "EMPTY_VAR"
        assert result.value == ""


class TestLoadEnvFile:
    """Test load_env_file function."""

    def test_load_simple_file(self):
        """Test loading a simple .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("KEY1=value1\nKEY2=value2\n")

            lines, values = load_env_file(env_path)

            assert len(lines) == 2
            assert values["KEY1"] == "value1"
            assert values["KEY2"] == "value2"

    def test_load_file_with_comments(self):
        """Test loading file with comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("# Comment\nKEY=value\n")

            lines, values = load_env_file(env_path)

            assert len(lines) == 2
            assert lines[0].is_comment
            assert values["KEY"] == "value"

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        lines, values = load_env_file(Path("/nonexistent/.env"))

        assert lines == []
        assert values == {}


class TestFormatEnvLine:
    """Test format_env_line function."""

    def test_format_simple_value(self):
        """Test formatting simple value."""
        result = format_env_line("KEY", "value")
        assert result == "KEY=value"

    def test_format_value_with_spaces(self):
        """Test formatting value with spaces."""
        result = format_env_line("KEY", "value with spaces")
        assert result == 'KEY="value with spaces"'

    def test_format_value_with_quotes(self):
        """Test formatting value with quotes."""
        result = format_env_line("KEY", 'value "quoted"')
        assert result == 'KEY="value \\"quoted\\""'


class TestUpsertEnvVar:
    """Test upsert_env_var function."""

    def test_insert_new_var(self):
        """Test inserting a new variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("EXISTING=value\n")

            result = upsert_env_var(env_path, "NEW_VAR", "new_value")

            assert result is True
            content = env_path.read_text()
            assert "EXISTING=value" in content
            assert "NEW_VAR=new_value" in content

    def test_update_existing_var(self):
        """Test updating an existing variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("KEY=old_value\n")

            result = upsert_env_var(env_path, "KEY", "new_value")

            assert result is True
            content = env_path.read_text()
            assert "KEY=new_value" in content
            assert "old_value" not in content

    def test_preserve_comments(self):
        """Test that comments are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("# Important comment\nKEY=value\n")

            result = upsert_env_var(env_path, "KEY", "new_value")

            assert result is True
            content = env_path.read_text()
            assert "# Important comment" in content

    def test_create_new_file(self):
        """Test creating a new .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            result = upsert_env_var(env_path, "KEY", "value")

            assert result is True
            assert env_path.exists()
            content = env_path.read_text()
            assert "KEY=value" in content


class TestRemoveEnvVar:
    """Test remove_env_var function."""

    def test_remove_existing_var(self):
        """Test removing an existing variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("KEY1=value1\nKEY2=value2\n")

            result = remove_env_var(env_path, "KEY1")

            assert result is True
            content = env_path.read_text()
            assert "KEY1" not in content
            assert "KEY2=value2" in content

    def test_remove_nonexistent_var(self):
        """Test removing a variable that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("KEY=value\n")

            result = remove_env_var(env_path, "NONEXISTENT")

            assert result is True
            content = env_path.read_text()
            assert "KEY=value" in content

    def test_remove_from_nonexistent_file(self):
        """Test removing from non-existent file."""
        result = remove_env_var(Path("/nonexistent/.env"), "KEY")
        assert result is True


class TestGetEnvResolution:
    """Test get_env_resolution function."""

    def test_resolution_from_system(self):
        """Test resolution when key is in system environment."""
        with patch.dict(os.environ, {"TEST_KEY": "system_value"}):
            result = get_env_resolution("TEST_KEY")

            assert result.source == "system"
            assert result.value == "system_value"
            assert result.system_value == "system_value"
            assert "priority" in result.priority_note.lower()

    def test_resolution_from_dotenv(self):
        """Test resolution when key is only in .env."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST_KEY=dotenv_value\n")

            # Ensure key is not in system env
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("TEST_KEY", None)

                result = get_env_resolution("TEST_KEY", env_path)

                assert result.source == "dotenv"
                assert result.value == "dotenv_value"
                assert result.dotenv_value == "dotenv_value"
                assert result.dotenv_path == env_path

    def test_resolution_not_found(self):
        """Test resolution when key is not found."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NONEXISTENT_KEY", None)

            result = get_env_resolution("NONEXISTENT_KEY")

            assert result.source == "none"
            assert result.value is None

    def test_system_takes_priority_over_dotenv(self):
        """Test that system env takes priority over .env."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST_KEY=dotenv_value\n")

            with patch.dict(os.environ, {"TEST_KEY": "system_value"}):
                result = get_env_resolution("TEST_KEY", env_path)

                assert result.source == "system"
                assert result.value == "system_value"
                assert result.dotenv_value == "dotenv_value"


class TestCreateEnvFileIfMissing:
    """Test create_env_file_if_missing function."""

    def test_create_new_file(self):
        """Test creating a new .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            result = create_env_file_if_missing(env_path)

            assert result is True
            assert env_path.exists()
            content = env_path.read_text()
            assert "OPENAI_API_KEY" in content

    def test_dont_overwrite_existing(self):
        """Test that existing file is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("CUSTOM=value\n")

            result = create_env_file_if_missing(env_path)

            assert result is True
            content = env_path.read_text()
            assert content == "CUSTOM=value\n"

    def test_create_with_nested_path(self):
        """Test creating file in nested directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "nested" / "dir" / ".env"

            result = create_env_file_if_missing(env_path)

            assert result is True
            assert env_path.exists()
