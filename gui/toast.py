"""Toast notification widget for AI Orchestrator."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Callable
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    Signal,
    QPoint,
    QSize,
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QGraphicsOpacityEffect,
    QApplication,
)
from PySide6.QtGui import QFont, QColor


class ToastType(Enum):
    """Toast notification type."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ToastStyle:
    """Style configuration for toast."""

    background: str
    border: str
    text: str
    icon: str


TOAST_STYLES = {
    ToastType.INFO: ToastStyle(
        background="#1e3a8a",
        border="#3b82f6",
        text="#dbeafe",
        icon="ℹ️",
    ),
    ToastType.SUCCESS: ToastStyle(
        background="#14532d",
        border="#22c55e",
        text="#dcfce7",
        icon="✓",
    ),
    ToastType.WARNING: ToastStyle(
        background="#78350f",
        border="#f59e0b",
        text="#fef3c7",
        icon="⚠",
    ),
    ToastType.ERROR: ToastStyle(
        background="#7f1d1d",
        border="#ef4444",
        text="#fee2e2",
        icon="✕",
    ),
}


class Toast(QWidget):
    """A single toast notification widget."""

    closed = Signal()

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration_ms: int = 4000,
        closable: bool = True,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type
        self.duration_ms = duration_ms
        self.closable = closable
        self.action_text = action_text
        self.action_callback = action_callback

        self._opacity = 1.0
        self._setup_ui()
        self._apply_style()

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self._start_fade_out)

    def _setup_ui(self):
        """Setup toast UI."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Main container
        container = QWidget()
        container.setObjectName("toast_container")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon
        style = TOAST_STYLES[self.toast_type]
        icon_label = QLabel(style.icon)
        icon_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(400)
        message_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(message_label, 1)

        # Action button
        if self.action_text and self.action_callback:
            action_btn = QPushButton(self.action_text)
            action_btn.setObjectName("toast_action")
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.clicked.connect(self._on_action)
            layout.addWidget(action_btn)

        # Close button
        if self.closable:
            close_btn = QPushButton("×")
            close_btn.setObjectName("toast_close")
            close_btn.setFixedSize(24, 24)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.clicked.connect(self._start_fade_out)
            layout.addWidget(close_btn)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        # Opacity effect for animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        container.setGraphicsEffect(self.opacity_effect)

        self.container = container

    def _apply_style(self):
        """Apply toast styling."""
        style = TOAST_STYLES[self.toast_type]

        self.setStyleSheet(f"""
            #toast_container {{
                background-color: {style.background};
                border: 1px solid {style.border};
                border-radius: 8px;
                color: {style.text};
            }}

            #toast_action {{
                background-color: transparent;
                color: {style.text};
                border: 1px solid {style.border};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
            }}

            #toast_action:hover {{
                background-color: {style.border};
                color: #ffffff;
            }}

            #toast_close {{
                background-color: transparent;
                color: {style.text};
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}

            #toast_close:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }}

            QLabel {{
                color: {style.text};
                background: transparent;
            }}
        """)

    def _on_action(self):
        """Handle action button click."""
        if self.action_callback:
            self.action_callback()
        self._start_fade_out()

    def _start_fade_out(self):
        """Start fade out animation."""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_animation.finished.connect(self._on_fade_finished)
        self.fade_animation.start()

    def _on_fade_finished(self):
        """Handle fade animation finished."""
        self.closed.emit()
        self.deleteLater()

    def show_at(self, x: int, y: int):
        """Show toast at specific position."""
        self.move(x, y)
        self.show()

        # Slide in animation
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(250)
        self.slide_animation.setStartValue(QPoint(x + 50, y))
        self.slide_animation.setEndValue(QPoint(x, y))
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.start()


class ToastManager(QWidget):
    """Manages toast notifications display and positioning."""

    _instance: Optional["ToastManager"] = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.toasts: List[Toast] = []
        self.margin = 16
        self.spacing = 8
        self.max_visible = 5

        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    @classmethod
    def instance(cls) -> "ToastManager":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    def show_toast(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration_ms: int = 4000,
        closable: bool = True,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
    ) -> Toast:
        """Show a toast notification."""
        # Remove oldest if at max
        while len(self.toasts) >= self.max_visible:
            oldest = self.toasts.pop(0)
            oldest.closed.disconnect()
            oldest.deleteLater()

        toast = Toast(
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
            closable=closable,
            action_text=action_text,
            action_callback=action_callback,
        )
        toast.closed.connect(lambda: self._remove_toast(toast))

        self.toasts.append(toast)
        self._position_toasts()
        toast.show()

        return toast

    def _remove_toast(self, toast: Toast):
        """Remove toast from list."""
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._position_toasts()

    def _position_toasts(self):
        """Position all visible toasts."""
        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()
        y = screen_geo.bottom() - self.margin

        for toast in reversed(self.toasts):
            toast.adjustSize()
            toast_width = toast.sizeHint().width()
            toast_height = toast.sizeHint().height()

            x = screen_geo.right() - toast_width - self.margin
            y -= toast_height

            toast.move(x, y)
            y -= self.spacing

    def clear_all(self):
        """Clear all toasts."""
        for toast in self.toasts[:]:
            toast.closed.disconnect()
            toast.deleteLater()
        self.toasts.clear()


# Convenience functions
def show_info(message: str, **kwargs) -> Toast:
    """Show info toast."""
    return ToastManager.instance().show_toast(message, ToastType.INFO, **kwargs)


def show_success(message: str, **kwargs) -> Toast:
    """Show success toast."""
    return ToastManager.instance().show_toast(message, ToastType.SUCCESS, **kwargs)


def show_warning(message: str, **kwargs) -> Toast:
    """Show warning toast."""
    return ToastManager.instance().show_toast(message, ToastType.WARNING, **kwargs)


def show_error(message: str, **kwargs) -> Toast:
    """Show error toast."""
    return ToastManager.instance().show_toast(message, ToastType.ERROR, **kwargs)
