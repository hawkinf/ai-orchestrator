"""Aggregated service for configuring and testing AI connections.

This is the single entry point the GUI uses for the "Conexões IA" experience:
it bundles ``.env`` management (OpenAI key), Claude CLI detection and the
OpenAI connectivity test behind one object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .claude_detector import ClaudeDetectionResult, ClaudeExecutorDetector, ClaudeStatus
from .engine_health import (
    ConnectionTestResult,
    check_client_initialization,
    check_network_connection,
    check_openai_connection,
)
from .env_config_service import EnvConfigService, EnvWriteResult, OpenAIKeyStatus


class OpenAIConnectionTester:
    """Lightweight, timeout-bounded OpenAI connectivity checks.

    Wraps :mod:`orchestrator.engine_health` so callers get one stable surface
    and never have to import the lower-level health helpers directly. Errors
    are already sanitized by ``engine_health`` so API keys never leak.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()

    def test(self, skip_network: bool = False, timeout_seconds: int = 10) -> ConnectionTestResult:
        """Test the key resolved from the system env / project ``.env``."""
        return check_openai_connection(
            project_root=self.project_root,
            skip_network_test=skip_network,
            timeout_seconds=timeout_seconds,
        )

    def test_key(
        self,
        api_key: str,
        skip_network: bool = False,
        timeout_seconds: int = 10,
    ) -> ConnectionTestResult:
        """Test an explicit key value (e.g. one just typed in the dialog)."""
        init_result = check_client_initialization(api_key or "")
        if not init_result.success or skip_network:
            return init_result
        return check_network_connection(api_key, timeout_seconds)


class AIConnectionService:
    """One object that owns OpenAI and Claude configuration + testing.

    The GUI holds a single instance and calls through it; nothing in the UI
    layer reads or writes ``.env``, resolves ``claude`` or builds OpenAI
    clients on its own.
    """

    def __init__(self, project_root: Optional[Path] = None, claude_command: str = "claude"):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.env = EnvConfigService(self.project_root)
        self.claude = ClaudeExecutorDetector(claude_command, self.project_root)
        self.openai = OpenAIConnectionTester(self.project_root)

    # ----------------------------------------------------------- OpenAI side
    def openai_status(self) -> OpenAIKeyStatus:
        return self.env.get_openai_status()

    def save_openai_key(self, key: str) -> EnvWriteResult:
        return self.env.save_openai_key(key)

    def remove_openai_key(self) -> EnvWriteResult:
        return self.env.remove_openai_key()

    def test_openai(self, skip_network: bool = False, timeout_seconds: int = 10) -> ConnectionTestResult:
        return self.openai.test(skip_network=skip_network, timeout_seconds=timeout_seconds)

    def test_openai_key(
        self,
        api_key: str,
        skip_network: bool = False,
        timeout_seconds: int = 10,
    ) -> ConnectionTestResult:
        return self.openai.test_key(api_key, skip_network=skip_network, timeout_seconds=timeout_seconds)

    # ----------------------------------------------------------- Claude side
    def set_claude_command(self, command: str) -> None:
        """Update the command used for subsequent Claude detection/tests."""
        self.claude = ClaudeExecutorDetector(command, self.project_root)

    def detect_claude(self, command: Optional[str] = None) -> ClaudeDetectionResult:
        return self.claude.detect(command)

    def test_claude(self, command: Optional[str] = None, timeout: int = 15) -> ClaudeDetectionResult:
        return self.claude.test(command, timeout=timeout)

    def claude_install_instructions(self) -> str:
        return self.claude.install_instructions()


__all__ = [
    "AIConnectionService",
    "OpenAIConnectionTester",
    "ClaudeDetectionResult",
    "ClaudeStatus",
]
