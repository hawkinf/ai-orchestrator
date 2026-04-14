"""Screen overlay used by the interactive demo."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .interactive_demo import InteractiveDemoCard


class DemoOverlay(QWidget):
    """Dim the main window and highlight a target widget."""

    next_requested = Signal()
    back_requested = Signal()
    skip_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._highlight_rect = QRect()
        self._card = InteractiveDemoCard(self)
        self._card.next_requested.connect(self.next_requested.emit)
        self._card.back_requested.connect(self.back_requested.emit)
        self._card.skip_requested.connect(self.skip_requested.emit)
        self._card.close_requested.connect(self.close_requested.emit)
        self.hide()

    def sync_geometry(self):
        """Match the parent size."""
        if self.parentWidget() is None:
            return
        self.setGeometry(self.parentWidget().rect())

    def set_step(self, *, index: int, total: int, step, target_widget: Optional[QWidget]):
        self.sync_geometry()
        self._highlight_rect = self._target_rect_for(target_widget)
        self._card.set_step(index, total, step)
        self._position_card()
        self.raise_()
        self._card.raise_()
        self.show()
        self.update()

    def clear(self):
        self._highlight_rect = QRect()
        self.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_card()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(3, 7, 18, 160))

        if not self._highlight_rect.isValid():
            return

        border_rect = self._highlight_rect.adjusted(-6, -6, 6, 6)
        pen = QPen(QColor("#7dd3fc"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(border_rect, 10, 10)

    def _position_card(self):
        margin = 20
        card = self._card
        card.adjustSize()
        width = min(card.width(), max(420, self.width() // 3))
        height = min(max(card.height(), 420), self.height() - 40)
        card.resize(width, height)

        x = self.width() - width - margin
        y = margin
        if self._highlight_rect.isValid() and self._highlight_rect.right() > self.width() * 0.55:
            x = margin
        if self._highlight_rect.isValid():
            y = max(margin, min(self._highlight_rect.top(), self.height() - height - margin))
        card.move(x, y)

    def _target_rect_for(self, widget: Optional[QWidget]) -> QRect:
        if widget is None or not widget.isVisible():
            return QRect()
        top_left = widget.mapTo(self, QPoint(0, 0))
        return QRect(top_left, widget.size())
