"""Tests for the Claude Code CLI detector service."""

import subprocess
import sys
from types import SimpleNamespace

import pytest

from orchestrator.claude_detector import (
    ClaudeExecutorDetector,
    ClaudeStatus,
)


def _fake_proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class TestDetectPath:
    def test_detect_via_simulated_path(self, monkeypatch):
        """A bare command is resolved through shutil.which."""
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude" if cmd == "claude" else None,
        )
        detector = ClaudeExecutorDetector("claude")
        assert detector.detect_path() == "/usr/local/bin/claude"

    def test_detect_returns_none_when_absent(self, monkeypatch):
        monkeypatch.setattr("orchestrator.claude_detector.shutil.which", lambda cmd: None)
        detector = ClaudeExecutorDetector("claude")
        assert detector.detect_path() is None

    def test_accepts_manual_path(self, tmp_path):
        """An explicit path to a binary is accepted without shutil.which."""
        fake_bin = tmp_path / "claude"
        fake_bin.write_text("#!/bin/sh\necho 1.0.0\n")
        detector = ClaudeExecutorDetector(str(fake_bin))
        assert detector.detect_path() == str(fake_bin)

    def test_manual_path_missing_returns_none(self, tmp_path):
        detector = ClaudeExecutorDetector(str(tmp_path / "does-not-exist"))
        assert detector.detect_path() is None


class TestDetect:
    def test_detect_found(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude",
        )
        result = ClaudeExecutorDetector("claude").detect()
        assert result.status == ClaudeStatus.FOUND
        assert result.found is True
        assert result.resolved_path == "/usr/local/bin/claude"

    def test_detect_not_found_is_friendly(self, monkeypatch):
        monkeypatch.setattr("orchestrator.claude_detector.shutil.which", lambda cmd: None)
        result = ClaudeExecutorDetector("claude").detect()
        assert result.status == ClaudeStatus.NOT_FOUND
        assert "não encontrado" in result.message.lower()
        # Friendly install hint must be available.
        joined = "\n".join(result.details)
        assert "npm install -g @anthropic-ai/claude-code" in joined


class TestTest:
    def test_responds_ok(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude",
        )
        monkeypatch.setattr(
            "orchestrator.claude_detector.subprocess.run",
            lambda *a, **k: _fake_proc(returncode=0, stdout="1.2.3 (Claude Code)"),
        )
        result = ClaudeExecutorDetector("claude").test()
        assert result.status == ClaudeStatus.RESPONDS_OK
        assert result.ok is True
        assert result.version == "1.2.3 (Claude Code)"

    def test_login_pending(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude",
        )
        monkeypatch.setattr(
            "orchestrator.claude_detector.subprocess.run",
            lambda *a, **k: _fake_proc(returncode=1, stderr="Please log in to continue"),
        )
        result = ClaudeExecutorDetector("claude").test()
        assert result.status == ClaudeStatus.LOGIN_PENDING
        assert "login" in result.message.lower()

    def test_error_on_nonzero(self, monkeypatch):
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude",
        )
        monkeypatch.setattr(
            "orchestrator.claude_detector.subprocess.run",
            lambda *a, **k: _fake_proc(returncode=2, stderr="unexpected failure"),
        )
        result = ClaudeExecutorDetector("claude").test()
        assert result.status == ClaudeStatus.ERROR

    def test_timeout_does_not_hang(self, monkeypatch):
        """A subprocess timeout is caught and reported, never propagated."""
        monkeypatch.setattr(
            "orchestrator.claude_detector.shutil.which",
            lambda cmd: "/usr/local/bin/claude",
        )

        def _raise_timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

        monkeypatch.setattr("orchestrator.claude_detector.subprocess.run", _raise_timeout)
        result = ClaudeExecutorDetector("claude").test(timeout=1)
        assert result.status == ClaudeStatus.ERROR
        assert "tempo" in result.message.lower() or "timeout" in result.message.lower()

    def test_not_found_returns_friendly_error(self, monkeypatch):
        monkeypatch.setattr("orchestrator.claude_detector.shutil.which", lambda cmd: None)
        result = ClaudeExecutorDetector("claude").test()
        assert result.status == ClaudeStatus.NOT_FOUND
        assert "selecione o executável manualmente" in result.message.lower()

    def test_does_not_break_on_macos_when_command_missing(self):
        """Calling test() with a bogus command must not raise on any platform."""
        result = ClaudeExecutorDetector("definitely-not-a-real-cmd-xyz-123").test()
        assert result.status == ClaudeStatus.NOT_FOUND


def test_install_instructions_static():
    text = ClaudeExecutorDetector.install_instructions()
    assert "npm install -g @anthropic-ai/claude-code" in text


def test_to_dict_roundtrip(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.claude_detector.shutil.which",
        lambda cmd: "/usr/local/bin/claude",
    )
    data = ClaudeExecutorDetector("claude").detect().to_dict()
    assert data["status"] == ClaudeStatus.FOUND.value
    assert data["resolved_path"] == "/usr/local/bin/claude"
    assert data["found"] is True
