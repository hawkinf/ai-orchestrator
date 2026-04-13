"""Checkpoint Center panel for GUI.

Provides centralized view and management of all checkpoints.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QTextEdit,
    QGroupBox, QScrollArea, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from orchestrator.checkpoint_index import (
    CheckpointDecisionStatus,
    CheckpointDetail,
    CheckpointFilter,
    CheckpointMetrics,
    CheckpointSeverity,
    CheckpointSummary,
)
from .checkpoints_models import (
    CheckpointUIState,
    MetricCard,
    format_datetime,
    format_duration,
    get_severity_display,
    get_status_display,
    get_reason_display,
    get_severity_icon,
)
from .checkpoints_worker import CheckpointManager as CheckpointWorkerManager

logger = logging.getLogger("ai_orchestrator.checkpoints_panel")


class SeverityBadge(QLabel):
    """Badge showing checkpoint severity."""

    def __init__(self, severity: CheckpointSeverity, parent=None):
        super().__init__(parent)
        self.set_severity(severity)

    def set_severity(self, severity: CheckpointSeverity):
        """Set severity and update style."""
        text, color = get_severity_display(severity)
        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)


class StatusBadge(QLabel):
    """Badge showing checkpoint status."""

    def __init__(self, status: CheckpointDecisionStatus, parent=None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: CheckpointDecisionStatus):
        """Set status and update style."""
        text, color = get_status_display(status)
        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)


class MetricCardWidget(QFrame):
    """Single metric card widget."""

    def __init__(self, label: str, value: int, color: str, parent=None):
        super().__init__(parent)
        self._setup_ui(label, value, color)

    def _setup_ui(self, label: str, value: int, color: str):
        """Setup the widget."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self.setMinimumWidth(90)
        self.setMaximumWidth(140)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 10, 10, 10)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {color};
        """)
        layout.addWidget(self.value_label)

        self.label_label = QLabel(label)
        self.label_label.setStyleSheet("""
            font-size: 11px;
            color: #6b7280;
        """)
        layout.addWidget(self.label_label)

    def update_value(self, value: int):
        """Update displayed value."""
        self.value_label.setText(str(value))


class MetricsBar(QWidget):
    """Bar showing checkpoint metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create cards - updated colors for dark theme
        card_specs = [
            ("total", "Total", "#4f8cff"),
            ("pending", "Pendentes", "#f59e0b"),
            ("approved", "Aprovados", "#22c55e"),
            ("rejected", "Rejeitados", "#ef4444"),
            ("critical", "Criticos", "#dc2626"),
            ("high_risk", "Alto Risco", "#ea580c"),
        ]

        for key, label, color in card_specs:
            card = MetricCardWidget(label, 0, color)
            self._cards[key] = card
            layout.addWidget(card)

        layout.addStretch()

    def update_metrics(self, metrics: CheckpointMetrics):
        """Update all metric cards."""
        self._cards["total"].update_value(metrics.total_checkpoints)
        self._cards["pending"].update_value(metrics.pending_checkpoints)
        self._cards["approved"].update_value(metrics.approved_checkpoints)
        self._cards["rejected"].update_value(metrics.rejected_checkpoints)
        self._cards["critical"].update_value(metrics.critical_pending)
        self._cards["high_risk"].update_value(metrics.high_risk_pending)


class FilterBar(QWidget):
    """Filter controls for checkpoint list."""

    filter_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 8, 0, 8)

        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por run_id, descricao...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.search_edit)

        # Status filter
        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos", None)
        self.status_combo.addItem("Pendentes", CheckpointDecisionStatus.PENDING)
        self.status_combo.addItem("Aprovados", CheckpointDecisionStatus.APPROVED)
        self.status_combo.addItem("Rejeitados", CheckpointDecisionStatus.REJECTED)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.status_combo)

        # Severity filter
        layout.addWidget(QLabel("Severidade:"))
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("Todas", None)
        self.severity_combo.addItem("Critico", CheckpointSeverity.CRITICAL)
        self.severity_combo.addItem("Alto Risco", CheckpointSeverity.HIGH_RISK)
        self.severity_combo.addItem("Alerta", CheckpointSeverity.WARNING)
        self.severity_combo.addItem("Info", CheckpointSeverity.INFO)
        self.severity_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.severity_combo)

        # Reason filter
        layout.addWidget(QLabel("Tipo:"))
        self.reason_combo = QComboBox()
        self.reason_combo.addItem("Todos", None)
        self.reason_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.reason_combo)

        layout.addStretch()

        # Clear filters
        clear_btn = QPushButton("Limpar")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.clear_filters)
        layout.addWidget(clear_btn)

    def _on_filter_changed(self):
        """Emit filter changed signal."""
        self.filter_changed.emit()

    def set_reasons(self, reasons: List[str]):
        """Update reason combo with available reasons."""
        current = self.reason_combo.currentData()
        self.reason_combo.clear()
        self.reason_combo.addItem("Todos", None)
        for reason in reasons:
            display = get_reason_display(reason)
            self.reason_combo.addItem(display, reason)

        # Restore selection if possible
        if current:
            idx = self.reason_combo.findData(current)
            if idx >= 0:
                self.reason_combo.setCurrentIndex(idx)

    def get_filter(self) -> CheckpointFilter:
        """Get current filter criteria."""
        f = CheckpointFilter()

        if self.search_edit.text():
            f.search_text = self.search_edit.text()

        status = self.status_combo.currentData()
        if status:
            f.status_filter = [status]

        severity = self.severity_combo.currentData()
        if severity:
            f.severity_filter = [severity]

        reason = self.reason_combo.currentData()
        if reason:
            f.reason_filter = [reason]

        return f

    def clear_filters(self):
        """Clear all filters."""
        self.search_edit.clear()
        self.status_combo.setCurrentIndex(0)
        self.severity_combo.setCurrentIndex(0)
        self.reason_combo.setCurrentIndex(0)


class CheckpointsTable(QTableWidget):
    """Table showing checkpoint list."""

    checkpoint_selected = Signal(str)  # checkpoint_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkpoints: List[CheckpointSummary] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the table."""
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "Status", "Severidade", "Run ID", "Tipo", "Descricao", "Etapa", "Criado"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_checkpoints(self, checkpoints: List[CheckpointSummary]):
        """Set checkpoints to display."""
        self._checkpoints = checkpoints
        self.setRowCount(len(checkpoints))

        for row, cp in enumerate(checkpoints):
            # Status
            status_text, status_color = get_status_display(cp.status)
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            status_item.setData(Qt.ItemDataRole.UserRole, cp.checkpoint_id)
            self.setItem(row, 0, status_item)

            # Severity
            sev_text, sev_color = get_severity_display(cp.severity)
            sev_item = QTableWidgetItem(sev_text)
            sev_item.setForeground(QColor(sev_color))
            self.setItem(row, 1, sev_item)

            # Run ID
            self.setItem(row, 2, QTableWidgetItem(cp.run_id[:20]))

            # Type/Reason
            self.setItem(row, 3, QTableWidgetItem(cp.reason_display))

            # Description
            desc = cp.description[:50] + "..." if len(cp.description) > 50 else cp.description
            self.setItem(row, 4, QTableWidgetItem(desc))

            # Pipeline Stage
            self.setItem(row, 5, QTableWidgetItem(cp.pipeline_stage))

            # Created
            self.setItem(row, 6, QTableWidgetItem(format_datetime(cp.created_at)))

    def _on_selection_changed(self):
        """Handle selection change."""
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            item = self.item(row, 0)
            if item:
                checkpoint_id = item.data(Qt.ItemDataRole.UserRole)
                if checkpoint_id:
                    self.checkpoint_selected.emit(checkpoint_id)

    def get_selected_checkpoint_id(self) -> Optional[str]:
        """Get selected checkpoint ID."""
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            item = self.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None


class CheckpointDetailPanel(QFrame):
    """Panel showing checkpoint details and actions."""

    approve_clicked = Signal(str, str)  # run_id, note
    reject_clicked = Signal(str, str)  # run_id, note
    open_run_clicked = Signal(str)  # run_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_detail: Optional[CheckpointDetail] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the panel."""
        self.setMinimumWidth(320)
        self.setStyleSheet("""
            QFrame {
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # Title
        self.title_label = QLabel("Selecione um checkpoint")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #e6edf3;")
        layout.addWidget(self.title_label)

        # Status badges
        badges_layout = QHBoxLayout()
        self.status_badge = StatusBadge(CheckpointDecisionStatus.PENDING)
        badges_layout.addWidget(self.status_badge)
        self.severity_badge = SeverityBadge(CheckpointSeverity.INFO)
        badges_layout.addWidget(self.severity_badge)
        badges_layout.addStretch()
        layout.addLayout(badges_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)

        # Info section
        info_group = QGroupBox("Informacoes")
        info_layout = QVBoxLayout(info_group)

        self.reason_label = QLabel()
        self.reason_label.setWordWrap(True)
        info_layout.addWidget(self.reason_label)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        info_layout.addWidget(self.desc_label)

        self.stage_label = QLabel()
        info_layout.addWidget(self.stage_label)

        self.iteration_label = QLabel()
        info_layout.addWidget(self.iteration_label)

        self.created_label = QLabel()
        info_layout.addWidget(self.created_label)

        content_layout.addWidget(info_group)

        # Task section
        task_group = QGroupBox("Tarefa")
        task_layout = QVBoxLayout(task_group)
        self.task_label = QLabel()
        self.task_label.setWordWrap(True)
        task_layout.addWidget(self.task_label)
        content_layout.addWidget(task_group)

        # Risk/Recommendation section
        risk_group = QGroupBox("Risco e Recomendacao")
        risk_layout = QVBoxLayout(risk_group)

        self.risk_label = QLabel()
        self.risk_label.setWordWrap(True)
        self.risk_label.setStyleSheet("color: #f59e0b;")
        risk_layout.addWidget(self.risk_label)

        self.recommendation_label = QLabel()
        self.recommendation_label.setWordWrap(True)
        risk_layout.addWidget(self.recommendation_label)

        self.action_label = QLabel()
        self.action_label.setWordWrap(True)
        self.action_label.setStyleSheet("color: #6b7280;")
        risk_layout.addWidget(self.action_label)

        content_layout.addWidget(risk_group)

        # Command section (if applicable)
        self.command_group = QGroupBox("Comando")
        command_layout = QVBoxLayout(self.command_group)
        self.command_text = QLabel()
        self.command_text.setWordWrap(True)
        self.command_text.setStyleSheet("font-family: monospace; background: #0f1115; padding: 8px; border-radius: 4px; color: #c9d1d9;")
        command_layout.addWidget(self.command_text)
        content_layout.addWidget(self.command_group)
        self.command_group.hide()

        # Files section
        self.files_group = QGroupBox("Arquivos Afetados")
        files_layout = QVBoxLayout(self.files_group)
        self.files_label = QLabel()
        self.files_label.setWordWrap(True)
        files_layout.addWidget(self.files_label)
        content_layout.addWidget(self.files_group)
        self.files_group.hide()

        # Diff preview section
        self.diff_group = QGroupBox("Preview do Diff")
        diff_layout = QVBoxLayout(self.diff_group)
        self.diff_text = QTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setMaximumHeight(150)
        self.diff_text.setStyleSheet("font-family: monospace; font-size: 11px;")
        diff_layout.addWidget(self.diff_text)
        content_layout.addWidget(self.diff_group)
        self.diff_group.hide()

        # Resolution section (for history)
        self.resolution_group = QGroupBox("Resolucao")
        resolution_layout = QVBoxLayout(self.resolution_group)
        self.resolution_label = QLabel()
        self.resolution_label.setWordWrap(True)
        resolution_layout.addWidget(self.resolution_label)
        self.resolved_at_label = QLabel()
        resolution_layout.addWidget(self.resolved_at_label)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        resolution_layout.addWidget(self.result_label)
        content_layout.addWidget(self.resolution_group)
        self.resolution_group.hide()

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Note input
        self.note_group = QGroupBox("Observacao (opcional)")
        note_layout = QVBoxLayout(self.note_group)
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Adicione uma observacao sobre sua decisao...")
        self.note_edit.setMaximumHeight(80)
        note_layout.addWidget(self.note_edit)
        layout.addWidget(self.note_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.open_run_btn = QPushButton("Ver Run")
        self.open_run_btn.setObjectName("secondary")
        self.open_run_btn.clicked.connect(self._on_open_run)
        buttons_layout.addWidget(self.open_run_btn)

        buttons_layout.addStretch()

        self.reject_btn = QPushButton("Rejeitar")
        self.reject_btn.setObjectName("danger")
        self.reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.reject_btn.clicked.connect(self._on_reject)
        buttons_layout.addWidget(self.reject_btn)

        self.approve_btn = QPushButton("Aprovar")
        self.approve_btn.setObjectName("success")
        self.approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.approve_btn.clicked.connect(self._on_approve)
        buttons_layout.addWidget(self.approve_btn)

        layout.addLayout(buttons_layout)

        # Initially hide action controls
        self._set_actions_visible(False)

    def set_checkpoint(self, detail: Optional[CheckpointDetail]):
        """Set checkpoint to display."""
        self._current_detail = detail

        if not detail:
            self.title_label.setText("Selecione um checkpoint")
            self._set_actions_visible(False)
            return

        # Title
        self.title_label.setText(f"Checkpoint: {detail.run_id[:20]}")

        # Badges
        self.status_badge.set_status(detail.status)
        self.severity_badge.set_severity(detail.severity)

        # Info
        self.reason_label.setText(f"Tipo: {detail.reason_display}")
        self.desc_label.setText(f"Descricao: {detail.description}")
        self.stage_label.setText(f"Etapa: {detail.pipeline_stage}")
        self.iteration_label.setText(f"Iteracao: {detail.iteration}/{detail.max_iterations}")
        self.created_label.setText(f"Criado: {format_datetime(detail.created_at)}")

        # Task
        task_text = detail.task_summary or detail.full_task[:200]
        self.task_label.setText(task_text)

        # Risk/Recommendation
        self.risk_label.setText(f"Risco: {detail.estimated_risk}")
        self.recommendation_label.setText(f"Recomendacao: {detail.system_recommendation}")
        self.action_label.setText(f"Sugestao: {detail.suggested_action}")

        # Command
        if detail.command:
            self.command_text.setText(detail.command)
            self.command_group.show()
        else:
            self.command_group.hide()

        # Files
        if detail.files_affected:
            self.files_label.setText("\n".join(detail.files_affected[:10]))
            if len(detail.files_affected) > 10:
                self.files_label.setText(
                    self.files_label.text() + f"\n... e mais {len(detail.files_affected) - 10}"
                )
            self.files_group.show()
        else:
            self.files_group.hide()

        # Diff preview
        if detail.diff_preview:
            self.diff_text.setPlainText(detail.diff_preview)
            self.diff_group.show()
        else:
            self.diff_group.hide()

        # Resolution (for history)
        if detail.status != CheckpointDecisionStatus.PENDING:
            self.resolution_label.setText(f"Decisao: {detail.resolution}")
            if detail.resolution_note:
                self.resolution_label.setText(
                    self.resolution_label.text() + f"\nNota: {detail.resolution_note}"
                )
            self.resolved_at_label.setText(f"Resolvido em: {format_datetime(detail.resolved_at)}")
            if detail.run_status_after:
                self.result_label.setText(f"Status da run apos: {detail.run_status_after}")
            if detail.commit_hash:
                self.result_label.setText(
                    self.result_label.text() + f"\nCommit: {detail.commit_hash[:12]}"
                )
            self.resolution_group.show()
            self._set_actions_visible(False)
        else:
            self.resolution_group.hide()
            self._set_actions_visible(True)

    def _set_actions_visible(self, visible: bool):
        """Show/hide action controls."""
        self.note_group.setVisible(visible)
        self.approve_btn.setVisible(visible)
        self.reject_btn.setVisible(visible)

    def _on_approve(self):
        """Handle approve button click."""
        if self._current_detail:
            note = self.note_edit.toPlainText().strip()
            self.approve_clicked.emit(self._current_detail.run_id, note)

    def _on_reject(self):
        """Handle reject button click."""
        if self._current_detail:
            note = self.note_edit.toPlainText().strip()
            self.reject_clicked.emit(self._current_detail.run_id, note)

    def _on_open_run(self):
        """Handle open run button click."""
        if self._current_detail:
            self.open_run_clicked.emit(self._current_detail.run_id)

    def clear_note(self):
        """Clear the note input."""
        self.note_edit.clear()


class CheckpointsPanel(QWidget):
    """Main checkpoint center panel."""

    checkpoint_approved = Signal(str)  # run_id
    checkpoint_rejected = Signal(str)  # run_id
    open_run = Signal(str)  # run_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_path: Optional[Path] = None
        self._config = None
        self._manager: Optional[CheckpointWorkerManager] = None
        self._state = CheckpointUIState()
        self._setup_ui()

    def _setup_ui(self):
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Centro de Checkpoints")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self._on_auto_refresh_changed)
        header_layout.addWidget(self.auto_refresh_cb)

        # Refresh button
        refresh_btn = QPushButton("Atualizar")
        refresh_btn.clicked.connect(self._refresh_data)
        header_layout.addWidget(refresh_btn)

        # Export button
        export_btn = QPushButton("Exportar")
        export_btn.clicked.connect(self._on_export)
        header_layout.addWidget(export_btn)

        # Copy button
        copy_btn = QPushButton("Copiar Resumo")
        copy_btn.clicked.connect(self._on_copy_summary)
        header_layout.addWidget(copy_btn)

        layout.addLayout(header_layout)

        # Metrics bar
        self.metrics_bar = MetricsBar()
        layout.addWidget(self.metrics_bar)

        # Filter bar
        self.filter_bar = FilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        layout.addWidget(self.filter_bar)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table
        self.table = CheckpointsTable()
        self.table.checkpoint_selected.connect(self._on_checkpoint_selected)
        splitter.addWidget(self.table)

        # Detail panel
        self.detail_panel = CheckpointDetailPanel()
        self.detail_panel.approve_clicked.connect(self._on_approve)
        self.detail_panel.reject_clicked.connect(self._on_reject)
        self.detail_panel.open_run_clicked.connect(self._on_open_run)
        splitter.addWidget(self.detail_panel)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

        # Loading indicator
        self.loading_label = QLabel("Carregando...")
        self.loading_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

    def set_workspace(self, workspace_path: Path):
        """Set workspace path."""
        self._workspace_path = workspace_path
        self._init_manager()

    def set_config(self, config):
        """Set config."""
        self._config = config
        if self._manager:
            self._manager.set_config(config)

    def _init_manager(self):
        """Initialize the worker manager."""
        if not self._workspace_path:
            return

        self._manager = CheckpointWorkerManager(self._workspace_path, self._config)
        self._manager.set_callbacks(
            on_data_loaded=self._on_data_loaded,
            on_detail_loaded=self._on_detail_loaded,
            on_error=self._on_error,
            on_action_completed=self._on_action_completed,
            on_export_completed=self._on_export_completed,
        )

        # Start auto-refresh if enabled
        if self.auto_refresh_cb.isChecked():
            self._manager.start_auto_refresh(5000)

        # Initial load
        self._refresh_data()

    def _refresh_data(self):
        """Refresh checkpoint data."""
        if not self._manager:
            return

        self.loading_label.show()
        self._manager.set_filter(self.filter_bar.get_filter())
        self._manager.load_data()

    def _on_data_loaded(self, checkpoints, metrics, reasons):
        """Handle data loaded."""
        self.loading_label.hide()
        self._state.checkpoints = checkpoints
        self._state.metrics = metrics
        self._state.available_reasons = reasons

        self.metrics_bar.update_metrics(metrics)
        self.filter_bar.set_reasons(reasons)
        self.table.set_checkpoints(checkpoints)

    def _on_detail_loaded(self, detail):
        """Handle detail loaded."""
        self._state.selected_detail = detail
        self.detail_panel.set_checkpoint(detail)

    def _on_error(self, error_msg):
        """Handle error."""
        self.loading_label.hide()
        QMessageBox.warning(self, "Erro", f"Erro ao carregar dados: {error_msg}")

    def _on_action_completed(self, action, success, message):
        """Handle action completed."""
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self.detail_panel.clear_note()
            self._refresh_data()

            # Emit signals for main window
            if action == "approve" and self._state.selected_detail:
                self.checkpoint_approved.emit(self._state.selected_detail.run_id)
            elif action == "reject" and self._state.selected_detail:
                self.checkpoint_rejected.emit(self._state.selected_detail.run_id)
        else:
            QMessageBox.warning(self, "Erro", message)

    def _on_export_completed(self, format, success, result):
        """Handle export completed."""
        if success:
            QMessageBox.information(
                self, "Exportado",
                f"Checkpoints exportados para:\n{result}"
            )
        else:
            QMessageBox.warning(self, "Erro", f"Erro ao exportar: {result}")

    def _on_checkpoint_selected(self, checkpoint_id):
        """Handle checkpoint selection."""
        if not self._manager:
            return

        self._state.selected_checkpoint_id = checkpoint_id
        self._manager.load_detail(checkpoint_id)

    def _on_filter_changed(self):
        """Handle filter change."""
        self._refresh_data()

    def _on_auto_refresh_changed(self, state):
        """Handle auto-refresh toggle."""
        if not self._manager:
            return

        if state == Qt.CheckState.Checked.value:
            self._manager.start_auto_refresh(5000)
        else:
            self._manager.stop_auto_refresh()

    def _on_approve(self, run_id, note):
        """Handle approve action."""
        if not self._manager:
            return

        reply = QMessageBox.question(
            self, "Confirmar Aprovacao",
            f"Deseja aprovar o checkpoint para run {run_id}?\n\n"
            "A execucao sera retomada automaticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.approve_checkpoint(run_id, note)

    def _on_reject(self, run_id, note):
        """Handle reject action."""
        if not self._manager:
            return

        reply = QMessageBox.question(
            self, "Confirmar Rejeicao",
            f"Deseja rejeitar o checkpoint para run {run_id}?\n\n"
            "A execucao sera cancelada.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.reject_checkpoint(run_id, note)

    def _on_open_run(self, run_id):
        """Handle open run action."""
        self.open_run.emit(run_id)

    def _on_export(self):
        """Handle export button."""
        if not self._manager:
            return

        self._manager.export_data("both")

    def _on_copy_summary(self):
        """Copy summary to clipboard."""
        if not self._manager:
            return

        summary = self._manager.get_clipboard_summary()
        clipboard = QApplication.clipboard()
        clipboard.setText(summary)

        QMessageBox.information(
            self, "Copiado",
            "Resumo copiado para a area de transferencia!"
        )
