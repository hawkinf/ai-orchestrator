"""Tests for configuration loading."""

import pytest
import tempfile
from pathlib import Path

from orchestrator.config import (
    load_config,
    OrchestratorConfig,
    TimeoutConfig,
    ModelConfig,
    ExecutorConfig,
    GitConfig,
    SecurityConfig,
    ProfileConfig,
    ConfigurationError,
)


class TestTimeoutConfig:
    """Test TimeoutConfig model."""

    def test_default_values(self):
        """Test default timeout values."""
        config = TimeoutConfig()
        assert config.planner_seconds == 120
        assert config.executor_seconds == 600
        assert config.reviewer_seconds == 120
        assert config.validation_seconds == 300

    def test_custom_values(self):
        """Test custom timeout values."""
        config = TimeoutConfig(
            planner_seconds=60,
            executor_seconds=1200,
            reviewer_seconds=90,
            validation_seconds=180,
        )
        assert config.planner_seconds == 60
        assert config.executor_seconds == 1200
        assert config.reviewer_seconds == 90
        assert config.validation_seconds == 180

    def test_validation_min_values(self):
        """Test minimum value validation."""
        with pytest.raises(Exception):
            TimeoutConfig(planner_seconds=10)  # Below minimum of 30

    def test_validation_max_values(self):
        """Test maximum value validation."""
        with pytest.raises(Exception):
            TimeoutConfig(executor_seconds=5000)  # Above maximum of 3600


class TestOrchestratorConfigWithTimeouts:
    """Test OrchestratorConfig with timeouts field."""

    def test_default_timeouts(self):
        """Test that timeouts has default values."""
        config = OrchestratorConfig()
        assert config.timeouts is not None
        assert isinstance(config.timeouts, TimeoutConfig)
        assert config.timeouts.planner_seconds == 120

    def test_custom_timeouts(self):
        """Test config with custom timeouts."""
        config = OrchestratorConfig(
            timeouts=TimeoutConfig(
                planner_seconds=180,
                executor_seconds=900,
            )
        )
        assert config.timeouts.planner_seconds == 180
        assert config.timeouts.executor_seconds == 900


class TestLoadConfigWithTimeouts:
    """Test load_config function with timeouts in YAML."""

    def test_load_config_with_timeouts(self):
        """Test loading config.yaml that contains timeouts section."""
        yaml_content = """
project_path: "."
workspace_path: "./workspace"
max_iterations: 5

timeouts:
  planner_seconds: 180
  executor_seconds: 900
  reviewer_seconds: 150
  validation_seconds: 240

planner:
  model_name: "gpt-4o"
  max_tokens: 4096
  temperature: 0.2
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            # Verify timeouts loaded correctly
            assert config.timeouts is not None
            assert config.timeouts.planner_seconds == 180
            assert config.timeouts.executor_seconds == 900
            assert config.timeouts.reviewer_seconds == 150
            assert config.timeouts.validation_seconds == 240

            # Verify other fields
            assert config.max_iterations == 5
            assert config.planner.model_name == "gpt-4o"

        finally:
            config_path.unlink()

    def test_load_config_without_timeouts(self):
        """Test loading config.yaml without timeouts section uses defaults."""
        yaml_content = """
project_path: "."
max_iterations: 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            # Verify default timeouts
            assert config.timeouts.planner_seconds == 120
            assert config.timeouts.executor_seconds == 600

        finally:
            config_path.unlink()

    def test_load_config_partial_timeouts(self):
        """Test loading config with partial timeouts uses defaults for missing."""
        yaml_content = """
timeouts:
  planner_seconds: 200
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            assert config.timeouts.planner_seconds == 200
            assert config.timeouts.executor_seconds == 600  # default
            assert config.timeouts.reviewer_seconds == 120  # default

        finally:
            config_path.unlink()

    def test_load_config_invalid_timeout_value(self):
        """Test that invalid timeout values raise ConfigurationError."""
        yaml_content = """
timeouts:
  planner_seconds: 10
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(config_path)
            assert "timeouts" in str(exc_info.value).lower()
        finally:
            config_path.unlink()


class TestLoadConfigErrors:
    """Test error handling in load_config."""

    def test_unknown_field_error(self):
        """Test that unknown fields raise clear error."""
        yaml_content = """
project_path: "."
unknown_field: "value"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(config_path)
            error_msg = str(exc_info.value)
            # Check that error mentions unknown/extra fields
            assert "unknown" in error_msg.lower() or "extra" in error_msg.lower()
        finally:
            config_path.unlink()

    def test_invalid_yaml_syntax(self):
        """Test that invalid YAML raises ConfigurationError."""
        yaml_content = """
project_path: "."
  bad_indent: value
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(config_path)
            assert "yaml" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()
        finally:
            config_path.unlink()

    def test_invalid_nested_config(self):
        """Test that invalid nested config raises clear error."""
        yaml_content = """
planner:
  model_name: "gpt-4"
  unknown_planner_field: "value"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(config_path)
            error_msg = str(exc_info.value).lower()
            assert "planner" in error_msg
        finally:
            config_path.unlink()


class TestConfigAccessPatterns:
    """Test accessing timeout values from config."""

    def test_access_timeouts_as_object(self):
        """Test accessing timeouts as object attributes."""
        config = OrchestratorConfig(
            timeouts=TimeoutConfig(planner_seconds=150)
        )

        # This is the correct access pattern
        assert config.timeouts.planner_seconds == 150
        assert config.timeouts.executor_seconds == 600

    def test_config_full_yaml_simulation(self):
        """Test with full config.yaml content similar to production."""
        yaml_content = """
# AI Orchestrator Configuration
project_path: "."
workspace_path: "./workspace"
max_iterations: 3

allow_auto_commit: true
require_human_on_destructive: true
auto_push_on_complete: true

profiles:
  flutter:
    validation_commands:
      - "flutter analyze"
      - "flutter test"

active_profile: "flutter"

planner:
  model_name: "gpt-4o"
  max_tokens: 4096
  temperature: 0.2

reviewer:
  model_name: "gpt-4o"
  max_tokens: 2048
  temperature: 0.1

executor:
  command: "claude"
  timeout_seconds: 600

git:
  remote: "origin"
  branch: "main"
  protected_branches:
    - "main"
    - "master"

log_level: "INFO"

security:
  command_allowlist:
    - "flutter"
    - "dart"
    - "git"

checkpoint_triggers:
  - "delete"
  - "migration"

timeouts:
  planner_seconds: 120
  executor_seconds: 600
  reviewer_seconds: 120
  validation_seconds: 300
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            # Verify all sections loaded
            assert config.timeouts.planner_seconds == 120
            assert config.timeouts.executor_seconds == 600
            assert config.planner.model_name == "gpt-4o"
            assert config.executor.command == "claude"
            assert config.git.branch == "main"
            assert "flutter" in config.security.command_allowlist
            assert config.active_profile == "flutter"
            assert config.allow_auto_commit is True

        finally:
            config_path.unlink()
