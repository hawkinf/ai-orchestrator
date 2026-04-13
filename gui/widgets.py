"""Premium UI widgets for AI Orchestrator."""

from typing import Optional, List, Callable
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    Signal,
    QSize,
    QTimer,
    Property,
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QProgressBar,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QSpacerItem,
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush


class StatusBadge(QLabel):
    """A styled status badge widget."""

    STYLES = {
        "success": ("background-color: #14532d; color: #4ade80; border: 1px solid #22c55e;", "✓"),
        "warning": ("background-color: #78350f; color: #fbbf24; border: 1px solid #f59e0b;", "⚠"),
        "error": ("background-color: #7f1d1d; color: #f87171; border: 1px solid #ef4444;", "✕"),
        "info": ("background-color: #1e3a8a; color: #60a5fa; border: 1px solid #3b82f6;", "ℹ"),
        "pending": ("background-color: #374151; color: #9ca3af; border: 1px solid #6b7280;", "○"),
        "running": ("background-color: #312e81; color: #a5b4fc; border: 1px solid #6366f1;", "◉"),
    }

    def __init__(
        self,
        text: str,
        status: str = "info",
        show_icon: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._status = status
        self._show_icon = show_icon
        self._text = text
        self._update_display()

    def _update_display(self):
        """Update badge display."""
        style_css, icon = self.STYLES.get(self._status, self.STYLES["info"])

        display_text = f"{icon} {self._text}" if self._show_icon else self._text
        self.setText(display_text)

        self.setStyleSheet(f"""
            QLabel {{
                {style_css}
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)

    def set_status(self, status: str, text: Optional[str] = None):
        """Update badge status and text."""
        self._status = status
        if text is not None:
            self._text = text
        self._update_display()


class Card(QFrame):
    """A styled card container widget."""

    clicked = Signal()

    def __init__(
        self,
        title: Optional[str] = None,
        clickable: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._clickable = clickable
        self._hovered = False

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            title_label.setObjectName("card_title")
            layout.addWidget(title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        layout.addLayout(self.content_layout)

        self._apply_style()

        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_style(self):
        """Apply card styling."""
        hover_style = "border-color: #475569;" if self._hovered else ""
        self.setStyleSheet(f"""
            #card {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                {hover_style}
            }}
            #card_title {{
                color: #f8fafc;
                background: transparent;
            }}
        """)

    def add_widget(self, widget: QWidget):
        """Add widget to card content."""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add layout to card content."""
        self.content_layout.addLayout(layout)

    def enterEvent(self, event):
        """Handle mouse enter."""
        if self._clickable:
            self._hovered = True
            self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        if self._clickable:
            self._hovered = False
            self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth animations."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._target_value = 0
        self._animation = None

        self.setTextVisible(False)
        self.setMinimum(0)
        self.setMaximum(100)

        self.setStyleSheet("""
            QProgressBar {
                background-color: #334155;
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
        """)

    def set_value_animated(self, value: int, duration_ms: int = 300):
        """Set value with animation."""
        if self._animation:
            self._animation.stop()

        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()


class LoadingSpinner(QWidget):
    """Animated loading spinner widget."""

    def __init__(self, size: int = 32, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._color = QColor("#3b82f6")

        self.setFixedSize(size, size)

    def start(self):
        """Start spinning."""
        self._timer.start(16)  # ~60fps

    def stop(self):
        """Stop spinning."""
        self._timer.stop()

    def set_color(self, color: QColor):
        """Set spinner color."""
        self._color = color
        self.update()

    def _rotate(self):
        """Rotate spinner."""
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        center = self._size // 2
        radius = (self._size - 4) // 2
        thickness = 3

        # Draw arc
        pen = QPen(self._color)
        pen.setWidth(thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawArc(rect, -self._angle * 16, 270 * 16)


class EmptyState(QWidget):
    """Empty state placeholder widget."""

    action_clicked = Signal()

    def __init__(
        self,
        icon: str = "📭",
        title: str = "No items",
        message: str = "There's nothing here yet.",
        action_text: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #f8fafc;")
        layout.addWidget(title_label)

        # Message
        message_label = QLabel(message)
        message_label.setFont(QFont("Segoe UI", 12))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(message_label)

        # Action button
        if action_text:
            layout.addSpacing(8)
            action_btn = QPushButton(action_text)
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            action_btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(action_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class StatCard(Card):
    """A card displaying a statistic value."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: Optional[str] = None,
        trend: Optional[str] = None,
        trend_positive: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)

        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #f8fafc; background: transparent;")
        self.add_widget(value_label)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12))
        title_label.setStyleSheet("color: #94a3b8; background: transparent;")
        self.add_widget(title_label)

        # Subtitle/Trend row
        if subtitle or trend:
            row = QHBoxLayout()
            row.setContentsMargins(0, 4, 0, 0)

            if subtitle:
                sub_label = QLabel(subtitle)
                sub_label.setFont(QFont("Segoe UI", 10))
                sub_label.setStyleSheet("color: #64748b; background: transparent;")
                row.addWidget(sub_label)

            if trend:
                trend_color = "#4ade80" if trend_positive else "#f87171"
                trend_label = QLabel(trend)
                trend_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                trend_label.setStyleSheet(f"color: {trend_color}; background: transparent;")
                row.addWidget(trend_label, alignment=Qt.AlignmentFlag.AlignRight)

            self.add_layout(row)


class Divider(QFrame):
    """A horizontal divider line."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setStyleSheet("background-color: #334155; max-height: 1px;")


class SectionHeader(QWidget):
    """A section header with optional action button."""

    action_clicked = Signal()

    def __init__(
        self,
        title: str,
        subtitle: Optional[str] = None,
        action_text: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Text section
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc;")
        text_layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setFont(QFont("Segoe UI", 11))
            sub_label.setStyleSheet("color: #94a3b8;")
            text_layout.addWidget(sub_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Action button
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #3b82f6;
                    border: 1px solid #3b82f6;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3b82f6;
                    color: white;
                }
            """)
            action_btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(action_btn)


class IconButton(QPushButton):
    """A button with icon and optional text."""

    def __init__(
        self,
        icon: str,
        text: str = "",
        tooltip: str = "",
        primary: bool = False,
        danger: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        display = f"{icon} {text}".strip() if text else icon
        self.setText(display)

        if tooltip:
            self.setToolTip(tooltip)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
        elif danger:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #f8fafc;
                }
            """)
