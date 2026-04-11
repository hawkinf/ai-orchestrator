"""Main task execution engine."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .artifact_writer import ArtifactWriter
from .checkpoint import CheckpointManager
from .config import OrchestratorConfig
from .executor_client import ExecutorClient, ManualExecutorClient
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
    ValidationResult,
    ValidationSummary,
)
from .paths import OrchestratorPaths
from .planner_client import ManualPlannerClient, PlannerClient
from .prompt_builder import PromptBuilder
from .report_parser import ReportParser
from .reviewer_client import ManualReviewerClient, ReviewerClient
from .state_store import StateStore


class TaskEngine:
    """
    Main orchestration engine.

    Coordinates the full pipeline:
    Task -> Plan -> Execute -> Review -> Validate -> Commit
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        paths: OrchestratorPaths,
        manual_mode: bool = True,
    ):
        self.config = config
        self.paths = paths
        self.manual_mode = manual_mode

        # Initialize components
        self.store = StateStore(paths)
        self.checkpoint_mgr = CheckpointManager(self.store, config)
        self.prompt_builder = PromptBuilder(config, paths.prompts_dir)
        self.artifact_writer = ArtifactWriter(paths)
        self.report_parser = ReportParser()
        self.git = GitOperations(config.project_path)

        # Initialize clients (manual vs automatic)
        if manual_mode:
            self.planner = ManualPlannerClient(
                response_file=str(paths.prompts_dir / "planner_response.json"),
                model_name=config.planner.model_name,
            )
            self.executor = ManualExecutorClient(
                prompts_dir=paths.prompts_dir,
                command=config.executor.command,
                working_dir=config.project_path,
            )
            self.reviewer = ManualReviewerClient(
                response_file=str(paths.prompts_dir / "reviewer_response.json"),
                model_name=config.reviewer.model_name,
            )
        else:
            self.planner = PlannerClient(model_name=config.planner.model_name)
            self.executor = ExecutorClient(
                command=config.executor.command,
                working_dir=config.project_path,
            )
            self.reviewer = ReviewerClient(model_name=config.reviewer.model_name)

    def start(self, task_description: str, profile: Optional[str] = None) -> RunState:
        """
        Start a new task run.

        Args:
            task_description: User's task description
            profile: Optional project profile override

        Returns:
            Initial RunState
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

        logger.section(f"Starting Run: {state.run_id}")
        logger.info(f"Task: {task_description}")

        # Save task artifact
        self.artifact_writer.write_task(state.run_id, task.model_dump())

        # Capture initial git status
        state.git_status_initial = self.git.get_status()
        if not state.git_status_initial.is_repo:
            logger.warning("Not a git repository - git operations will be skipped")

        # Move to planning phase
        state.status = TaskStatus.PLANNING
        self.store.save_state(state)

        # Generate planner prompt
        logger.step("Generating planner prompt")
        planner_prompt = self.prompt_builder.build_planner_prompt(
            task_description=task_description,
            constraints=self.config.checkpoint_triggers,
        )

        # Save prompt for manual use
        prompt_file = self.paths.prompts_dir / f"planner_{state.run_id}.txt"
        if self.manual_mode:
            formatted = self.planner.get_prompt_for_manual_use(planner_prompt)
            prompt_file.write_text(formatted, encoding="utf-8")
            logger.info(f"Planner prompt saved to: {prompt_file}")
            logger.checkpoint("Copy prompt to planner, paste response, then resume")
        else:
            prompt_file.write_text(planner_prompt, encoding="utf-8")

        self.store.save_state(state)
        return state

    def resume(self, run_id: str) -> Optional[RunState]:
        """
        Resume an existing run.

        Args:
            run_id: Run identifier

        Returns:
            Updated RunState or None if not found
        """
        state = self.store.load_state(run_id)
        if not state:
            return None

        logger = RunLogger(state.run_id, self.paths.logs_dir, self.config.log_level)
        logger.section(f"Resuming Run: {run_id}")
        logger.info(f"Current status: {state.status.value}")

        # Handle based on current status
        if state.status == TaskStatus.PLANNING:
            return self._resume_planning(state, logger)
        elif state.status == TaskStatus.EXECUTING:
            return self._resume_executing(state, logger)
        elif state.status == TaskStatus.REVIEWING:
            return self._resume_reviewing(state, logger)
        elif state.status == TaskStatus.VALIDATING:
            return self._resume_validating(state, logger)
        elif state.status == TaskStatus.CHECKPOINT:
            logger.warning("Run is waiting for checkpoint approval")
            if state.checkpoint:
                logger.info(f"Checkpoint reason: {state.checkpoint.reason.value}")
                logger.info(f"Description: {state.checkpoint.description}")
            return state
        elif state.status == TaskStatus.COMMITTING:
            return self._resume_committing(state, logger)
        else:
            logger.info(f"Run is in terminal state: {state.status.value}")
            return state

    def _resume_planning(self, state: RunState, logger: RunLogger) -> RunState:
        """Resume from planning phase."""
        logger.step("Checking for planner response")

        # Try to get plan
        planner_prompt = self.prompt_builder.build_planner_prompt(state.task.description)
        plan, raw = self.planner.plan(planner_prompt)

        if "[PENDING" in plan.objective:
            logger.warning("No planner response found")
            logger.info("Please paste the planner response to the response file")
            return state

        # Plan received
        logger.success("Plan received")
        state.plan = plan
        self.artifact_writer.write_plan(state.run_id, plan.model_dump())

        # Check for checkpoint triggers in plan
        needs_check, reason = self.checkpoint_mgr.requires_checkpoint(plan.execution_prompt)
        if needs_check and reason:
            logger.checkpoint(f"Plan contains checkpoint trigger: {reason.value}")
            self.checkpoint_mgr.create_checkpoint(
                state, reason, f"Plan requires approval: {reason.value}"
            )
            return state

        # Move to executing
        state.status = TaskStatus.EXECUTING
        state.current_iteration = 1
        self.store.save_state(state)

        return self._resume_executing(state, logger)

    def _resume_executing(self, state: RunState, logger: RunLogger) -> RunState:
        """Resume from executing phase."""
        logger.step(f"Executing iteration {state.current_iteration}")

        if not state.plan:
            logger.error("No plan available for execution")
            state.status = TaskStatus.FAILED
            state.error_message = "No plan available"
            self.store.save_state(state)
            return state

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

        # Execute
        result = self.executor.execute(
            prompt=exec_prompt,
            run_id=state.run_id,
            iteration=state.current_iteration,
        )

        # Check for pending (manual mode)
        if result.exit_code == -2:
            logger.warning("Execution pending manual completion")
            logger.info(result.stderr)
            return state

        # Save execution logs
        self.artifact_writer.write_execution_log(
            state.run_id,
            state.current_iteration,
            result.stdout,
            result.stderr,
        )

        # Parse report
        report = self.report_parser.parse(result.stdout)
        report.files_changed = self.git.get_changed_files()

        # Create iteration state
        iteration = IterationState(
            iteration_number=state.current_iteration,
            started_at=result.started_at,
            ended_at=result.ended_at,
            execution_result=result,
            execution_report=report,
        )
        state.iterations.append(iteration)

        # Save report artifact
        self.artifact_writer.write_execution_report(
            state.run_id,
            state.current_iteration,
            result.stdout,
        )

        if not result.success:
            logger.failure(f"Execution failed: {result.stderr[:200]}")
            # Check for repeated failures
            failures = sum(1 for i in state.iterations if not i.execution_result.success)
            if failures >= 3:
                self.checkpoint_mgr.create_failure_checkpoint(state, failures, result.stderr)
                return state

        # Move to reviewing
        state.status = TaskStatus.REVIEWING
        self.store.save_state(state)

        return self._resume_reviewing(state, logger)

    def _resume_reviewing(self, state: RunState, logger: RunLogger) -> RunState:
        """Resume from reviewing phase."""
        logger.step(f"Reviewing iteration {state.current_iteration}")

        if not state.iterations:
            logger.error("No execution to review")
            state.status = TaskStatus.FAILED
            self.store.save_state(state)
            return state

        current_iter = state.iterations[-1]
        if not current_iter.execution_report:
            current_iter.execution_report = ExecutionReport(summary="No report available")

        # Get git diff
        git_diff = self.git.get_diff() + "\n" + self.git.get_diff(staged=True)

        # Build reviewer prompt
        review_prompt = self.prompt_builder.build_reviewer_prompt(
            state=state,
            execution_report=current_iter.execution_report,
            git_diff=git_diff,
        )

        # Get review
        review, raw = self.reviewer.review(review_prompt)

        if "[PENDING" in str(review.findings):
            # Save prompt for manual use
            prompt_file = self.paths.prompts_dir / f"reviewer_{state.run_id}_iter{state.current_iteration}.txt"
            if self.manual_mode:
                formatted = self.reviewer.get_prompt_for_manual_use(review_prompt)
                prompt_file.write_text(formatted, encoding="utf-8")
            logger.warning("No reviewer response found")
            logger.info("Please paste the reviewer response to the response file")
            return state

        # Review received
        current_iter.review_response = review
        self.artifact_writer.write_review(
            state.run_id,
            state.current_iteration,
            review.model_dump(),
        )

        logger.info(f"Review status: {review.status.value}")

        # Handle review decision
        if review.status == ReviewStatus.APPROVED:
            logger.success("Review approved")
            state.status = TaskStatus.VALIDATING
        elif review.status == ReviewStatus.NEEDS_FOLLOWUP:
            logger.warning("Review needs follow-up")
            if state.current_iteration >= self.config.max_iterations:
                logger.error(f"Max iterations ({self.config.max_iterations}) reached")
                state.status = TaskStatus.VALIDATING  # Proceed to validation anyway
            else:
                state.current_iteration += 1
                state.status = TaskStatus.EXECUTING
        else:  # BLOCKED
            logger.failure("Review blocked execution")
            if review.human_review_required:
                self.checkpoint_mgr.create_checkpoint(
                    state,
                    CheckpointReason.MANUAL_REQUEST,
                    "Reviewer requests human review",
                )
                return state
            state.status = TaskStatus.FAILED
            state.error_message = "Blocked by reviewer"

        self.store.save_state(state)

        if state.status == TaskStatus.EXECUTING:
            return self._resume_executing(state, logger)
        elif state.status == TaskStatus.VALIDATING:
            return self._resume_validating(state, logger)

        return state

    def _resume_validating(self, state: RunState, logger: RunLogger) -> RunState:
        """Resume from validating phase."""
        logger.step("Running validations")

        validation_commands = self.config.get_validation_commands()
        if not validation_commands:
            logger.info("No validation commands configured")
            state.validation_final = ValidationSummary(all_passed=True)
            state.status = TaskStatus.COMMITTING
            self.store.save_state(state)
            return self._resume_committing(state, logger)

        results = []
        all_passed = True

        for cmd in validation_commands:
            logger.info(f"Running: {cmd}")
            try:
                start = datetime.now()
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.config.project_path,
                    capture_output=True,
                    text=True,
                    timeout=self.config.iteration_timeout_seconds,
                )
                duration = (datetime.now() - start).total_seconds()

                result = ValidationResult(
                    command=cmd,
                    success=proc.returncode == 0,
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    duration_seconds=duration,
                )
                results.append(result)

                # Save validation output
                self.artifact_writer.write_validation(
                    state.run_id,
                    cmd.split()[0],
                    f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
                )

                if result.success:
                    logger.success(f"Passed: {cmd}")
                else:
                    logger.failure(f"Failed: {cmd}")
                    all_passed = False

            except subprocess.TimeoutExpired:
                logger.failure(f"Timeout: {cmd}")
                results.append(ValidationResult(
                    command=cmd,
                    success=False,
                    exit_code=-1,
                    stderr="Timeout",
                ))
                all_passed = False
            except Exception as e:
                logger.failure(f"Error: {cmd} - {e}")
                results.append(ValidationResult(
                    command=cmd,
                    success=False,
                    exit_code=-1,
                    stderr=str(e),
                ))
                all_passed = False

        state.validation_final = ValidationSummary(
            all_passed=all_passed,
            results=results,
            total_duration=sum(r.duration_seconds for r in results),
        )

        if all_passed:
            state.status = TaskStatus.COMMITTING
            self.store.save_state(state)
            return self._resume_committing(state, logger)
        else:
            logger.warning("Validation failed - checking review")
            # Check if last review allows commit anyway
            if state.iterations and state.iterations[-1].review_response:
                if state.iterations[-1].review_response.commit_allowed:
                    logger.warning("Proceeding to commit despite validation failures")
                    state.status = TaskStatus.COMMITTING
                    self.store.save_state(state)
                    return self._resume_committing(state, logger)

            state.status = TaskStatus.FAILED
            state.error_message = "Validation failed"
            self.store.save_state(state)
            return state

    def _resume_committing(self, state: RunState, logger: RunLogger) -> RunState:
        """Resume from committing phase."""
        logger.step("Committing changes")

        # Save git artifacts
        self.git.save_diff_to_file(self.paths.run_git_dir(state.run_id) / "diff.patch")
        self.git.save_status_to_file(self.paths.run_git_dir(state.run_id) / "git_status.txt")

        if not self.git.is_repo():
            logger.warning("Not a git repository - skipping commit")
            state.status = TaskStatus.COMPLETED
            state.completed_at = datetime.now()
            self.store.save_state(state)
            return self._finalize(state, logger)

        # Check for changes
        git_status = self.git.get_status()
        if git_status.is_clean:
            logger.info("No changes to commit")
            state.status = TaskStatus.COMPLETED
            state.completed_at = datetime.now()
            self.store.save_state(state)
            return self._finalize(state, logger)

        # Build commit message
        commit_msg = self._build_commit_message(state)

        # Stage and commit
        stage_result = self.git.stage_all()
        if not stage_result.success:
            logger.failure(f"Failed to stage: {stage_result.error}")
            state.status = TaskStatus.FAILED
            state.error_message = f"Git stage failed: {stage_result.error}"
            self.store.save_state(state)
            return state

        commit_result = self.git.commit(commit_msg)
        if not commit_result.success:
            logger.failure(f"Failed to commit: {commit_result.error}")
            state.status = TaskStatus.FAILED
            state.error_message = f"Git commit failed: {commit_result.error}"
            self.store.save_state(state)
            return state

        logger.success(f"Committed: {commit_result.commit_hash}")
        state.git_result_final = commit_result

        # Push if configured
        if self.config.auto_push_on_complete:
            logger.step("Pushing to remote")
            push_result = self.git.push(
                remote=self.config.git.remote,
                branch=self.config.git.branch,
            )
            if push_result.success:
                logger.success("Pushed to remote")
            else:
                logger.warning(f"Push failed: {push_result.error}")

        state.status = TaskStatus.COMPLETED
        state.completed_at = datetime.now()
        self.store.save_state(state)

        return self._finalize(state, logger)

    def _finalize(self, state: RunState, logger: RunLogger) -> RunState:
        """Generate final report and clean up."""
        logger.section("Finalizing Run")

        # Write final report
        json_path, md_path = self.artifact_writer.write_final_report(state)
        logger.info(f"Final report: {md_path}")

        logger.separator()
        logger.info(f"Run ID: {state.run_id}")
        logger.info(f"Status: {state.status.value}")
        if state.git_result_final and state.git_result_final.commit_hash:
            logger.info(f"Commit: {state.git_result_final.commit_hash}")
        logger.separator()

        return state

    def _build_commit_message(self, state: RunState) -> str:
        """Build commit message from run state."""
        # Get profile prefix
        profile = state.task.profile or self.config.active_profile
        prefix = profile.upper()[:3] if profile else "DEV"

        # Build message
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

    def approve_checkpoint(self, run_id: str, note: Optional[str] = None) -> Optional[RunState]:
        """Approve a pending checkpoint."""
        state = self.checkpoint_mgr.approve_checkpoint(run_id, note)
        if state:
            return self.resume(run_id)
        return None

    def reject_checkpoint(self, run_id: str, reason: Optional[str] = None) -> Optional[RunState]:
        """Reject a pending checkpoint."""
        return self.checkpoint_mgr.reject_checkpoint(run_id, reason)

    def validate(self, run_id: str) -> Optional[ValidationSummary]:
        """Run validations for a run."""
        state = self.store.load_state(run_id)
        if not state:
            return None

        logger = RunLogger(state.run_id, self.paths.logs_dir, self.config.log_level)
        state.status = TaskStatus.VALIDATING
        self.store.save_state(state)

        state = self._resume_validating(state, logger)
        return state.validation_final

    def finalize(self, run_id: str) -> Optional[RunState]:
        """Force finalize a run with commit."""
        state = self.store.load_state(run_id)
        if not state:
            return None

        logger = RunLogger(state.run_id, self.paths.logs_dir, self.config.log_level)
        state.status = TaskStatus.COMMITTING
        self.store.save_state(state)

        return self._resume_committing(state, logger)
