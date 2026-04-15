"""Renewed in-app manual with search and section index."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QSplitter,
    QApplication,
)

from .help_content import HELP_SECTIONS, find_help_section


class HelpPanel(QWidget):
    """Main help panel with embedded manual and contextual navigation."""

    help_link_requested = Signal(str)
    about_requested = Signal()
    updates_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._section_map = {section.key: section for section in HELP_SECTIONS}
        self._setup_ui()
        self.set_current_section("overview")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("Manual e Ajuda")
        header.setProperty("heading", True)
        layout.addWidget(header)

        subheader = QLabel(
            "Use o índice para navegar pelo manual, pesquise por um termo específico e copie instruções quando precisar compartilhar um passo a passo."
        )
        subheader.setProperty("subheading", True)
        subheader.setWordWrap(True)
        layout.addWidget(subheader)

        actions = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por OpenAI, replay, checkpoint, Git...")
        self.search_input.textChanged.connect(self._filter_sections)
        actions.addWidget(self.search_input, 1)

        self.copy_btn = QPushButton("Copiar instruções")
        self.copy_btn.clicked.connect(self._copy_current_section)
        actions.addWidget(self.copy_btn)

        self.about_btn = QPushButton("Sobre")
        self.about_btn.clicked.connect(self.about_requested.emit)
        actions.addWidget(self.about_btn)

        self.updates_btn = QPushButton("Atualizações")
        self.updates_btn.clicked.connect(self.updates_requested.emit)
        actions.addWidget(self.updates_btn)
        layout.addLayout(actions)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        self.section_list = QListWidget()
        self.section_list.setMaximumWidth(260)
        self.section_list.currentItemChanged.connect(self._on_section_changed)
        splitter.addWidget(self.section_list)

        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.anchorClicked.connect(lambda url: self.help_link_requested.emit(url.toString()))
        splitter.addWidget(self.content_browser)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        for section in HELP_SECTIONS:
            item = QListWidgetItem(section.title)
            item.setData(Qt.ItemDataRole.UserRole, section.key)
            item.setToolTip(section.summary)
            self.section_list.addItem(item)

    def _filter_sections(self, text: str):
        query = text.strip().lower()
        first_visible = None
        for index in range(self.section_list.count()):
            item = self.section_list.item(index)
            key = item.data(Qt.ItemDataRole.UserRole)
            section = self._section_map[key]
            visible = not query or query in section.title.lower() or query in section.summary.lower() or query in section.content.lower()
            item.setHidden(not visible)
            if visible and first_visible is None:
                first_visible = item

        if first_visible and (self.section_list.currentItem() is None or self.section_list.currentItem().isHidden()):
            self.section_list.setCurrentItem(first_visible)

    def _on_section_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current is None:
            return
        self.set_current_section(current.data(Qt.ItemDataRole.UserRole))

    def set_current_section(self, key: str):
        """Display a help section by key."""
        section = find_help_section(key)
        content = (
            f"<h1>{section.title}</h1>"
            f"<p style='color:#9da7b3'>{section.summary}</p>"
            f"{section.content}"
        )
        self.content_browser.setHtml(content)
        self.content_browser.moveCursor(QTextCursor.MoveOperation.Start)

        for index in range(self.section_list.count()):
            item = self.section_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == section.key:
                self.section_list.setCurrentItem(item)
                break

    def _copy_current_section(self):
        """Copy the current section contents to the clipboard."""
        text = self.content_browser.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self.content_browser.moveCursor(QTextCursor.MoveOperation.Start)
