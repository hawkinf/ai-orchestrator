"""Integrated task execution engine with real API calls."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .artifact_writer import ArtifactWriter
from .checkpoint import CheckpointManager
from .claude_executor import ClaudeExecutor, MockClaudeExecutor
from .config import OrchestratorConfig
from .git_ops import GitOperations
from .logger import RunLogger
from .models import (
    CheckpointReason,
    ExecutionReport,
    IterationState,
    ReviewStatus,
    RunState,
    TaskRequest,
    TaskStatus,
    ValidationSummary,
)
from .openai_client import PlannerClient, ReviewerClient
from .paths import OrchestratorPaths
from .prompt_builder import PromptBuilder
from .report_parser import ReportParser
from .state_store import StateStore
from .validation import ValidationRunner


class IntegratedTaskEngine:
    """
    Fully integrated orchestration engine.

    Uses:
    - OpenAI API for planner/reviewer
    - Claude Code CLI for executor
    - Local validation commands
    - Git for version control
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        paths: OrchestratorPaths,
        mock_executor: bool = False,
    ):
        self.config = config
        self.paths = paths
        self.mock_executor = mock_executor

        # Initialize core components
        self.store = StateStore(paths)
        self.checkpoint_mgr = CheckpointManager(self.store, config)
        self.prompt_builder = PromptBuilder(config, paths.prompts_dir)
        self.artifact_writer = ArtifactWriter(paths)
        self.report_parser = ReportParser()
        self.git = GitOperations(config.project_path)
        self.validator = ValidationRunner(config, config.project_path)

        # Initialize API clients
        self.planner = PlannerClient(
            model_name=config.planner.model_name,
            max_tokens=config.planner.max_tokens,
            temperature=config.planner.temperature,
        )

        self.reviewer = ReviewerClient(
            model_name=config.reviewer.model_name,
            max_tokens=config.reviewer.max_tokens,
            temperature=config.reviewer.temperature,
        )

        # Initialize executor
        if mock_executor:
            self.executor = MockClaudeExecutor(
                command=config.executor.command,
                working_dir=config.project_path,
                timeout_seconds=config.executor.timeout_seconds,
            )
        else:
            self.executor = ClaudeExecutor(
                command=config.executor.command,
                working_dir=config.project_path,
                timeout_seconds=config.executor.timeout_seconds,
            )

    def start(self, task_description: str, profile: Optional[str] = None) -> RunState:
        """
        Start a new fully automated task run.

        Args:
            task_description: User's task description
            profile: Optional project profile override

        Returns:
            Final RunState after execution
        """
        # Create task request
        task = TaskRequest(
            description=task_description,
            project_path=str(self.config.project_path),
            profile=profile or self.config.active_profile,
        )

        # Create run state
        state = self.store.create_run(task)
        logger = RunLogger(state.run_id, self.paths.logs_dir, self.config.log_level)

        logger.section(f"Starting Integrated Run: {state.run_id}")
        logger.info(f"Task: {task_description}")

        # Save task artifact
        self.artifact_writer.write_task(state.run_id, task.model_dump())

        # Capture initial git status
        state.git_status_initial = self.git.get_status()
        if not state.git_status_initial.is_repo:
            logger.warning("Not a git repository - git operations will be skipped")

        # Run the full pipeline
        try:
            state = self._run_pipeline(state, logger)
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            state.status = TaskStatus.FAILED
            state.error_message = str(e)
            self.store.save_state(state)

        return state

    def _run_pipeline(self, state: RunState, logger: RunLogger) -> RunState:
        """Run the complete orchestration pipeline."""

        # PHASE 1: Planning
        logger.section("PHASE 1: Planning")
        state = self._phase_planning(state, logger)
        if state.status in (TaskStatus.FAILED, TaskStatus.CHECKPOINT):
            return state

        # PHASE 2-4: Execute-Review Loop
        while state.current_iteration <= self.config.max_iterations:
            logger.section(f"PHASE 2-4: Iteration {state.current_iteration}")

            # Execute
            state = self._phase_execution(state, logger)
            if state.status in (TaskStatus.FAILED, TaskStatus.CHECKPOINT):
                return state

            # Review
            state = self._phase_review(state, logger)
            if state.status == TaskStatus.FAILED:
                return state
            if state.status == TaskStatus.CHECKPOINT:
                return state

            # Check if approved
            if state.status == TaskStatus.VALIDATING:
                break

            # Continue to next iteration
            state.current_iteration += 1
            self.store.save_state(state)

        # PHASE 5: Validation
        logger.section("PHASE 5: Validation")
        state = self._phase_validation(state, logger)
        if state.status == TaskStatus.FAILED:
            return state

        # PHASE 6: Commit and Push
        logger.section("PHASE 6: Commit and Push")
        state = self._phase_commit(state, logger)

        # PHASE 7: Finalize
        logger.section("PHASE 7: Finalize")
        state = self._phase_finalize(state, logger)

        return state

    def _phase_planning(self, state: RunState, logger: RunLogger) -> RunState:
        """Execute planning phase with OpenAI."""
        logger.step("Generating plan with OpenAI")

        state.status = TaskStatus.PLANNING
        self.store.save_state(state)

        # Load system prompt
        system_prompt = self.prompt_builder._load_template(
            "planner_system",
            self.prompt_builder.PLANNER_SYSTEM_DEFAULT if hasattr(self.prompt_builder, 'PLANNER_SYSTEM_DEFAULT') else ""
        )

        # Build user prompt
        user_prompt = self.prompt_builder.build_planner_prompt(
            task_description=state.task.description,
            constraints=self.config.checkpoint_triggers,
        )

        # Save prompt
        prompt_path = self.paths.run_dir(state.run_id) / "planner" / "prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(user_prompt, encoding="utf-8")

        # Call OpenAI
        plan, raw_response, error = self.planner.plan(system_prompt, user_prompt)

        # Save raw response
        raw_path = self.paths.run_dir(state.run_id) / "planner" / "raw_response.txt"
        raw_path.write_text(raw_response, encoding="utf-8")

        if error:
            logger.error(f"Planning error: {error}")
            if "[PARSE ERROR]" in plan.objective:
                # Still continue with what we have
                logger.warning("Continuing with partial plan")

        # Save parsed plan
        self.artifact_writer.write_plan(state.run_id, plan.model_dump())

        logger.success(f"Plan created: {plan.objective[:50]}...")
        state.plan = plan

        # Check for checkpoint triggers
        needs_checkpoint, reason = self.checkpoint_mgr.requires_checkpoint(plan.execution_prompt)
        if needs_checkpoint and reason and self.config.require_human_on_destructive:
            logger.checkpoint(f"Plan contains checkpoint trigger: {reason.value}")
            self.checkpoint_mgr.create_checkpoint(
                state, reason, f"Plan requires approval: {reason.value}"
            )
            return state

        # Move to executing
        state.status = TaskStatus.EXECUTING
        state.current_iteration = 1
        self.store.save_state(state)

        return state

    def _phase_execution(self, state: RunState, logger: RunLogger) -> RunState:
        """Execute task with Claude Code."""
        logger.step(f"Executing with Claude Code (iteration {state.current_iteration})")

        state.status = TaskStatus.EXECUTING
        self.store.save_state(state)

        # Get previous feedback if any
        previous_feedback = None
        if state.iterations and state.iterations[-1].review_response:
            previous_feedback = state.iterations[-1].review_response.next_prompt

        # Build executor prompt
        exec_prompt = self.prompt_builder.build_executor_prompt(
            plan=state.plan,
            iteration=state.current_iteration,
            previous_feedback=previous_feedback,
        )

        # Save prompt
        exec_dir = self.paths.run_dir(state.run_id) / "execution"
        exec_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = exec_dir / f"iteration_{state.current_iteration}_prompt.txt"
        prompt_path.write_text(exec_prompt, encoding="utf-8")

        # Execute with Claude
        logger.info("Calling Claude Code CLI...")
        result = self.executor.execute(
            prompt=exec_prompt,
            run_id=state.run_id,
            iteration=state.current_iteration,
        )

        # Save execution logs
        self.artifact_writer.write_execution_log(
            state.run_id,
            state.current_iteration,
            result.stdout,
            result.stderr,
        )

        if not result.success:
            logger.warning(f"Execution returned non-zero: {result.exit_code}")
            if result.stderr:
                logger.warning(f"Stderr: {result.stderr[:200]}")

        # Parse report from stdout
        report = self.report_parser.parse(result.stdout)

        # Update with actual git changes
        git_changed = self.git.get_changed_files()
        if git_changed:
            report.files_changed = list(set(report.files_changed + git_changed))

        # Save parsed report
        report_path = exec_dir / f"iteration_{state.current_iteration}_report_parsed.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        logger.info(f"Files changed: {len(report.files_changed)}")
        logger.info(f"Summary: {report.summary[:100]}...")

        # Create iteration state
        iteration = IterationState(
            iteration_number=state.current_iteration,
            started_at=result.started_at,
            ended_at=result.ended_at,
            execution_result=result,
            execution_report=report,
        )
        state.iterations.append(iteration)

        # Check for checkpoint triggers in report
        if report.needs_checkpoint and self.config.require_human_on_destructive:
            logger.checkpoint(f"Execution requires checkpoint: {report.checkpoint_reason}")
            self.checkpoint_mgr.create_checkpoint(
                state,
                CheckpointReason.MANUAL_REQUEST,
                f"Execution flagged for review: {report.checkpoint_reason}",
            )
            return state

        # Check for repeated failures
        failures = sum(1 for i in state.iterations if i.execution_result and not i.execution_result.success)
        if failures >= 3:
            self.checkpoint_mgr.create_failure_checkpoint(state, failures, result.stderr)
            return state

        state.status = TaskStatus.REVIEWING
        self.store.save_state(state)

        return state

    def _phase_review(self, state: RunState, logger: RunLogger) -> RunState:
        """Review execution with OpenAI."""
        logger.step(f"Reviewing with OpenAI (iteration {state.current_iteration})")

        current_iter = state.iterations[-1]
        report = current_iter.execution_report or ExecutionReport(summary="No report")

        # Get git diff
        git_diff = self.git.get_diff() + "\n" + self.git.get_diff(staged=True)

        # Load system prompt
        system_prompt = self.prompt_builder._load_template(
            "reviewer_system",
            self.prompt_builder.REVIEWER_SYSTEM_DEFAULT if hasattr(self.prompt_builder, 'REVIEWER_SYSTEM_DEFAULT') else ""
        )

        # Build user prompt
        user_prompt = self.prompt_builder.build_reviewer_prompt(
            state=state,
            execution_report=report,
            git_diff=git_diff,
        )

        # Save prompt
        review_dir = self.paths.run_dir(state.run_id) / "review"
        review_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = review_dir / f"iteration_{state.current_iteration}_prompt.txt"
        prompt_path.write_text(user_prompt, encoding="utf-8")

        # Call OpenAI
        review, raw_response, error = self.reviewer.review(system_prompt, user_prompt)

        # Save raw response
        raw_path = review_dir / f"iteration_{state.current_iteration}_raw_response.txt"
        raw_path.write_text(raw_response, encoding="utf-8")

        if error:
            logger.warning(f"Review parse warning: {error}")

        # Save parsed review
        self.artifact_writer.write_review(
            state.run_id,
            state.current_iteration,
            review.model_dump(),
        )

        current_iter.review_response = review
        logger.info(f"Review status: {review.status.value}")

        # Handle review decision
        if review.status == ReviewStatus.APPROVED:
            logger.success("Review APPROVED")
            state.status = TaskStatus.VALIDATING
        elif review.status == ReviewStatus.NEEDS_FOLLOWUP:
            logger.warning("Review needs follow-up")
            if state.current_iteration >= self.config.max_iterations:
                logger.warning(f"Max iterations ({self.config.max_iterations}) reached - proceeding to validation")
                state.status = TaskStatus.VALIDATING
            else:
                logger.info(f"Next prompt: {review.next_prompt[:100] if review.next_prompt else 'None'}...")
                state.status = TaskStatus.EXECUTING
        else:  # BLOCKED
            logger.failure("Review BLOCKED")
            if review.human_review_required:
                self.checkpoint_mgr.create_checkpoint(
                    state,
                    CheckpointReason.MANUAL_REQUEST,
                    "Reviewer requests human review",
                )
                return state
            state.status = TaskStatus.FAILED
            state.error_message = f"Blocked by reviewer: {review.findings}"

        self.store.save_state(state)
        return state

    def _phase_validation(self, state: RunState, logger: RunLogger) -> RunState:
        """Run local validation commands."""
        logger.step("Running validation commands")

        state.status = TaskStatus.VALIDATING
        self.store.save_state(state)

        validation_commands = self.config.get_validation_commands()
        if not validation_commands:
            logger.info("No validation commands configured")
            state.validation_final = ValidationSummary(all_passed=True, results=[], total_duration=0)
            state.status = TaskStatus.COMMITTING
            self.store.save_state(state)
            return state

        # Run all validations
        summary = self.validator.run_all()

        # Save validation logs
        val_dir = self.paths.run_validation_dir(state.run_id)
        for result in summary.results:
            cmd_name = result.command.split()[0].replace("/", "_").replace("\\", "_")
            log_path = val_dir / f"{cmd_name}.log"
            log_path.write_text(
                f"Command: {result.command}\n"
                f"Exit code: {result.exit_code}\n"
                f"Duration: {result.duration_seconds:.1f}s\n"
                f"\n=== STDOUT ===\n{result.stdout}\n"
                f"\n=== STDERR ===\n{result.stderr}\n",
                encoding="utf-8"
            )

            if result.success:
                logger.success(f"PASSED: {result.command}")
            else:
                logger.failure(f"FAILED: {result.command}")

        state.validation_final = summary

        if summary.all_passed:
            logger.success("All validations passed")
            state.status = TaskStatus.COMMITTING
        else:
            logger.warning("Some validations failed")
            # Check if last review allows commit anyway
            if state.iterations and state.iterations[-1].review_response:
                if state.iterations[-1].review_response.commit_allowed:
                    logger.warning("Proceeding to commit (review allowed)")
                    state.status = TaskStatus.COMMITTING
                else:
                    state.status = TaskStatus.FAILED
                    state.error_message = "Validation failed"
            else:
                state.status = TaskStatus.FAILED
                state.error_message = "Validation failed"

        self.store.save_state(state)
        return state

    def _phase_commit(self, state: RunState, logger: RunLogger) -> RunState:
        """Commit and push changes."""
        logger.step("Committing changes")

        state.status = TaskStatus.COMMITTING
        self.store.save_state(state)

        # Save git artifacts
        git_dir = self.paths.run_git_dir(state.run_id)
        self.git.save_diff_to_file(git_dir / "diff.patch")
        self.git.save_status_to_file(git_dir / "status.txt")

        if not self.git.is_repo():
            logger.warning("Not a git repository - skipping commit")
            state.status = TaskStatus.COMPLETED
            state.completed_at = datetime.now()
            self.store.save_state(state)
            return state

        # Check for changes
        git_status = self.git.get_status()
        if git_status.is_clean:
            logger.info("No changes to commit")
            state.status = TaskStatus.COMPLETED
            state.completed_at = datetime.now()
            self.store.save_state(state)
            return state

        if not self.config.allow_auto_commit:
            logger.warning("Auto-commit disabled - changes not committed")
            state.status = TaskStatus.COMPLETED
            state.completed_at = datetime.now()
            self.store.save_state(state)
            return state

        # Build commit message
        commit_msg = self._build_commit_message(state)

        # Stage all changes
        stage_result = self.git.stage_all()
        if not stage_result.success:
            logger.failure(f"Failed to stage: {stage_result.error}")
            state.status = TaskStatus.FAILED
            state.error_message = f"Git stage failed: {stage_result.error}"
            self.store.save_state(state)
            return state

        # Commit
        commit_result = self.git.commit(commit_msg)
        if not commit_result.success:
            logger.failure(f"Failed to commit: {commit_result.error}")
            state.status = TaskStatus.FAILED
            state.error_message = f"Git commit failed: {commit_result.error}"
            self.store.save_state(state)
            return state

        logger.success(f"Committed: {commit_result.commit_hash}")
        state.git_result_final = commit_result

        # Save commit info
        commit_path = git_dir / "commit.txt"
        commit_path.write_text(
            f"Hash: {commit_result.commit_hash}\n"
            f"Message:\n{commit_msg}\n",
            encoding="utf-8"
        )

        # Push if configured
        if self.config.auto_push_on_complete:
            logger.step("Pushing to remote")
            push_result = self.git.push(
                remote=self.config.git.remote,
                branch=self.config.git.branch,
            )
            if push_result.success:
                logger.success(f"Pushed to {self.config.git.remote}/{self.config.git.branch}")
            else:
                logger.warning(f"Push failed: {push_result.error}")

        state.status = TaskStatus.COMPLETED
        state.completed_at = datetime.now()
        self.store.save_state(state)

        return state

    def _phase_finalize(self, state: RunState, logger: RunLogger) -> RunState:
        """Generate final report."""
        logger.step("Generating final report")

        # Write final reports
        json_path, md_path = self.artifact_writer.write_final_report(state)

        logger.separator()
        logger.info(f"Run ID: {state.run_id}")
        logger.info(f"Status: {state.status.value}")
        logger.info(f"Iterations: {len(state.iterations)}")
        if state.git_result_final and state.git_result_final.commit_hash:
            logger.info(f"Commit: {state.git_result_final.commit_hash}")
        logger.info(f"Report: {md_path}")
        logger.separator()

        return state

    def _build_commit_message(self, state: RunState) -> str:
        """Build commit message from run state."""
        profile = state.task.profile or self.config.active_profile
        prefix = profile.upper()[:3] if profile else "DEV"

        summary = state.task.description[:50]
        if len(state.task.description) > 50:
            summary += "..."

        files_changed = set()
        for iteration in state.iterations:
            if iteration.execution_report:
                files_changed.update(iteration.execution_report.files_changed)

        message = f"""{prefix}: task - {summary}

Run ID: {state.run_id}
Iterations: {len(state.iterations)}
Files changed: {len(files_changed)}

Co-Authored-By: AI Orchestrator <noreply@orchestrator.local>
"""
        return message

    def resume(self, run_id: str) -> Optional[RunState]:
        """Resume an existing run from its current state."""
        state = self.store.load_state(run_id)
        if not state:
            return None

        logger = RunLogger(state.run_id, self.paths.logs_dir, self.config.log_level)
        logger.section(f"Resuming Run: {run_id}")
        logger.info(f"Current status: {state.status.value}")

        # Handle checkpoint first
        if state.status == TaskStatus.CHECKPOINT:
            logger.warning("Run is waiting for checkpoint approval")
            if state.checkpoint:
                logger.info(f"Reason: {state.checkpoint.reason.value}")
                logger.info(f"Description: {state.checkpoint.description}")
            return state

        # Resume based on status
        if state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            logger.info("Run is in terminal state")
            return state

        # Continue pipeline
        try:
            state = self._run_pipeline(state, logger)
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            state.status = TaskStatus.FAILED
            state.error_message = str(e)
            self.store.save_state(state)

        return state

    def approve_checkpoint(self, run_id: str, note: Optional[str] = None) -> Optional[RunState]:
        """Approve checkpoint and resume."""
        state = self.checkpoint_mgr.approve_checkpoint(run_id, note)
        if state:
            return self.resume(run_id)
        return None

    def reject_checkpoint(self, run_id: str, reason: Optional[str] = None) -> Optional[RunState]:
        """Reject checkpoint."""
        return self.checkpoint_mgr.reject_checkpoint(run_id, reason)
