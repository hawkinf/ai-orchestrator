"""Update dialog and worker thread for desktop releases."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from orchestrator.updater import ReleaseInfo, UpdateResult, UpdateStatus, Updater


class UpdateTaskThread(QThread):
    """Background thread for checking or installing updates."""

    progress_changed = Signal(float, str)
    result_ready = Signal(object)

    def __init__(self, updater: Updater, mode: str, release: Optional[ReleaseInfo] = None, parent=None):
        super().__init__(parent)
        self._updater = updater
        self._mode = mode
        self._release = release

    def run(self):
        self._updater.set_progress_callback(self.progress_changed.emit)
        if self._mode == "check":
            result = self._updater.check_for_updates()
        else:
            if self._release is None:
                result = UpdateResult(
                    status=UpdateStatus.CHECK_FAILED,
                    current_version=str(self._updater.current_version),
                    error_message="Nenhuma release foi informada para atualização.",
                )
            else:
                result = self._updater.download_update(self._release)
                if result.download_path and result.status != UpdateStatus.CHECK_FAILED:
                    result = self._updater.install_update(result.download_path)
        self._updater.set_progress_callback(None)
        self.result_ready.emit(result)


class UpdateDialog(QDialog):
    """Compact update dialog with product-focused actions."""

    check_requested = Signal()
    update_requested = Signal(object)
    preferences_changed = Signal(bool)

    def __init__(self, current_version: str, release_url: str, auto_check_updates: bool, parent=None):
        super().__init__(parent)
        self.release_info: Optional[ReleaseInfo] = None
        self._release_url = release_url
        self.setWindowTitle("Atualizações")
        self.setMinimumSize(560, 420)
        self._setup_ui(current_version, auto_check_updates)

    def _setup_ui(self, current_version: str, auto_check_updates: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Atualizações do aplicativo")
        title.setProperty("heading", True)
        layout.addWidget(title)

        self.summary_label = QLabel("Verifique se há uma versão mais recente disponível.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.current_version_label = QLabel(f"Versão atual: {current_version}")
        layout.addWidget(self.current_version_label)

        self.latest_version_label = QLabel("Última versão: -")
        layout.addWidget(self.latest_version_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.changelog_browser = QTextBrowser()
        self.changelog_browser.setMarkdown("Clique em Verificar atualizações para consultar as releases.")
        self.changelog_browser.setOpenExternalLinks(True)
        layout.addWidget(self.changelog_browser, 1)

        self.auto_check_checkbox = QCheckBox("Verificar automaticamente ao iniciar")
        self.auto_check_checkbox.setChecked(auto_check_updates)
        self.auto_check_checkbox.toggled.connect(self.preferences_changed.emit)
        layout.addWidget(self.auto_check_checkbox)

        button_row = QHBoxLayout()
        self.update_button = QPushButton("Atualizar")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self._request_update)
        button_row.addWidget(self.update_button)

        self.changelog_button = QPushButton("Ver changelog")
        self.changelog_button.clicked.connect(self._open_release_page)
        button_row.addWidget(self.changelog_button)

        self.check_button = QPushButton("Verificar atualizações")
        self.check_button.clicked.connect(self.check_requested.emit)
        button_row.addWidget(self.check_button)

        self.later_button = QPushButton("Depois")
        self.later_button.clicked.connect(self.reject)
        button_row.addWidget(self.later_button)
        layout.addLayout(button_row)

    def set_checking(self):
        self.summary_label.setText("Consultando releases disponíveis...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.update_button.setEnabled(False)

    def set_progress(self, progress: float, message: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(100, int(progress * 100))))
        self.summary_label.setText(message)

    def present_result(self, result: UpdateResult):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.release_info = result.release_info
        self.latest_version_label.setText(f"Última versão: {result.latest_version or '-'}")

        if result.release_info:
            notes = result.release_info.body.strip() or "Sem changelog publicado para esta release."
            self.changelog_browser.setMarkdown(notes)

        if result.status == UpdateStatus.UPDATE_AVAILABLE and result.release_info:
            self.summary_label.setText("Uma nova versão está pronta para download.")
            self.update_button.setEnabled(True)
        elif result.status == UpdateStatus.UP_TO_DATE:
            self.summary_label.setText("Você já está na versão mais recente.")
            self.update_button.setEnabled(False)
        else:
            self.summary_label.setText(result.error_message or "Não foi possível verificar atualizações agora.")
            self.update_button.setEnabled(False)

    def present_install_result(self, result: UpdateResult) -> bool:
        self.progress_bar.setVisible(False)
        if result.status == UpdateStatus.RESTART_REQUIRED:
            QMessageBox.information(
                self,
                "Atualização pronta",
                "A atualização foi preparada. O aplicativo será reiniciado para concluir a instalação.",
            )
            return True

        QMessageBox.warning(
            self,
            "Falha na atualização",
            result.error_message or "Não foi possível aplicar a atualização.",
        )
        return False

    def _open_release_page(self):
        QDesktopServices.openUrl(QUrl(self._release_url))

    def _request_update(self):
        if self.release_info is not None:
            self.update_requested.emit(self.release_info)