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
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(32, 28, 32, 28)

        # Header - compact
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header = QLabel("Nova Tarefa")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #e6edf3;")
        header_layout.addWidget(header)

        subheader = QLabel("Descreva o que você deseja realizar")
        subheader.setStyleSheet("color: #6b7280; font-size: 13px;")
        header_layout.addWidget(subheader)

        content_layout.addLayout(header_layout)

        # Task description - main focus area
        task_section = self._create_task_section()
        content_layout.addWidget(task_section)

        # Settings section - collapsible appearance
        settings_section = self._create_settings_section()
        content_layout.addWidget(settings_section)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Bottom action bar - fixed
        action_bar = self._create_action_bar()
        layout.addWidget(action_bar)

    def _create_task_section(self) -> QWidget:
        """Create main task input section."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Task input
        self.task_edit = QTextEdit()
        self.task_edit.setPlaceholderText(
            "Descreva a tarefa em linguagem natural...\n\n"
            "Exemplos:\n"
            "• Corrigir o bug de login onde o usuário não consegue entrar\n"
            "• Adicionar validação de email no formulário de cadastro\n"
            "• Criar endpoint GET /api/users com paginação"
        )
        self.task_edit.setMinimumHeight(180)
        self.task_edit.setMaximumHeight(280)
        self.task_edit.setStyleSheet("""
            QTextEdit {
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.6;
                color: #e6edf3;
            }
            QTextEdit:focus {
                border-color: #4f8cff;
            }
        """)
        self.task_edit.textChanged.connect(self._on_task_changed)
        layout.addWidget(self.task_edit)

        # Character counter - subtle
        self.char_counter = QLabel("0 caracteres")
        self.char_counter.setStyleSheet("color: #4b5563; font-size: 11px;")
        self.char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.char_counter)

        return container

    def _create_settings_section(self) -> QWidget:
        """Create settings section with clean layout."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # Section header
        section_header = QLabel("Configurações")
        section_header.setStyleSheet("""
            color: #9da7b3;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding-bottom: 4px;
        """)
        layout.addWidget(section_header)

        # Settings grid - two columns
        grid = QHBoxLayout()
        grid.setSpacing(24)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Project path
        path_row = self._create_field_row("Diretório", self._create_path_input())
        left_col.addLayout(path_row)

        # Profile
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["flutter", "python", "generic"])
        self.profile_combo.setCurrentText("flutter")
        self.profile_combo.setFixedWidth(140)
        profile_row = self._create_field_row("Perfil", self.profile_combo)
        left_col.addLayout(profile_row)

        # Max iterations
        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 10)
        self.max_iter_spin.setValue(3)
        self.max_iter_spin.setFixedWidth(80)
        iter_row = self._create_field_row("Iterações", self.max_iter_spin)
        left_col.addLayout(iter_row)

        grid.addLayout(left_col)

        # Right column - options
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        options_label = QLabel("Opções")
        options_label.setStyleSheet("color: #6b7280; font-size: 12px; margin-bottom: 4px;")
        right_col.addWidget(options_label)

        self.auto_validate_cb = QCheckBox("Validar automaticamente")
        self.auto_validate_cb.setChecked(True)
        right_col.addWidget(self.auto_validate_cb)

        self.auto_commit_cb = QCheckBox("Commit automático")
        self.auto_commit_cb.setChecked(False)
        right_col.addWidget(self.auto_commit_cb)

        self.require_approval_cb = QCheckBox("Exigir aprovação")
        self.require_approval_cb.setChecked(True)
        self.require_approval_cb.setToolTip("Pausa para aprovação antes de mudanças importantes")
        right_col.addWidget(self.require_approval_cb)

        self.auto_push_cb = QCheckBox("Push automático")
        self.auto_push_cb.setChecked(False)
        right_col.addWidget(self.auto_push_cb)

        right_col.addStretch()
        grid.addLayout(right_col)
        grid.addStretch()

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
        self.path_edit.setFixedWidth(200)
        layout.addWidget(self.path_edit)

        browse_btn = QPushButton("...")
        browse_btn.setFixedSize(32, 28)
        browse_btn.setProperty("ghost", True)
        browse_btn.clicked.connect(self._browse_path)
        layout.addWidget(browse_btn)

        return container

    def _create_field_row(self, label_text: str, widget: QWidget) -> QHBoxLayout:
        """Create a labeled field row."""
        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(label_text)
        label.setFixedWidth(70)
        label.setStyleSheet("color: #6b7280; font-size: 12px;")
        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch()

        return row

    def _create_action_bar(self) -> QWidget:
        """Create bottom action bar."""
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border-top: 1px solid #2a2f3a;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(12)

        # Summary - compact
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._update_summary()
        layout.addWidget(self.summary_label)

        layout.addStretch()

        # Clear button
        self.clear_btn = QPushButton("Limpar")
        self.clear_btn.setProperty("ghost", True)
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.clicked.connect(self._clear_form)
        layout.addWidget(self.clear_btn)

        # Submit button
        self.submit_btn = QPushButton("Executar")
        self.submit_btn.setFixedWidth(120)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                font-weight: 600;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #2d3442;
                color: #4b5563;
            }
        """)
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
        self.summary_label.setText(f"{profile} • {max_iter} iterações")

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
