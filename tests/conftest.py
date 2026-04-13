"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for Qt tests.

    This fixture is session-scoped to avoid creating multiple QApplication
    instances which would cause Qt to crash.
    """
    from PySide6.QtWidgets import QApplication

    # Check if an instance already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    # Don't quit the app as it may be reused


@pytest.fixture(autouse=True)
def qt_app_for_widgets(request, qapp):
    """Auto-use fixture that provides QApplication for widget tests.

    This fixture is automatically applied to tests in classes that test
    Qt widgets (TestCheckpointsPanel, etc.).
    """
    # Only apply to test classes that create widgets
    widget_test_classes = [
        "TestCheckpointsPanel",
        "TestPolicyPanel",
        "TestReplayPanel",
    ]

    if request.node.cls and request.node.cls.__name__ in widget_test_classes:
        yield qapp
    else:
        yield None
