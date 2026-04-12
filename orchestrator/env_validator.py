"""Environment validation and diagnostics for API keys."""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv


class EnvKeyStatus(Enum):
    """Status of an environment variable."""
    OK = "ok"
    MISSING = "missing"
    EMPTY = "empty"


@dataclass
class EnvValidationResult:
    """Result of environment variable validation."""
    key_name: str
    status: EnvKeyStatus
    value_preview: Optional[str] = None  # First 8 chars masked
    source: Optional[str] = None  # "env", ".env", "system"

    @property
    def is_valid(self) -> bool:
        return self.status == EnvKeyStatus.OK


@dataclass
class EnvironmentDiagnostics:
    """Full environment diagnostics."""
    openai_key: EnvValidationResult
    dotenv_loaded: bool
    dotenv_path: Optional[Path] = None
    system_info: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        """Check if environment is ready for orchestration."""
        return self.openai_key.is_valid


class EnvironmentValidator:
    """Validates and diagnoses environment configuration."""

    OPENAI_KEY_NAME = "OPENAI_API_KEY"

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._dotenv_loaded = False
        self._dotenv_path: Optional[Path] = None

    def load_dotenv(self) -> Tuple[bool, Optional[Path]]:
        """Load .env file if it exists."""
        # Try common locations
        candidates = [
            self.project_root / ".env",
            Path.cwd() / ".env",
            Path(__file__).parent.parent / ".env",
        ]

        for dotenv_path in candidates:
            if dotenv_path.exists():
                load_dotenv(dotenv_path, override=False)
                self._dotenv_loaded = True
                self._dotenv_path = dotenv_path
                return True, dotenv_path

        return False, None

    def validate_openai_key(self) -> EnvValidationResult:
        """Validate OpenAI API key."""
        value = os.getenv(self.OPENAI_KEY_NAME)

        if value is None:
            return EnvValidationResult(
                key_name=self.OPENAI_KEY_NAME,
                status=EnvKeyStatus.MISSING,
            )

        if not value.strip():
            return EnvValidationResult(
                key_name=self.OPENAI_KEY_NAME,
                status=EnvKeyStatus.EMPTY,
            )

        # Determine source
        source = "system"
        if self._dotenv_loaded and self._dotenv_path:
            # Check if key came from .env
            try:
                env_content = self._dotenv_path.read_text()
                if self.OPENAI_KEY_NAME in env_content:
                    source = ".env"
            except Exception:
                pass

        # Create preview (mask all but first 8 chars)
        preview = value[:8] + "..." if len(value) > 8 else value[:4] + "..."

        return EnvValidationResult(
            key_name=self.OPENAI_KEY_NAME,
            status=EnvKeyStatus.OK,
            value_preview=preview,
            source=source,
        )

    def run_full_diagnostics(self) -> EnvironmentDiagnostics:
        """Run full environment diagnostics."""
        # Load .env first
        dotenv_loaded, dotenv_path = self.load_dotenv()

        # Validate key
        openai_result = self.validate_openai_key()

        # System info
        system_info = f"Python {sys.version_info.major}.{sys.version_info.minor} on {sys.platform}"

        return EnvironmentDiagnostics(
            openai_key=openai_result,
            dotenv_loaded=dotenv_loaded,
            dotenv_path=dotenv_path,
            system_info=system_info,
        )

    def get_help_message(self, result: EnvValidationResult) -> str:
        """Generate help message for fixing environment issues."""
        if result.is_valid:
            return f"{result.key_name} is configured correctly (source: {result.source})"

        key_name = result.key_name

        if result.status == EnvKeyStatus.MISSING:
            return f"""{key_name} not found in environment.

How to configure on Windows:

1. Temporary (current session only):
   PowerShell:  $env:{key_name} = "sk-your-key-here"
   CMD:         set {key_name}=sk-your-key-here

2. Permanent (user level):
   PowerShell:  [Environment]::SetEnvironmentVariable("{key_name}", "sk-your-key-here", "User")

   Or: Settings > System > About > Advanced system settings > Environment Variables

3. Via .env file:
   Create a file named ".env" in the project root with:
   {key_name}=sk-your-key-here

Note: After setting environment variables, you must restart VS Code/terminal."""

        if result.status == EnvKeyStatus.EMPTY:
            return f"""{key_name} is set but empty.

Check your environment variable value:
   PowerShell:  echo $env:{key_name}
   CMD:         echo %{key_name}%

The variable exists but has no value. Set it correctly:
   PowerShell:  $env:{key_name} = "sk-your-key-here" """

        return f"Unknown issue with {key_name}"


def validate_environment(project_root: Optional[Path] = None) -> EnvironmentDiagnostics:
    """Quick helper to validate environment."""
    validator = EnvironmentValidator(project_root)
    return validator.run_full_diagnostics()


def get_openai_key_or_raise(project_root: Optional[Path] = None) -> str:
    """
    Get OpenAI API key with better error message.

    Raises:
        EnvironmentError: If key is missing or invalid, with helpful message.
    """
    validator = EnvironmentValidator(project_root)
    validator.load_dotenv()
    result = validator.validate_openai_key()

    if result.is_valid:
        return os.getenv(validator.OPENAI_KEY_NAME)

    help_msg = validator.get_help_message(result)
    raise EnvironmentError(f"OpenAI API key not configured.\n\n{help_msg}")
