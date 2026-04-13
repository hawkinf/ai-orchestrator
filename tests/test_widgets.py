"""Tests for premium UI widgets."""

import pytest

from gui.toast import ToastType, ToastStyle, TOAST_STYLES


class TestToastType:
    """Tests for ToastType enum."""

    def test_toast_types(self):
        """Test toast type values."""
        assert ToastType.INFO.value == "info"
        assert ToastType.SUCCESS.value == "success"
        assert ToastType.WARNING.value == "warning"
        assert ToastType.ERROR.value == "error"


class TestToastStyles:
    """Tests for toast styles."""

    def test_styles_exist_for_all_types(self):
        """Test all toast types have styles."""
        for toast_type in ToastType:
            assert toast_type in TOAST_STYLES

    def test_style_has_required_fields(self):
        """Test styles have all required fields."""
        for style in TOAST_STYLES.values():
            assert hasattr(style, "background")
            assert hasattr(style, "border")
            assert hasattr(style, "text")
            assert hasattr(style, "icon")

    def test_style_colors_are_valid(self):
        """Test style colors are valid hex codes."""
        for style in TOAST_STYLES.values():
            assert style.background.startswith("#")
            assert style.border.startswith("#")
            assert style.text.startswith("#")

    def test_info_style(self):
        """Test info style values."""
        style = TOAST_STYLES[ToastType.INFO]
        assert "#" in style.background
        assert style.icon == "ℹ️"

    def test_success_style(self):
        """Test success style values."""
        style = TOAST_STYLES[ToastType.SUCCESS]
        assert "#" in style.background
        assert style.icon == "✓"

    def test_warning_style(self):
        """Test warning style values."""
        style = TOAST_STYLES[ToastType.WARNING]
        assert "#" in style.background
        assert style.icon == "⚠"

    def test_error_style(self):
        """Test error style values."""
        style = TOAST_STYLES[ToastType.ERROR]
        assert "#" in style.background
        assert style.icon == "✕"


class TestToastStyleDataclass:
    """Tests for ToastStyle dataclass."""

    def test_style_creation(self):
        """Test creating a toast style."""
        style = ToastStyle(
            background="#000000",
            border="#ffffff",
            text="#cccccc",
            icon="★",
        )

        assert style.background == "#000000"
        assert style.border == "#ffffff"
        assert style.text == "#cccccc"
        assert style.icon == "★"
