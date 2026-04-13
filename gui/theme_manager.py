"""Theme manager for AI Orchestrator GUI - Dark/Light mode support."""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


class ThemeMode(Enum):
    """Theme mode options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ColorScheme:
    """Color scheme for a theme."""

    # Primary colors
    primary: str = "#2563eb"
    primary_hover: str = "#1d4ed8"
    primary_pressed: str = "#1e40af"
    primary_disabled: str = "#93c5fd"

    # Background colors
    background: str = "#ffffff"
    background_secondary: str = "#f8fafc"
    background_tertiary: str = "#f1f5f9"

    # Surface colors (cards, panels)
    surface: str = "#ffffff"
    surface_hover: str = "#f8fafc"
    surface_elevated: str = "#ffffff"

    # Text colors
    text_primary: str = "#0f172a"
    text_secondary: str = "#475569"
    text_tertiary: str = "#94a3b8"
    text_on_primary: str = "#ffffff"
    text_disabled: str = "#cbd5e1"

    # Border colors
    border: str = "#e2e8f0"
    border_hover: str = "#cbd5e1"
    border_focus: str = "#2563eb"

    # Status colors
    success: str = "#22c55e"
    success_bg: str = "#dcfce7"
    warning: str = "#f59e0b"
    warning_bg: str = "#fef3c7"
    error: str = "#ef4444"
    error_bg: str = "#fee2e2"
    info: str = "#3b82f6"
    info_bg: str = "#dbeafe"

    # Sidebar
    sidebar_bg: str = "#1e293b"
    sidebar_text: str = "#e2e8f0"
    sidebar_text_active: str = "#ffffff"
    sidebar_hover: str = "#334155"
    sidebar_active: str = "#2563eb"

    # Shadow
    shadow: str = "rgba(0, 0, 0, 0.1)"
    shadow_elevated: str = "rgba(0, 0, 0, 0.15)"


# Pre-defined themes
LIGHT_THEME = ColorScheme()

DARK_THEME = ColorScheme(
    # Primary colors
    primary="#3b82f6",
    primary_hover="#60a5fa",
    primary_pressed="#2563eb",
    primary_disabled="#1e40af",
    # Background colors
    background="#0f172a",
    background_secondary="#1e293b",
    background_tertiary="#334155",
    # Surface colors
    surface="#1e293b",
    surface_hover="#334155",
    surface_elevated="#334155",
    # Text colors
    text_primary="#f8fafc",
    text_secondary="#cbd5e1",
    text_tertiary="#94a3b8",
    text_on_primary="#ffffff",
    text_disabled="#475569",
    # Border colors
    border="#334155",
    border_hover="#475569",
    border_focus="#3b82f6",
    # Status colors
    success="#4ade80",
    success_bg="#14532d",
    warning="#fbbf24",
    warning_bg="#78350f",
    error="#f87171",
    error_bg="#7f1d1d",
    info="#60a5fa",
    info_bg="#1e3a8a",
    # Sidebar
    sidebar_bg="#020617",
    sidebar_text="#94a3b8",
    sidebar_text_active="#f8fafc",
    sidebar_hover="#1e293b",
    sidebar_active="#3b82f6",
    # Shadow
    shadow="rgba(0, 0, 0, 0.3)",
    shadow_elevated="rgba(0, 0, 0, 0.4)",
)


@dataclass
class ThemeConfig:
    """Theme configuration settings."""

    mode: ThemeMode = ThemeMode.DARK
    accent_color: str = "#2563eb"
    font_family: str = "Segoe UI"
    font_size_base: int = 13
    border_radius: int = 8
    spacing_unit: int = 4
    animations_enabled: bool = True
    transition_duration: int = 150  # ms


class ThemeManager(QObject):
    """Manages application theming and style switching."""

    theme_changed = Signal(str)  # Emits theme mode name

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize theme manager."""
        super().__init__()

        if config_path is None:
            config_path = Path.home() / ".ai-orchestrator" / "theme.json"
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._config: ThemeConfig = ThemeConfig()
        self._current_scheme: ColorScheme = DARK_THEME
        self._listeners: List[Callable[[ColorScheme], None]] = []

        self.load_config()

    @property
    def config(self) -> ThemeConfig:
        """Get current theme configuration."""
        return self._config

    @property
    def colors(self) -> ColorScheme:
        """Get current color scheme."""
        return self._current_scheme

    @property
    def mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._config.mode

    def load_config(self) -> None:
        """Load theme configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = ThemeConfig(
                    mode=ThemeMode(data.get("mode", "dark")),
                    accent_color=data.get("accent_color", "#2563eb"),
                    font_family=data.get("font_family", "Segoe UI"),
                    font_size_base=data.get("font_size_base", 13),
                    border_radius=data.get("border_radius", 8),
                    spacing_unit=data.get("spacing_unit", 4),
                    animations_enabled=data.get("animations_enabled", True),
                    transition_duration=data.get("transition_duration", 150),
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        self._apply_mode()

    def save_config(self) -> None:
        """Save theme configuration to file."""
        data = {
            "mode": self._config.mode.value,
            "accent_color": self._config.accent_color,
            "font_family": self._config.font_family,
            "font_size_base": self._config.font_size_base,
            "border_radius": self._config.border_radius,
            "spacing_unit": self._config.spacing_unit,
            "animations_enabled": self._config.animations_enabled,
            "transition_duration": self._config.transition_duration,
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_mode(self, mode: ThemeMode) -> None:
        """Set theme mode and apply."""
        self._config.mode = mode
        self._apply_mode()
        self.save_config()
        self.theme_changed.emit(mode.value)

    def toggle_mode(self) -> ThemeMode:
        """Toggle between light and dark mode."""
        if self._config.mode == ThemeMode.DARK:
            self.set_mode(ThemeMode.LIGHT)
        else:
            self.set_mode(ThemeMode.DARK)
        return self._config.mode

    def _apply_mode(self) -> None:
        """Apply the current theme mode."""
        if self._config.mode == ThemeMode.DARK:
            self._current_scheme = DARK_THEME
        elif self._config.mode == ThemeMode.LIGHT:
            self._current_scheme = LIGHT_THEME
        else:
            # System mode - detect from OS (default to dark)
            self._current_scheme = DARK_THEME

        # Notify listeners
        for listener in self._listeners:
            listener(self._current_scheme)

    def add_listener(self, callback: Callable[[ColorScheme], None]) -> None:
        """Add a theme change listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[ColorScheme], None]) -> None:
        """Remove a theme change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def get_stylesheet(self) -> str:
        """Generate complete application stylesheet."""
        c = self._current_scheme
        cfg = self._config
        r = cfg.border_radius
        sp = cfg.spacing_unit
        font = cfg.font_family
        fs = cfg.font_size_base
        trans = cfg.transition_duration if cfg.animations_enabled else 0

        return f"""
        /* ===== Global Styles ===== */
        QWidget {{
            font-family: "{font}", "Segoe UI", system-ui, sans-serif;
            font-size: {fs}px;
            color: {c.text_primary};
            background-color: {c.background};
        }}

        QMainWindow {{
            background-color: {c.background};
        }}

        /* ===== Buttons ===== */
        QPushButton {{
            background-color: {c.primary};
            color: {c.text_on_primary};
            border: none;
            border-radius: {r}px;
            padding: {sp*2}px {sp*4}px;
            font-weight: 600;
            min-height: 32px;
        }}

        QPushButton:hover {{
            background-color: {c.primary_hover};
        }}

        QPushButton:pressed {{
            background-color: {c.primary_pressed};
        }}

        QPushButton:disabled {{
            background-color: {c.primary_disabled};
            color: {c.text_disabled};
        }}

        QPushButton[secondary="true"] {{
            background-color: transparent;
            color: {c.text_primary};
            border: 1px solid {c.border};
        }}

        QPushButton[secondary="true"]:hover {{
            background-color: {c.surface_hover};
            border-color: {c.border_hover};
        }}

        QPushButton[danger="true"] {{
            background-color: {c.error};
        }}

        QPushButton[danger="true"]:hover {{
            background-color: #dc2626;
        }}

        /* ===== Input Fields ===== */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            padding: {sp*2}px {sp*3}px;
            selection-background-color: {c.primary};
            selection-color: {c.text_on_primary};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c.border_focus};
            outline: none;
        }}

        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {c.background_tertiary};
            color: {c.text_disabled};
        }}

        QLineEdit::placeholder {{
            color: {c.text_tertiary};
        }}

        /* ===== ComboBox ===== */
        QComboBox {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            padding: {sp*2}px {sp*3}px;
            min-height: 32px;
        }}

        QComboBox:hover {{
            border-color: {c.border_hover};
        }}

        QComboBox:focus {{
            border-color: {c.border_focus};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c.text_secondary};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            selection-background-color: {c.primary};
            selection-color: {c.text_on_primary};
            outline: none;
        }}

        /* ===== Checkbox & Radio ===== */
        QCheckBox, QRadioButton {{
            color: {c.text_primary};
            spacing: {sp*2}px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c.border};
            border-radius: 4px;
            background-color: {c.surface};
        }}

        QCheckBox::indicator:checked {{
            background-color: {c.primary};
            border-color: {c.primary};
        }}

        QCheckBox::indicator:hover {{
            border-color: {c.border_hover};
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c.border};
            border-radius: 9px;
            background-color: {c.surface};
        }}

        QRadioButton::indicator:checked {{
            background-color: {c.primary};
            border-color: {c.primary};
        }}

        /* ===== ScrollBar ===== */
        QScrollBar:vertical {{
            background-color: {c.background_secondary};
            width: 12px;
            margin: 0;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {c.border};
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {c.border_hover};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background-color: {c.background_secondary};
            height: 12px;
            margin: 0;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {c.border};
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {c.border_hover};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* ===== Tables ===== */
        QTableWidget, QTableView {{
            background-color: {c.surface};
            alternate-background-color: {c.background_secondary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            gridline-color: {c.border};
            selection-background-color: {c.primary};
            selection-color: {c.text_on_primary};
        }}

        QTableWidget::item, QTableView::item {{
            padding: {sp*2}px {sp*3}px;
        }}

        QHeaderView::section {{
            background-color: {c.background_secondary};
            color: {c.text_secondary};
            font-weight: 600;
            border: none;
            border-bottom: 1px solid {c.border};
            padding: {sp*2}px {sp*3}px;
        }}

        QHeaderView::section:hover {{
            background-color: {c.background_tertiary};
        }}

        /* ===== Lists ===== */
        QListWidget, QListView {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            outline: none;
        }}

        QListWidget::item, QListView::item {{
            padding: {sp*2}px {sp*3}px;
            border-radius: {r - 2}px;
            margin: 2px {sp}px;
        }}

        QListWidget::item:selected, QListView::item:selected {{
            background-color: {c.primary};
            color: {c.text_on_primary};
        }}

        QListWidget::item:hover, QListView::item:hover {{
            background-color: {c.surface_hover};
        }}

        /* ===== Tree View ===== */
        QTreeWidget, QTreeView {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            alternate-background-color: {c.background_secondary};
        }}

        QTreeWidget::item, QTreeView::item {{
            padding: {sp}px;
        }}

        QTreeWidget::item:selected, QTreeView::item:selected {{
            background-color: {c.primary};
            color: {c.text_on_primary};
        }}

        /* ===== Tabs ===== */
        QTabWidget::pane {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: {r}px;
            margin-top: -1px;
        }}

        QTabBar::tab {{
            background-color: {c.background_secondary};
            color: {c.text_secondary};
            border: 1px solid {c.border};
            border-bottom: none;
            border-top-left-radius: {r}px;
            border-top-right-radius: {r}px;
            padding: {sp*2}px {sp*4}px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {c.surface};
            color: {c.text_primary};
            border-bottom: 1px solid {c.surface};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {c.background_tertiary};
        }}

        /* ===== Progress Bar ===== */
        QProgressBar {{
            background-color: {c.background_tertiary};
            border: none;
            border-radius: {r // 2}px;
            text-align: center;
            color: {c.text_secondary};
            height: 8px;
        }}

        QProgressBar::chunk {{
            background-color: {c.primary};
            border-radius: {r // 2}px;
        }}

        /* ===== Slider ===== */
        QSlider::groove:horizontal {{
            background-color: {c.background_tertiary};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background-color: {c.primary};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {c.primary_hover};
        }}

        /* ===== ToolTip ===== */
        QToolTip {{
            background-color: {c.surface_elevated};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            padding: {sp*2}px {sp*3}px;
        }}

        /* ===== Menu ===== */
        QMenu {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            padding: {sp}px;
        }}

        QMenu::item {{
            padding: {sp*2}px {sp*4}px;
            border-radius: {r - 2}px;
        }}

        QMenu::item:selected {{
            background-color: {c.primary};
            color: {c.text_on_primary};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {c.border};
            margin: {sp}px {sp*2}px;
        }}

        /* ===== GroupBox ===== */
        QGroupBox {{
            font-weight: 600;
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r}px;
            margin-top: 16px;
            padding-top: 16px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: {sp*3}px;
            padding: 0 {sp*2}px;
            background-color: {c.background};
        }}

        /* ===== Splitter ===== */
        QSplitter::handle {{
            background-color: {c.border};
        }}

        QSplitter::handle:horizontal {{
            width: 2px;
        }}

        QSplitter::handle:vertical {{
            height: 2px;
        }}

        /* ===== Status Bar ===== */
        QStatusBar {{
            background-color: {c.background_secondary};
            color: {c.text_secondary};
            border-top: 1px solid {c.border};
        }}

        /* ===== Labels ===== */
        QLabel {{
            color: {c.text_primary};
            background-color: transparent;
        }}

        QLabel[heading="true"] {{
            font-size: {fs + 4}px;
            font-weight: 600;
        }}

        QLabel[subheading="true"] {{
            font-size: {fs + 2}px;
            font-weight: 500;
            color: {c.text_secondary};
        }}

        QLabel[muted="true"] {{
            color: {c.text_tertiary};
        }}

        /* ===== Cards ===== */
        QFrame[card="true"] {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: {r}px;
            padding: {sp*4}px;
        }}

        QFrame[card="true"]:hover {{
            border-color: {c.border_hover};
        }}

        /* ===== Status Badges ===== */
        QLabel[badge="success"] {{
            background-color: {c.success_bg};
            color: {c.success};
            border-radius: {r // 2}px;
            padding: {sp}px {sp*2}px;
            font-size: {fs - 1}px;
            font-weight: 600;
        }}

        QLabel[badge="warning"] {{
            background-color: {c.warning_bg};
            color: {c.warning};
            border-radius: {r // 2}px;
            padding: {sp}px {sp*2}px;
            font-size: {fs - 1}px;
            font-weight: 600;
        }}

        QLabel[badge="error"] {{
            background-color: {c.error_bg};
            color: {c.error};
            border-radius: {r // 2}px;
            padding: {sp}px {sp*2}px;
            font-size: {fs - 1}px;
            font-weight: 600;
        }}

        QLabel[badge="info"] {{
            background-color: {c.info_bg};
            color: {c.info};
            border-radius: {r // 2}px;
            padding: {sp}px {sp*2}px;
            font-size: {fs - 1}px;
            font-weight: 600;
        }}

        /* ===== Sidebar Navigation ===== */
        QWidget[sidebar="true"] {{
            background-color: {c.sidebar_bg};
        }}

        QPushButton[nav="true"] {{
            background-color: transparent;
            color: {c.sidebar_text};
            text-align: left;
            padding: {sp*3}px {sp*4}px;
            border: none;
            border-radius: {r}px;
        }}

        QPushButton[nav="true"]:hover {{
            background-color: {c.sidebar_hover};
        }}

        QPushButton[nav="true"][active="true"] {{
            background-color: {c.sidebar_active};
            color: {c.sidebar_text_active};
        }}
        """


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(config_path: Optional[Path] = None) -> ThemeManager:
    """Get or create global theme manager."""
    global _theme_manager

    if _theme_manager is None:
        _theme_manager = ThemeManager(config_path)

    return _theme_manager


def apply_theme(app: QApplication) -> None:
    """Apply current theme to application."""
    manager = get_theme_manager()
    app.setStyleSheet(manager.get_stylesheet())


def toggle_theme() -> ThemeMode:
    """Toggle between light and dark theme."""
    return get_theme_manager().toggle_mode()
