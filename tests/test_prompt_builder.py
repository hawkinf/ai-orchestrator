"""Tests for prompt builder."""

import pytest

from orchestrator.config import OrchestratorConfig
from orchestrator.models import PlanResponse
from orchestrator.prompt_builder import PromptBuilder


@pytest.fixture
def config():
    """Create test config."""
    return OrchestratorConfig()


@pytest.fixture
def prompt_builder(config):
    """Create prompt builder."""
    return PromptBuilder(config)


class TestPromptBuilder:
    """Tests for PromptBuilder class."""

    def test_build_planner_prompt(self, prompt_builder):
        """Test building planner prompt."""
        prompt = prompt_builder.build_planner_prompt(
            task_description="Fix the login bug",
            project_context="Flutter app using Riverpod",
            constraints=["Don't change the UI"],
        )

        assert "Fix the login bug" in prompt
        assert "Flutter app using Riverpod" in prompt
        assert "Don't change the UI" in prompt
        assert "JSON" in prompt

    def test_build_planner_prompt_minimal(self, prompt_builder):
        """Test building planner prompt with minimal args."""
        prompt = prompt_builder.build_planner_prompt(
            task_description="Add a feature",
        )

        assert "Add a feature" in prompt
        assert "objective" in prompt.lower()

    def test_build_executor_prompt(self, prompt_builder):
        """Test building executor prompt."""
        plan = PlanResponse(
            objective="Fix the login bug",
            scope="auth module",
            constraints=["Preserve existing tests"],
            files_likely_affected=["lib/auth/login.dart"],
            risks=["May affect logout"],
            validation_steps=["Run flutter test"],
            checkpoints=[],
            execution_prompt="Fix the null check in login.dart line 42",
        )

        prompt = prompt_builder.build_executor_prompt(
            plan=plan,
            iteration=1,
        )

        assert "Fix the login bug" in prompt
        assert "auth module" in prompt
        assert "login.dart" in prompt
        assert "iteration 1" in prompt.lower()

    def test_build_executor_prompt_with_feedback(self, prompt_builder):
        """Test building executor prompt with previous feedback."""
        plan = PlanResponse(
            objective="Fix the login bug",
            scope="auth module",
            constraints=[],
            files_likely_affected=[],
            risks=[],
            validation_steps=[],
            checkpoints=[],
            execution_prompt="Fix the null check",
        )

        prompt = prompt_builder.build_executor_prompt(
            plan=plan,
            iteration=2,
            previous_feedback="You missed the error handling",
        )

        assert "iteration 2" in prompt.lower()
        assert "missed the error handling" in prompt

    def test_build_reviewer_prompt(self, prompt_builder):
        """Test building reviewer prompt."""
        from orchestrator.models import ExecutionReport, RunState, TaskRequest

        task = TaskRequest(description="Fix the login bug")
        state = RunState(
            run_id="test-run",
            task=task,
            plan=PlanResponse(
                objective="Fix the login bug",
                scope="auth module",
                constraints=[],
                files_likely_affected=[],
                risks=[],
                validation_steps=[],
                checkpoints=[],
                execution_prompt="Fix it",
            ),
        )

        report = ExecutionReport(
            summary="Fixed the null check",
            files_changed=["lib/auth/login.dart"],
            commands_executed=["flutter test"],
            tests_passed=10,
            tests_failed=0,
        )

        prompt = prompt_builder.build_reviewer_prompt(
            state=state,
            execution_report=report,
            git_diff="- old line\n+ new line",
        )

        assert "Fix the login bug" in prompt
        assert "Fixed the null check" in prompt
        assert "login.dart" in prompt
        assert "10" in prompt  # tests passed
