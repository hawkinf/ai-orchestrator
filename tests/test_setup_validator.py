"""Tests for setup validator and minimum configuration checks."""

from pathlib import Path
from unittest.mock import patch

from orchestrator.setup_validator import SetupCheckResult, SetupValidator


def test_minimum_validation_reports_missing_openai(tmp_path):
    validator = SetupValidator(tmp_path)

    with patch.object(validator, "check_openai") as mock_openai:
        mock_openai.return_value = SetupCheckResult(
            key="openai",
            title="OpenAI",
            ok=False,
            required=True,
            summary="Chave ausente",
        )

        result = validator.validate_minimum_configuration(
            project_path=tmp_path,
            workspace_path=tmp_path / "workspace",
            profile="flutter",
            executor_command="claude",
        )

    assert not result.is_ready
    assert result.by_key("openai") is not None
    assert any(check.key == "openai" for check in result.blockers)


def test_workspace_check_creates_directory(tmp_path):
    validator = SetupValidator(tmp_path)
    workspace = tmp_path / "workspace"

    result = validator.check_workspace(workspace)

    assert result.ok is True
    assert workspace.exists()


def test_git_check_is_optional_when_repo_missing(tmp_path):
    validator = SetupValidator(tmp_path)

    result = validator.check_git(tmp_path)

    assert result.required is False
