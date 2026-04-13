"""Dashboard panel for runs overview.

Provides consolidated view of all runs with metrics, filters, and quick actions.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QGroupBox,
    QMessageBox, QApplication, QCheckBox, QSpinBox,
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor, QClipboard

from .dashboard_models import (
    RunStatus, RunSummary, RunMetrics, RunFilter,
    DashboardUIState, MetricCard, get_status_display,
    format_duration, format_datetime,
)
from .dashboard_worker import DashboardManager

logger = logging.getLogger("ai_orchestrator.dashboard_panel")


class MetricCardWidget(QFrame):
    """Widget displaying a single metric card."""

    def __init__(self, label: str, value: int, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metric_card")
        self._setup_ui(label, value, color)

    def _setup_ui(self, label: str, value: int, color: str):
        """Setup the UI."""
        self.setStyleSheet(f"""
            QFrame#metric_card {{
                background-color: #1e293b;
                border-radius: 8px;
                padding: 12px;
                min-width: 100px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # Value
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {color};
        """)
        layout.addWidget(self.value_label)

        # Label
        self.label_label = QLabel(label)
        self.label_label.setStyleSheet("""
            font-size: 12px;
            color: #94a3b8;
        """)
        layout.addWidget(self.label_label)

    def update_value(self, value: int):
        """Update the displayed value."""
        self.value_label.setText(str(value))


class MetricsBar(QFrame):
    """Bar displaying all metric cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create cards
        card_configs = [
            ("total", "Total", 0, "#3b82f6"),
            ("running", "Em Execucao", 0, "#f59e0b"),
            ("completed", "Concluidas", 0, "#22c55e"),
            ("failed", "Falhas", 0, "#ef4444"),
            ("checkpoint", "Checkpoint", 0, "#a855f7"),
            ("blocked", "Bloqueadas", 0, "#6b7280"),
        ]

        for key, label, value, color in card_configs:
            card = MetricCardWidget(label, value, color)
            self._cards[key] = card
            layout.addWidget(card)

        layout.addStretch()

    def update_metrics(self, metrics: RunMetrics):
        """Update all metric cards."""
        if "total" in self._cards:
            self._cards["total"].update_value(metrics.total_runs)
        if "running" in self._cards:
            self._cards["running"].update_value(metrics.running_runs)
        if "completed" in self._cards:
            self._cards["completed"].update_value(metrics.completed_runs)
        if "failed" in self._cards:
            self._cards["failed"].update_value(metrics.failed_runs)
        if "checkpoint" in self._cards:
            self._cards["checkpoint"].update_value(metrics.checkpoint_runs)
        if "blocked" in self._cards:
            self._cards["blocked"].update_value(metrics.blocked_runs)


class FilterBar(QFrame):
    """Bar with filter controls."""

    filter_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 8, 0, 8)

        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por run_id ou tarefa...")
        self.search_edit.setFixedWidth(250)
        self.search_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.search_edit)

        # Status filter
        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos", None)
        self.status_combo.addItem("Em Execucao", RunStatus.RUNNING)
        self.status_combo.addItem("Concluidas", RunStatus.COMPLETED)
        self.status_combo.addItem("Falhas", RunStatus.FAILED)
        self.status_combo.addItem("Checkpoint", RunStatus.CHECKPOINT)
        self.status_combo.addItem("Bloqueadas", RunStatus.BLOCKED)
        self.status_combo.setFixedWidth(140)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.status_combo)

        # Profile filter
        layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Todos", None)
        self.profile_combo.setFixedWidth(120)
        self.profile_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.profile_combo)

        # Checkpoint filter
        self.checkpoint_cb = QCheckBox("Com Checkpoint")
        self.checkpoint_cb.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.checkpoint_cb)

        # Error filter
        self.error_cb = QCheckBox("Com Erro")
        self.error_cb.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.error_cb)

        layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.setFixedWidth(100)
        layout.addWidget(self.refresh_btn)

    def _on_filter_changed(self):
        """Handle filter change."""
        self.filter_changed.emit()

    def get_filter(self) -> RunFilter:
        """Get current filter settings."""
        f = RunFilter()

        # Search text
        f.search_text = self.search_edit.text().strip()

        # Status
        status = self.status_combo.currentData()
        if status:
            f.status_filter = [status]

        # Profile
        profile = self.profile_combo.currentData()
        if profile:
            f.profile_filter = profile

        # Checkpoint
        if self.checkpoint_cb.isChecked():
            f.has_checkpoint = True

        # Error
        if self.error_cb.isChecked():
            f.has_error = True

        return f

    def set_profiles(self, profiles: List[str]):
        """Set available profiles."""
        current = self.profile_combo.currentData()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Todos", None)
        for profile in profiles:
            self.profile_combo.addItem(profile, profile)
        # Restore selection
        for i in range(self.profile_combo.count()):
            if self.profile_combo.itemData(i) == current:
                self.profile_combo.setCurrentIndex(i)
                break
        self.profile_combo.blockSignals(False)

    def clear_filters(self):
        """Clear all filters."""
        self.search_edit.clear()
        self.status_combo.setCurrentIndex(0)
        self.profile_combo.setCurrentIndex(0)
        self.checkpoint_cb.setChecked(False)
        self.error_cb.setChecked(False)


class RunsTable(QTableWidget):
    """Table showing all runs."""

    run_selected = Signal(str)  # run_id
    run_action = Signal(str, str)  # run_id, action

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the table."""
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            "Run ID", "Status", "Tarefa", "Etapa", "Iter",
            "Duracao", "Profile", "Criado"
        ])

        # Styling
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        # Column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(0, 140)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 50)
        self.setColumnWidth(5, 80)
        self.setColumnWidth(6, 80)
        self.setColumnWidth(7, 100)

        # Connect selection
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Handle selection change."""
        items = self.selectedItems()
        if items:
            row = items[0].row()
            run_id = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if run_id:
                self.run_selected.emit(run_id)

    def set_runs(self, runs: List[RunSummary]):
        """Update table with runs."""
        self.setRowCount(0)
        self.setRowCount(len(runs))

        for row, run in enumerate(runs):
            # Run ID
            id_item = QTableWidgetItem(run.run_id[:16])
            id_item.setData(Qt.ItemDataRole.UserRole, run.run_id)
            if run.is_corrupted:
                id_item.setForeground(QColor("#ef4444"))
                id_item.setToolTip(f"Corrompido: {run.corruption_reason}")
            self.setItem(row, 0, id_item)

            # Status
            status_text, status_color = get_status_display(run.status)
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.setItem(row, 1, status_item)

            # Task
            task_item = QTableWidgetItem(run.task_summary)
            task_item.setToolTip(run.full_task)
            self.setItem(row, 2, task_item)

            # Stage
            stage_item = QTableWidgetItem(run.current_stage)
            self.setItem(row, 3, stage_item)

            # Iteration
            iter_text = f"{run.iteration}/{run.max_iterations}"
            iter_item = QTableWidgetItem(iter_text)
            self.setItem(row, 4, iter_item)

            # Duration
            duration_item = QTableWidgetItem(format_duration(run.duration_seconds))
            self.setItem(row, 5, duration_item)

            # Profile
            profile_item = QTableWidgetItem(run.project_type)
            self.setItem(row, 6, profile_item)

            # Created
            created_item = QTableWidgetItem(format_datetime(run.created_at))
            self.setItem(row, 7, created_item)

    def get_selected_run_id(self) -> Optional[str]:
        """Get currently selected run ID."""
        items = self.selectedItems()
        if items:
            row = items[0].row()
            return self.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return None


class RunDetailPreview(QFrame):
    """Panel showing selected run details."""

    open_folder = Signal(str)  # run_id
    open_report = Signal(str)  # run_id
    open_diff = Signal(str)  # run_id
    resume_run = Signal(str)  # run_id
    open_diagnostics = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run: Optional[RunSummary] = None
        self._workspace_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        self.setObjectName("preview_panel")
        self.setStyleSheet("""
            QFrame#preview_panel {
                background-color: #1e293b;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Selecione uma run")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #f8fafc;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.status_badge = QLabel("")
        self.status_badge.setStyleSheet("""
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
        """)
        header_layout.addWidget(self.status_badge)
        layout.addLayout(header_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        # Info rows
        self.task_label = self._create_info_row(content_layout, "Tarefa:")
        self.stage_label = self._create_info_row(content_layout, "Etapa:")
        self.iteration_label = self._create_info_row(content_layout, "Iteracao:")
        self.duration_label = self._create_info_row(content_layout, "Duracao:")
        self.created_label = self._create_info_row(content_layout, "Criado:")

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #334155;")
        content_layout.addWidget(sep)

        # Plan objective
        self.plan_label = self._create_info_row(content_layout, "Objetivo:")

        # Execution summary
        self.exec_label = self._create_info_row(content_layout, "Execucao:")

        # Review status
        self.review_label = self._create_info_row(content_layout, "Review:")

        # Commit
        self.commit_label = self._create_info_row(content_layout, "Commit:")

        # Error
        self.error_label = self._create_info_row(content_layout, "Erro:")

        # Checkpoint
        self.checkpoint_label = self._create_info_row(content_layout, "Checkpoint:")

        # Risks
        self.risks_label = self._create_info_row(content_layout, "Riscos:")

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Actions
        actions_layout = QHBoxLayout()

        self.resume_btn = QPushButton("Retomar")
        self.resume_btn.setObjectName("primary")
        self.resume_btn.clicked.connect(self._on_resume)
        self.resume_btn.setVisible(False)
        actions_layout.addWidget(self.resume_btn)

        self.folder_btn = QPushButton("Pasta")
        self.folder_btn.setObjectName("secondary")
        self.folder_btn.clicked.connect(self._on_open_folder)
        actions_layout.addWidget(self.folder_btn)

        self.report_btn = QPushButton("Relatorio")
        self.report_btn.setObjectName("secondary")
        self.report_btn.clicked.connect(self._on_open_report)
        actions_layout.addWidget(self.report_btn)

        self.diff_btn = QPushButton("Diff")
        self.diff_btn.setObjectName("secondary")
        self.diff_btn.clicked.connect(self._on_open_diff)
        actions_layout.addWidget(self.diff_btn)

        self.diag_btn = QPushButton("Diagnostico")
        self.diag_btn.setObjectName("secondary")
        self.diag_btn.clicked.connect(lambda: self.open_diagnostics.emit())
        actions_layout.addWidget(self.diag_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def _create_info_row(self, layout: QVBoxLayout, label: str) -> QLabel:
        """Create an info row with label."""
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748b; min-width: 70px;")
        row.addWidget(lbl)

        value = QLabel("-")
        value.setStyleSheet("color: #e2e8f0;")
        value.setWordWrap(True)
        row.addWidget(value, 1)

        layout.addLayout(row)
        return value

    def set_workspace(self, workspace_path: Path):
        """Set workspace path."""
        self._workspace_path = workspace_path

    def set_run(self, run: Optional[RunSummary]):
        """Update with run details."""
        self._run = run

        if not run:
            self.title_label.setText("Selecione uma run")
            self.status_badge.setText("")
            self._clear_labels()
            return

        # Title
        self.title_label.setText(f"Run: {run.run_id[:16]}")

        # Status badge
        status_text, status_color = get_status_display(run.status)
        self.status_badge.setText(status_text)
        self.status_badge.setStyleSheet(f"""
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
            background-color: {status_color};
            color: white;
        """)

        # Info
        self.task_label.setText(run.full_task[:200] if run.full_task else "-")
        self.stage_label.setText(run.current_stage or "-")
        self.iteration_label.setText(f"{run.iteration}/{run.max_iterations}")
        self.duration_label.setText(format_duration(run.duration_seconds))
        self.created_label.setText(format_datetime(run.created_at))

        self.plan_label.setText(run.plan_objective[:150] if run.plan_objective else "-")
        self.exec_label.setText(run.execution_summary[:150] if run.execution_summary else "-")
        self.review_label.setText(run.review_status or "-")
        self.commit_label.setText(run.commit_hash[:12] if run.commit_hash else "-")

        # Error
        if run.last_error_summary:
            self.error_label.setText(run.last_error_summary[:100])
            self.error_label.setStyleSheet("color: #ef4444;")
        else:
            self.error_label.setText("-")
            self.error_label.setStyleSheet("color: #e2e8f0;")

        # Checkpoint
        if run.has_checkpoint:
            self.checkpoint_label.setText(run.checkpoint_reason or "Pendente")
            self.checkpoint_label.setStyleSheet("color: #a855f7;")
        else:
            self.checkpoint_label.setText("-")
            self.checkpoint_label.setStyleSheet("color: #e2e8f0;")

        # Risks
        if run.risks:
            self.risks_label.setText(", ".join(run.risks[:3]))
        else:
            self.risks_label.setText("-")

        # Show/hide buttons
        self.resume_btn.setVisible(run.status not in (RunStatus.COMPLETED, RunStatus.RUNNING))
        self.report_btn.setEnabled(run.has_final_report)
        self.diff_btn.setEnabled(run.has_diff)

    def _clear_labels(self):
        """Clear all info labels."""
        for lbl in [
            self.task_label, self.stage_label, self.iteration_label,
            self.duration_label, self.created_label, self.plan_label,
            self.exec_label, self.review_label, self.commit_label,
            self.error_label, self.checkpoint_label, self.risks_label
        ]:
            lbl.setText("-")
            lbl.setStyleSheet("color: #e2e8f0;")

        self.resume_btn.setVisible(False)

    def _on_resume(self):
        """Handle resume button."""
        if self._run:
            self.resume_run.emit(self._run.run_id)

    def _on_open_folder(self):
        """Handle open folder button."""
        if self._run:
            self.open_folder.emit(self._run.run_id)

    def _on_open_report(self):
        """Handle open report button."""
        if self._run:
            self.open_report.emit(self._run.run_id)

    def _on_open_diff(self):
        """Handle open diff button."""
        if self._run:
            self.open_diff.emit(self._run.run_id)


class DashboardPanel(QWidget):
    """Main dashboard panel with runs overview."""

    # Signals for external actions
    run_selected = Signal(str)  # run_id
    run_resume = Signal(str)  # run_id
    open_folder = Signal(str)  # run_id
    open_diagnostics = Signal()
    navigate_to_runs = Signal(str)  # run_id to show

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_path: Optional[Path] = None
        self._manager: Optional[DashboardManager] = None
        self._state = DashboardUIState()
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Central de Runs")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8fafc;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self._on_auto_refresh_changed)
        header_layout.addWidget(self.auto_refresh_cb)

        # Export button
        export_btn = QPushButton("Exportar")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._on_export)
        header_layout.addWidget(export_btn)

        # Copy button
        copy_btn = QPushButton("Copiar Resumo")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(self._on_copy)
        header_layout.addWidget(copy_btn)

        layout.addLayout(header_layout)

        # Metrics bar
        self.metrics_bar = MetricsBar()
        layout.addWidget(self.metrics_bar)

        # Filter bar
        self.filter_bar = FilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        self.filter_bar.refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(self.filter_bar)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Runs table
        self.runs_table = RunsTable()
        self.runs_table.run_selected.connect(self._on_run_selected)
        splitter.addWidget(self.runs_table)

        # Detail preview
        self.detail_preview = RunDetailPreview()
        self.detail_preview.open_folder.connect(self._on_open_folder)
        self.detail_preview.open_report.connect(self._on_open_report)
        self.detail_preview.open_diff.connect(self._on_open_diff)
        self.detail_preview.resume_run.connect(self._on_resume)
        self.detail_preview.open_diagnostics.connect(lambda: self.open_diagnostics.emit())
        splitter.addWidget(self.detail_preview)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter, 1)

        # Status bar
        status_layout = QHBoxLayout()

        self.status_label = QLabel("Aguardando...")
        self.status_label.setStyleSheet("color: #64748b;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.last_update_label = QLabel("")
        self.last_update_label.setStyleSheet("color: #64748b;")
        status_layout.addWidget(self.last_update_label)

        layout.addLayout(status_layout)

    def set_workspace(self, workspace_path: Path):
        """Set workspace path and initialize manager."""
        self._workspace_path = workspace_path

        # Create manager
        self._manager = DashboardManager(workspace_path)
        self.detail_preview.set_workspace(workspace_path)

        # Start auto-refresh
        if self.auto_refresh_cb.isChecked():
            self._start_auto_refresh()
        else:
            self._load_data()

    def _start_auto_refresh(self):
        """Start auto-refresh."""
        if self._manager:
            self._manager.start_auto_refresh(
                on_data=self._on_data_loaded,
                on_error=self._on_load_error,
                interval_ms=5000,
            )

    def _stop_auto_refresh(self):
        """Stop auto-refresh."""
        if self._manager:
            self._manager.stop_auto_refresh()

    def _load_data(self):
        """Load data once."""
        if self._manager:
            self._manager.set_filter(self.filter_bar.get_filter())
            self._manager.load_data(
                on_data=self._on_data_loaded,
                on_error=self._on_load_error,
            )
            self.status_label.setText("Carregando...")

    def _on_data_loaded(self, runs: List[RunSummary], metrics: RunMetrics, profiles: List[str]):
        """Handle data loaded."""
        self._state.runs = runs
        self._state.metrics = metrics
        self._state.available_profiles = profiles
        self._state.last_refresh = datetime.now()

        # Update UI
        self.metrics_bar.update_metrics(metrics)
        self.filter_bar.set_profiles(profiles)

        # Apply local filter if any
        filtered = self._state.apply_filter()
        self.runs_table.set_runs(filtered)

        # Update status
        self.status_label.setText(f"{len(runs)} runs")
        self.last_update_label.setText(
            f"Atualizado: {datetime.now().strftime('%H:%M:%S')}"
        )

        # Update selected run detail if still selected
        if self._state.selected_run_id:
            run = self._state.get_selected_run()
            self.detail_preview.set_run(run)

    def _on_load_error(self, error_msg: str):
        """Handle load error."""
        self.status_label.setText(f"Erro: {error_msg}")
        logger.error(f"Dashboard load error: {error_msg}")

    def _on_filter_changed(self):
        """Handle filter change."""
        self._manager.set_filter(self.filter_bar.get_filter())
        self._load_data()

    def _on_refresh(self):
        """Handle manual refresh."""
        self._load_data()

    def _on_auto_refresh_changed(self, state: int):
        """Handle auto-refresh toggle."""
        if state == Qt.CheckState.Checked.value:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _on_run_selected(self, run_id: str):
        """Handle run selection."""
        self._state.selected_run_id = run_id
        run = self._state.get_selected_run()
        self.detail_preview.set_run(run)
        self.run_selected.emit(run_id)

    def _on_open_folder(self, run_id: str):
        """Open run folder."""
        if not self._workspace_path:
            return

        run_path = self._workspace_path / "runs" / run_id
        if run_path.exists():
            self._open_path(run_path)
        else:
            QMessageBox.warning(self, "Aviso", f"Pasta nao encontrada:\n{run_path}")

    def _on_open_report(self, run_id: str):
        """Open final report."""
        if not self._workspace_path:
            return

        run_path = self._workspace_path / "runs" / run_id / "final"
        report_json = run_path / "final_report.json"
        report_md = run_path / "final_report.md"

        if report_md.exists():
            self._open_path(report_md)
        elif report_json.exists():
            self._open_path(report_json)
        else:
            QMessageBox.warning(self, "Aviso", "Relatorio final nao encontrado")

    def _on_open_diff(self, run_id: str):
        """Open diff file."""
        if not self._workspace_path:
            return

        run_path = self._workspace_path / "runs" / run_id / "git"
        diff_patch = run_path / "diff.patch"
        changes_diff = run_path / "changes.diff"

        if diff_patch.exists():
            self._open_path(diff_patch)
        elif changes_diff.exists():
            self._open_path(changes_diff)
        else:
            QMessageBox.warning(self, "Aviso", "Diff nao encontrado")

    def _on_resume(self, run_id: str):
        """Handle resume request."""
        self.run_resume.emit(run_id)

    def _on_export(self):
        """Handle export."""
        if not self._workspace_path or not self._manager:
            return

        output_dir = self._workspace_path / "logs"

        def on_complete(paths):
            msg = "Exportado:\n"
            for fmt, path in paths.items():
                msg += f"- {fmt}: {path.name}\n"
            QMessageBox.information(self, "Exportar", msg)

        def on_error(error):
            QMessageBox.warning(self, "Erro", f"Erro ao exportar:\n{error}")

        self._manager.export_data(
            output_dir=output_dir,
            format="both",
            on_complete=on_complete,
            on_error=on_error,
        )

    def _on_copy(self):
        """Copy summary to clipboard."""
        if not self._manager:
            return

        summary = self._manager.get_clipboard_summary()
        clipboard = QApplication.clipboard()
        clipboard.setText(summary)

        self.status_label.setText("Resumo copiado!")
        QTimer.singleShot(2000, lambda: self.status_label.setText(f"{len(self._state.runs)} runs"))

    def _open_path(self, path: Path):
        """Open a path with default application."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao abrir:\n{e}")

    def refresh(self):
        """Force refresh."""
        self._load_data()

    def stop(self):
        """Stop background operations."""
        self._stop_auto_refresh()
