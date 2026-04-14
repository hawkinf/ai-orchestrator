"""Run insights widget.

Displays actionable insights, executive summary, and recommendations
for a run based on timeline analysis.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QApplication,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from orchestrator.run_insights import (
    RunInsightReport,
    RunInsight,
    InsightSeverity,
    InsightCategory,
    RunOutcome,
    InsightsAnalyzer,
    OUTCOME_DISPLAY,
)
from orchestrator.run_timeline import TimelineBuilder


# Severity colors
SEVERITY_COLORS = {
    InsightSeverity.INFO: "#3b82f6",      # Blue
    InsightSeverity.SUCCESS: "#22c55e",   # Green
    InsightSeverity.WARNING: "#f59e0b",   # Amber
    InsightSeverity.ERROR: "#ef4444",     # Red
}

# Severity icons
SEVERITY_ICONS = {
    InsightSeverity.INFO: "ℹ️",
    InsightSeverity.SUCCESS: "✅",
    InsightSeverity.WARNING: "⚠️",
    InsightSeverity.ERROR: "❌",
}

# Outcome colors
OUTCOME_COLORS = {
    RunOutcome.SUCCESS: "#22c55e",
    RunOutcome.SUCCESS_WITH_WARNINGS: "#f59e0b",
    RunOutcome.FAILED: "#ef4444",
    RunOutcome.INTERRUPTED: "#6b7280",
    RunOutcome.NEEDS_ATTENTION: "#f59e0b",
    RunOutcome.IN_PROGRESS: "#3b82f6",
}


class InsightCard(QFrame):
    """Card widget for a single insight."""

    action_clicked = Signal(str)  # recommendation_key

    def __init__(self, insight: RunInsight, parent=None):
        super().__init__(parent)
        self.insight = insight
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("insight-card", True)

        color = SEVERITY_COLORS.get(self.insight.severity, "#6b7280")
        self.setStyleSheet(f"""
            QFrame[insight-card=true] {{
                background-color: #161b22;
                border-left: 3px solid {color};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header with icon and title
        header = QHBoxLayout()
        header.setSpacing(8)

        icon = SEVERITY_ICONS.get(self.insight.severity, "•")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 14px;")
        header.addWidget(icon_label)

        title = QLabel(self.insight.title)
        title.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600;")
        header.addWidget(title)

        # Category badge
        category_names = {
            InsightCategory.VALIDATION: "Validação",
            InsightCategory.EXECUTION: "Execução",
            InsightCategory.REVIEW: "Revisão",
            InsightCategory.CHECKPOINT: "Checkpoint",
            InsightCategory.GIT: "Git",
            InsightCategory.CONFIGURATION: "Config",
            InsightCategory.PERFORMANCE: "Performance",
            InsightCategory.RELIABILITY: "Confiabilidade",
            InsightCategory.SUMMARY: "Resumo",
        }
        category_text = category_names.get(self.insight.category, self.insight.category.value)
        category_badge = QLabel(category_text)
        category_badge.setStyleSheet("""
            background-color: #21262d;
            color: #8b949e;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 8px;
        """)
        header.addWidget(category_badge)

        header.addStretch()
        layout.addLayout(header)

        # Message
        message = QLabel(self.insight.message)
        message.setWordWrap(True)
        message.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        layout.addWidget(message)

        # Recommendation
        if self.insight.recommendation:
            rec_layout = QHBoxLayout()
            rec_layout.setSpacing(6)

            rec_label = QLabel("💡")
            rec_label.setStyleSheet("font-size: 12px;")
            rec_layout.addWidget(rec_label)

            rec_text = QLabel(self.insight.recommendation)
            rec_text.setWordWrap(True)
            rec_text.setStyleSheet("color: #8b949e; font-size: 11px; font-style: italic;")
            rec_layout.addWidget(rec_text, 1)

            layout.addLayout(rec_layout)


class ExecutiveSummaryWidget(QFrame):
    """Widget for displaying executive summary."""

    copy_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report: Optional[RunInsightReport] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("summary-card", True)
        self.setStyleSheet("""
            QFrame[summary-card=true] {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        self.outcome_icon = QLabel("•")
        self.outcome_icon.setStyleSheet("font-size: 20px;")
        header.addWidget(self.outcome_icon)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.outcome_label = QLabel("Resultado")
        self.outcome_label.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: 600;")
        title_layout.addWidget(self.outcome_label)

        self.short_label = QLabel("")
        self.short_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_layout.addWidget(self.short_label)

        header.addLayout(title_layout)
        header.addStretch()

        # Copy button
        copy_btn = QPushButton("📋 Copiar")
        copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #8b949e;
                font-size: 11px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #21262d;
                color: #e6edf3;
            }
        """)
        copy_btn.clicked.connect(self._copy_summary)
        header.addWidget(copy_btn)

        layout.addLayout(header)

        # Summary text
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #c9d1d9; font-size: 13px;")
        layout.addWidget(self.summary_label)

        # Metrics row
        self.metrics_widget = QWidget()
        metrics_layout = QHBoxLayout(self.metrics_widget)
        metrics_layout.setContentsMargins(0, 8, 0, 0)
        metrics_layout.setSpacing(24)

        self.duration_label = self._create_metric("Duração", "-")
        metrics_layout.addWidget(self.duration_label)

        self.iterations_label = self._create_metric("Iterações", "-")
        metrics_layout.addWidget(self.iterations_label)

        self.checkpoints_label = self._create_metric("Checkpoints", "-")
        metrics_layout.addWidget(self.checkpoints_label)

        self.validation_label = self._create_metric("Validação", "-")
        metrics_layout.addWidget(self.validation_label)

        metrics_layout.addStretch()
        layout.addWidget(self.metrics_widget)

    def _create_metric(self, label: str, value: str) -> QWidget:
        """Create a metric display widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #6b7280; font-size: 10px;")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: 500;")
        value_widget.setObjectName("metric_value")
        layout.addWidget(value_widget)

        return widget

    def set_report(self, report: RunInsightReport):
        """Set the report to display."""
        self._report = report

        # Update outcome
        outcome_display = OUTCOME_DISPLAY.get(report.outcome, report.outcome.value)
        color = OUTCOME_COLORS.get(report.outcome, "#6b7280")

        outcome_icons = {
            RunOutcome.SUCCESS: "✓",
            RunOutcome.SUCCESS_WITH_WARNINGS: "⚠",
            RunOutcome.FAILED: "✗",
            RunOutcome.INTERRUPTED: "⏹",
            RunOutcome.NEEDS_ATTENTION: "⚡",
            RunOutcome.IN_PROGRESS: "⏳",
        }
        icon = outcome_icons.get(report.outcome, "•")

        self.outcome_icon.setText(icon)
        self.outcome_icon.setStyleSheet(f"color: {color}; font-size: 20px;")
        self.outcome_label.setText(outcome_display)
        self.outcome_label.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 600;")
        self.short_label.setText(report.short_label)

        # Update summary
        self.summary_label.setText(report.executive_summary)

        # Update metrics
        duration = self._format_duration(report.total_duration_seconds)
        self._update_metric(self.duration_label, duration)
        self._update_metric(self.iterations_label, str(report.iteration_count))
        self._update_metric(self.checkpoints_label, str(report.checkpoint_count))

        validation_text = "Passou" if report.validation_passed else "Falhou"
        validation_color = "#22c55e" if report.validation_passed else "#ef4444"
        val_value = self.validation_label.findChild(QLabel, "metric_value")
        if val_value:
            val_value.setText(validation_text)
            val_value.setStyleSheet(f"color: {validation_color}; font-size: 12px; font-weight: 500;")

    def _update_metric(self, widget: QWidget, value: str):
        """Update a metric widget's value."""
        value_label = widget.findChild(QLabel, "metric_value")
        if value_label:
            value_label.setText(value)

    def _format_duration(self, seconds: float) -> str:
        """Format duration for display."""
        if seconds <= 0:
            return "-"
        if seconds < 60:
            return f"{int(seconds)}s"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"

    def _copy_summary(self):
        """Copy summary to clipboard."""
        if self._report:
            text = f"{self._report.executive_summary}\n\n"
            text += f"Duração: {self._format_duration(self._report.total_duration_seconds)}\n"
            text += f"Iterações: {self._report.iteration_count}\n"
            text += f"Checkpoints: {self._report.checkpoint_count}\n"
            text += f"Validação: {'Passou' if self._report.validation_passed else 'Falhou'}"

            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.copy_clicked.emit()


class RunInsightsWidget(QWidget):
    """Complete insights widget for a run."""

    action_requested = Signal(str)  # recommendation_key

    def __init__(self, workspace_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self._report: Optional[RunInsightReport] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Insights da Run")
        title.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: 600;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.insight_count_label = QLabel("")
        self.insight_count_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        header_layout.addWidget(self.insight_count_label)

        layout.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0d1117;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #0d1117;
            }
        """)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)

        # Executive summary
        self.summary_widget = ExecutiveSummaryWidget()
        self.content_layout.addWidget(self.summary_widget)

        # Insights container
        self.insights_container = QWidget()
        self.insights_layout = QVBoxLayout(self.insights_container)
        self.insights_layout.setContentsMargins(0, 0, 0, 0)
        self.insights_layout.setSpacing(8)
        self.content_layout.addWidget(self.insights_container)

        self.content_layout.addStretch()

        # Empty state
        self.empty_label = QLabel("Selecione uma run para ver os insights")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6b7280; font-size: 13px; padding: 40px;")
        self.content_layout.insertWidget(0, self.empty_label)
        self.summary_widget.setVisible(False)
        self.insights_container.setVisible(False)

        scroll.setWidget(self.content)
        layout.addWidget(scroll, 1)

    def set_workspace(self, workspace_path: Path):
        """Set the workspace path."""
        self.workspace_path = workspace_path

    def load_insights(self, run_id: str):
        """Load and display insights for a run."""
        if not self.workspace_path:
            return

        analyzer = InsightsAnalyzer(self.workspace_path)
        report = analyzer.analyze_from_run_id(run_id)

        if report:
            self.set_report(report)
        else:
            self.clear_insights()

    def set_report(self, report: RunInsightReport):
        """Set the report to display."""
        self._report = report
        self._rebuild_ui()

    def clear_insights(self):
        """Clear the insights display."""
        self._report = None
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Rebuild the UI with current report."""
        # Clear existing insights
        while self.insights_layout.count():
            item = self.insights_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._report:
            self.empty_label.setVisible(True)
            self.summary_widget.setVisible(False)
            self.insights_container.setVisible(False)
            self.insight_count_label.setText("")
            return

        self.empty_label.setVisible(False)
        self.summary_widget.setVisible(True)
        self.insights_container.setVisible(True)

        # Update summary
        self.summary_widget.set_report(self._report)

        # Update insight count
        count = len(self._report.insights)
        self.insight_count_label.setText(f"{count} insight(s)")

        # Add section headers and insights by severity
        error_insights = self._report.get_by_severity(InsightSeverity.ERROR)
        warning_insights = self._report.get_by_severity(InsightSeverity.WARNING)
        info_insights = self._report.get_by_severity(InsightSeverity.INFO)
        success_insights = self._report.get_by_severity(InsightSeverity.SUCCESS)

        if error_insights:
            self._add_section("Problemas", error_insights)

        if warning_insights:
            self._add_section("Avisos", warning_insights)

        if info_insights:
            self._add_section("Informações", info_insights)

        if success_insights:
            self._add_section("Sucessos", success_insights)

    def _add_section(self, title: str, insights: list):
        """Add a section with insights."""
        if not insights:
            return

        # Section header
        header = QLabel(title)
        header.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 600; margin-top: 8px;")
        self.insights_layout.addWidget(header)

        # Add insight cards
        for insight in insights:
            card = InsightCard(insight)
            card.action_clicked.connect(self.action_requested.emit)
            self.insights_layout.addWidget(card)

    def get_report(self) -> Optional[RunInsightReport]:
        """Get the current report."""
        return self._report

    def get_short_label(self) -> str:
        """Get the short label for dashboard display."""
        if self._report:
            return self._report.short_label
        return ""


def get_short_insight_label(workspace_path: Path, run_id: str) -> str:
    """Get a short insight label for a run (for dashboard use)."""
    analyzer = InsightsAnalyzer(workspace_path)
    report = analyzer.analyze_from_run_id(run_id)
    if report:
        return report.short_label
    return ""
