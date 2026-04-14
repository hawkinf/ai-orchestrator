"""Shared pytest fixtures for GUI tests."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Ensure tests run headlessly so no real dialogs pop up during build
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Force an isolated per-run basetemp so pytest exits cleanly on Windows."""
    if config.option.basetemp:
        return

    basetemp_root = Path(tempfile.gettempdir()) / "ai-orchestrator-pytest"
    basetemp_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    config.option.basetemp = str(basetemp_root / f"run_{timestamp}_{os.getpid()}")


@pytest.fixture(scope="session")
def qapp():
    """Provide a shared QApplication instance for widget tests."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
