"""Tests for interface mode manager."""

from gui.mode_manager import (
    MODE_SIMPLE,
    MODE_ADVANCED,
    InterfaceModeManager,
)


def test_normalize_returns_simple_by_default():
    assert InterfaceModeManager.normalize("") == MODE_SIMPLE
    assert InterfaceModeManager.normalize("unknown") == MODE_SIMPLE
    assert InterfaceModeManager.normalize("other") == MODE_SIMPLE


def test_normalize_returns_advanced_when_specified():
    assert InterfaceModeManager.normalize(MODE_ADVANCED) == MODE_ADVANCED
    assert InterfaceModeManager.normalize("advanced") == MODE_ADVANCED


def test_normalize_returns_simple_when_specified():
    assert InterfaceModeManager.normalize(MODE_SIMPLE) == MODE_SIMPLE
    assert InterfaceModeManager.normalize("simple") == MODE_SIMPLE


def test_simple_mode_has_fewer_sections():
    simple_sections = InterfaceModeManager.visible_sections(MODE_SIMPLE)
    advanced_sections = InterfaceModeManager.visible_sections(MODE_ADVANCED)

    assert len(simple_sections) < len(advanced_sections)


def test_simple_mode_excludes_technical_panels():
    sections = InterfaceModeManager.visible_sections(MODE_SIMPLE)

    # Simple mode should not show policies, replay, or logs
    assert "policies" not in sections
    assert "replay" not in sections
    assert "logs" not in sections


def test_simple_mode_includes_essential_panels():
    sections = InterfaceModeManager.visible_sections(MODE_SIMPLE)

    # Simple mode should show core functionality
    assert "new_task" in sections
    assert "dashboard" in sections
    assert "checkpoints" in sections
    assert "diagnostics" in sections
    assert "settings" in sections
    assert "help" in sections
    assert "runs" in sections


def test_advanced_mode_includes_all_panels():
    sections = InterfaceModeManager.visible_sections(MODE_ADVANCED)

    expected = {
        "new_task",
        "dashboard",
        "checkpoints",
        "diagnostics",
        "settings",
        "help",
        "runs",
        "logs",
        "policies",
        "replay",
    }

    assert sections == expected


def test_visible_sections_returns_set():
    simple = InterfaceModeManager.visible_sections(MODE_SIMPLE)
    advanced = InterfaceModeManager.visible_sections(MODE_ADVANCED)

    assert isinstance(simple, set)
    assert isinstance(advanced, set)


def test_advanced_sections_is_superset_of_simple():
    simple = InterfaceModeManager.visible_sections(MODE_SIMPLE)
    advanced = InterfaceModeManager.visible_sections(MODE_ADVANCED)

    assert simple.issubset(advanced)
