"""Central service for reading/writing the project ``.env`` file.

The GUI must never touch ``.env`` directly — it goes through this service so
that backups, ``.gitignore`` hygiene and secret masking are handled in one
place and stay consistent.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .env_file import (
    create_env_file_if_missing,
    load_env_file,
    mask_secret,
    remove_env_var,
    upsert_env_var,
)

OPENAI_KEY_NAME = "OPENAI_API_KEY"


class OpenAIKeyState(Enum):
    """Where the OpenAI key was found (configuration state, not connectivity)."""

    NOT_CONFIGURED = "not_configured"
    FOUND_IN_ENV = "found_in_env"
    FOUND_IN_SYSTEM = "found_in_system"
    FOUND_IN_BOTH = "found_in_both"


@dataclass
class OpenAIKeyStatus:
    """Snapshot of how ``OPENAI_API_KEY`` is currently configured."""

    state: OpenAIKeyState
    in_env: bool
    in_system: bool
    env_path: Path
    effective_source: str  # "system", "dotenv" or "none"
    masked_value: Optional[str] = None
    note: str = ""

    @property
    def configured(self) -> bool:
        return self.state != OpenAIKeyState.NOT_CONFIGURED


@dataclass
class EnvWriteResult:
    """Outcome of a write/remove operation on the ``.env`` file."""

    success: bool
    message: str
    backup_created: bool = False
    backup_path: Optional[Path] = None
    masked_value: Optional[str] = None
    gitignore_updated: bool = False
    details: List[str] = field(default_factory=list)


class EnvConfigService:
    """Safe, backed-up read/write access to the project ``.env`` file."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()

    # ------------------------------------------------------------------ paths
    @property
    def env_path(self) -> Path:
        return self.project_root / ".env"

    @property
    def backup_path(self) -> Path:
        return self.project_root / ".env.bak"

    @property
    def gitignore_path(self) -> Path:
        return self.project_root / ".gitignore"

    # ------------------------------------------------------------------ state
    def get_openai_status(self) -> OpenAIKeyStatus:
        """Report where the OpenAI key lives and which value will be used."""
        system_value = os.environ.get(OPENAI_KEY_NAME)
        in_system = bool(system_value and system_value.strip())

        _, values = load_env_file(self.env_path)
        env_value = values.get(OPENAI_KEY_NAME)
        in_env = bool(env_value and env_value.strip())

        if in_system and in_env:
            return OpenAIKeyStatus(
                state=OpenAIKeyState.FOUND_IN_BOTH,
                in_env=True,
                in_system=True,
                env_path=self.env_path,
                effective_source="system",
                masked_value=mask_secret(system_value),
                note=(
                    "A chave existe no ambiente do sistema e no .env. "
                    "A do ambiente do sistema será usada (tem prioridade)."
                ),
            )
        if in_system:
            return OpenAIKeyStatus(
                state=OpenAIKeyState.FOUND_IN_SYSTEM,
                in_env=False,
                in_system=True,
                env_path=self.env_path,
                effective_source="system",
                masked_value=mask_secret(system_value),
                note="Chave encontrada no ambiente do sistema.",
            )
        if in_env:
            return OpenAIKeyStatus(
                state=OpenAIKeyState.FOUND_IN_ENV,
                in_env=True,
                in_system=False,
                env_path=self.env_path,
                effective_source="dotenv",
                masked_value=mask_secret(env_value),
                note="Chave encontrada no arquivo .env do projeto.",
            )
        return OpenAIKeyStatus(
            state=OpenAIKeyState.NOT_CONFIGURED,
            in_env=False,
            in_system=False,
            env_path=self.env_path,
            effective_source="none",
            masked_value=None,
            note="OpenAI não configurada. Clique em Configurar ChatGPT/OpenAI e cole sua chave API.",
        )

    def get_openai_key_value(self) -> Optional[str]:
        """Return the effective key value (system env wins over .env), or None."""
        system_value = os.environ.get(OPENAI_KEY_NAME)
        if system_value and system_value.strip():
            return system_value.strip()
        _, values = load_env_file(self.env_path)
        env_value = values.get(OPENAI_KEY_NAME)
        if env_value and env_value.strip():
            return env_value.strip()
        return None

    # ------------------------------------------------------------------ write
    def save_openai_key(self, key: str) -> EnvWriteResult:
        """Persist ``OPENAI_API_KEY`` to ``.env`` with a backup and gitignore guard."""
        key = (key or "").strip()
        if not key:
            return EnvWriteResult(False, "Digite uma chave para salvar.")

        backup_created, backup_path = self._backup_env()
        if self.env_path.exists() is False:
            create_env_file_if_missing(self.env_path)

        if not upsert_env_var(self.env_path, OPENAI_KEY_NAME, key):
            return EnvWriteResult(
                False,
                "Erro ao gravar o arquivo .env. Verifique as permissões de escrita.",
                backup_created=backup_created,
                backup_path=backup_path,
            )

        gitignore_updated = self.ensure_env_in_gitignore()
        details = [f"Arquivo: {self.env_path}"]
        if backup_created:
            details.append(f"Backup criado: {backup_path}")
        if gitignore_updated:
            details.append(".env adicionado ao .gitignore.")
        return EnvWriteResult(
            success=True,
            message="Chave salva com sucesso no arquivo .env do projeto.",
            backup_created=backup_created,
            backup_path=backup_path,
            masked_value=mask_secret(key),
            gitignore_updated=gitignore_updated,
            details=details,
        )

    def remove_openai_key(self) -> EnvWriteResult:
        """Remove ``OPENAI_API_KEY`` from ``.env`` (keeps a backup first)."""
        if not self.env_path.exists():
            return EnvWriteResult(True, "Nenhum arquivo .env para limpar.")

        backup_created, backup_path = self._backup_env()
        if not remove_env_var(self.env_path, OPENAI_KEY_NAME):
            return EnvWriteResult(
                False,
                "Erro ao atualizar o arquivo .env. Verifique as permissões.",
                backup_created=backup_created,
                backup_path=backup_path,
            )
        details = [f"Arquivo: {self.env_path}"]
        if backup_created:
            details.append(f"Backup criado: {backup_path}")
        return EnvWriteResult(
            success=True,
            message="Chave removida do arquivo .env.",
            backup_created=backup_created,
            backup_path=backup_path,
            details=details,
        )

    def _backup_env(self) -> tuple[bool, Optional[Path]]:
        """Copy ``.env`` to ``.env.bak`` before mutating it."""
        if not self.env_path.exists():
            return False, None
        try:
            shutil.copy2(self.env_path, self.backup_path)
            return True, self.backup_path
        except OSError:
            return False, None

    # -------------------------------------------------------------- gitignore
    def is_env_gitignored(self) -> bool:
        """True when ``.env`` is already covered by ``.gitignore``."""
        if not self.gitignore_path.exists():
            return False
        try:
            content = self.gitignore_path.read_text(encoding="utf-8")
        except OSError:
            return False
        for raw in content.splitlines():
            entry = raw.strip()
            if entry in (".env", "/.env"):
                return True
        return False

    def ensure_env_in_gitignore(self) -> bool:
        """Make sure ``.env`` (and ``.env.bak``) are ignored by git.

        Returns True when the file was modified, False when nothing was needed.
        Existing comments and entries are preserved.
        """
        path = self.gitignore_path
        existing = ""
        present: set[str] = set()
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                existing = ""
            for raw in existing.splitlines():
                present.add(raw.strip())

        wanted = [".env", ".env.bak"]
        missing = [entry for entry in wanted if entry not in present and f"/{entry}" not in present]
        if not missing:
            return False

        content = existing
        if content and not content.endswith("\n"):
            content += "\n"
        if missing:
            content += "\n# AI Orchestrator: nunca commitar segredos\n"
            content += "\n".join(missing) + "\n"
        try:
            path.write_text(content, encoding="utf-8")
        except OSError:
            return False
        return True
