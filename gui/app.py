"""Main GUI application entry point."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


def run_gui():
    """Run the GUI application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Orchestrator")
    app.setOrganizationName("Hawk Informatica")

    # Load configuration
    config = None
    paths = None

    try:
        # Add parent directory to path for imports
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        from orchestrator.config import load_config
        from orchestrator.paths import OrchestratorPaths

        config = load_config()
        paths = OrchestratorPaths(config.workspace_path)

    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        print("Starting with default configuration...")

    # Import here to avoid issues with Qt initialization
    from .main_window import MainWindow

    # Create and show main window
    window = MainWindow(config=config, paths=paths)
    window.show()

    # Run event loop
    return app.exec()


def main():
    """Main entry point."""
    sys.exit(run_gui())


if __name__ == "__main__":
    main()
