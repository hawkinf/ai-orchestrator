"""Utility functions for the orchestrator."""

import json
import re
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


def generate_run_id() -> str:
    """Generate a unique run ID based on timestamp."""
    now = datetime.now()
    return now.strftime("%Y%m%d-%H%M%S")


def safe_filename(text: str, max_length: int = 50) -> str:
    """Convert text to a safe filename."""
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', text)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.strip('_')
    return safe[:max_length]


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def parse_json_from_text(text: str) -> Optional[dict]:
    """
    Extract and parse JSON from text that may contain other content.
    Handles common LLM output patterns.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in markdown code fence
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*({\s*.*?\s*})\s*```',
        r'(\{[\s\S]*\})',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    return None


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def read_file_safe(path: Path, default: str = "") -> str:
    """Read file content safely, return default on error."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return default


def write_file_safe(path: Path, content: str) -> bool:
    """Write file content safely, return success status."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except (PermissionError, OSError):
        return False


def dict_to_yaml_str(data: dict, indent: int = 0) -> str:
    """Simple dict to YAML-like string for display."""
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dict_to_yaml_str(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(dict_to_yaml_str(item, indent + 2))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def mask_sensitive(text: str) -> str:
    """Mask potentially sensitive data in text."""
    patterns = [
        (r'sk-[a-zA-Z0-9]{20,}', 'sk-****'),
        (r'api[_-]?key["\s:=]+["\']?([^"\'\s]+)', 'api_key: ****'),
        (r'password["\s:=]+["\']?([^"\'\s]+)', 'password: ****'),
        (r'token["\s:=]+["\']?([^"\'\s]+)', 'token: ****'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result
