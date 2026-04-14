"""Interface mode definitions and helpers."""

from __future__ import annotations

MODE_SIMPLE = "simple"
MODE_ADVANCED = "advanced"


class InterfaceModeManager:
    """Central visibility rules for interface modes."""

    SIMPLE_SECTIONS = {"command_center", "new_task", "dashboard", "checkpoints", "diagnostics", "settings", "help", "runs"}
    ADVANCED_SECTIONS = {
        "command_center",
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

    @classmethod
    def normalize(cls, mode: str) -> str:
        return MODE_ADVANCED if mode == MODE_ADVANCED else MODE_SIMPLE

    @classmethod
    def visible_sections(cls, mode: str) -> set[str]:
        normalized = cls.normalize(mode)
        return cls.ADVANCED_SECTIONS if normalized == MODE_ADVANCED else cls.SIMPLE_SECTIONS
