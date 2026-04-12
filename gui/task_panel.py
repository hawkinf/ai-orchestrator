"""Task creation panel - Nova Tarefa."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QLineEdit, QFileDialog, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt

from .ui_models import TaskConfig


class TaskPanel(QWidget):
    """Panel for creating and submitting new tasks."""

    # Signals
    task_submitted = Signal(TaskConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Nova Tarefa")
        header.setObjectName("header")
        header.setStyleSheet("font-size: 24px; font-weight: 600; color: #1e293b;")
        layout.addWidget(header)

        subheader = QLabel("Descreva a tarefa que deseja executar")
        subheader.setObjectName("subheader")
        subheader.setStyleSheet("color: #64748b; margin-bottom: 16px;")
        layout.addWidget(subheader)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)

        # Task description
        task_group = self._create_task_group()
        scroll_layout.addWidget(task_group)

        # Project settings
        project_group = self._create_project_group()
        scroll_layout.addWidget(project_group)

        # Execution options
        options_group = self._create_options_group()
        scroll_layout.addWidget(options_group)

        # Config summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("""
            background-color: #f1f5f9;
            border-radius: 6px;
            padding: 12px;
            color: #64748b;
        """)
        self._update_summary()
        scroll_layout.addWidget(self.summary_label)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.clear_btn = QPushButton("Limpar")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._clear_form)
        buttons_layout.addWidget(self.clear_btn)

        buttons_layout.addStretch()

        self.submit_btn = QPushButton("Executar")
        self.submit_btn.setFixedWidth(140)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.submit_btn.clicked.connect(self._submit_task)
        buttons_layout.addWidget(self.submit_btn)

        layout.addLayout(buttons_layout)

    def _create_task_group(self) -> QGroupBox:
        """Create task description group."""
        group = QGroupBox("Descricao da Tarefa")
        layout = QVBoxLayout(group)

        self.task_edit = QTextEdit()
        self.task_edit.setPlaceholderText(
            "Descreva a tarefa aqui...\n\n"
            "Exemplo:\n"
            "- Corrigir bug de login\n"
            "- Adicionar validacao de campos\n"
            "- Rodar flutter analyze e flutter test"
        )
        self.task_edit.setMinimumHeight(200)
        self.task_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        self.task_edit.textChanged.connect(self._update_summary)
        layout.addWidget(self.task_edit)

        # Character counter
        self.char_counter = QLabel("0 caracteres")
        self.char_counter.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.task_edit.textChanged.connect(self._update_char_count)
        layout.addWidget(self.char_counter)

        return group

    def _create_project_group(self) -> QGroupBox:
        """Create project settings group."""
        group = QGroupBox("Projeto")
        layout = QVBoxLayout(group)

        # Project path
        path_layout = QHBoxLayout()
        path_label = QLabel("Diretorio:")
        path_label.setFixedWidth(80)
        path_layout.addWidget(path_label)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(".")
        self.path_edit.setText(".")
        path_layout.addWidget(self.path_edit)

        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(40)
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Profile
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Perfil:")
        profile_label.setFixedWidth(80)
        profile_layout.addWidget(profile_label)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["flutter", "python", "generic"])
        self.profile_combo.setCurrentText("flutter")
        self.profile_combo.currentTextChanged.connect(self._update_summary)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()

        layout.addLayout(profile_layout)

        # Mode
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Modo:")
        mode_label.setFixedWidth(80)
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Execucao Completa",
            "Somente Planejar",
            "Planejar + Executar",
        ])
        self.mode_combo.currentTextChanged.connect(self._update_summary)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        return group

    def _create_options_group(self) -> QGroupBox:
        """Create execution options group."""
        group = QGroupBox("Opcoes de Execucao")
        layout = QVBoxLayout(group)

        # Checkboxes row 1
        row1 = QHBoxLayout()

        self.auto_validate_cb = QCheckBox("Auto Validar")
        self.auto_validate_cb.setChecked(True)
        self.auto_validate_cb.stateChanged.connect(self._update_summary)
        row1.addWidget(self.auto_validate_cb)

        self.auto_commit_cb = QCheckBox("Auto Commit")
        self.auto_commit_cb.setChecked(False)
        self.auto_commit_cb.stateChanged.connect(self._update_summary)
        row1.addWidget(self.auto_commit_cb)

        self.auto_push_cb = QCheckBox("Auto Push/Sync")
        self.auto_push_cb.setChecked(False)
        self.auto_push_cb.stateChanged.connect(self._update_summary)
        row1.addWidget(self.auto_push_cb)

        row1.addStretch()
        layout.addLayout(row1)

        # Checkboxes row 2
        row2 = QHBoxLayout()

        self.require_approval_cb = QCheckBox("Exigir aprovacao em mudancas destrutivas")
        self.require_approval_cb.setChecked(True)
        self.require_approval_cb.stateChanged.connect(self._update_summary)
        row2.addWidget(self.require_approval_cb)

        row2.addStretch()
        layout.addLayout(row2)

        # Max iterations
        iter_layout = QHBoxLayout()
        iter_label = QLabel("Max Iteracoes:")
        iter_layout.addWidget(iter_label)

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 10)
        self.max_iter_spin.setValue(3)
        self.max_iter_spin.setFixedWidth(80)
        self.max_iter_spin.valueChanged.connect(self._update_summary)
        iter_layout.addWidget(self.max_iter_spin)

        iter_layout.addStretch()
        layout.addLayout(iter_layout)

        return group

    def _update_char_count(self):
        """Update character counter."""
        count = len(self.task_edit.toPlainText())
        self.char_counter.setText(f"{count} caracteres")

    def _update_summary(self):
        """Update configuration summary."""
        task_len = len(self.task_edit.toPlainText())
        profile = self.profile_combo.currentText()
        mode = self.mode_combo.currentText()
        max_iter = self.max_iter_spin.value()

        opts = []
        if self.auto_validate_cb.isChecked():
            opts.append("validar")
        if self.auto_commit_cb.isChecked():
            opts.append("commit")
        if self.auto_push_cb.isChecked():
            opts.append("push")
        if self.require_approval_cb.isChecked():
            opts.append("checkpoint")

        opts_str = ", ".join(opts) if opts else "nenhuma"

        summary = (
            f"Perfil: {profile} | Modo: {mode} | "
            f"Max Iteracoes: {max_iter} | Opcoes: {opts_str}"
        )
        self.summary_label.setText(summary)

    def _browse_path(self):
        """Open directory browser."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Diretorio do Projeto",
            self.path_edit.text() or ".",
        )
        if path:
            self.path_edit.setText(path)

    def _clear_form(self):
        """Clear the form."""
        self.task_edit.clear()
        self.path_edit.setText(".")
        self.profile_combo.setCurrentIndex(0)
        self.mode_combo.setCurrentIndex(0)
        self.auto_validate_cb.setChecked(True)
        self.auto_commit_cb.setChecked(False)
        self.auto_push_cb.setChecked(False)
        self.require_approval_cb.setChecked(True)
        self.max_iter_spin.setValue(3)

    def _submit_task(self):
        """Submit the task."""
        task_text = self.task_edit.toPlainText().strip()
        if not task_text:
            return

        # Map mode
        mode_map = {
            "Execucao Completa": "full",
            "Somente Planejar": "plan_only",
            "Planejar + Executar": "plan_execute",
        }
        mode = mode_map.get(self.mode_combo.currentText(), "full")

        config = TaskConfig(
            task_description=task_text,
            project_path=self.path_edit.text() or ".",
            profile=self.profile_combo.currentText(),
            mode=mode,
            auto_validate=self.auto_validate_cb.isChecked(),
            auto_commit=self.auto_commit_cb.isChecked(),
            auto_push=self.auto_push_cb.isChecked(),
            require_approval_destructive=self.require_approval_cb.isChecked(),
            max_iterations=self.max_iter_spin.value(),
        )

        self.task_submitted.emit(config)

    def set_task(self, task: str):
        """Set task text (for resuming or templates)."""
        self.task_edit.setPlainText(task)

    def set_profile(self, profile: str):
        """Set profile selection."""
        index = self.profile_combo.findText(profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def set_path(self, path: str):
        """Set project path."""
        self.path_edit.setText(path)

    def get_config(self) -> Optional[TaskConfig]:
        """Get current configuration without submitting."""
        task_text = self.task_edit.toPlainText().strip()
        if not task_text:
            return None

        mode_map = {
            "Execucao Completa": "full",
            "Somente Planejar": "plan_only",
            "Planejar + Executar": "plan_execute",
        }
        mode = mode_map.get(self.mode_combo.currentText(), "full")

        return TaskConfig(
            task_description=task_text,
            project_path=self.path_edit.text() or ".",
            profile=self.profile_combo.currentText(),
            mode=mode,
            auto_validate=self.auto_validate_cb.isChecked(),
            auto_commit=self.auto_commit_cb.isChecked(),
            auto_push=self.auto_push_cb.isChecked(),
            require_approval_destructive=self.require_approval_cb.isChecked(),
            max_iterations=self.max_iter_spin.value(),
        )
