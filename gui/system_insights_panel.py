"""Full panel for aggregate system insights."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from orchestrator.run_index import RunStatus
from orchestrator.recommended_actions import RecommendedActionsEngine
from orchestrator.system_insights import SystemInsightReport, SystemInsightsAnalyzer, get_system_insights_analyzer, health_status_display, trend_direction_display
from .recommended_actions_widget import RecommendedActionsWidget


class SystemInsightsPanel(QWidget):
    """Detailed system insights view with filters and export."""

    action_requested = Signal(object)

    def __init__(self, workspace_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self._analyzer: Optional[SystemInsightsAnalyzer] = None
        self._report: Optional[SystemInsightReport] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Insights do Sistema")
        title.setProperty("heading", True)
        title_box.addWidget(title)
        subtitle = QLabel("Analise o histórico recente de runs para detectar padrões operacionais, gargalos e recomendações.")
        subtitle.setProperty("subheading", True)
        subtitle.setWordWrap(True)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        self.export_btn = QPushButton("Exportar")
        self.export_btn.setObjectName("secondary")
        self.export_btn.clicked.connect(self._export_report)
        header.addWidget(self.export_btn)

        self.copy_btn = QPushButton("Copiar resumo")
        self.copy_btn.setObjectName("secondary")
        self.copy_btn.clicked.connect(self._copy_summary)
        header.addWidget(self.copy_btn)
        layout.addLayout(header)

        filters = QFrame()
        filters.setProperty("card", True)
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(16, 12, 16, 12)
        filters_layout.setSpacing(10)

        self.range_combo = QComboBox()
        self.range_combo.addItem("Últimas 10 runs", 10)
        self.range_combo.addItem("Últimas 20 runs", 20)
        self.range_combo.addItem("Últimas 50 runs", 50)
        self.range_combo.addItem("Últimas 100 runs", 100)
        filters_layout.addWidget(self.range_combo)

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Todos os perfis", None)
        filters_layout.addWidget(self.profile_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos os status", None)
        self.status_combo.addItem("Concluídas", RunStatus.COMPLETED)
        self.status_combo.addItem("Falhas", RunStatus.FAILED)
        self.status_combo.addItem("Checkpoint", RunStatus.CHECKPOINT)
        filters_layout.addWidget(self.status_combo)

        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_from_edit.setSpecialValueText("Sem início")
        self.date_from_edit.setMinimumDate(QDate(2000, 1, 1))
        self.date_from_edit.setDate(self.date_from_edit.minimumDate())
        filters_layout.addWidget(self.date_from_edit)

        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_to_edit.setSpecialValueText("Sem fim")
        self.date_to_edit.setMinimumDate(QDate(2000, 1, 1))
        self.date_to_edit.setDate(self.date_to_edit.minimumDate())
        filters_layout.addWidget(self.date_to_edit)
        filters_layout.addStretch()
        layout.addWidget(filters)

        self.summary_card = QFrame()
        self.summary_card.setProperty("card", True)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(18, 16, 18, 16)
        summary_layout.setSpacing(8)

        summary_header = QHBoxLayout()
        self.health_label = QLabel("Sem dados")
        self.health_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #e6edf3;")
        summary_header.addWidget(self.health_label)
        summary_header.addStretch()
        self.window_label = QLabel("")
        self.window_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        summary_header.addWidget(self.window_label)
        summary_layout.addLayout(summary_header)

        self.summary_label = QLabel("Ainda não há dados suficientes para gerar insights do sistema.")
        self.summary_label.setProperty("subheading", True)
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_card)

        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(10)
        metrics_wrap = QWidget()
        metrics_wrap.setLayout(self.metrics_grid)
        layout.addWidget(metrics_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)

    def set_workspace(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self._analyzer = get_system_insights_analyzer(workspace_path)
        self._load_profiles()

    def refresh(self):
        if not self.workspace_path:
            return
        if self._analyzer is None:
            self._analyzer = get_system_insights_analyzer(self.workspace_path)
        self.set_report(
            self._analyzer.analyze(
                limit=int(self.range_combo.currentData()),
                profile=self.profile_combo.currentData(),
                statuses=[self.status_combo.currentData()] if self.status_combo.currentData() else None,
                date_from=self._date_edit_to_datetime(self.date_from_edit, is_end=False),
                date_to=self._date_edit_to_datetime(self.date_to_edit, is_end=True),
            )
        )

    def set_report(self, report: SystemInsightReport):
        self._report = report
        self._rebuild_ui()

    def get_report(self) -> Optional[SystemInsightReport]:
        return self._report

    def _date_edit_to_datetime(self, widget: QDateEdit, *, is_end: bool) -> Optional[datetime]:
        if widget.date() == widget.minimumDate():
            return None
        qdate = widget.date()
        base = datetime(qdate.year(), qdate.month(), qdate.day())
        return datetime.combine(base.date(), time.max if is_end else time.min)

    def _load_profiles(self):
        if not self.workspace_path:
            return
        analyzer = self._analyzer or get_system_insights_analyzer(self.workspace_path)
        profiles = analyzer.index.get_profiles()
        current = self.profile_combo.currentData()
        self.profile_combo.clear()
        self.profile_combo.addItem("Todos os perfis", None)
        for profile in profiles:
            self.profile_combo.addItem(profile, profile)
        for index in range(self.profile_combo.count()):
            if self.profile_combo.itemData(index) == current:
                self.profile_combo.setCurrentIndex(index)
                break

    def _rebuild_ui(self):
        while self.metrics_grid.count():
            item = self.metrics_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._report or self._report.total_runs == 0:
            self.health_label.setText("Sem dados")
            self.window_label.setText("")
            self.summary_label.setText("Nenhuma run encontrada para os filtros escolhidos.")
            empty = QLabel("Nenhuma run encontrada para os filtros escolhidos.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("font-size: 12px; color: #8b949e; padding: 28px;")
            self.scroll_layout.addWidget(empty)
            return

        self.health_label.setText(health_status_display(self._report.health_status))
        self.window_label.setText(self._report.analysis_window.get("label", ""))
        self.summary_label.setText(self._report.executive_summary)

        for index, metric in enumerate(self._report.metrics):
            self.metrics_grid.addWidget(self._create_metric_card(metric.label, metric.display_value, trend_direction_display(metric.direction)), index // 3, index % 3)

        actions_widget = RecommendedActionsWidget()
        actions_widget.action_requested.connect(self.action_requested.emit)
        actions_widget.set_group(RecommendedActionsEngine().from_system_report(self._report))
        self.scroll_layout.addWidget(actions_widget)
        for insight in self._report.insights:
            self.scroll_layout.addWidget(self._create_insight_card(insight.title, insight.message, insight.recommendation, insight.severity))
        self.scroll_layout.addStretch()

    def _create_metric_card(self, label_text: str, value_text: str, detail_text: str) -> QFrame:
        frame = QFrame()
        frame.setProperty("card", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10px; color: #6b7280;")
        layout.addWidget(label)
        value = QLabel(value_text)
        value.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        layout.addWidget(value)
        detail = QLabel(detail_text)
        detail.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(detail)
        return frame

    def _create_insight_card(self, title_text: str, message_text: str, recommendation_text: str, severity: str) -> QFrame:
        color = {"success": "#22c55e", "info": "#4f8cff", "warning": "#f59e0b", "error": "#ef4444"}.get(severity, "#6b7280")
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: #161a22; border: 1px solid #2a2f3a; border-left: 3px solid {color}; border-radius: 6px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        layout.addWidget(title)
        message = QLabel(message_text)
        message.setWordWrap(True)
        message.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        layout.addWidget(message)
        if recommendation_text:
            recommendation = QLabel(f"Recomendação: {recommendation_text}")
            recommendation.setWordWrap(True)
            recommendation.setStyleSheet("font-size: 11px; color: #9da7b3;")
            layout.addWidget(recommendation)
        return frame

    def _export_report(self):
        if not self._report or not self.workspace_path:
            return
        try:
            analyzer = self._analyzer or get_system_insights_analyzer(self.workspace_path)
            paths = analyzer.export_report(self._report)
            QMessageBox.information(
                self,
                "Exportar insights",
                f"Relatório exportado:\n- JSON: {paths['json'].name}\n- Markdown: {paths['markdown'].name}\n- Ações: {paths['actions'].name}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Erro ao exportar", str(exc))

    def _copy_summary(self):
        if self._report:
            QApplication.clipboard().setText(self._report.executive_summary)
