"""Configuration panel for settings."""

import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QCheckBox, QGroupBox, QScrollArea,
    QFrame, QTabWidget, QTextEdit, QComboBox, QMessageBox,
)
from PySide6.QtCore import Signal

from .ui_models import SettingsViewModel

# Add parent to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


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

        # Environment tab (API Keys)
        env_tab = self._create_environment_tab()
        self.tabs.addTab(env_tab, "Ambiente")

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

    def _create_environment_tab(self) -> QWidget:
        """Create environment/API settings tab."""
        from PySide6.QtCore import Qt

        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # OpenAI API Key Status
        api_group = QGroupBox("OpenAI API Key")
        api_layout = QVBoxLayout(api_group)

        # Status row
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.api_status_label = QLabel("Verificando...")
        self.api_status_label.setStyleSheet("font-weight: 600;")
        status_row.addWidget(self.api_status_label)
        status_row.addStretch()
        api_layout.addLayout(status_row)

        # Source row
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Origem:"))
        self.api_source_label = QLabel("-")
        self.api_source_label.setStyleSheet("color: #64748b;")
        source_row.addWidget(self.api_source_label)
        source_row.addStretch()
        api_layout.addLayout(source_row)

        # Priority note row
        priority_row = QHBoxLayout()
        self.api_priority_label = QLabel("")
        self.api_priority_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self.api_priority_label.setWordWrap(True)
        priority_row.addWidget(self.api_priority_label)
        api_layout.addLayout(priority_row)

        # Current value preview row
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("Valor atual:"))
        self.api_preview_label = QLabel("-")
        self.api_preview_label.setStyleSheet("color: #64748b; font-family: monospace;")
        preview_row.addWidget(self.api_preview_label)
        preview_row.addStretch()
        api_layout.addLayout(preview_row)

        # .env file row
        dotenv_row = QHBoxLayout()
        dotenv_row.addWidget(QLabel("Arquivo .env:"))
        self.dotenv_label = QLabel("-")
        self.dotenv_label.setStyleSheet("color: #64748b;")
        dotenv_row.addWidget(self.dotenv_label)
        dotenv_row.addStretch()
        api_layout.addLayout(dotenv_row)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #e2e8f0;")
        api_layout.addWidget(separator)

        # API Key input section
        input_label = QLabel("Editar/Salvar API Key no .env:")
        input_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        api_layout.addWidget(input_label)

        # Input row
        input_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        input_row.addWidget(self.api_key_input)

        self.show_key_btn = QPushButton("Mostrar")
        self.show_key_btn.setFixedWidth(70)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self._toggle_key_visibility)
        input_row.addWidget(self.show_key_btn)
        api_layout.addLayout(input_row)

        # Action buttons row
        actions_row = QHBoxLayout()

        save_env_btn = QPushButton("Salvar no .env")
        save_env_btn.setFixedWidth(120)
        save_env_btn.clicked.connect(self._save_api_key_to_env)
        actions_row.addWidget(save_env_btn)

        refresh_btn = QPushButton("Recarregar")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._check_api_key)
        actions_row.addWidget(refresh_btn)

        clear_btn = QPushButton("Limpar")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(lambda: self.api_key_input.clear())
        actions_row.addWidget(clear_btn)

        actions_row.addStretch()
        api_layout.addLayout(actions_row)

        # Save status
        self.save_status_label = QLabel("")
        self.save_status_label.setWordWrap(True)
        api_layout.addWidget(self.save_status_label)

        content_layout.addWidget(api_group)

        # Test Engine button
        test_group = QGroupBox("Teste de Engine")
        test_layout = QVBoxLayout(test_group)

        test_desc = QLabel(
            "Testa a inicializacao do Planner e Reviewer (OpenAI).\n"
            "Use para verificar se a configuracao esta correta."
        )
        test_desc.setStyleSheet("color: #64748b;")
        test_desc.setWordWrap(True)
        test_layout.addWidget(test_desc)

        test_btn_row = QHBoxLayout()
        self.test_engine_btn = QPushButton("Testar Engine")
        self.test_engine_btn.setFixedWidth(150)
        self.test_engine_btn.clicked.connect(self._test_engine)
        test_btn_row.addWidget(self.test_engine_btn)
        test_btn_row.addStretch()
        test_layout.addLayout(test_btn_row)

        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        test_layout.addWidget(self.test_result_label)

        content_layout.addWidget(test_group)

        # Help section
        help_group = QGroupBox("Como Configurar")
        help_layout = QVBoxLayout(help_group)

        help_text = QLabel("""
<b>Windows PowerShell (temporario):</b><br/>
<code>$env:OPENAI_API_KEY = "sk-sua-chave"</code><br/><br/>

<b>Windows permanente:</b><br/>
<code>[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-sua-chave", "User")</code><br/><br/>

<b>Arquivo .env (na raiz do projeto):</b><br/>
<code>OPENAI_API_KEY=sk-sua-chave</code><br/><br/>

<b>Importante:</b> Apos definir a variavel, reinicie o VS Code/terminal.
""")
        from PySide6.QtCore import Qt
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setStyleSheet("color: #64748b; font-size: 12px;")
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)

        content_layout.addWidget(help_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Run initial check
        self._check_api_key()

        return widget

    def _toggle_key_visibility(self, show: bool):
        """Toggle API key visibility in input field."""
        if show:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Ocultar")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Mostrar")

    def _save_api_key_to_env(self):
        """Save API key to .env file."""
        key_value = self.api_key_input.text().strip()

        if not key_value:
            self.save_status_label.setText("Digite uma chave para salvar.")
            self.save_status_label.setStyleSheet("color: #f59e0b;")
            return

        # Validate key format (basic check)
        if not key_value.startswith("sk-"):
            reply = QMessageBox.question(
                self,
                "Formato da Chave",
                "A chave nao comeca com 'sk-'. Chaves OpenAI geralmente comecam com 'sk-'.\n\n"
                "Deseja salvar mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            from pathlib import Path
            from orchestrator.env_file import upsert_env_var, create_env_file_if_missing, mask_secret

            # Determine .env path
            env_path = Path.cwd() / ".env"

            # Create .env if missing
            create_env_file_if_missing(env_path)

            # Save key
            success = upsert_env_var(env_path, "OPENAI_API_KEY", key_value)

            if success:
                masked = mask_secret(key_value)
                self.save_status_label.setText(
                    f"Chave salva com sucesso em {env_path}\n"
                    f"Valor: {masked}"
                )
                self.save_status_label.setStyleSheet("color: #22c55e;")

                # Clear input for security
                self.api_key_input.clear()

                # Reload environment and refresh status
                from dotenv import load_dotenv
                load_dotenv(env_path, override=True)
                self._check_api_key()
            else:
                self.save_status_label.setText(
                    f"Erro ao salvar em {env_path}\n"
                    "Verifique permissoes de escrita."
                )
                self.save_status_label.setStyleSheet("color: #ef4444;")

        except Exception as e:
            self.save_status_label.setText(f"Erro: {e}")
            self.save_status_label.setStyleSheet("color: #ef4444;")

    def _check_api_key(self):
        """Check OpenAI API key status."""
        try:
            from orchestrator.env_validator import EnvironmentValidator, EnvKeyStatus
            from orchestrator.env_file import mask_secret

            validator = EnvironmentValidator()
            diag = validator.run_full_diagnostics()

            # Update status
            if diag.openai_key.status == EnvKeyStatus.OK:
                self.api_status_label.setText("OK")
                self.api_status_label.setStyleSheet("color: #22c55e; font-weight: 600;")
            elif diag.openai_key.status == EnvKeyStatus.MISSING:
                self.api_status_label.setText("NAO ENCONTRADA")
                self.api_status_label.setStyleSheet("color: #ef4444; font-weight: 600;")
            elif diag.openai_key.status == EnvKeyStatus.EMPTY:
                self.api_status_label.setText("VAZIA")
                self.api_status_label.setStyleSheet("color: #f59e0b; font-weight: 600;")

            # Update source and priority info from resolution
            if diag.resolution:
                res = diag.resolution
                if res.source == "system":
                    self.api_source_label.setText("Variavel de sistema")
                    self.api_source_label.setStyleSheet("color: #22c55e;")
                elif res.source == "dotenv":
                    self.api_source_label.setText(f"Arquivo .env")
                    self.api_source_label.setStyleSheet("color: #3b82f6;")
                else:
                    self.api_source_label.setText("-")
                    self.api_source_label.setStyleSheet("color: #64748b;")

                self.api_priority_label.setText(res.priority_note)

                # Show value preview
                if res.value:
                    self.api_preview_label.setText(mask_secret(res.value))
                else:
                    self.api_preview_label.setText("-")

                # Show .env file path
                if res.dotenv_path:
                    self.dotenv_label.setText(str(res.dotenv_path))
                    if res.dotenv_value:
                        self.dotenv_label.setStyleSheet("color: #22c55e;")
                    else:
                        self.dotenv_label.setStyleSheet("color: #64748b;")
                else:
                    self.dotenv_label.setText("Nao encontrado")
                    self.dotenv_label.setStyleSheet("color: #64748b;")
            else:
                # Fallback if no resolution
                self.api_source_label.setText(diag.openai_key.source or "-")
                self.api_priority_label.setText("")
                if diag.openai_key.value_preview:
                    self.api_preview_label.setText(diag.openai_key.value_preview)
                else:
                    self.api_preview_label.setText("-")

                if diag.dotenv_loaded and diag.dotenv_path:
                    self.dotenv_label.setText(str(diag.dotenv_path))
                    self.dotenv_label.setStyleSheet("color: #22c55e;")
                else:
                    self.dotenv_label.setText("Nao encontrado")
                    self.dotenv_label.setStyleSheet("color: #64748b;")

        except Exception as e:
            self.api_status_label.setText(f"ERRO: {e}")
            self.api_status_label.setStyleSheet("color: #ef4444; font-weight: 600;")

    def _test_engine(self):
        """Test engine initialization."""
        self.test_result_label.setText("Testando...")
        self.test_result_label.setStyleSheet("color: #64748b;")
        self.test_engine_btn.setEnabled(False)

        try:
            from orchestrator.openai_client import PlannerClient, ReviewerClient

            # Try to create planner client
            planner = PlannerClient()
            self.test_result_label.setText("Planner OK, testando Reviewer...")

            # Try to create reviewer client
            reviewer = ReviewerClient()

            self.test_result_label.setText(
                "SUCESSO!\n\n"
                "Planner e Reviewer inicializados corretamente.\n"
                "A engine esta pronta para uso."
            )
            self.test_result_label.setStyleSheet("color: #22c55e;")

        except EnvironmentError as e:
            # API key issue
            error_msg = str(e)
            # Extract just the first line for display
            first_line = error_msg.split("\n")[0]
            self.test_result_label.setText(
                f"FALHA: {first_line}\n\n"
                "Verifique a aba 'Como Configurar' acima."
            )
            self.test_result_label.setStyleSheet("color: #ef4444;")

        except Exception as e:
            self.test_result_label.setText(f"ERRO: {e}")
            self.test_result_label.setStyleSheet("color: #ef4444;")

        finally:
            self.test_engine_btn.setEnabled(True)

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
