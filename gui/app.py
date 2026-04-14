"""Main GUI application entry point."""

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from orchestrator.version import get_version_info


# Setup logging
def setup_logging(log_dir: Path = None) -> logging.Logger:
    """Setup application logging to console and file."""
    logger = logging.getLogger("ai_orchestrator")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console output is useful in development, but should stay silent in the
    # packaged desktop app to avoid user-facing terminal noise.
    if not getattr(sys, "frozen", False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler (if log_dir provided)
    if log_dir:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"gui_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")

    return logger


# Global exception handler
def global_exception_handler(exc_type, exc_value, exc_tb):
    """Handle uncaught exceptions."""
    logger = logging.getLogger("ai_orchestrator")

    # Format traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text = "".join(tb_lines)

    # Log the error
    logger.critical(f"Uncaught exception:\n{tb_text}")

    # Show error dialog if QApplication exists
    app = QApplication.instance()
    if app:
        QMessageBox.critical(
            None,
            "Erro Fatal",
            f"Ocorreu um erro inesperado:\n\n{exc_value}\n\n"
            "Verifique o console para mais detalhes."
        )


def run_gui():
    """Run the GUI application."""
    # Setup basic logging first
    logger = setup_logging()
    logger.info("Starting AI Orchestrator GUI...")

    # Install global exception handler
    sys.excepthook = global_exception_handler

    try:
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        version_info = get_version_info()
        app.setApplicationName(version_info.app_name)
        app.setOrganizationName("Hawk Informatica")
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        # Load configuration
        config = None
        paths = None
        config_error = None

        try:
            # Add parent directory to path for imports
            parent_dir = Path(__file__).parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            from orchestrator.config import load_config, ConfigurationError, OrchestratorConfig
            from orchestrator.paths import OrchestratorPaths

            logger.info("Loading configuration...")
            config = load_config()
            logger.info(f"Configuration loaded: workspace_path={config.workspace_path}")

            # Create paths manager (this ensures directories exist)
            paths = OrchestratorPaths(config.workspace_path, config.project_path)
            logger.info(f"Workspace initialized: {paths.workspace_root}")

            # Re-setup logging with proper log directory
            setup_logging(paths.logs_dir)

        except ConfigurationError as e:
            config_error = str(e)
            logger.error(f"Configuration Error: {e}")
            logger.info("Starting with default configuration...")

            # Create default config and paths
            try:
                from orchestrator.config import OrchestratorConfig
                from orchestrator.paths import OrchestratorPaths

                config = OrchestratorConfig()
                paths = OrchestratorPaths(config.workspace_path, config.project_path)
                logger.info(f"Default workspace: {paths.workspace_root}")
            except Exception as fallback_error:
                logger.error(f"Failed to create default config: {fallback_error}")

        except Exception as e:
            config_error = str(e)
            logger.error(f"Unexpected error loading config: {e}")
            logger.debug(traceback.format_exc())
            logger.info("Starting with default configuration...")

            # Create default config and paths
            try:
                from orchestrator.config import OrchestratorConfig
                from orchestrator.paths import OrchestratorPaths

                config = OrchestratorConfig()
                paths = OrchestratorPaths(config.workspace_path, config.project_path)
            except Exception as fallback_error:
                logger.error(f"Failed to create default config: {fallback_error}")

        # Import here to avoid issues with Qt initialization
        from .main_window import MainWindow

        logger.info("Creating main window...")

        # Create and show main window
        window = MainWindow(config=config, paths=paths)
        window.show()

        # Show config error dialog if there was one
        if config_error:
            QMessageBox.warning(
                window,
                "Aviso de Configuracao",
                f"Houve um problema ao carregar a configuracao:\n\n{config_error}\n\n"
                "A aplicacao iniciou com configuracao padrao.\n"
                "Verifique o arquivo config.yaml."
            )

        logger.info("GUI started successfully")

        # Run event loop
        return app.exec()

    except Exception as e:
        logger.critical(f"Fatal error starting GUI: {e}")
        logger.critical(traceback.format_exc())

        # Try to show error dialog
        try:
            app = QApplication.instance()
            if app:
                QMessageBox.critical(
                    None,
                    "Erro Fatal",
                    f"Nao foi possivel iniciar a aplicacao:\n\n{e}\n\n"
                    "Verifique o console para mais detalhes."
                )
        except Exception:
            pass

        return 1


def main():
    """Main entry point."""
    try:
        sys.exit(run_gui())
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"FATAL ERROR: {e}")
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
