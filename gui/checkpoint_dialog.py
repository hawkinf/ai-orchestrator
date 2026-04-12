"""Checkpoint approval dialog."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QFrame,
)
from PySide6.QtCore import Qt


class CheckpointDialog(QDialog):
    """Dialog for checkpoint approval/rejection."""

    def __init__(
        self,
        run_id: str,
        reason: str,
        description: str,
        parent=None
    ):
        super().__init__(parent)
        self.run_id = run_id
        self.reason = reason
        self.description = description
        self._approved = False
        self._note = ""
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Checkpoint Pendente")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("Aprovacao de Checkpoint")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(header)

        # Info
        info_group = QGroupBox("Informacoes")
        info_layout = QVBoxLayout(info_group)

        run_label = QLabel(f"Run: {self.run_id}")
        run_label.setStyleSheet("font-weight: 500;")
        info_layout.addWidget(run_label)

        reason_label = QLabel(f"Motivo: {self.reason}")
        reason_label.setWordWrap(True)
        info_layout.addWidget(reason_label)

        if self.description:
            desc_label = QLabel(f"Descricao: {self.description}")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

        layout.addWidget(info_group)

        # Warning
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_label = QLabel(
            "ATENCAO: Esta acao pode conter mudancas destrutivas ou irreversiveis.\n"
            "Revise cuidadosamente antes de aprovar."
        )
        warning_label.setStyleSheet("color: #92400e; font-weight: 500;")
        warning_label.setWordWrap(True)
        warning_layout.addWidget(warning_label)
        layout.addWidget(warning_frame)

        # Note input
        note_group = QGroupBox("Observacao (opcional)")
        note_layout = QVBoxLayout(note_group)
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Adicione uma observacao sobre sua decisao...")
        self.note_edit.setMaximumHeight(100)
        note_layout.addWidget(self.note_edit)
        layout.addWidget(note_group)

        # Buttons
        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        buttons_layout.addStretch()

        reject_btn = QPushButton("Rejeitar")
        reject_btn.setObjectName("danger")
        reject_btn.clicked.connect(self._reject)
        buttons_layout.addWidget(reject_btn)

        approve_btn = QPushButton("Aprovar")
        approve_btn.setObjectName("success")
        approve_btn.clicked.connect(self._approve)
        buttons_layout.addWidget(approve_btn)

        layout.addLayout(buttons_layout)

    def _approve(self):
        """Approve the checkpoint."""
        self._approved = True
        self._note = self.note_edit.toPlainText().strip()
        self.accept()

    def _reject(self):
        """Reject the checkpoint."""
        self._approved = False
        self._note = self.note_edit.toPlainText().strip()
        self.accept()

    def was_approved(self) -> bool:
        """Check if checkpoint was approved."""
        return self._approved

    def get_note(self) -> str:
        """Get the user's note."""
        return self._note


class CheckpointNotification(QFrame):
    """Notification widget for pending checkpoints."""

    def __init__(self, run_id: str, reason: str, parent=None):
        super().__init__(parent)
        self.run_id = run_id
        self.reason = reason
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setStyleSheet("""
            QFrame {
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)

        # Icon/indicator
        icon_label = QLabel("!")
        icon_label.setStyleSheet("""
            background-color: #f59e0b;
            color: white;
            font-weight: bold;
            font-size: 14px;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
            border-radius: 12px;
            text-align: center;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel("Checkpoint Pendente")
        title_label.setStyleSheet("font-weight: 600; color: #92400e;")
        text_layout.addWidget(title_label)

        info_label = QLabel(f"Run: {self.run_id} - {self.reason}")
        info_label.setStyleSheet("color: #92400e; font-size: 12px;")
        text_layout.addWidget(info_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Action button
        self.action_btn = QPushButton("Revisar")
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
        """)
        layout.addWidget(self.action_btn)
