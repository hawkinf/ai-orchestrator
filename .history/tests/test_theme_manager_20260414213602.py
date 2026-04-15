"""Tests for theme manager module."""

import json
import pytest
from pathlib import Path

from gui.theme_manager import (
    ThemeMode,
    ColorScheme,
    ThemeConfig,
    ThemeManager,
    LIGHT_THEME,
    DARK_THEME,
    get_theme_manager,
)


class TestThemeMode:
    """Tests for ThemeMode enum."""

    def test_mode_values(self):
        """Test theme mode enum values."""
        assert ThemeMode.LIGHT.value == "light"
        assert ThemeMode.DARK.value == "dark"
        assert ThemeMode.SYSTEM.value == "system"


class TestColorScheme:
    """Tests for ColorScheme class."""

    def test_default_colors(self):
        """Test default color scheme."""
        scheme = ColorScheme()

        assert scheme.primary == "#2563eb"
        assert scheme.background == "#ffffff"
        assert scheme.text_primary == "#0f172a"

    def test_light_theme_preset(self):
        """Test light theme preset."""
        assert LIGHT_THEME.background == "#ffffff"
        assert LIGHT_THEME.text_primary == "#0f172a"

    def test_dark_theme_preset(self):
        """Test dark theme preset."""
        assert DARK_THEME.background == "#0f172a"
        assert DARK_THEME.text_primary == "#f8fafc"

    def test_custom_colors(self):
        """Test custom color scheme."""
        scheme = ColorScheme(
            primary="#ff0000",
            background="#000000",
        )

        assert scheme.primary == "#ff0000"
        assert scheme.background == "#000000"


class TestThemeConfig:
    """Tests for ThemeConfig class."""

    def test_default_config(self):
        """Test default theme configuration."""
        config = ThemeConfig()

        assert config.mode == ThemeMode.DARK
        assert config.accent_color == "#2563eb"
        assert config.font_family == "Segoe UI"
        assert config.font_size_base == 13
        assert config.border_radius == 8
        assert config.animations_enabled is True

    def test_custom_config(self):
        """Test custom theme configuration."""
        config = ThemeConfig(
            mode=ThemeMode.LIGHT,
            font_size_base=14,
            border_radius=4,
        )

        assert config.mode == ThemeMode.LIGHT
        assert config.font_size_base == 14
        assert config.border_radius == 4


class TestThemeManager:
    """Tests for ThemeManager class."""

    def test_manager_init(self, tmp_path):
        """Test theme manager initialization."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        assert manager.config_path == config_path
        assert manager.mode == ThemeMode.DARK  # Default

    def test_manager_load_config(self, tmp_path):
        """Test loading config from file."""
        config_path = tmp_path / "theme.json"
        config_path.write_text(json.dumps({
            "mode": "light",
            "font_size_base": 14,
        }))

        manager = ThemeManager(config_path)

        assert manager.mode == ThemeMode.LIGHT
        assert manager.config.font_size_base == 14

    def test_manager_save_config(self, tmp_path):
        """Test saving config to file."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        manager._config.mode = ThemeMode.LIGHT
        manager._config.font_size_base = 16
        manager.save_config()

        # Read back
        data = json.loads(config_path.read_text())
        assert data["mode"] == "light"
        assert data["font_size_base"] == 16

    def test_manager_set_mode(self, tmp_path):
        """Test setting theme mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        manager.set_mode(ThemeMode.LIGHT)

        assert manager.mode == ThemeMode.LIGHT
        assert manager.colors.background == LIGHT_THEME.background

    def test_manager_toggle_mode(self, tmp_path):
        """Test toggling theme mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        # Start in dark mode (default)
        assert manager.mode == ThemeMode.DARK

        # Toggle to light
        new_mode = manager.toggle_mode()
        assert new_mode == ThemeMode.LIGHT
        assert manager.mode == ThemeMode.LIGHT

        # Toggle back to dark
        new_mode = manager.toggle_mode()
        assert new_mode == ThemeMode.DARK
        assert manager.mode == ThemeMode.DARK

    def test_manager_colors_dark(self, tmp_path):
        """Test colors in dark mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        manager.set_mode(ThemeMode.DARK)

        assert manager.colors.background == DARK_THEME.background
        assert manager.colors.text_primary == DARK_THEME.text_primary

    def test_manager_colors_light(self, tmp_path):
        """Test colors in light mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        manager.set_mode(ThemeMode.LIGHT)

        assert manager.colors.background == LIGHT_THEME.background
        assert manager.colors.text_primary == LIGHT_THEME.text_primary

    def test_manager_add_listener(self, tmp_path):
        """Test adding theme change listener."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        received_schemes = []

        def on_theme_change(scheme: ColorScheme):
            received_schemes.append(scheme)

        manager.add_listener(on_theme_change)
        manager.set_mode(ThemeMode.LIGHT)

        assert len(received_schemes) == 1
        assert received_schemes[0] == LIGHT_THEME

    def test_manager_remove_listener(self, tmp_path):
        """Test removing theme change listener."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        received_schemes = []

        def on_theme_change(scheme: ColorScheme):
            received_schemes.append(scheme)

        manager.add_listener(on_theme_change)
        manager.remove_listener(on_theme_change)
        manager.set_mode(ThemeMode.LIGHT)

        assert len(received_schemes) == 0

    def test_manager_get_stylesheet(self, tmp_path):
        """Test generating stylesheet."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        stylesheet = manager.get_stylesheet()

        # Should contain key styles
        assert "QWidget" in stylesheet
        assert "QPushButton" in stylesheet
        assert "QLineEdit" in stylesheet
        assert manager.colors.primary in stylesheet

    def test_manager_stylesheet_dark_mode(self, tmp_path):
        """Test stylesheet in dark mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        manager.set_mode(ThemeMode.DARK)

        stylesheet = manager.get_stylesheet()

        assert DARK_THEME.background in stylesheet
        assert DARK_THEME.text_primary in stylesheet

    def test_manager_stylesheet_light_mode(self, tmp_path):
        """Test stylesheet in light mode."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        manager.set_mode(ThemeMode.LIGHT)

        stylesheet = manager.get_stylesheet()

        assert LIGHT_THEME.background in stylesheet

    def test_manager_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        config_path = tmp_path / "theme.json"
        config_path.write_text("invalid json")

        manager = ThemeManager(config_path)

        # Should use defaults
        assert manager.mode == ThemeMode.DARK

    def test_manager_config_property(self, tmp_path):
        """Test config property access."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        config = manager.config

        assert config.mode == ThemeMode.DARK
        assert config.font_family == "Segoe UI"

    def test_manager_creates_parent_dir(self, tmp_path):
        """Test that manager creates parent directory."""
        config_path = tmp_path / "subdir" / "theme.json"
        manager = ThemeManager(config_path)

        assert config_path.parent.exists()

    def test_manager_signal_emission(self, tmp_path):
        """Test theme_changed signal emission."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)

        received_modes = []

        def on_signal(mode: str):
            received_modes.append(mode)

        manager.theme_changed.connect(on_signal)
        manager.set_mode(ThemeMode.LIGHT)

        assert received_modes == ["light"]


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_theme_manager(self, tmp_path):
        """Test getting theme manager."""
        # Reset global instance
        import gui.theme_manager as tm
        tm._theme_manager = None

        config_path = tmp_path / "theme.json"
        manager = get_theme_manager(config_path)

        assert manager is not None
        assert manager.config_path == config_path

    def test_get_theme_manager_singleton(self, tmp_path):
        """Test theme manager singleton behavior."""
        import gui.theme_manager as tm
        tm._theme_manager = None

        config_path = tmp_path / "theme.json"
        manager1 = get_theme_manager(config_path)
        manager2 = get_theme_manager()

        assert manager1 is manager2


class TestStylesheetOutput:
    """Tests for stylesheet output details."""

    def test_stylesheet_contains_all_widgets(self, tmp_path):
        """Test stylesheet covers all main widgets."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        stylesheet = manager.get_stylesheet()

        widgets = [
            "QWidget",
            "QMainWindow",
            "QPushButton",
            "QLineEdit",
            "QTextEdit",
            "QComboBox",
            "QCheckBox",
            "QRadioButton",
            "QScrollBar",
            "QTableWidget",
            "QListWidget",
            "QTreeWidget",
            "QTabWidget",
            "QProgressBar",
            "QSlider",
            "QToolTip",
            "QMenu",
            "QGroupBox",
            "QLabel",
        ]

        for widget in widgets:
            assert widget in stylesheet, f"{widget} not in stylesheet"

    def test_stylesheet_custom_properties(self, tmp_path):
        """Test stylesheet includes custom property selectors."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        stylesheet = manager.get_stylesheet()

        # Check for custom property selectors
        assert '[secondary="true"]' in stylesheet
        assert '[danger="true"]' in stylesheet
        assert '[badge="success"]' in stylesheet
        assert '[badge="warning"]' in stylesheet
        assert '[badge="error"]' in stylesheet
        assert '[badge="info"]' in stylesheet
        assert '[nav="true"]' in stylesheet
        assert '[card="true"]' in stylesheet

    def test_stylesheet_uses_config_values(self, tmp_path):
        """Test stylesheet uses config values."""
        config_path = tmp_path / "theme.json"
        manager = ThemeManager(config_path)
        manager._config.font_size_base = 15
        manager._config.border_radius = 12

        stylesheet = manager.get_stylesheet()

        assert "15px" in stylesheet
        assert "12px" in stylesheet
