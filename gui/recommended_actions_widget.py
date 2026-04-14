"""Reusable widget for recommended actions."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from orchestrator.recommended_actions import ActionPriority, RecommendedAction, RecommendedActionGroup


PRIORITY_STYLES = {
    ActionPriority.IMMEDIATE: ("Agora", "#ef4444"),
    ActionPriority.RECOMMENDED: ("Recomendado", "#f59e0b"),
    ActionPriority.OPTIONAL: ("Opcional", "#4f8cff"),
}


class RecommendedActionCard(QFrame):
    """Single recommended action card."""

    action_requested = Signal(object)

    def __init__(self, action: RecommendedAction, parent=None):
        super().__init__(parent)
        self.action = action
        self._setup_ui()

    def _setup_ui(self):
        label, color = PRIORITY_STYLES.get(self.action.priority, ("Ação", "#6b7280"))
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-left: 3px solid {color};
                border-radius: 6px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(self.action.title)
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        header.addWidget(title)
        header.addStretch()

        badge = QLabel(label)
        badge.setStyleSheet(f"background-color: {color}20; color: {color}; padding: 2px 7px; border-radius: 9px; font-size: 10px; font-weight: 600;")
        header.addWidget(badge)
        layout.addLayout(header)

        description = QLabel(self.action.description)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        layout.addWidget(description)

        if self.action.recommendation_reason:
            reason = QLabel(self.action.recommendation_reason)
            reason.setWordWrap(True)
            reason.setStyleSheet("font-size: 11px; color: #8b949e;")
            layout.addWidget(reason)

        footer = QHBoxLayout()
        confidence = QLabel(f"Confiança {int(self.action.confidence * 100)}%")
        confidence.setStyleSheet("font-size: 10px; color: #6b7280;")
        footer.addWidget(confidence)
        footer.addStretch()

        action_btn = QPushButton("Executar ação")
        action_btn.clicked.connect(lambda: self.action_requested.emit(self.action))
        footer.addWidget(action_btn)
        layout.addLayout(footer)


class RecommendedActionsWidget(QFrame):
    """List of recommended actions with compact empty state."""

    action_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._group: Optional[RecommendedActionGroup] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("Ações recomendadas")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #e6edf3;")
        header.addWidget(self.title_label)
        header.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.summary_label = QLabel("As próximas ações vão aparecer aqui quando houver contexto suficiente.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        layout.addWidget(self.summary_label)

        self.actions_layout = QVBoxLayout()
        self.actions_layout.setSpacing(8)
        layout.addLayout(self.actions_layout)

        self.empty_label = QLabel("Nenhuma ação recomendada no momento.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("font-size: 12px; color: #6b7280; padding: 18px;")
        layout.addWidget(self.empty_label)

    def set_group(self, group: RecommendedActionGroup):
        self._group = group
        self._rebuild_ui()

    def clear_group(self):
        self._group = None
        self._rebuild_ui()

    def get_group(self) -> Optional[RecommendedActionGroup]:
        return self._group

    def _rebuild_ui(self):
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._group or not self._group.actions:
            self.title_label.setText("Ações recomendadas")
            self.count_label.setText("")
            self.summary_label.setText("As próximas ações vão aparecer aqui quando houver contexto suficiente.")
            self.empty_label.setVisible(True)
            return

        self.title_label.setText(self._group.title)
        self.count_label.setText(f"{len(self._group.actions)} ação(ões)")
        self.summary_label.setText(self._group.summary)
        self.empty_label.setVisible(False)

        for action in self._group.actions:
            card = RecommendedActionCard(action)
            card.action_requested.connect(self.action_requested.emit)
            self.actions_layout.addWidget(card)
