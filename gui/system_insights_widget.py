"""Compact dashboard widget for aggregate system insights."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from orchestrator.recommended_actions import RecommendedActionsEngine
from orchestrator.system_insights import (
    SystemHealthStatus,
    SystemInsightReport,
    get_system_insights_analyzer,
    health_status_display,
    trend_direction_display,
)
from .recommended_actions_widget import RecommendedActionsWidget


HEALTH_COLORS = {
    SystemHealthStatus.STABLE: "#22c55e",
    SystemHealthStatus.USABLE_WITH_ALERTS: "#f59e0b",
    SystemHealthStatus.DEGRADED: "#fb7185",
    SystemHealthStatus.RECURRING_FAILURES: "#ef4444",
}


class SystemInsightMiniCard(QFrame):
    """Small line item for a top aggregate insight."""

    def __init__(self, title: str, message: str, severity: str, parent=None):
        super().__init__(parent)
        color = {"success": "#22c55e", "info": "#4f8cff", "warning": "#f59e0b", "error": "#ef4444"}.get(severity, "#6b7280")
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: #12161d;
                border: 1px solid #2a2f3a;
                border-left: 3px solid {color};
                border-radius: 6px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #e6edf3;")
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 11px; color: #9da7b3;")
        layout.addWidget(message_label)


class SystemInsightsWidget(QFrame):
    """Compact summary widget for the dashboard."""

    open_requested = Signal()
    action_requested = Signal(object)

    def __init__(self, workspace_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self._report: Optional[SystemInsightReport] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("Insights do Sistema")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #e6edf3;")
        title_box.addWidget(title)

        subtitle = QLabel("Resumo operacional recente com padrões e recomendações.")
        subtitle.setStyleSheet("font-size: 11px; color: #8b949e;")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.health_badge = QLabel("Sem dados")
        self.health_badge.setStyleSheet("background-color: #1f2937; color: #9da7b3; padding: 4px 8px; border-radius: 10px;")
        header.addWidget(self.health_badge)

        open_btn = QPushButton("Abrir visão completa")
        open_btn.setObjectName("secondary")
        open_btn.clicked.connect(self.open_requested.emit)
        header.addWidget(open_btn)
        layout.addLayout(header)

        self.summary_label = QLabel("Ainda não há histórico suficiente para gerar insights agregados.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        layout.addWidget(self.summary_label)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self.metric_widgets: dict[str, QWidget] = {}
        for key in ["success_rate", "failure_rate", "avg_duration", "checkpoint_rate"]:
            widget = self._create_metric_widget()
            self.metric_widgets[key] = widget
            metrics_row.addWidget(widget)
        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        self.insights_container = QVBoxLayout()
        self.insights_container.setSpacing(8)
        layout.addLayout(self.insights_container)

        self.actions_widget = RecommendedActionsWidget()
        self.actions_widget.action_requested.connect(self.action_requested.emit)
        layout.addWidget(self.actions_widget)

    def _create_metric_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel("-")
        label.setObjectName("label")
        label.setStyleSheet("font-size: 10px; color: #6b7280;")
        layout.addWidget(label)

        value = QLabel("-")
        value.setObjectName("value")
        value.setStyleSheet("font-size: 12px; color: #e6edf3; font-weight: 600;")
        layout.addWidget(value)

        detail = QLabel("")
        detail.setObjectName("detail")
        detail.setStyleSheet("font-size: 10px; color: #6b7280;")
        layout.addWidget(detail)
        return widget

    def set_workspace(self, workspace_path: Path):
        self.workspace_path = workspace_path

    def load_report(self, *, limit: int = 10):
        if not self.workspace_path:
            return
        analyzer = get_system_insights_analyzer(self.workspace_path)
        self.set_report(analyzer.analyze(limit=limit))

    def set_report(self, report: SystemInsightReport):
        self._report = report
        self._rebuild_ui()

    def clear_report(self):
        self._report = None
        self._rebuild_ui()

    def copy_summary(self):
        if self._report:
            QApplication.clipboard().setText(self._report.executive_summary)

    def get_report(self) -> Optional[SystemInsightReport]:
        return self._report

    def _rebuild_ui(self):
        while self.insights_container.count():
            item = self.insights_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._report:
            self.health_badge.setText("Sem dados")
            self.summary_label.setText("Ainda não há histórico suficiente para gerar insights agregados.")
            for widget in self.metric_widgets.values():
                self._set_metric(widget, "-", "-", "")
            self.actions_widget.clear_group()
            return

        color = HEALTH_COLORS.get(self._report.health_status, "#6b7280")
        self.health_badge.setText(health_status_display(self._report.health_status))
        self.health_badge.setStyleSheet(f"background-color: {color}20; color: {color}; padding: 4px 8px; border-radius: 10px;")
        self.summary_label.setText(self._report.executive_summary)

        metric_map = {metric.key: metric for metric in self._report.metrics}
        for key, widget in self.metric_widgets.items():
            metric = metric_map.get(key)
            if metric:
                self._set_metric(widget, metric.label, metric.display_value, trend_direction_display(metric.direction))
            else:
                self._set_metric(widget, "-", "-", "")

        for insight in self._report.insights[:3]:
            self.insights_container.addWidget(SystemInsightMiniCard(insight.title, insight.message, insight.severity))

        self.actions_widget.set_group(RecommendedActionsEngine().from_system_report(self._report))

    def _set_metric(self, widget: QWidget, label_text: str, value_text: str, detail_text: str):
        label = widget.findChild(QLabel, "label")
        value = widget.findChild(QLabel, "value")
        detail = widget.findChild(QLabel, "detail")
        if label:
            label.setText(label_text)
        if value:
            value.setText(value_text)
        if detail:
            detail.setText(detail_text)
