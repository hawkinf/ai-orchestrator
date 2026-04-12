"""Utilities for .env file manipulation.

Provides safe operations for reading, writing, and updating .env files
without losing existing content or comments.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class EnvLine:
    """Represents a line in a .env file."""
    raw: str
    key: Optional[str] = None
    value: Optional[str] = None
    is_comment: bool = False
    is_empty: bool = False


@dataclass
class EnvResolution:
    """Details about how an environment variable was resolved."""
    key: str
    value: Optional[str]
    source: str  # "system", "dotenv", "none"
    system_value: Optional[str] = None
    dotenv_value: Optional[str] = None
    dotenv_path: Optional[Path] = None
    priority_note: str = ""


def mask_secret(value: str, visible_chars: int = 8) -> str:
    """
    Mask a secret value, showing only first few characters.

    Args:
        value: The secret value to mask
        visible_chars: Number of characters to show at start

    Returns:
        Masked string like "sk-abc12..." or full value if very short
    """
    if not value:
        return ""

    if len(value) <= visible_chars:
        return value[:2] + "..." if len(value) > 2 else "***"

    return value[:visible_chars] + "..."


def parse_env_line(line: str) -> EnvLine:
    """
    Parse a single line from a .env file.

    Args:
        line: Raw line from file

    Returns:
        EnvLine with parsed components
    """
    raw = line.rstrip('\r\n')

    # Empty line
    if not raw.strip():
        return EnvLine(raw=raw, is_empty=True)

    # Comment line
    if raw.strip().startswith('#'):
        return EnvLine(raw=raw, is_comment=True)

    # Key=value line
    match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', raw)
    if match:
        key = match.group(1)
        value = match.group(2)

        # Remove surrounding quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        return EnvLine(raw=raw, key=key, value=value)

    # Unrecognized format - treat as comment/passthrough
    return EnvLine(raw=raw, is_comment=True)


def load_env_file(path: Path) -> Tuple[List[EnvLine], Dict[str, str]]:
    """
    Load and parse a .env file.

    Args:
        path: Path to .env file

    Returns:
        Tuple of (list of EnvLines, dict of key->value)
    """
    lines: List[EnvLine] = []
    values: Dict[str, str] = {}

    if not path.exists():
        return lines, values

    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        # Try with other encodings
        try:
            content = path.read_text(encoding='latin-1')
        except Exception:
            return lines, values

    for raw_line in content.splitlines():
        env_line = parse_env_line(raw_line)
        lines.append(env_line)

        if env_line.key:
            values[env_line.key] = env_line.value or ""

    return lines, values


def format_env_line(key: str, value: str) -> str:
    """
    Format a key-value pair as a .env line.

    Args:
        key: Variable name
        value: Variable value

    Returns:
        Formatted line like KEY=value or KEY="value with spaces"
    """
    # Quote if contains spaces, quotes, or special chars
    needs_quotes = any(c in value for c in [' ', '"', "'", '#', '\n', '\t'])

    if needs_quotes:
        # Escape existing quotes
        escaped = value.replace('"', '\\"')
        return f'{key}="{escaped}"'

    return f'{key}={value}'


def upsert_env_var(path: Path, key: str, value: str) -> bool:
    """
    Update or insert an environment variable in a .env file.

    Preserves existing content, comments, and formatting.

    Args:
        path: Path to .env file
        key: Variable name
        value: Variable value

    Returns:
        True if successful, False otherwise
    """
    lines, _ = load_env_file(path)

    # Find if key exists
    key_found = False
    new_lines: List[str] = []

    for env_line in lines:
        if env_line.key == key:
            # Replace this line
            new_lines.append(format_env_line(key, value))
            key_found = True
        else:
            new_lines.append(env_line.raw)

    # If key not found, append it
    if not key_found:
        # Add empty line before if file doesn't end with one
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(format_env_line(key, value))

    # Write back
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with newline at end
        content = '\n'.join(new_lines)
        if not content.endswith('\n'):
            content += '\n'

        path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False


def remove_env_var(path: Path, key: str) -> bool:
    """
    Remove an environment variable from a .env file.

    Args:
        path: Path to .env file
        key: Variable name to remove

    Returns:
        True if successful (or key not found), False on error
    """
    if not path.exists():
        return True

    lines, _ = load_env_file(path)

    new_lines: List[str] = []
    for env_line in lines:
        if env_line.key != key:
            new_lines.append(env_line.raw)

    try:
        content = '\n'.join(new_lines)
        if content and not content.endswith('\n'):
            content += '\n'

        path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False


def get_env_resolution(
    key: str,
    dotenv_path: Optional[Path] = None
) -> EnvResolution:
    """
    Get detailed resolution info for an environment variable.

    Shows where the value comes from (system vs .env) and priority.

    Args:
        key: Environment variable name
        dotenv_path: Optional path to .env file

    Returns:
        EnvResolution with full details
    """
    # Get system environment value
    system_value = os.environ.get(key)

    # Get .env file value
    dotenv_value: Optional[str] = None
    resolved_path: Optional[Path] = None

    if dotenv_path:
        if dotenv_path.exists():
            _, values = load_env_file(dotenv_path)
            dotenv_value = values.get(key)
            resolved_path = dotenv_path
    else:
        # Try common locations
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent / ".env",
        ]
        for candidate in candidates:
            if candidate.exists():
                _, values = load_env_file(candidate)
                if key in values:
                    dotenv_value = values[key]
                    resolved_path = candidate
                    break

    # Determine effective value and source
    if system_value:
        # System env takes priority
        return EnvResolution(
            key=key,
            value=system_value,
            source="system",
            system_value=system_value,
            dotenv_value=dotenv_value,
            dotenv_path=resolved_path,
            priority_note="System environment variable (takes priority over .env)"
        )
    elif dotenv_value:
        return EnvResolution(
            key=key,
            value=dotenv_value,
            source="dotenv",
            system_value=None,
            dotenv_value=dotenv_value,
            dotenv_path=resolved_path,
            priority_note=f"Loaded from .env file: {resolved_path}"
        )
    else:
        return EnvResolution(
            key=key,
            value=None,
            source="none",
            system_value=None,
            dotenv_value=None,
            dotenv_path=resolved_path,
            priority_note="Not found in system environment or .env file"
        )


def create_env_file_if_missing(path: Path) -> bool:
    """
    Create an empty .env file with header comment if it doesn't exist.

    Args:
        path: Path to .env file

    Returns:
        True if created or already exists, False on error
    """
    if path.exists():
        return True

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        header = """# AI Orchestrator Environment Configuration
# This file is automatically loaded by the application.
# Do not commit this file to version control.
#
# Required variables:
# OPENAI_API_KEY=sk-your-key-here
#
# Optional variables:
# PROJECT_PATH=.
# LOG_LEVEL=INFO

"""
        path.write_text(header, encoding='utf-8')
        return True
    except Exception:
        return False
