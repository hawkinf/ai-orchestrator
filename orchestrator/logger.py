"""Logging configuration for the orchestrator."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


console = Console()


def setup_logger(
    name: str = "orchestrator",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Setup and return a configured logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    # Console handler with rich formatting
    if log_to_console:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
        )
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_run_logger(run_id: str, logs_dir: Path, level: str = "INFO") -> logging.Logger:
    """
    Get a logger for a specific run.

    Args:
        run_id: Run identifier
        logs_dir: Directory for log files
        level: Log level

    Returns:
        Configured logger for the run
    """
    log_file = logs_dir / f"run_{run_id}.log"
    return setup_logger(
        name=f"orchestrator.run.{run_id}",
        level=level,
        log_file=log_file,
        log_to_console=True,
    )


class RunLogger:
    """Context-aware logger for runs with structured output."""

    def __init__(self, run_id: str, logs_dir: Path, level: str = "INFO"):
        self.run_id = run_id
        self.logs_dir = logs_dir
        self._logger = get_run_logger(run_id, logs_dir, level)
        self._step_count = 0

    def step(self, message: str) -> None:
        """Log a step in the process."""
        self._step_count += 1
        self._logger.info(f"[Step {self._step_count}] {message}")

    def info(self, message: str) -> None:
        self._logger.info(message)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def success(self, message: str) -> None:
        """Log a success message."""
        self._logger.info(f"✓ {message}")

    def failure(self, message: str) -> None:
        """Log a failure message."""
        self._logger.error(f"✗ {message}")

    def checkpoint(self, message: str) -> None:
        """Log a checkpoint message."""
        self._logger.warning(f"⚠ CHECKPOINT: {message}")

    def separator(self) -> None:
        """Log a visual separator."""
        self._logger.info("─" * 60)

    def section(self, title: str) -> None:
        """Log a section header."""
        self.separator()
        self._logger.info(f"▶ {title}")
        self.separator()
