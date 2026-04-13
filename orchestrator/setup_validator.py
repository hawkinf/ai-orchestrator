"""Reusable setup validation for onboarding and configuration UX."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .claude_executor import ClaudeExecutor
from .engine_health import (
    check_client_initialization,
    check_key_resolution,
    check_network_connection,
)
from .git_ops import GitOperations


@dataclass
class SetupCheckResult:
    """Result of a single setup requirement check."""

    key: str
    title: str
    ok: bool
    required: bool
    summary: str
    details: list[str] = field(default_factory=list)
    action_hint: str = ""


@dataclass
class SetupValidationResult:
    """Aggregated setup validation state."""

    checks: list[SetupCheckResult]

    @property
    def blockers(self) -> list[SetupCheckResult]:
        return [check for check in self.checks if check.required and not check.ok]

    @property
    def warnings(self) -> list[SetupCheckResult]:
        return [check for check in self.checks if not check.required and not check.ok]

    @property
    def is_ready(self) -> bool:
        return not self.blockers

    def by_key(self, key: str) -> Optional[SetupCheckResult]:
        return next((check for check in self.checks if check.key == key), None)


class SetupValidator:
    """Validate the minimum recommended configuration."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()

    def check_project(self, project_path: Path) -> SetupCheckResult:
        project_path = Path(project_path).resolve()
        details = [f"Projeto: {project_path}"]

        if not project_path.exists():
            return SetupCheckResult(
                key="project_path",
                title="Projeto",
                ok=False,
                required=True,
                summary="Diretório do projeto não encontrado.",
                details=details,
                action_hint="Escolha uma pasta de projeto válida.",
            )

        if not project_path.is_dir():
            return SetupCheckResult(
                key="project_path",
                title="Projeto",
                ok=False,
                required=True,
                summary="O caminho informado não é uma pasta.",
                details=details,
                action_hint="Selecione a pasta raiz do projeto.",
            )

        return SetupCheckResult(
            key="project_path",
            title="Projeto",
            ok=True,
            required=True,
            summary="Projeto pronto para uso.",
            details=details,
        )

    def check_profile(self, profile: str) -> SetupCheckResult:
        allowed = {"flutter", "python", "generic"}
        ok = profile in allowed
        return SetupCheckResult(
            key="profile",
            title="Perfil",
            ok=ok,
            required=True,
            summary=f"Perfil ativo: {profile}" if ok else "Escolha um perfil compatível.",
            details=[f"Perfis disponíveis: {', '.join(sorted(allowed))}"],
            action_hint="" if ok else "Escolha flutter, python ou generic.",
        )

    def check_workspace(self, workspace_path: Path) -> SetupCheckResult:
        workspace_path = Path(workspace_path).resolve()
        details = [f"Workspace: {workspace_path}"]

        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            logs_dir = workspace_path / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            test_file = logs_dir / ".setup_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except Exception as exc:
            details.append(f"Erro: {exc}")
            return SetupCheckResult(
                key="workspace",
                title="Workspace",
                ok=False,
                required=True,
                summary="Workspace sem permissão de escrita.",
                details=details,
                action_hint="Escolha uma pasta onde o app possa criar logs e runs.",
            )

        return SetupCheckResult(
            key="workspace",
            title="Workspace",
            ok=True,
            required=True,
            summary="Workspace acessível.",
            details=details,
        )

    def check_openai(
        self,
        project_path: Path,
        explicit_api_key: Optional[str] = None,
        network_test: bool = False,
    ) -> SetupCheckResult:
        details: list[str] = []

        if explicit_api_key:
            init_result = check_client_initialization(explicit_api_key)
            details.extend(init_result.details)
            if not init_result.success:
                return SetupCheckResult(
                    key="openai",
                    title="OpenAI",
                    ok=False,
                    required=True,
                    summary=init_result.message or "Falha ao validar a chave da OpenAI.",
                    details=details,
                    action_hint="Revise a chave da OpenAI e tente novamente.",
                )

            if network_test:
                network_result = check_network_connection(explicit_api_key)
                details.extend(network_result.details)
                return SetupCheckResult(
                    key="openai",
                    title="OpenAI",
                    ok=network_result.success,
                    required=True,
                    summary=network_result.message,
                    details=details,
                    action_hint="" if network_result.success else "Teste a chave novamente ou revise a conectividade.",
                )

            return SetupCheckResult(
                key="openai",
                title="OpenAI",
                ok=True,
                required=True,
                summary="Chave da OpenAI validada.",
                details=details,
            )

        resolution = check_key_resolution(Path(project_path))
        details.extend(resolution.details)
        if not resolution.success:
            return SetupCheckResult(
                key="openai",
                title="OpenAI",
                ok=False,
                required=True,
                summary=resolution.message or "Chave da OpenAI ausente.",
                details=details,
                action_hint="Configure OPENAI_API_KEY na GUI ou no arquivo .env.",
            )

        return SetupCheckResult(
            key="openai",
            title="OpenAI",
            ok=True,
            required=True,
            summary="Configuração da OpenAI encontrada.",
            details=details,
        )

    def check_executor(self, command: str, project_path: Path) -> SetupCheckResult:
        executor = ClaudeExecutor(command=command, working_dir=project_path)
        details = [f"Comando: {command}"]

        if not executor.is_available():
            return SetupCheckResult(
                key="executor",
                title="Claude Executor",
                ok=False,
                required=True,
                summary="Executor Claude não encontrado.",
                details=details,
                action_hint="Instale o Claude Code CLI ou ajuste o comando.",
            )

        version = executor.get_version()
        if version:
            details.append(f"Versão: {version}")

        return SetupCheckResult(
            key="executor",
            title="Claude Executor",
            ok=True,
            required=True,
            summary="Executor Claude disponível.",
            details=details,
        )

    def check_git(self, project_path: Path) -> SetupCheckResult:
        details: list[str] = []
        git = GitOperations(project_path)

        try:
            version = subprocess.run(
                ["git", "--version"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as exc:
            return SetupCheckResult(
                key="git",
                title="Git",
                ok=False,
                required=False,
                summary="Git não está disponível no sistema.",
                details=[str(exc)],
                action_hint="Instale o Git para habilitar commit e push automáticos.",
            )

        details.append(version.stdout.strip() or "git encontrado")
        if not git.is_repo():
            return SetupCheckResult(
                key="git",
                title="Git",
                ok=False,
                required=False,
                summary="Projeto sem repositório Git.",
                details=details,
                action_hint="Você pode usar o app sem Git, mas commit e push ficarão indisponíveis.",
            )

        status = git.get_status()
        details.append(f"Branch atual: {status.branch or 'desconhecida'}")
        return SetupCheckResult(
            key="git",
            title="Git",
            ok=True,
            required=False,
            summary="Git pronto para commit e push.",
            details=details,
        )

    def validate_minimum_configuration(
        self,
        project_path: Path,
        workspace_path: Path,
        profile: str,
        executor_command: str,
        explicit_api_key: Optional[str] = None,
        network_test: bool = False,
    ) -> SetupValidationResult:
        checks = [
            self.check_project(project_path),
            self.check_profile(profile),
            self.check_openai(project_path, explicit_api_key=explicit_api_key, network_test=network_test),
            self.check_executor(executor_command, project_path),
            self.check_workspace(workspace_path),
            self.check_git(project_path),
        ]
        return SetupValidationResult(checks=checks)
