"""Floating content card for the interactive demo."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout

from .demo_scenarios import DemoStep


class InteractiveDemoCard(QFrame):
    """Compact floating panel with the current demo step."""

    next_requested = Signal()
    back_requested = Signal()
    skip_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("interactive_demo_card")
        self.setStyleSheet(
            """
            QFrame#interactive_demo_card {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            """
        )
        self.setMinimumWidth(420)
        self.setMaximumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.progress_label = QLabel("Etapa 1 de 1")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600;")
        top_row.addWidget(self.progress_label)
        top_row.addStretch()

        close_btn = QPushButton("Fechar demo")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(self.close_requested.emit)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        self.title_label = QLabel("Demo Interativo")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: 700;")
        layout.addWidget(self.title_label)

        self.body_label = QLabel("")
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        layout.addWidget(self.body_label)

        self.hint_label = QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            "color: #7dd3fc; font-size: 11px; background-color: #082f49; border-radius: 8px; padding: 8px;"
        )
        layout.addWidget(self.hint_label)

        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setMinimumHeight(240)
        self.content_browser.setStyleSheet(
            "QTextBrowser { background-color: #0f172a; border: 1px solid #1f2937; border-radius: 8px; padding: 8px; }"
        )
        layout.addWidget(self.content_browser, 1)

        actions = QHBoxLayout()
        self.skip_btn = QPushButton("Pular demo")
        self.skip_btn.setProperty("secondary", True)
        self.skip_btn.clicked.connect(self.skip_requested.emit)
        actions.addWidget(self.skip_btn)

        actions.addStretch()

        self.back_btn = QPushButton("Voltar")
        self.back_btn.setProperty("secondary", True)
        self.back_btn.clicked.connect(self.back_requested.emit)
        actions.addWidget(self.back_btn)

        self.next_btn = QPushButton("Próximo")
        self.next_btn.clicked.connect(self.next_requested.emit)
        actions.addWidget(self.next_btn)
        layout.addLayout(actions)

    def set_step(self, index: int, total: int, step: DemoStep):
        self.progress_label.setText(f"Etapa {index} de {total}")
        self.title_label.setText(step.title)
        self.body_label.setText(step.body)
        self.hint_label.setText(step.primary_hint or "")
        self.hint_label.setVisible(bool(step.primary_hint))
        self.content_browser.setHtml(step.content_html or "")
        self.content_browser.verticalScrollBar().setValue(0)
        self.back_btn.setEnabled(index > 1)
        self.next_btn.setText("Concluir" if index == total else "Próximo")
