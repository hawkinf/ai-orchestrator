"""Run history and details panel."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QSplitter, QTabWidget, QTextEdit, QLineEdit, QComboBox,
    QScrollArea, QGroupBox, QProgressBar, QMessageBox, QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from .ui_models import RunListItem, RunDetailViewModel
from .styles import get_status_color, STATUS_COLORS
from .run_timeline_widget import RunTimelineWidget


class RunListPanel(QWidget):
    """Panel showing list of runs."""

    run_selected = Signal(str)  # run_id
    run_resume = Signal(str)  # run_id
    run_refresh = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runs: List[RunListItem] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with filters
        header_layout = QHBoxLayout()

        title = QLabel("Execucoes")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Filter
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Todos", "Em Andamento", "Concluidos", "Falhas", "Checkpoints"])
        self.filter_combo.setFixedWidth(140)
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        header_layout.addWidget(self.filter_combo)

        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self.search_edit)

        # Refresh button
        refresh_btn = QPushButton("Atualizar")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self.run_refresh.emit)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Run ID", "Tarefa", "Status", "Iteracao", "Data", "Acoes"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 100)

        self.table.cellClicked.connect(self._on_cell_clicked)

        layout.addWidget(self.table)

    def set_runs(self, runs: List[RunListItem]):
        """Update the runs list."""
        self._runs = runs
        self._apply_filter()

    def _apply_filter(self):
        """Apply filter and search to runs."""
        filter_text = self.filter_combo.currentText()
        search_text = self.search_edit.text().lower()

        filtered = self._runs

        # Apply status filter
        if filter_text == "Em Andamento":
            filtered = [r for r in filtered if r.status in ("planning", "executing", "reviewing", "validating")]
        elif filter_text == "Concluidos":
            filtered = [r for r in filtered if r.status == "completed"]
        elif filter_text == "Falhas":
            filtered = [r for r in filtered if r.status == "failed"]
        elif filter_text == "Checkpoints":
            filtered = [r for r in filtered if r.has_checkpoint]

        # Apply search
        if search_text:
            filtered = [r for r in filtered if search_text in r.run_id.lower() or search_text in r.task_summary.lower()]

        self._populate_table(filtered)

    def _populate_table(self, runs: List[RunListItem]):
        """Populate table with runs."""
        self.table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            # Run ID
            id_item = QTableWidgetItem(run.run_id)
            id_item.setData(Qt.ItemDataRole.UserRole, run.run_id)
            self.table.setItem(row, 0, id_item)

            # Task
            task_item = QTableWidgetItem(run.task_short)
            task_item.setToolTip(run.task_summary)
            self.table.setItem(row, 1, task_item)

            # Status
            status_item = QTableWidgetItem(run.status.upper())
            color = get_status_color(run.status)
            status_item.setForeground(QColor(color))
            self.table.setItem(row, 2, status_item)

            # Iteration
            iter_item = QTableWidgetItem(str(run.current_iteration))
            iter_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, iter_item)

            # Date
            date_str = run.created_at.strftime("%d/%m %H:%M")
            date_item = QTableWidgetItem(date_str)
            self.table.setItem(row, 4, date_item)

            # Actions - using a button
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            view_btn = QPushButton("Ver")
            view_btn.setFixedSize(40, 26)
            view_btn.setStyleSheet("font-size: 11px; padding: 4px;")
            view_btn.clicked.connect(lambda checked, r=run.run_id: self.run_selected.emit(r))
            action_layout.addWidget(view_btn)

            if run.status not in ("completed", "cancelled"):
                resume_btn = QPushButton(">>")
                resume_btn.setFixedSize(30, 26)
                resume_btn.setStyleSheet("font-size: 11px; padding: 4px;")
                resume_btn.setToolTip("Retomar")
                resume_btn.clicked.connect(lambda checked, r=run.run_id: self.run_resume.emit(r))
                action_layout.addWidget(resume_btn)

            self.table.setCellWidget(row, 5, action_widget)

    def _on_cell_clicked(self, row: int, column: int):
        """Handle cell click."""
        if column != 5:  # Not the actions column
            item = self.table.item(row, 0)
            if item:
                run_id = item.data(Qt.ItemDataRole.UserRole)
                self.run_selected.emit(run_id)


class RunDetailPanel(QWidget):
    """Panel showing run details."""

    checkpoint_approve = Signal(str, str)  # run_id, note
    checkpoint_reject = Signal(str, str)  # run_id, reason
    open_folder = Signal(str)  # run_id
    run_resume = Signal(str)  # run_id
    open_artifact = Signal(str)  # file_path

    def __init__(self, parent=None, workspace_path: Optional[Path] = None):
        super().__init__(parent)
        self._run_id: Optional[str] = None
        self._workspace_path = workspace_path
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Detalhes da Run")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #e6edf3;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: 500;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        layout.addWidget(self.progress_bar)

        # Tabs
        self.tabs = QTabWidget()

        # Timeline tab (new - first position)
        self.timeline_widget = RunTimelineWidget(workspace_path=self._workspace_path)
        self.tabs.addTab(self.timeline_widget, "Timeline")

        # Overview tab
        overview_widget = self._create_overview_tab()
        self.tabs.addTab(overview_widget, "Visao Geral")

        # Plan tab
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        self.tabs.addTab(self.plan_text, "Plano")

        # Execution tab
        self.exec_text = QTextEdit()
        self.exec_text.setReadOnly(True)
        self.tabs.addTab(self.exec_text, "Execucao")

        # Review tab
        self.review_text = QTextEdit()
        self.review_text.setReadOnly(True)
        self.tabs.addTab(self.review_text, "Review")

        # Validation tab
        self.validation_text = QTextEdit()
        self.validation_text.setReadOnly(True)
        self.tabs.addTab(self.validation_text, "Validacao")

        # Git tab
        self.git_text = QTextEdit()
        self.git_text.setReadOnly(True)
        self.tabs.addTab(self.git_text, "Git")

        # Artifacts tab
        artifacts_widget = self._create_artifacts_tab()
        self.tabs.addTab(artifacts_widget, "Artefatos")

        layout.addWidget(self.tabs)

        # Action buttons
        actions_layout = QHBoxLayout()

        self.open_folder_btn = QPushButton("Abrir Pasta")
        self.open_folder_btn.setObjectName("secondary")
        self.open_folder_btn.clicked.connect(self._open_folder)
        actions_layout.addWidget(self.open_folder_btn)

        self.resume_btn = QPushButton("Retomar")
        self.resume_btn.clicked.connect(self._resume_run)
        actions_layout.addWidget(self.resume_btn)

        actions_layout.addStretch()

        # Checkpoint buttons (hidden by default)
        self.approve_btn = QPushButton("Aprovar Checkpoint")
        self.approve_btn.setObjectName("success")
        self.approve_btn.clicked.connect(self._approve_checkpoint)
        self.approve_btn.setVisible(False)
        actions_layout.addWidget(self.approve_btn)

        self.reject_btn = QPushButton("Rejeitar")
        self.reject_btn.setObjectName("danger")
        self.reject_btn.clicked.connect(self._reject_checkpoint)
        self.reject_btn.setVisible(False)
        actions_layout.addWidget(self.reject_btn)

        layout.addLayout(actions_layout)

    def _create_overview_tab(self) -> QWidget:
        """Create overview tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Task description
        self.task_group = QGroupBox("Tarefa")
        task_layout = QVBoxLayout(self.task_group)
        self.task_label = QLabel()
        self.task_label.setWordWrap(True)
        self.task_label.setStyleSheet("color: #c9d1d9;")
        task_layout.addWidget(self.task_label)
        content_layout.addWidget(self.task_group)

        # Status info
        self.status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(self.status_group)
        self.status_info_label = QLabel()
        self.status_info_label.setWordWrap(True)
        status_layout.addWidget(self.status_info_label)
        content_layout.addWidget(self.status_group)

        # Checkpoint info (hidden by default)
        self.checkpoint_group = QGroupBox("Checkpoint Pendente")
        self.checkpoint_group.setStyleSheet("""
            QGroupBox {
                background-color: #2a2418;
                border-color: #f59e0b;
            }
        """)
        checkpoint_layout = QVBoxLayout(self.checkpoint_group)
        self.checkpoint_label = QLabel()
        self.checkpoint_label.setWordWrap(True)
        checkpoint_layout.addWidget(self.checkpoint_label)
        self.checkpoint_group.setVisible(False)
        content_layout.addWidget(self.checkpoint_group)

        # Files changed
        self.files_group = QGroupBox("Arquivos Alterados")
        files_layout = QVBoxLayout(self.files_group)
        self.files_label = QLabel()
        self.files_label.setWordWrap(True)
        files_layout.addWidget(self.files_label)
        content_layout.addWidget(self.files_group)

        # Risks/Pending
        self.risks_group = QGroupBox("Riscos e Pendencias")
        risks_layout = QVBoxLayout(self.risks_group)
        self.risks_label = QLabel()
        self.risks_label.setWordWrap(True)
        risks_layout.addWidget(self.risks_label)
        content_layout.addWidget(self.risks_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_artifacts_tab(self) -> QWidget:
        """Create artifacts tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Arquivos gerados durante a execucao")
        header_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        refresh_btn = QPushButton("Atualizar")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._refresh_artifacts)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Artifacts list
        self.artifacts_list = QListWidget()
        self.artifacts_list.setAlternatingRowColors(True)
        self.artifacts_list.itemDoubleClicked.connect(self._open_artifact_item)
        layout.addWidget(self.artifacts_list)

        # Open selected button
        open_layout = QHBoxLayout()
        open_layout.addStretch()

        open_btn = QPushButton("Abrir Selecionado")
        open_btn.clicked.connect(self._open_selected_artifact)
        open_layout.addWidget(open_btn)

        layout.addLayout(open_layout)

        return widget

    def _refresh_artifacts(self):
        """Refresh the artifacts list."""
        self.artifacts_list.clear()

        if not self._run_id or not self._workspace_path:
            return

        run_dir = self._workspace_path / "runs" / self._run_id
        if not run_dir.exists():
            return

        # Find all files in run directory
        for file_path in sorted(run_dir.rglob("*")):
            if file_path.is_file():
                relative_path = file_path.relative_to(run_dir)
                item = QListWidgetItem(str(relative_path))
                item.setData(Qt.ItemDataRole.UserRole, str(file_path))

                # Add icon based on extension
                ext = file_path.suffix.lower()
                if ext == ".json":
                    item.setToolTip("Arquivo JSON - dados estruturados")
                elif ext == ".md":
                    item.setToolTip("Arquivo Markdown - relatorio")
                elif ext == ".log":
                    item.setToolTip("Arquivo de log")
                elif ext == ".txt":
                    item.setToolTip("Arquivo de texto")
                elif ext == ".patch":
                    item.setToolTip("Arquivo de diff/patch")
                else:
                    item.setToolTip(f"Arquivo {ext}")

                self.artifacts_list.addItem(item)

    def _open_artifact_item(self, item: QListWidgetItem):
        """Open artifact when double-clicked."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self._open_file(file_path)

    def _open_selected_artifact(self):
        """Open currently selected artifact."""
        current = self.artifacts_list.currentItem()
        if current:
            self._open_artifact_item(current)

    def _open_file(self, file_path: str):
        """Open a file with the default application."""
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, "Erro", f"Arquivo nao encontrado:\n{file_path}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao abrir arquivo:\n{e}")

    def set_workspace_path(self, workspace_path: Path):
        """Set the workspace path for artifact discovery."""
        self._workspace_path = workspace_path
        self.timeline_widget.set_workspace(workspace_path)

    def set_run(self, run: RunDetailViewModel):
        """Update display with run details."""
        self._run_id = run.run_id

        # Load timeline
        if self._workspace_path:
            self.timeline_widget.set_workspace(self._workspace_path)
            self.timeline_widget.load_timeline(run.run_id)

        # Header
        self.title_label.setText(f"Run: {run.run_id}")
        color = get_status_color(run.status)
        self.status_label.setText(run.status.upper())
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

        # Overview tab
        self.task_label.setText(run.task_description)

        status_info = (
            f"Status: {run.status}\n"
            f"Iteracao: {run.current_iteration}/{run.max_iterations}\n"
            f"Perfil: {run.profile}\n"
            f"Criado: {run.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        if run.completed_at:
            status_info += f"\nConcluido: {run.completed_at.strftime('%d/%m/%Y %H:%M:%S')}"
        if run.commit_hash:
            status_info += f"\nCommit: {run.commit_hash}"
        self.status_info_label.setText(status_info)

        # Checkpoint
        self.checkpoint_group.setVisible(run.checkpoint_pending)
        self.approve_btn.setVisible(run.checkpoint_pending)
        self.reject_btn.setVisible(run.checkpoint_pending)
        if run.checkpoint_pending:
            self.checkpoint_label.setText(
                f"Motivo: {run.checkpoint_reason or 'Nao especificado'}\n"
                f"Descricao: {run.checkpoint_description or ''}"
            )

        # Files
        if run.files_changed:
            self.files_label.setText("\n".join(f"- {f}" for f in run.files_changed))
        else:
            self.files_label.setText("Nenhum arquivo alterado")

        # Risks
        risks_text = ""
        if run.risks:
            risks_text += "Riscos:\n" + "\n".join(f"- {r}" for r in run.risks)
        if run.pending_items:
            if risks_text:
                risks_text += "\n\n"
            risks_text += "Pendencias:\n" + "\n".join(f"- {p}" for p in run.pending_items)
        if run.error_message:
            if risks_text:
                risks_text += "\n\n"
            risks_text += f"Erro: {run.error_message}"
        self.risks_label.setText(risks_text or "Nenhum risco ou pendencia identificado")

        # Plan tab
        plan_text = ""
        if run.plan_objective:
            plan_text += f"Objetivo:\n{run.plan_objective}\n\n"
        if run.plan_scope:
            plan_text += f"Escopo:\n{run.plan_scope}\n\n"
        if run.plan_steps:
            plan_text += "Passos:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(run.plan_steps))
        self.plan_text.setPlainText(plan_text or "Plano nao disponivel")

        # Execution tab
        exec_text = ""
        if run.execution_summary:
            exec_text += f"Resumo:\n{run.execution_summary}\n\n"
        if run.commands_run:
            exec_text += "Comandos executados:\n" + "\n".join(f"- {c}" for c in run.commands_run)
        self.exec_text.setPlainText(exec_text or "Execucao nao disponivel")

        # Review tab
        review_text = ""
        if run.review_status:
            review_text += f"Status: {run.review_status}\n"
            review_text += f"Aprovado: {'Sim' if run.review_approved else 'Nao'}\n\n"
        if run.review_findings:
            review_text += f"Analise:\n{run.review_findings}"
        self.review_text.setPlainText(review_text or "Review nao disponivel")

        # Validation tab
        val_text = ""
        if run.validation_results:
            val_text += f"Resultado: {'Passou' if run.validation_passed else 'Falhou'}\n\n"
            for v in run.validation_results:
                status = "OK" if v.get("success") else "FALHA"
                val_text += f"[{status}] {v.get('command', 'N/A')}\n"
        self.validation_text.setPlainText(val_text or "Validacao nao disponivel")

        # Git tab
        git_text = ""
        if run.git_branch:
            git_text += f"Branch: {run.git_branch}\n"
        if run.commit_hash:
            git_text += f"Commit: {run.commit_hash}\n\n"
        if run.diff_summary:
            git_text += f"Diff:\n{run.diff_summary}"
        self.git_text.setPlainText(git_text or "Informacoes Git nao disponiveis")

        # Update buttons
        self.resume_btn.setVisible(run.status not in ("completed", "cancelled"))

        # Refresh artifacts
        self._refresh_artifacts()

    def set_loading(self, loading: bool):
        """Show/hide loading indicator."""
        self.progress_bar.setVisible(loading)

    def clear(self):
        """Clear the panel."""
        self._run_id = None
        self.title_label.setText("Detalhes da Run")
        self.status_label.setText("")
        self.task_label.setText("")
        self.status_info_label.setText("")
        self.files_label.setText("")
        self.risks_label.setText("")
        self.plan_text.clear()
        self.exec_text.clear()
        self.review_text.clear()
        self.validation_text.clear()
        self.git_text.clear()
        self.artifacts_list.clear()
        self.checkpoint_group.setVisible(False)
        self.approve_btn.setVisible(False)
        self.reject_btn.setVisible(False)
        self.timeline_widget.clear_timeline()

    def _open_folder(self):
        """Open run folder."""
        if self._run_id:
            self.open_folder.emit(self._run_id)

    def _resume_run(self):
        """Resume the run."""
        if self._run_id:
            self.run_resume.emit(self._run_id)

    def _approve_checkpoint(self):
        """Approve checkpoint."""
        if self._run_id:
            # Could show a dialog for note
            self.checkpoint_approve.emit(self._run_id, "")

    def _reject_checkpoint(self):
        """Reject checkpoint."""
        if self._run_id:
            # Could show a dialog for reason
            self.checkpoint_reject.emit(self._run_id, "")


class RunPanel(QWidget):
    """Combined panel with list and detail."""

    # Forward signals
    checkpoint_approve = Signal(str, str)
    checkpoint_reject = Signal(str, str)
    open_folder = Signal(str)
    run_resume = Signal(str)
    run_refresh = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        # Splitter for list and detail
        splitter = QSplitter(Qt.Orientation.Vertical)

        # List panel
        self.list_panel = RunListPanel()
        self.list_panel.run_selected.connect(self._on_run_selected)
        self.list_panel.run_resume.connect(self.run_resume.emit)
        self.list_panel.run_refresh.connect(self.run_refresh.emit)
        splitter.addWidget(self.list_panel)

        # Detail panel
        self.detail_panel = RunDetailPanel()
        self.detail_panel.checkpoint_approve.connect(self.checkpoint_approve.emit)
        self.detail_panel.checkpoint_reject.connect(self.checkpoint_reject.emit)
        self.detail_panel.open_folder.connect(self.open_folder.emit)
        self.detail_panel.run_resume.connect(self.run_resume.emit)
        splitter.addWidget(self.detail_panel)

        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

    def _on_run_selected(self, run_id: str):
        """Handle run selection."""
        # This will be connected to load run details
        pass

    def set_runs(self, runs: List[RunListItem]):
        """Update runs list."""
        self.list_panel.set_runs(runs)

    def set_run_detail(self, run: RunDetailViewModel):
        """Update run detail."""
        self.detail_panel.set_run(run)

    def clear_detail(self):
        """Clear detail panel."""
        self.detail_panel.clear()

    def get_list_panel(self) -> RunListPanel:
        """Get list panel for external connections."""
        return self.list_panel

    def get_detail_panel(self) -> RunDetailPanel:
        """Get detail panel for external connections."""
        return self.detail_panel

    def set_workspace_path(self, workspace_path: Path):
        """Set workspace path for artifact discovery."""
        self._workspace_path = workspace_path
        self.detail_panel.set_workspace_path(workspace_path)
