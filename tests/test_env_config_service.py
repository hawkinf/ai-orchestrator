"""Tests for EnvConfigService — safe .env read/write for the GUI."""

import pytest

from orchestrator.env_config_service import (
    EnvConfigService,
    OpenAIKeyState,
)

REAL_KEY = "sk-realsecret1234567890abcdefghijklmnop"


@pytest.fixture(autouse=True)
def _no_system_key(monkeypatch):
    """Ensure the host's OPENAI_API_KEY never leaks into these tests."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestSaveOpenAIKey:
    def test_creates_key_in_new_env(self, tmp_path):
        service = EnvConfigService(tmp_path)
        result = service.save_openai_key(REAL_KEY)
        assert result.success
        content = (tmp_path / ".env").read_text()
        assert f"OPENAI_API_KEY={REAL_KEY}" in content

    def test_updates_existing_key(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("OPENAI_API_KEY=sk-old-value\n")
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        content = env.read_text()
        assert REAL_KEY in content
        assert "sk-old-value" not in content

    def test_does_not_duplicate_key(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("OPENAI_API_KEY=sk-old\n")
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        content = env.read_text()
        assert content.count("OPENAI_API_KEY=") == 1

    def test_preserves_other_variables(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("FOO=bar\nOPENAI_API_KEY=sk-old\nBAZ=qux\n")
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        content = env.read_text()
        assert "FOO=bar" in content
        assert "BAZ=qux" in content

    def test_preserves_comments(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("# important comment\nOPENAI_API_KEY=sk-old\n")
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        assert "# important comment" in env.read_text()

    def test_creates_backup(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("OPENAI_API_KEY=sk-old\n")
        service = EnvConfigService(tmp_path)
        result = service.save_openai_key(REAL_KEY)
        assert result.backup_created
        assert (tmp_path / ".env.bak").exists()
        assert "sk-old" in (tmp_path / ".env.bak").read_text()

    def test_no_backup_when_no_existing_env(self, tmp_path):
        service = EnvConfigService(tmp_path)
        result = service.save_openai_key(REAL_KEY)
        assert result.backup_created is False

    def test_empty_key_rejected(self, tmp_path):
        service = EnvConfigService(tmp_path)
        result = service.save_openai_key("   ")
        assert result.success is False

    def test_key_never_appears_in_result(self, tmp_path):
        """The raw key must never be echoed back in the write result."""
        service = EnvConfigService(tmp_path)
        result = service.save_openai_key(REAL_KEY)
        blob = " ".join([result.message, *(result.details or [])])
        assert REAL_KEY not in blob
        assert result.masked_value is not None
        assert REAL_KEY not in result.masked_value
        assert result.masked_value.endswith("...")


class TestGitignore:
    def test_creates_gitignore_when_missing(self, tmp_path):
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        gi = (tmp_path / ".gitignore").read_text()
        assert ".env" in gi.splitlines()

    def test_appends_to_existing_gitignore(self, tmp_path):
        gi = tmp_path / ".gitignore"
        gi.write_text("__pycache__/\n")
        service = EnvConfigService(tmp_path)
        changed = service.ensure_env_in_gitignore()
        assert changed is True
        lines = gi.read_text().splitlines()
        assert "__pycache__/" in lines  # preserved
        assert ".env" in lines

    def test_does_not_duplicate_env_entry(self, tmp_path):
        gi = tmp_path / ".gitignore"
        gi.write_text(".env\n.env.bak\n")
        service = EnvConfigService(tmp_path)
        changed = service.ensure_env_in_gitignore()
        assert changed is False
        assert gi.read_text().count(".env\n") == 1

    def test_is_env_gitignored(self, tmp_path):
        service = EnvConfigService(tmp_path)
        assert service.is_env_gitignored() is False
        (tmp_path / ".gitignore").write_text(".env\n")
        assert service.is_env_gitignored() is True


class TestOpenAIStatus:
    def test_not_configured(self, tmp_path):
        service = EnvConfigService(tmp_path)
        status = service.get_openai_status()
        assert status.state == OpenAIKeyState.NOT_CONFIGURED
        assert status.configured is False

    def test_found_in_env(self, tmp_path):
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        status = service.get_openai_status()
        assert status.state == OpenAIKeyState.FOUND_IN_ENV
        assert status.in_env is True
        assert status.effective_source == "dotenv"
        # Masked, never the full key.
        assert status.masked_value and REAL_KEY not in status.masked_value

    def test_found_in_system(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", REAL_KEY)
        service = EnvConfigService(tmp_path)
        status = service.get_openai_status()
        assert status.state == OpenAIKeyState.FOUND_IN_SYSTEM
        assert status.in_system is True
        assert status.effective_source == "system"

    def test_found_in_both_warns_about_priority(self, tmp_path, monkeypatch):
        service = EnvConfigService(tmp_path)
        service.save_openai_key(REAL_KEY)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-system-value-xxxxxxxxxxxx")
        status = service.get_openai_status()
        assert status.state == OpenAIKeyState.FOUND_IN_BOTH
        assert status.effective_source == "system"
        assert "prioridade" in status.note.lower()


class TestRemoveOpenAIKey:
    def test_removes_key_and_backs_up(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("FOO=bar\nOPENAI_API_KEY=sk-old\n")
        service = EnvConfigService(tmp_path)
        result = service.remove_openai_key()
        assert result.success
        content = env.read_text()
        assert "OPENAI_API_KEY" not in content
        assert "FOO=bar" in content
        assert (tmp_path / ".env.bak").exists()

    def test_remove_when_no_env(self, tmp_path):
        service = EnvConfigService(tmp_path)
        result = service.remove_openai_key()
        assert result.success is True
