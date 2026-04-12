"""Log and report viewer panel."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSplitter, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QTabWidget, QFrame,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class LogViewer(QWidget):
    """Panel for viewing logs and reports."""

    open_folder = Signal(str)  # run_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run_id: Optional[str] = None
        self._workspace_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Logs e Relatorios")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Run selector
        header_layout.addWidget(QLabel("Run:"))
        self.run_combo = QComboBox()
        self.run_combo.setMinimumWidth(200)
        self.run_combo.currentTextChanged.connect(self._on_run_changed)
        header_layout.addWidget(self.run_combo)

        layout.addLayout(header_layout)

        # Splitter for file list and content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        file_list_layout.setContentsMargins(0, 0, 0, 0)

        file_list_label = QLabel("Arquivos")
        file_list_label.setStyleSheet("font-weight: 600;")
        file_list_layout.addWidget(file_list_label)

        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self._on_file_selected)
        file_list_layout.addWidget(self.file_list)

        splitter.addWidget(file_list_widget)

        # Content viewer
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_header = QHBoxLayout()
        self.file_label = QLabel("Selecione um arquivo")
        self.file_label.setStyleSheet("font-weight: 600;")
        content_header.addWidget(self.file_label)

        content_header.addStretch()

        copy_btn = QPushButton("Copiar")
        copy_btn.setObjectName("secondary")
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(self._copy_content)
        content_header.addWidget(copy_btn)

        export_btn = QPushButton("Exportar")
        export_btn.setObjectName("secondary")
        export_btn.setFixedWidth(80)
        export_btn.clicked.connect(self._export_content)
        content_header.addWidget(export_btn)

        content_layout.addLayout(content_header)

        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setFont(QFont("Consolas", 10))
        self.content_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e293b;
                color: #e2e8f0;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        content_layout.addWidget(self.content_edit)

        splitter.addWidget(content_widget)
        splitter.setSizes([200, 600])

        layout.addWidget(splitter)

        # Action buttons
        actions_layout = QHBoxLayout()

        open_folder_btn = QPushButton("Abrir Pasta")
        open_folder_btn.setObjectName("secondary")
        open_folder_btn.clicked.connect(self._open_folder)
        actions_layout.addWidget(open_folder_btn)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

    def set_workspace_path(self, path: Path):
        """Set workspace path for loading runs."""
        self._workspace_path = path
        self._load_runs()

    def _load_runs(self):
        """Load available runs."""
        self.run_combo.clear()
        self.run_combo.addItem("Selecione uma run...")

        if not self._workspace_path:
            return

        runs_path = self._workspace_path / "runs"
        if not runs_path.exists():
            return

        runs = sorted(runs_path.iterdir(), reverse=True)
        for run_dir in runs:
            if run_dir.is_dir():
                self.run_combo.addItem(run_dir.name)

    def _on_run_changed(self, run_id: str):
        """Handle run selection change."""
        self.file_list.clear()
        self.content_edit.clear()
        self.file_label.setText("Selecione um arquivo")

        if not run_id or run_id.startswith("Selecione"):
            self._run_id = None
            return

        self._run_id = run_id
        self._load_files()

    def _load_files(self):
        """Load files for selected run."""
        if not self._workspace_path or not self._run_id:
            return

        run_path = self._workspace_path / "runs" / self._run_id

        if not run_path.exists():
            return

        # Add files recursively
        for file_path in sorted(run_path.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(run_path)
                item = QListWidgetItem(str(rel_path))
                item.setData(Qt.ItemDataRole.UserRole, str(file_path))
                self.file_list.addItem(item)

    def _on_file_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        """Handle file selection."""
        if not current:
            return

        file_path = current.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return

        self.file_label.setText(current.text())

        try:
            path = Path(file_path)
            if path.suffix.lower() in (".json", ".txt", ".md", ".log", ".py", ".yaml", ".yml", ".patch"):
                content = path.read_text(encoding="utf-8")
                self.content_edit.setPlainText(content)
            else:
                self.content_edit.setPlainText(f"[Arquivo binario: {path.name}]")
        except Exception as e:
            self.content_edit.setPlainText(f"Erro ao ler arquivo: {e}")

    def _copy_content(self):
        """Copy content to clipboard."""
        content = self.content_edit.toPlainText()
        if content:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(content)
            QMessageBox.information(self, "Copiado", "Conteudo copiado para a area de transferencia!")

    def _export_content(self):
        """Export content to file."""
        content = self.content_edit.toPlainText()
        if not content:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Arquivo",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                Path(file_path).write_text(content, encoding="utf-8")
                QMessageBox.information(self, "Exportado", f"Arquivo salvo em: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao salvar: {e}")

    def _open_folder(self):
        """Open run folder."""
        if self._run_id:
            self.open_folder.emit(self._run_id)

    def set_run(self, run_id: str):
        """Set current run."""
        index = self.run_combo.findText(run_id)
        if index >= 0:
            self.run_combo.setCurrentIndex(index)
        else:
            self._load_runs()
            index = self.run_combo.findText(run_id)
            if index >= 0:
                self.run_combo.setCurrentIndex(index)

    def refresh(self):
        """Refresh the file list."""
        self._load_runs()
        if self._run_id:
            self.set_run(self._run_id)


class ReportViewer(QWidget):
    """Panel for viewing final reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tabs for different report formats
        self.tabs = QTabWidget()

        # Markdown view
        self.md_view = QTextEdit()
        self.md_view.setReadOnly(True)
        self.tabs.addTab(self.md_view, "Relatorio")

        # JSON view
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.json_view, "JSON")

        layout.addWidget(self.tabs)

    def set_report(self, md_content: str, json_content: str):
        """Set report content."""
        self.md_view.setPlainText(md_content)
        self.json_view.setPlainText(json_content)

    def clear(self):
        """Clear the report."""
        self.md_view.clear()
        self.json_view.clear()
