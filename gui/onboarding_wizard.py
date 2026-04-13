"""First-run onboarding wizard."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from orchestrator.env_file import create_env_file_if_missing, upsert_env_var
from orchestrator.setup_validator import SetupCheckResult, SetupValidator

from .ui_models import SettingsViewModel


def _status_text(result: Optional[SetupCheckResult]) -> str:
    if result is None:
        return "Ainda não testado."
    return result.summary


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Boas-vindas")
        self.setSubTitle("Vamos preparar o essencial para sua primeira execução.")
        layout = QVBoxLayout(self)
        body = QLabel(
            "O AI Orchestrator guia uma tarefa pelo fluxo:\n"
            "tarefa → planner → executor → review → validação → commit/push.\n\n"
            "Este onboarding foca só no que você precisa para começar sem adivinhar."
        )
        body.setWordWrap(True)
        layout.addWidget(body)


class ProjectPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Projeto")
        self.setSubTitle("Escolha a pasta do projeto e o perfil principal.")
        layout = QVBoxLayout(self)

        project_row = QHBoxLayout()
        self.project_edit = QLineEdit(str(Path.cwd()))
        browse_btn = QPushButton("Escolher pasta")
        browse_btn.clicked.connect(self._browse_project)
        project_row.addWidget(self.project_edit)
        project_row.addWidget(browse_btn)
        layout.addWidget(QLabel("Diretório do projeto"))
        layout.addLayout(project_row)

        layout.addWidget(QLabel("Perfil"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["flutter", "python", "generic"])
        layout.addWidget(self.profile_combo)

        self.status_label = QLabel("Selecione um projeto para continuar.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.registerField("project_path*", self.project_edit)
        self.registerField("profile", self.profile_combo, "currentText", self.profile_combo.currentTextChanged)

    def _browse_project(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar projeto", self.project_edit.text() or ".")
        if path:
            self.project_edit.setText(path)


class OpenAIPage(QWizardPage):
    def __init__(self, validator: SetupValidator):
        super().__init__()
        self.validator = validator
        self._last_result: Optional[SetupCheckResult] = None
        self.setTitle("OpenAI")
        self.setSubTitle("Informe a chave e teste a configuração.")
        layout = QVBoxLayout(self)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("OpenAI API Key"))
        layout.addWidget(self.api_key_input)

        self.test_btn = QPushButton("Testar conexão")
        self.test_btn.clicked.connect(self._run_test)
        layout.addWidget(self.test_btn)

        self.status_label = QLabel("A chave pode ser salva no .env ao finalizar o onboarding.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _run_test(self):
        project_path = Path(self.field("project_path") or Path.cwd())
        self._last_result = self.validator.check_openai(
            project_path=project_path,
            explicit_api_key=self.api_key_input.text().strip() or None,
            network_test=False,
        )
        self.status_label.setText(_status_text(self._last_result))

    def validatePage(self) -> bool:
        if not self.api_key_input.text().strip():
            self.status_label.setText("Informe uma chave da OpenAI para continuar.")
            return False

        self._run_test()
        return bool(self._last_result and self._last_result.ok)


class ExecutorPage(QWizardPage):
    def __init__(self, validator: SetupValidator):
        super().__init__()
        self.validator = validator
        self._last_result: Optional[SetupCheckResult] = None
        self.setTitle("Claude Executor")
        self.setSubTitle("Confirme o comando usado para executar alterações.")
        layout = QVBoxLayout(self)

        self.command_edit = QLineEdit("claude")
        layout.addWidget(QLabel("Comando do executor"))
        layout.addWidget(self.command_edit)

        self.test_btn = QPushButton("Testar executor")
        self.test_btn.clicked.connect(self._run_test)
        layout.addWidget(self.test_btn)

        self.status_label = QLabel("Use o comando instalado no seu ambiente.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.registerField("executor_command*", self.command_edit)

    def _run_test(self):
        project_path = Path(self.field("project_path") or Path.cwd())
        self._last_result = self.validator.check_executor(self.command_edit.text().strip() or "claude", project_path)
        self.status_label.setText(_status_text(self._last_result))

    def validatePage(self) -> bool:
        self._run_test()
        return bool(self._last_result and self._last_result.ok)


class WorkspaceGitPage(QWizardPage):
    def __init__(self, validator: SetupValidator):
        super().__init__()
        self.validator = validator
        self.setTitle("Workspace e Git")
        self.setSubTitle("Valide a pasta de trabalho e o estado do Git.")
        layout = QVBoxLayout(self)

        workspace_row = QHBoxLayout()
        self.workspace_edit = QLineEdit(str(Path.cwd() / "workspace"))
        browse_btn = QPushButton("Escolher pasta")
        browse_btn.clicked.connect(self._browse_workspace)
        workspace_row.addWidget(self.workspace_edit)
        workspace_row.addWidget(browse_btn)
        layout.addWidget(QLabel("Workspace"))
        layout.addLayout(workspace_row)

        self.test_btn = QPushButton("Validar workspace e Git")
        self.test_btn.clicked.connect(self._run_test)
        layout.addWidget(self.test_btn)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(120)
        layout.addWidget(self.status_text)

        self.registerField("workspace_path*", self.workspace_edit)

    def _browse_workspace(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar workspace", self.workspace_edit.text() or ".")
        if path:
            self.workspace_edit.setText(path)

    def _run_test(self):
        workspace = Path(self.workspace_edit.text().strip() or "./workspace")
        project = Path(self.field("project_path") or Path.cwd())
        results = [
            self.validator.check_workspace(workspace),
            self.validator.check_git(project),
        ]
        self.status_text.setPlainText("\n".join(f"{item.title}: {item.summary}" for item in results))


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.next_destination = "new_task"
        self.setTitle("Finalização")
        self.setSubTitle("Revise o resumo e escolha seu próximo passo.")
        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        card = QFrame()
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        self.new_task_radio = QRadioButton("Ir para Nova Tarefa")
        self.new_task_radio.setChecked(True)
        self.new_task_radio.toggled.connect(self._update_destination)
        card_layout.addWidget(self.new_task_radio)
        self.diagnostics_radio = QRadioButton("Abrir Diagnóstico")
        self.diagnostics_radio.toggled.connect(self._update_destination)
        card_layout.addWidget(self.diagnostics_radio)
        layout.addWidget(card)

    def initializePage(self):
        project = self.field("project_path")
        profile = self.field("profile")
        executor = self.field("executor_command")
        workspace = self.field("workspace_path")
        self.summary_label.setText(
            "Checklist final:\n"
            f"• Projeto: {project}\n"
            f"• Perfil: {profile}\n"
            f"• Executor: {executor}\n"
            f"• Workspace: {workspace}\n\n"
            "Ao concluir, a configuração será salva e o app seguirá para a área escolhida."
        )

    def _update_destination(self):
        self.next_destination = "diagnostics" if self.diagnostics_radio.isChecked() else "new_task"


class OnboardingWizard(QWizard):
    """Guided first-run setup."""

    def __init__(self, project_root: Optional[Path] = None, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.validator = SetupValidator(project_root)
        self.finish_page = FinishPage()
        self.setWindowTitle("Onboarding do AI Orchestrator")
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setMinimumSize(680, 460)

        self.addPage(WelcomePage())
        self.project_page = ProjectPage()
        self.addPage(self.project_page)
        self.openai_page = OpenAIPage(self.validator)
        self.addPage(self.openai_page)
        self.executor_page = ExecutorPage(self.validator)
        self.addPage(self.executor_page)
        self.workspace_page = WorkspaceGitPage(self.validator)
        self.addPage(self.workspace_page)
        self.addPage(self.finish_page)

    def save_openai_key_if_needed(self):
        """Persist the OpenAI key in .env when provided."""
        api_key = self.openai_page.api_key_input.text().strip()
        if not api_key:
            return

        env_path = Path(self.field("project_path")) / ".env"
        create_env_file_if_missing(env_path)
        upsert_env_var(env_path, "OPENAI_API_KEY", api_key)

    def build_settings(self) -> SettingsViewModel:
        """Return the resulting settings from the wizard."""
        return SettingsViewModel(
            project_path=str(Path(self.field("project_path"))),
            workspace_path=str(Path(self.field("workspace_path"))),
            active_profile=str(self.field("profile")),
            executor_command=str(self.field("executor_command")),
        )

    def selected_destination(self) -> str:
        """Return the page to open after onboarding."""
        return self.finish_page.next_destination
