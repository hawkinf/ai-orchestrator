"""Shared pytest fixtures for GUI tests."""

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Provide a shared QApplication instance for widget tests."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
