"""Configuration management for the orchestrator."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# Load .env file
load_dotenv()


class ModelConfig(BaseModel):
    """Configuration for an AI model."""
    model_name: str = "gpt-4"
    max_tokens: int = 4096
    temperature: float = 0.2


class ExecutorConfig(BaseModel):
    """Configuration for the executor."""
    command: str = "claude"
    working_dir: str = "."
    timeout_seconds: int = 300


class GitConfig(BaseModel):
    """Git configuration."""
    remote: str = "origin"
    branch: str = "main"
    protected_branches: list[str] = Field(default_factory=lambda: ["main", "master"])


class SecurityConfig(BaseModel):
    """Security configuration."""
    command_allowlist: list[str] = Field(default_factory=lambda: [
        "flutter", "dart", "python", "pip", "pytest",
        "dotnet", "git", "npm", "node", "pnpm", "yarn"
    ])
    blocked_patterns: list[str] = Field(default_factory=lambda: [
        "rm -rf /", "format c:", "> /dev/sda", "dd if="
    ])


class ProfileConfig(BaseModel):
    """Project profile configuration."""
    setup_commands: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)


class OrchestratorConfig(BaseSettings):
    """Main orchestrator configuration."""

    # Paths
    project_path: Path = Field(default=Path("."))
    workspace_path: Path = Field(default=Path("./workspace"))

    # Execution limits
    max_iterations: int = Field(default=3, ge=1, le=10)
    iteration_timeout_seconds: int = Field(default=300)
    total_timeout_seconds: int = Field(default=1800)

    # Behaviors
    allow_auto_commit: bool = Field(default=False)
    require_human_on_destructive: bool = Field(default=True)
    auto_push_on_complete: bool = Field(default=False)

    # Active profile
    active_profile: str = Field(default="generic")

    # Nested configs
    planner: ModelConfig = Field(default_factory=ModelConfig)
    reviewer: ModelConfig = Field(default_factory=lambda: ModelConfig(max_tokens=2048, temperature=0.1))
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Profiles
    profiles: dict[str, ProfileConfig] = Field(default_factory=lambda: {
        "flutter": ProfileConfig(
            setup_commands=["flutter pub get"],
            validation_commands=["flutter analyze", "flutter test"]
        ),
        "python": ProfileConfig(
            setup_commands=["pip install -r requirements.txt"],
            validation_commands=["python -m pytest", "ruff check ."]
        ),
        "csharp": ProfileConfig(
            setup_commands=["dotnet restore"],
            validation_commands=["dotnet build", "dotnet test"]
        ),
        "generic": ProfileConfig()
    })

    # Checkpoint triggers
    checkpoint_triggers: list[str] = Field(default_factory=lambda: [
        "delete", "migration", "drop table", "force push",
        "reset --hard", "rebase", "infrastructure"
    ])

    # Logging
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=True)

    class Config:
        env_prefix = "ORCH_"

    def get_active_profile(self) -> ProfileConfig:
        """Get the currently active profile."""
        return self.profiles.get(self.active_profile, ProfileConfig())

    def get_validation_commands(self) -> list[str]:
        """Get validation commands for active profile."""
        return self.get_active_profile().validation_commands

    def get_setup_commands(self) -> list[str]:
        """Get setup commands for active profile."""
        return self.get_active_profile().setup_commands

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is in the allowlist."""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False
        base_cmd = cmd_parts[0]
        return base_cmd in self.security.command_allowlist

    def is_command_blocked(self, command: str) -> bool:
        """Check if a command matches blocked patterns."""
        cmd_lower = command.lower()
        for pattern in self.security.blocked_patterns:
            if pattern.lower() in cmd_lower:
                return True
        return False

    def needs_checkpoint(self, text: str) -> bool:
        """Check if text contains checkpoint triggers."""
        text_lower = text.lower()
        for trigger in self.checkpoint_triggers:
            if trigger.lower() in text_lower:
                return True
        return False


def load_config(config_path: Optional[Path] = None) -> OrchestratorConfig:
    """
    Load configuration from file and environment.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Loaded configuration
    """
    config_data: dict[str, Any] = {}

    # Try to load from file
    if config_path is None:
        # Look for config.yaml in current dir or parent
        for try_path in [Path("config.yaml"), Path("orchestrator.yaml")]:
            if try_path.exists():
                config_path = try_path
                break

    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    # Convert nested dicts to proper models
    if "planner" in config_data:
        config_data["planner"] = ModelConfig(**config_data["planner"])
    if "reviewer" in config_data:
        config_data["reviewer"] = ModelConfig(**config_data["reviewer"])
    if "executor" in config_data:
        config_data["executor"] = ExecutorConfig(**config_data["executor"])
    if "git" in config_data:
        config_data["git"] = GitConfig(**config_data["git"])
    if "security" in config_data:
        config_data["security"] = SecurityConfig(**config_data["security"])
    if "profiles" in config_data:
        config_data["profiles"] = {
            k: ProfileConfig(**v) for k, v in config_data["profiles"].items()
        }

    return OrchestratorConfig(**config_data)


# Global config instance (lazy loaded)
_config: Optional[OrchestratorConfig] = None


def get_config() -> OrchestratorConfig:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: OrchestratorConfig) -> None:
    """Set the global config instance."""
    global _config
    _config = config
