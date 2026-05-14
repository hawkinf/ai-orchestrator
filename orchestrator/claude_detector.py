"""Detection and health-check for the Claude Code CLI executor.

Centralizes the logic the GUI uses to find, validate and report on the
``claude`` command so that the UI never has to call ``subprocess`` directly.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ClaudeStatus(Enum):
    """Possible states of the Claude Code CLI."""

    NOT_FOUND = "not_found"
    FOUND = "found"
    RESPONDS_OK = "responds_ok"
    LOGIN_PENDING = "login_pending"
    ERROR = "error"


# Friendly, pt-BR install hint for macOS (and any platform with npm).
MACOS_INSTALL_HINT = (
    "Claude não encontrado. Instale o Claude Code ou selecione o executável "
    "manualmente.\n\nNo macOS:\n"
    "  npm install -g @anthropic-ai/claude-code\n"
    "  claude"
)


@dataclass
class ClaudeDetectionResult:
    """Result of detecting/testing the Claude Code CLI."""

    status: ClaudeStatus
    command: str
    resolved_path: Optional[str] = None
    version: Optional[str] = None
    message: str = ""
    details: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when Claude is installed and responds correctly."""
        return self.status == ClaudeStatus.RESPONDS_OK

    @property
    def found(self) -> bool:
        """True when a Claude executable was located on disk."""
        return self.status != ClaudeStatus.NOT_FOUND

    def to_dict(self) -> dict:
        """Serialize for cross-thread signal delivery."""
        return {
            "status": self.status.value,
            "command": self.command,
            "resolved_path": self.resolved_path,
            "version": self.version,
            "message": self.message,
            "details": list(self.details),
            "ok": self.ok,
            "found": self.found,
        }


class ClaudeExecutorDetector:
    """Locate and validate the Claude Code CLI without blocking on I/O.

    The actual ``subprocess`` calls are short-lived and timeout-bounded; the
    GUI still runs :meth:`test` on a worker thread so the window never freezes.
    """

    def __init__(self, command: str = "claude", working_dir: Optional[Path] = None):
        self.command = (command or "claude").strip() or "claude"
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def detect_path(self, command: Optional[str] = None) -> Optional[str]:
        """Resolve ``command`` to an absolute path, or return None if missing.

        Accepts either a bare command name (resolved via ``shutil.which``) or an
        explicit path to a binary selected by the user.
        """
        cmd = (command or self.command).strip()
        if not cmd:
            return None

        candidate = Path(cmd).expanduser()
        looks_like_path = candidate.is_absolute() or any(sep in cmd for sep in ("/", "\\"))
        if looks_like_path:
            if candidate.exists() and candidate.is_file():
                return str(candidate)
            return None

        return shutil.which(cmd)

    def detect(self, command: Optional[str] = None) -> ClaudeDetectionResult:
        """Lightweight check: is a Claude executable present? (no subprocess)."""
        cmd = (command or self.command).strip()
        resolved = self.detect_path(cmd)
        if resolved is None:
            return ClaudeDetectionResult(
                status=ClaudeStatus.NOT_FOUND,
                command=cmd,
                message="Claude não encontrado.",
                details=[f"Comando: {cmd}", MACOS_INSTALL_HINT],
            )
        return ClaudeDetectionResult(
            status=ClaudeStatus.FOUND,
            command=cmd,
            resolved_path=resolved,
            message="Claude encontrado.",
            details=[f"Comando: {cmd}", f"Caminho: {resolved}"],
        )

    def test(self, command: Optional[str] = None, timeout: int = 15) -> ClaudeDetectionResult:
        """Run ``<claude> --version`` with a timeout and classify the result."""
        cmd = (command or self.command).strip()
        resolved = self.detect_path(cmd)
        details: List[str] = [f"Comando: {cmd}"]
        if resolved:
            details.append(f"Caminho: {resolved}")

        if resolved is None:
            return ClaudeDetectionResult(
                status=ClaudeStatus.NOT_FOUND,
                command=cmd,
                message="Claude não encontrado. Instale o Claude Code ou selecione o executável manualmente.",
                details=details + [MACOS_INSTALL_HINT],
            )

        try:
            proc = subprocess.run(
                [resolved, "--version"],
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ClaudeDetectionResult(
                status=ClaudeStatus.ERROR,
                command=cmd,
                resolved_path=resolved,
                message=f"Tempo esgotado ao testar o Claude (timeout de {timeout}s).",
                details=details + [f"Timeout após {timeout}s. Verifique a instalação do Claude."],
            )
        except FileNotFoundError:
            return ClaudeDetectionResult(
                status=ClaudeStatus.NOT_FOUND,
                command=cmd,
                message="Claude não encontrado. Instale o Claude Code ou selecione o executável manualmente.",
                details=details + [MACOS_INSTALL_HINT],
            )
        except OSError as exc:
            return ClaudeDetectionResult(
                status=ClaudeStatus.ERROR,
                command=cmd,
                resolved_path=resolved,
                message="Erro ao executar o Claude.",
                details=details + [str(exc)],
            )

        combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        lowered = combined.lower()

        if proc.returncode == 0:
            version = (proc.stdout.strip() or proc.stderr.strip()) or None
            return ClaudeDetectionResult(
                status=ClaudeStatus.RESPONDS_OK,
                command=cmd,
                resolved_path=resolved,
                version=version,
                message="Claude responde OK.",
                details=details + ([f"Versão: {version}"] if version else ["Claude respondeu sem erros."]),
            )

        login_markers = ("login", "log in", "logged in", "authenticate", "not authenticated", "unauthorized")
        if any(marker in lowered for marker in login_markers):
            return ClaudeDetectionResult(
                status=ClaudeStatus.LOGIN_PENDING,
                command=cmd,
                resolved_path=resolved,
                message="Claude instalado, mas o login está pendente.",
                details=details + [combined or "É necessário fazer login no Claude."],
            )

        npm_markers = ("node", "npm")
        extra: List[str] = []
        if any(marker in lowered for marker in npm_markers):
            extra.append("Verifique se o Node.js/npm estão instalados corretamente.")
        return ClaudeDetectionResult(
            status=ClaudeStatus.ERROR,
            command=cmd,
            resolved_path=resolved,
            message="Erro ao executar o Claude.",
            details=details + ([combined] if combined else [f"Código de saída {proc.returncode}."]) + extra,
        )

    @staticmethod
    def install_instructions() -> str:
        """Return the pt-BR install hint shown when Claude is missing."""
        return MACOS_INSTALL_HINT
