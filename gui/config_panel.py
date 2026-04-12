"""Configuration panel for settings."""

from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QCheckBox, QGroupBox, QScrollArea,
    QFrame, QTabWidget, QTextEdit, QComboBox, QMessageBox,
)
from PySide6.QtCore import Signal

from .ui_models import SettingsViewModel


class ConfigPanel(QWidget):
    """Panel for editing configuration settings."""

    settings_changed = Signal(SettingsViewModel)
    settings_saved = Signal()
    settings_reset = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings: Optional[SettingsViewModel] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Configuracoes")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Tabs for different sections
        self.tabs = QTabWidget()

        # General tab
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "Geral")

        # Models tab
        models_tab = self._create_models_tab()
        self.tabs.addTab(models_tab, "Modelos")

        # Executor tab
        executor_tab = self._create_executor_tab()
        self.tabs.addTab(executor_tab, "Executor")

        # Validation tab
        validation_tab = self._create_validation_tab()
        self.tabs.addTab(validation_tab, "Validacao")

        # Git tab
        git_tab = self._create_git_tab()
        self.tabs.addTab(git_tab, "Git")

        # Security tab
        security_tab = self._create_security_tab()
        self.tabs.addTab(security_tab, "Seguranca")

        layout.addWidget(self.tabs)

        # Action buttons
        actions_layout = QHBoxLayout()

        reset_btn = QPushButton("Restaurar Padroes")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._reset_defaults)
        actions_layout.addWidget(reset_btn)

        actions_layout.addStretch()

        validate_btn = QPushButton("Validar")
        validate_btn.setObjectName("secondary")
        validate_btn.clicked.connect(self._validate_config)
        actions_layout.addWidget(validate_btn)

        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self._save_settings)
        actions_layout.addWidget(save_btn)

        layout.addLayout(actions_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Project path
        path_group = QGroupBox("Caminhos")
        path_layout = QVBoxLayout(path_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Projeto:"))
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setPlaceholderText(".")
        row1.addWidget(self.project_path_edit)
        path_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Workspace:"))
        self.workspace_path_edit = QLineEdit()
        self.workspace_path_edit.setPlaceholderText("./workspace")
        row2.addWidget(self.workspace_path_edit)
        path_layout.addLayout(row2)

        content_layout.addWidget(path_group)

        # Profile
        profile_group = QGroupBox("Perfil")
        profile_layout = QHBoxLayout(profile_group)
        profile_layout.addWidget(QLabel("Perfil Ativo:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["flutter", "python", "generic"])
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()
        content_layout.addWidget(profile_group)

        # Iterations
        iter_group = QGroupBox("Iteracoes")
        iter_layout = QHBoxLayout(iter_group)
        iter_layout.addWidget(QLabel("Max Iteracoes:"))
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 10)
        self.max_iter_spin.setValue(3)
        iter_layout.addWidget(self.max_iter_spin)
        iter_layout.addStretch()
        content_layout.addWidget(iter_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_models_tab(self) -> QWidget:
        """Create models settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Planner
        planner_group = QGroupBox("Planner (OpenAI)")
        planner_layout = QVBoxLayout(planner_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Modelo:"))
        self.planner_model_edit = QLineEdit()
        self.planner_model_edit.setPlaceholderText("gpt-4o")
        row1.addWidget(self.planner_model_edit)
        planner_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Timeout (s):"))
        self.planner_timeout_spin = QSpinBox()
        self.planner_timeout_spin.setRange(30, 600)
        self.planner_timeout_spin.setValue(120)
        row2.addWidget(self.planner_timeout_spin)
        row2.addStretch()
        planner_layout.addLayout(row2)

        content_layout.addWidget(planner_group)

        # Reviewer
        reviewer_group = QGroupBox("Reviewer (OpenAI)")
        reviewer_layout = QVBoxLayout(reviewer_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Modelo:"))
        self.reviewer_model_edit = QLineEdit()
        self.reviewer_model_edit.setPlaceholderText("gpt-4o")
        row1.addWidget(self.reviewer_model_edit)
        reviewer_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Timeout (s):"))
        self.reviewer_timeout_spin = QSpinBox()
        self.reviewer_timeout_spin.setRange(30, 600)
        self.reviewer_timeout_spin.setValue(120)
        row2.addWidget(self.reviewer_timeout_spin)
        row2.addStretch()
        reviewer_layout.addLayout(row2)

        content_layout.addWidget(reviewer_group)

        # API Key info
        api_group = QGroupBox("API Key")
        api_layout = QVBoxLayout(api_group)
        api_label = QLabel(
            "A chave da API OpenAI deve ser definida na variavel de ambiente OPENAI_API_KEY\n"
            "ou no arquivo .env"
        )
        api_label.setStyleSheet("color: #64748b;")
        api_label.setWordWrap(True)
        api_layout.addWidget(api_label)
        content_layout.addWidget(api_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_executor_tab(self) -> QWidget:
        """Create executor settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Executor
        executor_group = QGroupBox("Claude Code Executor")
        executor_layout = QVBoxLayout(executor_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Comando:"))
        self.executor_cmd_edit = QLineEdit()
        self.executor_cmd_edit.setPlaceholderText("claude")
        row1.addWidget(self.executor_cmd_edit)
        executor_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Timeout (s):"))
        self.executor_timeout_spin = QSpinBox()
        self.executor_timeout_spin.setRange(60, 3600)
        self.executor_timeout_spin.setValue(600)
        row2.addWidget(self.executor_timeout_spin)
        row2.addStretch()
        executor_layout.addLayout(row2)

        content_layout.addWidget(executor_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_validation_tab(self) -> QWidget:
        """Create validation settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Flutter commands
        flutter_group = QGroupBox("Flutter")
        flutter_layout = QVBoxLayout(flutter_group)
        flutter_layout.addWidget(QLabel("Comandos de validacao (um por linha):"))
        self.flutter_cmds_edit = QTextEdit()
        self.flutter_cmds_edit.setMaximumHeight(100)
        self.flutter_cmds_edit.setPlaceholderText("flutter analyze\nflutter test")
        flutter_layout.addWidget(self.flutter_cmds_edit)
        content_layout.addWidget(flutter_group)

        # Python commands
        python_group = QGroupBox("Python")
        python_layout = QVBoxLayout(python_group)
        python_layout.addWidget(QLabel("Comandos de validacao (um por linha):"))
        self.python_cmds_edit = QTextEdit()
        self.python_cmds_edit.setMaximumHeight(100)
        self.python_cmds_edit.setPlaceholderText("python -m pytest\nruff check .")
        python_layout.addWidget(self.python_cmds_edit)
        content_layout.addWidget(python_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_git_tab(self) -> QWidget:
        """Create git settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Git settings
        git_group = QGroupBox("Git")
        git_layout = QVBoxLayout(git_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Remote:"))
        self.git_remote_edit = QLineEdit()
        self.git_remote_edit.setPlaceholderText("origin")
        row1.addWidget(self.git_remote_edit)
        git_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Branch:"))
        self.git_branch_edit = QLineEdit()
        self.git_branch_edit.setPlaceholderText("main")
        row2.addWidget(self.git_branch_edit)
        git_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Branches Protegidas:"))
        self.protected_branches_edit = QLineEdit()
        self.protected_branches_edit.setPlaceholderText("main, master")
        row3.addWidget(self.protected_branches_edit)
        git_layout.addLayout(row3)

        content_layout.addWidget(git_group)

        # Auto actions
        auto_group = QGroupBox("Acoes Automaticas")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_commit_cb = QCheckBox("Permitir Auto Commit")
        auto_layout.addWidget(self.auto_commit_cb)

        self.auto_push_cb = QCheckBox("Permitir Auto Push")
        auto_layout.addWidget(self.auto_push_cb)

        content_layout.addWidget(auto_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_security_tab(self) -> QWidget:
        """Create security settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Checkpoints
        checkpoint_group = QGroupBox("Checkpoints")
        checkpoint_layout = QVBoxLayout(checkpoint_group)

        self.require_human_cb = QCheckBox("Exigir aprovacao humana em mudancas destrutivas")
        self.require_human_cb.setChecked(True)
        checkpoint_layout.addWidget(self.require_human_cb)

        checkpoint_layout.addWidget(QLabel("Gatilhos de checkpoint (um por linha):"))
        self.triggers_edit = QTextEdit()
        self.triggers_edit.setMaximumHeight(100)
        self.triggers_edit.setPlaceholderText("delete\nmigration\nforce push")
        checkpoint_layout.addWidget(self.triggers_edit)

        content_layout.addWidget(checkpoint_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def set_settings(self, settings: SettingsViewModel):
        """Load settings into the form."""
        self._settings = settings

        # General
        self.project_path_edit.setText(settings.project_path)
        self.workspace_path_edit.setText(settings.workspace_path)
        index = self.profile_combo.findText(settings.active_profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self.max_iter_spin.setValue(settings.max_iterations)

        # Models
        self.planner_model_edit.setText(settings.planner_model)
        self.reviewer_model_edit.setText(settings.reviewer_model)
        self.planner_timeout_spin.setValue(settings.planner_timeout)
        self.reviewer_timeout_spin.setValue(settings.reviewer_timeout)

        # Executor
        self.executor_cmd_edit.setText(settings.executor_command)
        self.executor_timeout_spin.setValue(settings.executor_timeout)

        # Validation
        self.flutter_cmds_edit.setPlainText("\n".join(settings.flutter_commands))
        self.python_cmds_edit.setPlainText("\n".join(settings.python_commands))

        # Git
        self.git_remote_edit.setText(settings.git_remote)
        self.git_branch_edit.setText(settings.git_branch)
        self.protected_branches_edit.setText(", ".join(settings.protected_branches))
        self.auto_commit_cb.setChecked(settings.allow_auto_commit)
        self.auto_push_cb.setChecked(settings.allow_auto_push)

        # Security
        self.require_human_cb.setChecked(settings.require_human_on_destructive)
        self.triggers_edit.setPlainText("\n".join(settings.checkpoint_triggers))

    def get_settings(self) -> SettingsViewModel:
        """Get settings from the form."""
        flutter_cmds = [c.strip() for c in self.flutter_cmds_edit.toPlainText().split("\n") if c.strip()]
        python_cmds = [c.strip() for c in self.python_cmds_edit.toPlainText().split("\n") if c.strip()]
        protected = [b.strip() for b in self.protected_branches_edit.text().split(",") if b.strip()]
        triggers = [t.strip() for t in self.triggers_edit.toPlainText().split("\n") if t.strip()]

        return SettingsViewModel(
            project_path=self.project_path_edit.text() or ".",
            workspace_path=self.workspace_path_edit.text() or "./workspace",
            active_profile=self.profile_combo.currentText(),
            max_iterations=self.max_iter_spin.value(),
            planner_model=self.planner_model_edit.text() or "gpt-4o",
            reviewer_model=self.reviewer_model_edit.text() or "gpt-4o",
            planner_timeout=self.planner_timeout_spin.value(),
            reviewer_timeout=self.reviewer_timeout_spin.value(),
            executor_command=self.executor_cmd_edit.text() or "claude",
            executor_timeout=self.executor_timeout_spin.value(),
            flutter_commands=flutter_cmds,
            python_commands=python_cmds,
            allow_auto_commit=self.auto_commit_cb.isChecked(),
            allow_auto_push=self.auto_push_cb.isChecked(),
            git_remote=self.git_remote_edit.text() or "origin",
            git_branch=self.git_branch_edit.text() or "main",
            protected_branches=protected,
            require_human_on_destructive=self.require_human_cb.isChecked(),
            checkpoint_triggers=triggers,
        )

    def _validate_config(self):
        """Validate current configuration."""
        settings = self.get_settings()
        errors = []

        if not settings.project_path:
            errors.append("Caminho do projeto e obrigatorio")
        if not settings.executor_command:
            errors.append("Comando do executor e obrigatorio")
        if settings.max_iterations < 1:
            errors.append("Max iteracoes deve ser pelo menos 1")

        if errors:
            QMessageBox.warning(
                self,
                "Validacao",
                "Erros encontrados:\n\n" + "\n".join(f"- {e}" for e in errors)
            )
        else:
            QMessageBox.information(
                self,
                "Validacao",
                "Configuracao valida!"
            )

    def _save_settings(self):
        """Save settings."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        self.settings_saved.emit()

    def _reset_defaults(self):
        """Reset to default settings."""
        reply = QMessageBox.question(
            self,
            "Restaurar Padroes",
            "Deseja restaurar todas as configuracoes para os valores padrao?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.set_settings(SettingsViewModel())
            self.settings_reset.emit()
