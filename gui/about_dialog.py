"""About dialog for the desktop product surface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from orchestrator.version import ReleaseChannel, VersionInfo


class AboutDialog(QDialog):
    """Compact dialog with version, changelog and update preferences."""

    check_updates_requested = Signal()
    preferences_changed = Signal(bool, str, str)

    def __init__(
        self,
        version_info: VersionInfo,
        release_url: str,
        changelog_markdown: str,
        auto_check_updates: bool,
        update_channel: str,
        parent=None,
    ):
        super().__init__(parent)
        self._version_info = version_info
        self._release_url = release_url
        self._changelog_markdown = changelog_markdown
        self.setWindowTitle("Sobre o AI Orchestrator")
        self.setMinimumSize(620, 520)
        self._setup_ui(auto_check_updates, update_channel)

    def _setup_ui(self, auto_check_updates: bool, update_channel: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("aboutHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(16)

        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        hero_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        meta_layout = QVBoxLayout()
        title = QLabel(self._version_info.app_name)
        title.setProperty("heading", True)
        meta_layout.addWidget(title)

        subtitle = QLabel("Assistente desktop para orquestração local de tarefas com IA")
        subtitle.setProperty("subheading", True)
        subtitle.setWordWrap(True)
        meta_layout.addWidget(subtitle)

        self.version_label = QLabel(f"Versão atual: {self._version_info.display_label}")
        meta_layout.addWidget(self.version_label)
        meta_layout.addWidget(QLabel(f"Canal: {self._version_info.channel.value}"))
        meta_layout.addWidget(QLabel(f"Build date: {self._version_info.build_date or 'N/D'}"))

        release_link = QLabel(f'<a href="{self._release_url}">Abrir página de releases</a>')
        release_link.setOpenExternalLinks(False)
        release_link.linkActivated.connect(self._open_release_link)
        meta_layout.addWidget(release_link)

        hero_layout.addLayout(meta_layout, 1)
        layout.addWidget(hero)

        prefs_frame = QFrame()
        prefs_layout = QVBoxLayout(prefs_frame)
        prefs_layout.setContentsMargins(0, 0, 0, 0)
        prefs_layout.setSpacing(8)

        prefs_title = QLabel("Atualizações")
        prefs_title.setProperty("heading", True)
        prefs_layout.addWidget(prefs_title)

        self.auto_check_checkbox = QCheckBox("Verificar atualizações automaticamente ao iniciar")
        self.auto_check_checkbox.setChecked(auto_check_updates)
        self.auto_check_checkbox.toggled.connect(self._emit_preferences_changed)
        prefs_layout.addWidget(self.auto_check_checkbox)

        channel_row = QHBoxLayout()
        channel_row.addWidget(QLabel("Canal:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("Estável", ReleaseChannel.STABLE.value)
        self.channel_combo.addItem("Beta", ReleaseChannel.BETA.value)
        self.channel_combo.addItem("Alpha", ReleaseChannel.ALPHA.value)
        self.channel_combo.addItem("Dev", ReleaseChannel.DEV.value)
        current_index = max(self.channel_combo.findData(update_channel), 0)
        self.channel_combo.setCurrentIndex(current_index)
        self.channel_combo.currentIndexChanged.connect(self._emit_preferences_changed)
        channel_row.addWidget(self.channel_combo)
        channel_row.addStretch()

        self.check_updates_button = QPushButton("Verificar atualizações")
        self.check_updates_button.clicked.connect(self.check_updates_requested.emit)
        channel_row.addWidget(self.check_updates_button)
        prefs_layout.addLayout(channel_row)
        layout.addWidget(prefs_frame)

        changes_title = QLabel("Mudanças recentes")
        changes_title.setProperty("heading", True)
        layout.addWidget(changes_title)

        self.changelog_browser = QTextBrowser()
        self.changelog_browser.setMarkdown(self._changelog_markdown)
        self.changelog_browser.setOpenExternalLinks(True)
        layout.addWidget(self.changelog_browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _open_release_link(self):
        QDesktopServices.openUrl(QUrl(self._release_url))

    def _emit_preferences_changed(self):
        self.preferences_changed.emit(
            self.auto_check_checkbox.isChecked(),
            self.channel_combo.currentData(),
            self._release_url,
        )