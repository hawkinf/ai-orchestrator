"""Task creation panel - Nova Tarefa - Clean modern design."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QSpinBox,
    QLineEdit, QFileDialog, QFrame, QScrollArea,
)
from PySide6.QtCore import Signal, Qt

from .ui_models import TaskConfig


class TaskPanel(QWidget):
    """Panel for creating and submitting new tasks - Clean design."""

    task_submitted = Signal(TaskConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(28, 24, 28, 24)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)

        header = QLabel("Nova Tarefa")
        header.setProperty("heading", True)
        header_layout.addWidget(header)

        subheader = QLabel("Descreva o objetivo e execute. As opções avançadas ficam fora do caminho até você precisar delas.")
        subheader.setProperty("subheading", True)
        subheader.setWordWrap(True)
        header_layout.addWidget(subheader)

        content_layout.addLayout(header_layout)

        # Task description - main focus area
        task_section = self._create_task_section()
        content_layout.addWidget(task_section)

        # Advanced settings toggle
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(12)

        self.advanced_toggle_btn = QPushButton("Mostrar opções avançadas")
        self.advanced_toggle_btn.setProperty("secondary", True)
        self.advanced_toggle_btn.setCheckable(True)
        self.advanced_toggle_btn.clicked.connect(self._toggle_advanced)
        toggle_row.addWidget(self.advanced_toggle_btn)

        helper = QLabel("Diretório, perfil, iterações e automações opcionais.")
        helper.setProperty("muted", True)
        toggle_row.addWidget(helper)
        toggle_row.addStretch()
        content_layout.addLayout(toggle_row)

        # Settings section - hidden by default
        self.settings_section = self._create_settings_section()
        self.settings_section.setVisible(False)
        content_layout.addWidget(self.settings_section)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Bottom action bar - fixed
        action_bar = self._create_action_bar()
        layout.addWidget(action_bar)

    def _create_task_section(self) -> QWidget:
        """Create main task input section."""
        container = QFrame()
        container.setProperty("card", True)
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("O que você quer fazer?")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        hint = QLabel("Use uma instrução objetiva. Você pode incluir contexto, restrições e resultado esperado.")
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Task input
        self.task_edit = QTextEdit()
        self.task_edit.setPlaceholderText(
            "Exemplo: corrigir a validação de login e adicionar testes para sessão expirada.\n\n"
            "Inclua:\n"
            "• o problema ou objetivo\n"
            "• o resultado esperado\n"
            "• restrições importantes\n\n"
            "Exemplos:\n"
            "• Corrigir o bug de login onde o usuário não consegue entrar\n"
            "• Adicionar validação de email no formulário de cadastro\n"
            "• Criar endpoint GET /api/users com paginação"
        )
        self.task_edit.setMinimumHeight(168)
        self.task_edit.setMaximumHeight(240)
        self.task_edit.textChanged.connect(self._on_task_changed)
        layout.addWidget(self.task_edit)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(12)

        support = QLabel("Comece no modo simples. Abra o avançado apenas se precisar ajustar o fluxo.")
        support.setProperty("muted", True)
        support.setWordWrap(True)
        footer.addWidget(support, 1)

        self.char_counter = QLabel("0 caracteres")
        self.char_counter.setProperty("muted", True)
        self.char_counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer.addWidget(self.char_counter)

        layout.addLayout(footer)

        return container

    def _create_settings_section(self) -> QWidget:
        """Create settings section with clean layout."""
        container = QFrame()
        container.setProperty("card", True)
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(18, 18, 18, 18)

        section_header = QLabel("Opções avançadas")
        section_header.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(section_header)

        section_hint = QLabel("Ajuste o ambiente e as automações quando precisar de mais controle.")
        section_hint.setProperty("muted", True)
        section_hint.setWordWrap(True)
        layout.addWidget(section_hint)

        grid = QHBoxLayout()
        grid.setSpacing(28)

        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        path_row = self._create_field_row("Diretório", self._create_path_input())
        left_col.addLayout(path_row)
        left_col.addWidget(self._create_field_help("Onde a execução deve atuar. Use '.' para a pasta atual."))

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["flutter", "python", "generic"])
        self.profile_combo.setCurrentText("flutter")
        self.profile_combo.setFixedWidth(160)
        self.profile_combo.currentIndexChanged.connect(self._update_summary)
        profile_row = self._create_field_row("Perfil", self.profile_combo)
        left_col.addLayout(profile_row)
        left_col.addWidget(self._create_field_help("Define comandos de validação e o contexto padrão do projeto."))

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 10)
        self.max_iter_spin.setValue(3)
        self.max_iter_spin.valueChanged.connect(self._update_summary)
        self.max_iter_spin.setFixedWidth(80)
        iter_row = self._create_field_row("Iterações", self.max_iter_spin)
        left_col.addLayout(iter_row)
        left_col.addWidget(self._create_field_help("Número máximo de tentativas automáticas antes de parar."))

        left_col.addStretch()

        grid.addLayout(left_col)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        options_label = QLabel("Automações")
        options_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        right_col.addWidget(options_label)

        self.auto_validate_cb = QCheckBox("Validar automaticamente")
        self.auto_validate_cb.setChecked(True)
        right_col.addWidget(self.auto_validate_cb)
        right_col.addWidget(self._create_option_help("Executa testes e validações do perfil ao final da execução."))

        self.auto_commit_cb = QCheckBox("Commit automático")
        self.auto_commit_cb.setChecked(False)
        right_col.addWidget(self.auto_commit_cb)
        right_col.addWidget(self._create_option_help("Cria commit quando a validação terminar com sucesso."))

        self.require_approval_cb = QCheckBox("Exigir aprovação em mudanças críticas")
        self.require_approval_cb.setChecked(True)
        right_col.addWidget(self.require_approval_cb)
        right_col.addWidget(self._create_option_help("Pausa antes de ações destrutivas ou sensíveis."))

        self.auto_push_cb = QCheckBox("Push automático")
        self.auto_push_cb.setChecked(False)
        right_col.addWidget(self.auto_push_cb)
        right_col.addWidget(self._create_option_help("Envia o commit para o remoto quando a execução terminar."))

        right_col.addStretch()
        grid.addLayout(right_col)

        layout.addLayout(grid)

        return container

    def _create_path_input(self) -> QWidget:
        """Create path input with browse button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(".")
        self.path_edit.setText(".")
        self.path_edit.setFixedWidth(220)
        layout.addWidget(self.path_edit)

        browse_btn = QPushButton("...")
        browse_btn.setFixedSize(32, 30)
        browse_btn.setProperty("ghost", True)
        browse_btn.clicked.connect(self._browse_path)
        layout.addWidget(browse_btn)

        return container

    def _create_field_row(self, label_text: str, widget: QWidget) -> QHBoxLayout:
        """Create a labeled field row."""
        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel(label_text)
        label.setFixedWidth(72)
        label.setProperty("muted", True)
        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch()

        return row

    def _create_field_help(self, text: str) -> QLabel:
        """Create helper text for advanced fields."""
        label = QLabel(text)
        label.setProperty("muted", True)
        label.setWordWrap(True)
        label.setContentsMargins(82, 0, 0, 0)
        return label

    def _create_option_help(self, text: str) -> QLabel:
        """Create helper text for advanced options."""
        label = QLabel(text)
        label.setProperty("muted", True)
        label.setWordWrap(True)
        label.setContentsMargins(24, -4, 0, 6)
        return label

    def _create_action_bar(self) -> QWidget:
        """Create bottom action bar."""
        bar = QFrame()
        bar.setObjectName("task_action_bar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)

        self.summary_label = QLabel()
        self.summary_label.setProperty("muted", True)
        self._update_summary()
        layout.addWidget(self.summary_label)

        layout.addStretch()

        self.clear_btn = QPushButton("Limpar")
        self.clear_btn.setProperty("ghost", True)
        self.clear_btn.setFixedWidth(88)
        self.clear_btn.clicked.connect(self._clear_form)
        layout.addWidget(self.clear_btn)

        self.submit_btn = QPushButton("Executar")
        self.submit_btn.setFixedWidth(132)
        self.submit_btn.setProperty("success", True)
        self.submit_btn.clicked.connect(self._submit_task)
        layout.addWidget(self.submit_btn)

        return bar

    def _on_task_changed(self):
        """Handle task text change."""
        count = len(self.task_edit.toPlainText())
        self.char_counter.setText(f"{count} caracteres")
        self._update_summary()

    def _update_summary(self):
        """Update configuration summary."""
        profile = self.profile_combo.currentText() if hasattr(self, 'profile_combo') else 'flutter'
        max_iter = self.max_iter_spin.value() if hasattr(self, 'max_iter_spin') else 3
        if self.settings_section.isVisible():
            self.summary_label.setText(f"Perfil {profile} • até {max_iter} iterações")
        else:
            self.summary_label.setText("Modo simples ativo")

    def _toggle_advanced(self):
        """Show or hide advanced options."""
        visible = self.advanced_toggle_btn.isChecked()
        self.settings_section.setVisible(visible)
        self.advanced_toggle_btn.setText(
            "Ocultar opções avançadas" if visible else "Mostrar opções avançadas"
        )
        self._update_summary()

    def _browse_path(self):
        """Open directory browser."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Diretório",
            self.path_edit.text() or ".",
        )
        if path:
            self.path_edit.setText(path)

    def _clear_form(self):
        """Clear the form."""
        self.task_edit.clear()
        self.path_edit.setText(".")
        self.profile_combo.setCurrentIndex(0)
        self.max_iter_spin.setValue(3)
        self.auto_validate_cb.setChecked(True)
        self.auto_commit_cb.setChecked(False)
        self.auto_push_cb.setChecked(False)
        self.require_approval_cb.setChecked(True)

    def _submit_task(self):
        """Submit the task."""
        task_text = self.task_edit.toPlainText().strip()
        if not task_text:
            return

        config = TaskConfig(
            task_description=task_text,
            project_path=self.path_edit.text() or ".",
            profile=self.profile_combo.currentText(),
            max_iterations=self.max_iter_spin.value(),
            auto_validate=self.auto_validate_cb.isChecked(),
            auto_commit=self.auto_commit_cb.isChecked(),
            auto_push=self.auto_push_cb.isChecked(),
            require_approval_destructive=self.require_approval_cb.isChecked(),
        )

        self.task_submitted.emit(config)

    def set_submitting(self, submitting: bool):
        """Set submitting state."""
        self.submit_btn.setEnabled(not submitting)
        self.submit_btn.setText("Executando..." if submitting else "Executar")

    def set_task_text(self, text: str):
        """Set task description text."""
        self.task_edit.setPlainText(text)

    def get_task_text(self) -> str:
        """Get task description text."""
        return self.task_edit.toPlainText()

    def get_config(self) -> TaskConfig:
        """Get current form configuration as TaskConfig."""
        return TaskConfig(
            task_description=self.task_edit.toPlainText().strip(),
            project_path=self.path_edit.text() or ".",
            profile=self.profile_combo.currentText(),
            max_iterations=self.max_iter_spin.value(),
            auto_validate=self.auto_validate_cb.isChecked(),
            auto_commit=self.auto_commit_cb.isChecked(),
            auto_push=self.auto_push_cb.isChecked(),
            require_approval_destructive=self.require_approval_cb.isChecked(),
        )
