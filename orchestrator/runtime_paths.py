"""Runtime path utilities for PyInstaller compatibility.

This module provides utilities to locate bundled resources when running
as a PyInstaller executable vs running from source.
"""

import sys
from pathlib import Path
from typing import Optional


def get_bundle_dir() -> Path:
    """Get the directory containing bundled resources.

    When running as PyInstaller executable:
        Returns sys._MEIPASS (temp extraction directory)

    When running from source:
        Returns the project root directory

    Returns:
        Path to the bundle/resource directory
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running from source - return project root
        return Path(__file__).parent.parent


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to a bundled resource file.

    Args:
        relative_path: Path relative to bundle directory (e.g., "config.yaml", "prompts/planner.txt")

    Returns:
        Absolute path to the resource

    Example:
        config_path = get_resource_path("config.yaml")
        prompt_path = get_resource_path("prompts/planner_system.txt")
    """
    return get_bundle_dir() / relative_path


def get_config_path() -> Optional[Path]:
    """Get path to config.yaml file.

    Checks in order:
    1. Current working directory
    2. Bundle directory (for PyInstaller)
    3. Project root (for source)

    Returns:
        Path to config.yaml if found, None otherwise
    """
    # Check current directory first (allows user override)
    cwd_config = Path("config.yaml")
    if cwd_config.exists():
        return cwd_config

    # Check orchestrator.yaml as alternative
    cwd_orchestrator = Path("orchestrator.yaml")
    if cwd_orchestrator.exists():
        return cwd_orchestrator

    # Check bundle directory
    bundle_config = get_bundle_dir() / "config.yaml"
    if bundle_config.exists():
        return bundle_config

    return None


def get_prompts_dir() -> Path:
    """Get path to prompts directory.

    Returns:
        Path to prompts directory
    """
    return get_bundle_dir() / "prompts"


def get_version_file() -> Path:
    """Get path to version.json file.

    Returns:
        Path to version.json
    """
    return get_bundle_dir() / "version.json"


def is_frozen() -> bool:
    """Check if running as PyInstaller executable.

    Returns:
        True if running as frozen executable, False otherwise
    """
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """Get the application directory.

    When frozen: Directory containing the executable
    When source: Project root directory

    Returns:
        Path to application directory
    """
    if is_frozen():
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def get_user_data_dir() -> Path:
    """Get the user data directory for storing user files.

    This is where user-specific data should be stored (not in the bundle).

    Returns:
        Path to user data directory (creates if doesn't exist)
    """
    user_dir = Path.home() / ".ai-orchestrator"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir
