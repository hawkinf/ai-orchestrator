"""Dialog for collecting product feedback from end users."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from orchestrator.feedback_store import FeedbackEntry, FeedbackStore
from orchestrator.observability import get_observability
from orchestrator.paths import OrchestratorPaths
from orchestrator.version import VersionInfo


class FeedbackDialog(QDialog):
    """Simple feedback capture dialog with optional diagnostic attachment."""

    def __init__(
        self,
        *,
        paths: OrchestratorPaths,
        version_info: VersionInfo,
        config_path: Optional[Path] = None,
        preferences_path: Optional[Path] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.paths = paths
        self.version_info = version_info
        self.config_path = config_path
        self.preferences_path = preferences_path
        self.store = FeedbackStore(paths, version_info)
        self._last_feedback_path: Optional[Path] = None
        self._last_feedback_json = ""
        self._last_diagnostic_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Enviar feedback")
        self.setModal(True)
        self.resize(580, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 18, 22, 18)

        title = QLabel("Enviar feedback")
        title.setProperty("heading", True)
        layout.addWidget(title)

        subtitle = QLabel("Conte em poucas palavras o que aconteceu ou o que você gostaria de ver na aplicação.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("subheading", True)
        layout.addWidget(subtitle)

        type_label = QLabel("Tipo")
        layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["bug", "sugestão", "dúvida"])
        layout.addWidget(self.type_combo)

        description_label = QLabel("Descrição")
        layout.addWidget(description_label)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Descreva o problema, a sugestão ou a dúvida do jeito mais simples possível.")
        self.description_edit.setMinimumHeight(180)
        layout.addWidget(self.description_edit, 1)

        self.attach_diagnostic_checkbox = QCheckBox("Anexar diagnóstico automaticamente")
        self.attach_diagnostic_checkbox.setChecked(True)
        layout.addWidget(self.attach_diagnostic_checkbox)

        self.status_label = QLabel("O feedback será salvo localmente para envio ou revisão futura.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.save_button = QPushButton("Salvar feedback")
        self.save_button.clicked.connect(self._save_feedback)
        actions.addWidget(self.save_button)

        self.copy_button = QPushButton("Copiar conteúdo")
        self.copy_button.setProperty("secondary", True)
        self.copy_button.clicked.connect(self._copy_feedback)
        actions.addWidget(self.copy_button)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setProperty("secondary", True)
        self.open_folder_button.clicked.connect(self._open_feedback_folder)
        actions.addWidget(self.open_folder_button)

        actions.addStretch()

        self.close_button = QPushButton("Fechar")
        self.close_button.setProperty("secondary", True)
        self.close_button.clicked.connect(self.close)
        actions.addWidget(self.close_button)

        layout.addLayout(actions)

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _build_feedback_entry(self) -> tuple[FeedbackEntry, str, Optional[Path]]:
        timestamp = self._timestamp()
        diagnostic_path = None
        if self.attach_diagnostic_checkbox.isChecked():
            diagnostic_path = get_observability().create_diagnostic_package(
                config_path=self.config_path,
                preferences_path=self.preferences_path,
                version_path=Path(__file__).resolve().parent.parent / "version.json",
                metadata={"origin": "feedback_dialog", "feedback_type": self.type_combo.currentText()},
            )

        entry = self.store.build_feedback(
            feedback_type=self.type_combo.currentText(),
            description=self.description_edit.toPlainText(),
            timestamp=timestamp,
            diagnostic_path=diagnostic_path,
        )
        return entry, timestamp, diagnostic_path

    def _render_feedback_json(self, entry: FeedbackEntry) -> str:
        return json.dumps(entry.to_dict(), indent=2, ensure_ascii=False)

    def _save_feedback(self):
        try:
            entry, _, diagnostic_path = self._build_feedback_entry()
            output_path = self.store.save_feedback(entry)
            self._last_feedback_path = output_path
            self._last_feedback_json = self._render_feedback_json(entry)
            self._last_diagnostic_path = diagnostic_path
            self.status_label.setText(
                "Feedback salvo com sucesso. Você pode copiar o conteúdo ou abrir a pasta para compartilhar depois."
            )
            get_observability().record_user_action(
                "save_feedback",
                {
                    "feedback_type": entry.feedback_type,
                    "feedback_path": str(output_path),
                    "diagnostic_attached": bool(diagnostic_path),
                },
            )
            QMessageBox.information(self, "Feedback salvo", f"Arquivo salvo em:\n\n{output_path}")
        except ValueError as exc:
            QMessageBox.warning(self, "Feedback incompleto", str(exc))
        except Exception as exc:
            get_observability().record_error(
                error_type=type(exc).__name__,
                message=str(exc),
                context={"action": "save_feedback"},
                exception=exc,
            )
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar o feedback.\n\n{exc}")

    def _copy_feedback(self):
        try:
            if not self._last_feedback_json:
                entry, _, diagnostic_path = self._build_feedback_entry()
                self._last_feedback_json = self._render_feedback_json(entry)
                self._last_diagnostic_path = diagnostic_path
            QApplication.clipboard().setText(self._last_feedback_json)
            self.status_label.setText("Conteúdo copiado. Você pode colar esse feedback onde precisar.")
            get_observability().record_user_action(
                "copy_feedback",
                {"has_saved_file": bool(self._last_feedback_path), "diagnostic_attached": bool(self._last_diagnostic_path)},
            )
            QMessageBox.information(self, "Conteúdo copiado", "O feedback foi copiado para a área de transferência.")
        except ValueError as exc:
            QMessageBox.warning(self, "Feedback incompleto", str(exc))
        except Exception as exc:
            get_observability().record_error(
                error_type=type(exc).__name__,
                message=str(exc),
                context={"action": "copy_feedback"},
                exception=exc,
            )
            QMessageBox.critical(self, "Erro", f"Não foi possível copiar o feedback.\n\n{exc}")

    def _open_feedback_folder(self):
        folder = self.paths.feedback_dir
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            get_observability().record_user_action("open_feedback_folder", {"path": str(folder)})
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir a pasta.\n\n{exc}")