#!/usr/bin/env python3
"""Main entry point for AI Orchestrator Desktop Application."""

import sys
import os
from pathlib import Path

# Ensure the project root is in the path
ROOT_PATH = Path(__file__).parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))


def setup_environment():
    """Setup runtime environment."""
    # Set Qt environment variables for better rendering
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    # Disable Qt debug output in production
    if not os.environ.get("DEBUG"):
        os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")


def main():
    """Launch the AI Orchestrator GUI application."""
    setup_environment()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    from gui.main_window import MainWindow
    from gui.theme_manager import get_theme_manager, apply_theme
    from orchestrator.version import get_version_manager

    # Create application
    app = QApplication(sys.argv)

    # Set application metadata
    version_manager = get_version_manager(ROOT_PATH)
    info = version_manager.info

    app.setApplicationName(info.app_name)
    app.setApplicationVersion(str(info.version))
    app.setOrganizationName(info.author)
    app.setOrganizationDomain("hawkinformatica.com.br")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply theme
    apply_theme(app)

    # Create and show main window
    window = MainWindow()
    window.setWindowTitle(f"{info.app_name} v{info.display_label}")
    window.show()

    # Run application
    sys.exit(app.exec())


def main_cli():
    """Launch the CLI interface."""
    from orchestrator.cli import app as cli_app
    cli_app()


if __name__ == "__main__":
    # Check if CLI mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.argv.pop(1)  # Remove --cli flag
        main_cli()
    else:
        main()
