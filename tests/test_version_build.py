"""Validate that the displayed app version matches the official build."""

import json
from pathlib import Path

import pytest

from orchestrator.version import get_version_manager
from gui.about_dialog import AboutDialog

ROOT = Path(__file__).resolve().parent.parent
VERSION_JSON = ROOT / "version.json"


def _official_display_version() -> str:
    data = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    return data["display_version"]


def test_version_json_has_build_display_label():
    label = _official_display_version()
    assert label.startswith("0.99 Build ")
    # Format: "0.99 Build AAAAMMDD HH:MM"
    parts = label.split()
    assert parts[0] == "0.99"
    assert parts[1] == "Build"
    assert len(parts[2]) == 8 and parts[2].isdigit()
    assert ":" in parts[3]


def test_version_manager_exposes_display_label():
    manager = get_version_manager(ROOT)
    assert manager.info.display_label == _official_display_version()


def test_version_info_txt_matches_major_minor():
    text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(0, 99, 0, 0)" in text
    assert "0.99 Build 20260514 14:35" in text


@pytest.mark.usefixtures("qapp")
def test_about_dialog_shows_official_build_version():
    """The 'Sobre' screen must show exactly the official build version."""
    manager = get_version_manager(ROOT)
    info = manager.info
    expected = _official_display_version()

    dialog = AboutDialog(
        version_info=info,
        release_url="https://github.com/hawkinf/ai-orchestrator/releases",
        changelog_markdown="## changelog",
        auto_check_updates=True,
        update_channel="stable",
    )
    assert expected in dialog.version_label.text()
