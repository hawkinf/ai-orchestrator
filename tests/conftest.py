"""Shared pytest fixtures for GUI tests."""

import pytest
import os

# Ensure tests run headlessly so no real dialogs pop up during build
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    """Provide a shared QApplication instance for widget tests."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
