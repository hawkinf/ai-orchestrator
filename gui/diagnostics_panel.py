"""Diagnostics panel for system health checks.

Provides a visual pre-flight check for the AI Orchestrator system.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGroupBox, QTextEdit, QMessageBox,
    QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtGui import QColor

from orchestrator.diagnostics import (
    DiagnosticStatus,
    DiagnosticCheckResult,
    DiagnosticReport,
    get_check_definitions,
)
from .diagnostics_models import DiagnosticsUIState, DiagnosticCheckUIState
from .diagnostics_worker import DiagnosticsManager

logger = logging.getLogger("ai_orchestrator.diagnostics_panel")


# Status colors - updated for dark theme
STATUS_COLORS = {
    DiagnosticStatus.NOT_TESTED: "#6b7280",  # gray
    DiagnosticStatus.RUNNING: "#4f8cff",     # blue
    DiagnosticStatus.OK: "#22c55e",          # green
    DiagnosticStatus.WARNING: "#f59e0b",     # amber
    DiagnosticStatus.FAILED: "#ef4444",      # red
    DiagnosticStatus.CRITICAL: "#dc2626",    # dark red
}

STATUS_ICONS = {
    DiagnosticStatus.NOT_TESTED: "[ - ]",
    DiagnosticStatus.RUNNING: "[...]",
    DiagnosticStatus.OK: "[OK]",
    DiagnosticStatus.WARNING: "[!]",
    DiagnosticStatus.FAILED: "[X]",
    DiagnosticStatus.CRITICAL: "[!!]",
}


class CheckItemWidget(QFrame):
    """Widget for a single diagnostic check item."""

    run_check = Signal(str)  # check_key

    def __init__(self, check_state: DiagnosticCheckUIState, parent=None):
        super().__init__(parent)
        self.check_state = check_state
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setObjectName("checkItem")
        self.setStyleSheet("""
            QFrame#checkItem {
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
                padding: 8px;
            }
            QFrame#checkItem:hover {
                border-color: #3a4150;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Status badge
        self.status_badge = QLabel()
        self.status_badge.setFixedWidth(50)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet("""
            font-weight: bold;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        header_layout.addWidget(self.status_badge)

        # Title and summary
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.title_label = QLabel(self.check_state.title)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #e6edf3;")
        title_layout.addWidget(self.title_label)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        title_layout.addWidget(self.summary_label)

        header_layout.addLayout(title_layout, 1)

        # Duration
        self.duration_label = QLabel()
        self.duration_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        header_layout.addWidget(self.duration_label)

        # Run button
        self.run_btn = QPushButton("Testar")
        self.run_btn.setFixedSize(70, 28)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #1c212b;
                border: 1px solid #2a2f3a;
                border-radius: 4px;
                font-size: 11px;
                color: #c9d1d9;
            }
            QPushButton:hover {
                background-color: #252b36;
            }
            QPushButton:disabled {
                color: #6b7280;
            }
        """)
        self.run_btn.clicked.connect(lambda: self.run_check.emit(self.check_state.key))
        header_layout.addWidget(self.run_btn)

        # Expand button
        self.expand_btn = QPushButton("v")
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.setCheckable(True)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 12px;
                color: #6b7280;
            }
            QPushButton:checked {
                transform: rotate(180deg);
            }
        """)
        self.expand_btn.clicked.connect(self._toggle_details)
        header_layout.addWidget(self.expand_btn)

        layout.addLayout(header_layout)

        # Details section (collapsible)
        self.details_frame = QFrame()
        self.details_frame.setVisible(False)
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setSpacing(8)
        details_layout.setContentsMargins(0, 8, 0, 0)

        # Description
        self.description_label = QLabel(self.check_state.description)
        self.description_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.description_label.setWordWrap(True)
        details_layout.addWidget(self.description_label)

        # Details text
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f1115;
                border: 1px solid #2a2f3a;
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
                padding: 8px;
                color: #c9d1d9;
            }
        """)
        details_layout.addWidget(self.details_text)

        # Recommendation
        self.recommendation_frame = QFrame()
        self.recommendation_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2418;
                border: 1px solid #f59e0b40;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        rec_layout = QHBoxLayout(self.recommendation_frame)
        rec_layout.setContentsMargins(8, 6, 8, 6)

        rec_icon = QLabel("!")
        rec_icon.setStyleSheet("font-weight: bold; color: #f59e0b;")
        rec_layout.addWidget(rec_icon)

        self.recommendation_label = QLabel()
        self.recommendation_label.setStyleSheet("color: #fbbf24; font-size: 12px;")
        self.recommendation_label.setWordWrap(True)
        rec_layout.addWidget(self.recommendation_label, 1)

        self.recommendation_frame.setVisible(False)
        details_layout.addWidget(self.recommendation_frame)

        layout.addWidget(self.details_frame)

    def _toggle_details(self):
        """Toggle details visibility."""
        self.check_state.is_expanded = self.expand_btn.isChecked()
        self.details_frame.setVisible(self.check_state.is_expanded)
        self.expand_btn.setText("^" if self.check_state.is_expanded else "v")

    def _update_display(self):
        """Update display from state."""
        status = self.check_state.status
        color = STATUS_COLORS.get(status, "#94a3b8")
        icon = STATUS_ICONS.get(status, "[ ? ]")

        # Update badge
        self.status_badge.setText(icon)
        self.status_badge.setStyleSheet(f"""
            font-weight: bold;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background-color: {color}20;
            color: {color};
        """)

        # Update summary
        if self.check_state.summary:
            self.summary_label.setText(self.check_state.summary)
        else:
            self.summary_label.setText(self.check_state.description)

        # Update duration
        if self.check_state.duration_ms > 0:
            self.duration_label.setText(f"{self.check_state.duration_ms}ms")
        else:
            self.duration_label.setText("")

        # Update details
        if self.check_state.details:
            self.details_text.setPlainText("\n".join(self.check_state.details))
        else:
            self.details_text.setPlainText("Nenhum detalhe disponivel")

        # Update recommendation
        if self.check_state.recommendation:
            self.recommendation_label.setText(self.check_state.recommendation)
            self.recommendation_frame.setVisible(True)
        else:
            self.recommendation_frame.setVisible(False)

        # Update run button state
        self.run_btn.setEnabled(status != DiagnosticStatus.RUNNING)

        # Critical indicator
        if self.check_state.is_critical and status in (DiagnosticStatus.FAILED, DiagnosticStatus.CRITICAL):
            self.setStyleSheet("""
                QFrame#checkItem {
                    background-color: #1f1515;
                    border: 1px solid #ef444440;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#checkItem {
                    background-color: #161a22;
                    border: 1px solid #2a2f3a;
                    border-radius: 6px;
                    padding: 8px;
                }
                QFrame#checkItem:hover {
                    border-color: #3a4150;
                }
            """)

    def update_state(self, state: DiagnosticCheckUIState):
        """Update with new state."""
        self.check_state = state
        self._update_display()

    def set_running(self, running: bool):
        """Set running state."""
        if running:
            self.check_state.status = DiagnosticStatus.RUNNING
            self.check_state.summary = "Testando..."
        self._update_display()


class DiagnosticsPanel(QWidget):
    """Panel for system diagnostics."""

    # Signals
    open_config = Signal()
    open_logs = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = None
        self._paths = None
        self._project_path: Optional[Path] = None
        self._manager: Optional[DiagnosticsManager] = None
        self._state = DiagnosticsUIState.initialize()
        self._check_widgets: dict[str, CheckItemWidget] = {}
        self._last_report: Optional[DiagnosticReport] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Diagnostico do Sistema")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Status badge
        self.overall_badge = QLabel("Nao testado")
        self.overall_badge.setStyleSheet("""
            background-color: #1c212b;
            color: #6b7280;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
        """)
        header_layout.addWidget(self.overall_badge)

        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "Verifique se todos os componentes estao prontos antes de iniciar uma tarefa. "
            "Clique em 'Executar Diagnostico' para testar todos os itens."
        )
        desc.setStyleSheet("color: #6b7280; font-size: 12px; margin-bottom: 8px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self._state.checks))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2a2f3a;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4f8cff;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Scroll area for checks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self.checks_layout = QVBoxLayout(scroll_content)
        self.checks_layout.setSpacing(8)
        self.checks_layout.setContentsMargins(0, 0, 0, 0)

        # Create check widgets
        for check_state in self._state.checks:
            widget = CheckItemWidget(check_state)
            widget.run_check.connect(self._run_single_check)
            self._check_widgets[check_state.key] = widget
            self.checks_layout.addWidget(widget)

        self.checks_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        # Run all button
        self.run_all_btn = QPushButton("Executar Diagnostico Completo")
        self.run_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f8cff;
                color: white;
                font-weight: 600;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3b7ae8;
            }
            QPushButton:disabled {
                background-color: #6b7280;
            }
        """)
        self.run_all_btn.clicked.connect(self._run_all_checks)
        actions_layout.addWidget(self.run_all_btn)

        actions_layout.addStretch()

        # Export button
        self.export_btn = QPushButton("Exportar Relatorio")
        self.export_btn.setObjectName("secondary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_report)
        actions_layout.addWidget(self.export_btn)

        # Copy button
        self.copy_btn = QPushButton("Copiar Relatorio")
        self.copy_btn.setObjectName("secondary")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_report)
        actions_layout.addWidget(self.copy_btn)

        # Open logs button
        open_logs_btn = QPushButton("Abrir Logs")
        open_logs_btn.setObjectName("secondary")
        open_logs_btn.clicked.connect(self._open_logs_folder)
        actions_layout.addWidget(open_logs_btn)

        # Open config button
        open_config_btn = QPushButton("Abrir Config")
        open_config_btn.setObjectName("secondary")
        open_config_btn.clicked.connect(self.open_config.emit)
        actions_layout.addWidget(open_config_btn)

        layout.addLayout(actions_layout)

    def set_config(self, config, paths, project_path: Optional[Path] = None):
        """Set configuration for diagnostics."""
        self._config = config
        self._paths = paths
        self._project_path = project_path or (paths.project_root if paths else None)
        self._manager = DiagnosticsManager(
            config=config,
            paths=paths,
            project_path=self._project_path,
        )

    def _run_all_checks(self):
        """Run all diagnostic checks."""
        if not self._manager:
            QMessageBox.warning(
                self, "Aviso",
                "Configuracao nao carregada. Inicialize o painel primeiro."
            )
            return

        if self._manager.is_running:
            return

        # Reset state
        for check in self._state.checks:
            check.status = DiagnosticStatus.NOT_TESTED
            check.summary = ""
            check.details = []
            check.recommendation = None
            check.duration_ms = 0

        self._update_all_widgets()
        self._state.is_running = True
        self._state.overall_status = DiagnosticStatus.RUNNING
        self._update_overall_badge()

        # Show progress
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.run_all_btn.setEnabled(False)

        # Run diagnostics
        self._manager.run_all(
            on_started=self._on_diagnostics_started,
            on_check_started=self._on_check_started,
            on_check_completed=self._on_check_completed,
            on_completed=self._on_diagnostics_completed,
            on_failed=self._on_diagnostics_failed,
        )

    @Slot(str)
    def _run_single_check(self, check_key: str):
        """Run a single diagnostic check."""
        if not self._manager:
            return

        # Update widget state
        widget = self._check_widgets.get(check_key)
        if widget:
            widget.set_running(True)

        self._manager.run_single(
            check_key=check_key,
            on_started=lambda k: None,
            on_completed=self._on_check_completed,
            on_failed=lambda e: self._on_single_check_failed(check_key, e),
        )

    def _on_diagnostics_started(self):
        """Handle diagnostics started."""
        logger.info("Diagnostics started")

    @Slot(str)
    def _on_check_started(self, check_key: str):
        """Handle check started."""
        self._state.current_check = check_key
        check = self._state.get_check(check_key)
        if check:
            check.status = DiagnosticStatus.RUNNING
            check.summary = "Testando..."

        widget = self._check_widgets.get(check_key)
        if widget:
            widget.set_running(True)

    @Slot(object)
    def _on_check_completed(self, result: DiagnosticCheckResult):
        """Handle check completed."""
        check = self._state.get_check(result.key)
        if check:
            check.update_from_result(result)

        widget = self._check_widgets.get(result.key)
        if widget:
            widget.update_state(check)

        # Update progress
        completed = sum(
            1 for c in self._state.checks
            if c.status not in (DiagnosticStatus.NOT_TESTED, DiagnosticStatus.RUNNING)
        )
        self.progress_bar.setValue(completed)

    @Slot(object)
    def _on_diagnostics_completed(self, report: DiagnosticReport):
        """Handle diagnostics completed."""
        self._state.is_running = False
        self._state.update_from_report(report)
        self._last_report = report

        # Update UI
        self._update_all_widgets()
        self._update_overall_badge()

        self.progress_bar.setVisible(False)
        self.run_all_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)

        logger.info(f"Diagnostics completed: {report.overall_status.value}")

    @Slot(str)
    def _on_diagnostics_failed(self, error: str):
        """Handle diagnostics failed."""
        self._state.is_running = False
        self._state.overall_status = DiagnosticStatus.FAILED

        self.progress_bar.setVisible(False)
        self.run_all_btn.setEnabled(True)
        self._update_overall_badge()

        QMessageBox.critical(
            self, "Erro",
            f"Erro ao executar diagnostico:\n\n{error}"
        )

    def _on_single_check_failed(self, check_key: str, error: str):
        """Handle single check failed."""
        check = self._state.get_check(check_key)
        if check:
            check.status = DiagnosticStatus.FAILED
            check.summary = f"Erro: {error[:50]}"
            check.details = [f"Erro: {error}"]

        widget = self._check_widgets.get(check_key)
        if widget:
            widget.update_state(check)

    def _update_all_widgets(self):
        """Update all check widgets from state."""
        for check in self._state.checks:
            widget = self._check_widgets.get(check.key)
            if widget:
                widget.update_state(check)

    def _update_overall_badge(self):
        """Update overall status badge."""
        status = self._state.overall_status
        color = STATUS_COLORS.get(status, "#94a3b8")
        text = self._state.get_status_summary()

        self.overall_badge.setText(text)
        self.overall_badge.setStyleSheet(f"""
            background-color: {color}20;
            color: {color};
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
        """)

    def _export_report(self):
        """Export diagnostic report to files."""
        if not self._last_report or not self._paths:
            QMessageBox.warning(self, "Aviso", "Nenhum relatorio disponivel.")
            return

        try:
            paths = self._manager.export_report(
                self._last_report,
                self._paths.workspace_root,
                format="both"
            )

            msg = "Relatorio exportado:\n"
            if "json" in paths:
                msg += f"\nJSON: {paths['json']}"
            if "markdown" in paths:
                msg += f"\nMarkdown: {paths['markdown']}"

            QMessageBox.information(self, "Exportado", msg)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar:\n{e}")

    def _copy_report(self):
        """Copy report to clipboard."""
        if not self._last_report:
            return

        try:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self._last_report.to_markdown())
            QMessageBox.information(self, "Copiado", "Relatorio copiado para a area de transferencia.")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao copiar: {e}")

    def _open_logs_folder(self):
        """Open logs folder in file explorer."""
        if not self._paths:
            return

        logs_path = self._paths.workspace_root / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)

        try:
            if sys.platform == "win32":
                os.startfile(logs_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(logs_path)])
            else:
                subprocess.run(["xdg-open", str(logs_path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao abrir pasta: {e}")
