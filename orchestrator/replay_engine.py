"""Replay engine for run simulation and comparison.

Allows replaying runs in different modes without side effects.
"""

import difflib
import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from .replay_models import (
    CheckpointComparison,
    ComparisonResult,
    FileDiff,
    ReplayComparison,
    ReplayConfig,
    ReplayListItem,
    ReplayMode,
    ReplayResult,
    ReplayStage,
    ReplayStatus,
    StageComparison,
    StageMetrics,
)
from .state_store import StateStore
from .paths import OrchestratorPaths
from .models import RunState, TaskStatus

logger = logging.getLogger("ai_orchestrator.replay_engine")


class ReplayEngine:
    """
    Engine for replaying runs without side effects.

    Supports three modes:
    - DRY_RUN: Simulate everything, no real execution
    - PARTIAL: Execute only specific stages
    - FULL: Full replay in isolated sandbox

    Usage:
        engine = ReplayEngine(workspace_path)
        result = engine.replay(run_id, config)
        comparison = result.comparison
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.replays_dir = workspace_path / "replays"

        # Create paths and store
        self.paths = OrchestratorPaths(workspace_path)
        self.store = StateStore(self.paths)

        self._ensure_dirs()
        self._cancel_requested = False

    def _ensure_dirs(self):
        """Ensure replay directories exist."""
        self.replays_dir.mkdir(parents=True, exist_ok=True)

    def replay(
        self,
        run_id: str,
        config: Optional[ReplayConfig] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> ReplayResult:
        """
        Replay a run with the given configuration.

        Args:
            run_id: ID of the original run to replay
            config: Replay configuration (defaults to dry-run)
            progress_callback: Optional callback for progress updates (message, percent)

        Returns:
            ReplayResult with comparison data
        """
        if config is None:
            config = ReplayConfig()

        self._cancel_requested = False
        replay_id = f"replay-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"

        result = ReplayResult(
            replay_id=replay_id,
            original_run_id=run_id,
            config=config,
            status=ReplayStatus.RUNNING,
            started_at=datetime.now(),
        )

        try:
            # Load original run
            original_state = self.store.load_state(run_id)
            if not original_state:
                raise ValueError(f"Run not found: {run_id}")

            # Create replay directory
            replay_dir = self.replays_dir / replay_id
            replay_dir.mkdir(parents=True, exist_ok=True)
            result.replay_dir = replay_dir

            self._report_progress(progress_callback, "Loading original run...", 0.1)

            # Setup sandbox if needed
            sandbox_path = None
            if config.use_sandbox:
                sandbox_path = self._setup_sandbox(config, original_state)
                self._report_progress(progress_callback, "Sandbox created", 0.2)

            # Execute replay based on mode
            if config.mode == ReplayMode.DRY_RUN:
                result = self._replay_dry_run(result, original_state, progress_callback)
            elif config.mode == ReplayMode.PARTIAL:
                result = self._replay_partial(result, original_state, config.stages, progress_callback)
            elif config.mode == ReplayMode.FULL:
                result = self._replay_full(result, original_state, sandbox_path, progress_callback)

            # Generate comparison
            self._report_progress(progress_callback, "Generating comparison...", 0.9)
            result.comparison = self._generate_comparison(original_state, result)

            # Save artifacts
            self._save_artifacts(result)

            # Cleanup sandbox
            if sandbox_path and config.use_sandbox:
                self._cleanup_sandbox(sandbox_path)
                result.sandbox_cleaned = True

            result.status = ReplayStatus.COMPLETED
            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            self._report_progress(progress_callback, "Replay completed", 1.0)
            logger.info(f"Replay completed: {replay_id}")

        except Exception as e:
            logger.error(f"Replay failed: {e}")
            result.status = ReplayStatus.FAILED
            result.error = str(e)
            result.success = False
            result.completed_at = datetime.now()
            if result.started_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        # Save result
        self._save_result(result)
        return result

    def cancel(self):
        """Request cancellation of current replay."""
        self._cancel_requested = True
        logger.info("Replay cancellation requested")

    def _check_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_requested

    def _report_progress(
        self,
        callback: Optional[Callable[[str, float], None]],
        message: str,
        percent: float,
    ):
        """Report progress to callback if provided."""
        if callback:
            callback(message, percent)

    # =========================================================================
    # Replay Modes
    # =========================================================================

    def _replay_dry_run(
        self,
        result: ReplayResult,
        original: RunState,
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> ReplayResult:
        """
        Dry-run replay: simulate all stages without real execution.

        This mode:
        - Does not execute any real commands
        - Does not modify any files
        - Simulates executor output based on original
        - Records what would have happened
        """
        logger.info(f"Starting dry-run replay for: {original.run_id}")

        stages = [
            (ReplayStage.PLANNING, 0.3),
            (ReplayStage.EXECUTION, 0.5),
            (ReplayStage.REVIEW, 0.7),
            (ReplayStage.VALIDATION, 0.8),
        ]

        for stage, progress in stages:
            if self._check_cancelled():
                result.status = ReplayStatus.CANCELLED
                return result

            self._report_progress(progress_callback, f"Simulating {stage.value}...", progress)
            metrics = self._simulate_stage(stage, original)
            result.stage_metrics.append(metrics)

        return result

    def _replay_partial(
        self,
        result: ReplayResult,
        original: RunState,
        stages: List[ReplayStage],
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> ReplayResult:
        """
        Partial replay: execute only specified stages.

        Useful for debugging specific pipeline phases.
        """
        logger.info(f"Starting partial replay for: {original.run_id}, stages: {stages}")

        if ReplayStage.ALL in stages:
            stages = [ReplayStage.PLANNING, ReplayStage.EXECUTION, ReplayStage.REVIEW, ReplayStage.VALIDATION]

        total_stages = len(stages)
        for i, stage in enumerate(stages):
            if self._check_cancelled():
                result.status = ReplayStatus.CANCELLED
                return result

            progress = 0.2 + (0.7 * (i + 1) / total_stages)
            self._report_progress(progress_callback, f"Replaying {stage.value}...", progress)

            # For partial replay, we simulate but record the decision
            metrics = self._simulate_stage(stage, original)
            result.stage_metrics.append(metrics)

        return result

    def _replay_full(
        self,
        result: ReplayResult,
        original: RunState,
        sandbox_path: Optional[Path],
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> ReplayResult:
        """
        Full replay: complete pipeline execution in sandbox.

        This mode:
        - Copies project to sandbox
        - Executes full pipeline with mocked/real components
        - Compares results with original
        """
        logger.info(f"Starting full replay for: {original.run_id}")

        # Full replay still simulates for safety
        # Real execution would require additional integration
        stages = [
            (ReplayStage.PLANNING, 0.3),
            (ReplayStage.EXECUTION, 0.5),
            (ReplayStage.REVIEW, 0.7),
            (ReplayStage.VALIDATION, 0.8),
        ]

        for stage, progress in stages:
            if self._check_cancelled():
                result.status = ReplayStatus.CANCELLED
                return result

            self._report_progress(progress_callback, f"Full replay: {stage.value}...", progress)
            metrics = self._simulate_stage(stage, original, sandbox_path)
            result.stage_metrics.append(metrics)

        return result

    def _simulate_stage(
        self,
        stage: ReplayStage,
        original: RunState,
        sandbox_path: Optional[Path] = None,
    ) -> StageMetrics:
        """Simulate a pipeline stage based on original run data."""
        metrics = StageMetrics(
            stage=stage,
            started_at=datetime.now(),
        )

        try:
            if stage == ReplayStage.PLANNING:
                metrics = self._simulate_planning(original, metrics)
            elif stage == ReplayStage.EXECUTION:
                metrics = self._simulate_execution(original, metrics)
            elif stage == ReplayStage.REVIEW:
                metrics = self._simulate_review(original, metrics)
            elif stage == ReplayStage.VALIDATION:
                metrics = self._simulate_validation(original, metrics)
            elif stage == ReplayStage.COMMIT:
                metrics = self._simulate_commit(original, metrics)

            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            logger.warning(f"Stage {stage.value} simulation failed: {e}")

        metrics.completed_at = datetime.now()
        if metrics.started_at:
            metrics.duration_seconds = (metrics.completed_at - metrics.started_at).total_seconds()

        return metrics

    def _simulate_planning(self, original: RunState, metrics: StageMetrics) -> StageMetrics:
        """Simulate planning stage."""
        if original.plan:
            metrics.output_summary = f"Objective: {original.plan.objective or 'N/A'}"
            if original.plan.scope:
                metrics.output_summary += f"\nScope: {original.plan.scope}"
            if hasattr(original.plan, 'validation_steps') and original.plan.validation_steps:
                metrics.output_summary += f"\nValidation steps: {len(original.plan.validation_steps)}"
        else:
            metrics.output_summary = "No plan in original run"
        return metrics

    def _simulate_execution(self, original: RunState, metrics: StageMetrics) -> StageMetrics:
        """Simulate execution stage."""
        if original.iterations:
            last_iter = original.iterations[-1]
            if last_iter.execution_report:
                report = last_iter.execution_report
                metrics.files_affected = len(report.files_changed or [])
                metrics.output_summary = report.summary or "Execution completed"
            else:
                metrics.output_summary = "No execution report in iteration"
        else:
            metrics.output_summary = "No iterations in original run"
        return metrics

    def _simulate_review(self, original: RunState, metrics: StageMetrics) -> StageMetrics:
        """Simulate review stage."""
        if original.iterations:
            last_iter = original.iterations[-1]
            if last_iter.review_response:
                review = last_iter.review_response
                metrics.output_summary = f"Review status: {review.status.value if review.status else 'N/A'}"
                if review.findings:
                    metrics.output_summary += f"\nFindings: {review.findings[:200]}"
            else:
                metrics.output_summary = "No review response in iteration"
        else:
            metrics.output_summary = "No iterations in original run"
        return metrics

    def _simulate_validation(self, original: RunState, metrics: StageMetrics) -> StageMetrics:
        """Simulate validation stage."""
        if original.validation_final:
            val = original.validation_final
            passed = sum(1 for r in val.results if r.success)
            total = len(val.results)
            metrics.output_summary = f"Validation: {passed}/{total} passed"
            metrics.output_summary += f"\nAll passed: {val.all_passed}"
        else:
            metrics.output_summary = "No validation in original run"
        return metrics

    def _simulate_commit(self, original: RunState, metrics: StageMetrics) -> StageMetrics:
        """Simulate commit stage."""
        if original.git_result_final:
            git = original.git_result_final
            metrics.output_summary = f"Commit: {git.commit_hash or 'N/A'}"
            if git.pushed:
                metrics.output_summary += " (pushed)"
        else:
            metrics.output_summary = "No git result in original run"
        return metrics

    # =========================================================================
    # Sandbox Management
    # =========================================================================

    def _setup_sandbox(self, config: ReplayConfig, original: RunState) -> Path:
        """Create sandbox directory with project copy."""
        if config.sandbox_path:
            sandbox_path = config.sandbox_path
        else:
            sandbox_path = Path(tempfile.mkdtemp(prefix="replay_sandbox_"))

        logger.info(f"Setting up sandbox at: {sandbox_path}")

        # In a real implementation, we would copy the project here
        # For safety, we just create the directory structure
        (sandbox_path / "project").mkdir(parents=True, exist_ok=True)
        (sandbox_path / "workspace").mkdir(parents=True, exist_ok=True)

        return sandbox_path

    def _cleanup_sandbox(self, sandbox_path: Path):
        """Clean up sandbox directory."""
        if sandbox_path.exists():
            try:
                shutil.rmtree(sandbox_path)
                logger.info(f"Cleaned up sandbox: {sandbox_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup sandbox: {e}")

    # =========================================================================
    # Comparison Generation
    # =========================================================================

    def _generate_comparison(
        self,
        original: RunState,
        result: ReplayResult,
    ) -> ReplayComparison:
        """Generate comparison between original run and replay."""
        comparison = ReplayComparison(
            original_run_id=original.run_id,
            replay_id=result.replay_id,
        )

        # Compare stages
        comparison.stage_comparisons = self._compare_stages(original, result)

        # Compare checkpoints
        comparison.checkpoint_comparisons = self._compare_checkpoints(original, result)
        comparison.checkpoints_identical = sum(
            1 for cc in comparison.checkpoint_comparisons
            if cc.comparison == ComparisonResult.IDENTICAL
        )
        comparison.checkpoints_different = len(comparison.checkpoint_comparisons) - comparison.checkpoints_identical

        # Calculate timing
        original_time = self._calculate_original_time(original)
        replay_time = result.duration_seconds
        comparison.original_total_time = original_time
        comparison.replay_total_time = replay_time
        if original_time > 0:
            comparison.time_difference_percent = ((replay_time - original_time) / original_time) * 100

        # Determine overall result
        if comparison.checkpoints_different > 0:
            comparison.overall_result = ComparisonResult.DIFFERENT
            comparison.summary = f"Found {comparison.checkpoints_different} checkpoint difference(s)"
        elif any(sc.comparison == ComparisonResult.DIFFERENT for sc in comparison.stage_comparisons):
            comparison.overall_result = ComparisonResult.DIFFERENT
            comparison.summary = "Stage outputs differ from original"
        else:
            comparison.overall_result = ComparisonResult.IDENTICAL
            comparison.summary = "Replay matches original run"

        return comparison

    def _compare_stages(
        self,
        original: RunState,
        result: ReplayResult,
    ) -> List[StageComparison]:
        """Compare stages between original and replay."""
        comparisons = []

        for replay_metrics in result.stage_metrics:
            original_metrics = self._get_original_stage_metrics(original, replay_metrics.stage)

            stage_comp = StageComparison(
                stage=replay_metrics.stage,
                original_metrics=original_metrics,
                replay_metrics=replay_metrics,
            )

            # Compare outputs
            orig_output = original_metrics.output_summary if original_metrics else ""
            replay_output = replay_metrics.output_summary

            if orig_output == replay_output:
                stage_comp.comparison = ComparisonResult.IDENTICAL
            else:
                stage_comp.comparison = ComparisonResult.DIFFERENT
                # Generate diff
                stage_comp.output_diff = list(difflib.unified_diff(
                    orig_output.split("\n"),
                    replay_output.split("\n"),
                    fromfile="original",
                    tofile="replay",
                    lineterm="",
                ))

            # Time comparison
            if original_metrics and original_metrics.duration_seconds > 0:
                time_diff = replay_metrics.duration_seconds - original_metrics.duration_seconds
                stage_comp.time_difference_seconds = time_diff
                stage_comp.time_difference_percent = (time_diff / original_metrics.duration_seconds) * 100

            comparisons.append(stage_comp)

        return comparisons

    def _get_original_stage_metrics(
        self,
        original: RunState,
        stage: ReplayStage,
    ) -> Optional[StageMetrics]:
        """Extract stage metrics from original run state."""
        metrics = StageMetrics(stage=stage)

        if stage == ReplayStage.PLANNING:
            if original.plan:
                metrics.output_summary = f"Objective: {original.plan.objective or 'N/A'}"
                metrics.success = True
        elif stage == ReplayStage.EXECUTION:
            if original.iterations:
                last_iter = original.iterations[-1]
                if last_iter.execution_report:
                    metrics.output_summary = last_iter.execution_report.summary or ""
                    metrics.files_affected = len(last_iter.execution_report.files_changed or [])
                    metrics.success = True
        elif stage == ReplayStage.REVIEW:
            if original.iterations:
                last_iter = original.iterations[-1]
                if last_iter.review_response:
                    metrics.output_summary = f"Review status: {last_iter.review_response.status.value}"
                    metrics.success = True
        elif stage == ReplayStage.VALIDATION:
            if original.validation_final:
                metrics.output_summary = f"All passed: {original.validation_final.all_passed}"
                metrics.success = original.validation_final.all_passed

        return metrics

    def _compare_checkpoints(
        self,
        original: RunState,
        result: ReplayResult,
    ) -> List[CheckpointComparison]:
        """Compare checkpoint decisions between original and replay."""
        comparisons = []

        if original.checkpoint:
            cp = original.checkpoint
            orig_decision = "approved" if cp.resolved else "pending"
            if hasattr(cp, 'rejected') and cp.rejected:
                orig_decision = "rejected"

            # Get replay decision from config
            replay_decision = result.config.checkpoint_decisions.get(
                cp.checkpoint_id or str(cp.id) if hasattr(cp, 'id') else "unknown",
                "auto_approved" if result.config.auto_approve_checkpoints else "pending"
            )

            comp = CheckpointComparison(
                checkpoint_id=cp.checkpoint_id or str(uuid4())[:8],
                checkpoint_type=cp.reason.value if cp.reason else "unknown",
                original_decision=orig_decision,
                replay_decision=replay_decision,
            )

            if orig_decision == replay_decision or (
                orig_decision == "approved" and replay_decision == "auto_approved"
            ):
                comp.comparison = ComparisonResult.IDENTICAL
            else:
                comp.comparison = ComparisonResult.DIFFERENT
                comp.notes = f"Original: {orig_decision}, Replay: {replay_decision}"

            comparisons.append(comp)

        return comparisons

    def _calculate_original_time(self, original: RunState) -> float:
        """Calculate total time of original run."""
        if original.completed_at and original.created_at:
            return (original.completed_at - original.created_at).total_seconds()
        return 0.0

    # =========================================================================
    # Artifacts
    # =========================================================================

    def _save_artifacts(self, result: ReplayResult):
        """Save replay artifacts to disk."""
        if not result.replay_dir:
            return

        # Save report
        report_path = result.replay_dir / "report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        result.report_path = report_path

        # Save metrics
        metrics_path = result.replay_dir / "metrics.json"
        metrics_data = {
            "replay_id": result.replay_id,
            "mode": result.config.mode.value,
            "duration_seconds": result.duration_seconds,
            "stages": [sm.to_dict() for sm in result.stage_metrics],
        }
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2, ensure_ascii=False)
        result.metrics_path = metrics_path

        # Save comparison diff if available
        if result.comparison and result.comparison.stage_comparisons:
            diff_path = result.replay_dir / "diff.patch"
            diff_lines = []
            for sc in result.comparison.stage_comparisons:
                if sc.output_diff:
                    diff_lines.append(f"# Stage: {sc.stage.value}")
                    diff_lines.extend(sc.output_diff)
                    diff_lines.append("")
            if diff_lines:
                with open(diff_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(diff_lines))
                result.diff_path = diff_path

        logger.info(f"Saved replay artifacts to: {result.replay_dir}")

    def _save_result(self, result: ReplayResult):
        """Save replay result to index."""
        index_file = self.replays_dir / "index.json"
        index = []

        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except (json.JSONDecodeError, Exception):
                pass

        # Add new result
        index.append({
            "replay_id": result.replay_id,
            "original_run_id": result.original_run_id,
            "mode": result.config.mode.value,
            "status": result.status.value,
            "success": result.success,
            "created_at": result.started_at.isoformat() if result.started_at else None,
            "duration_seconds": result.duration_seconds,
            "comparison_result": result.comparison.overall_result.value if result.comparison else None,
        })

        # Keep last 100 replays
        if len(index) > 100:
            index = index[-100:]

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def list_replays(self, limit: int = 50) -> List[ReplayListItem]:
        """List recent replays."""
        index_file = self.replays_dir / "index.json"
        if not index_file.exists():
            return []

        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

            items = []
            for entry in reversed(index[-limit:]):
                created_at = datetime.now()
                if entry.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(entry["created_at"])
                    except (ValueError, TypeError):
                        pass

                items.append(ReplayListItem(
                    replay_id=entry["replay_id"],
                    original_run_id=entry["original_run_id"],
                    mode=ReplayMode(entry.get("mode", "dry_run")),
                    status=ReplayStatus(entry.get("status", "completed")),
                    created_at=created_at,
                    duration_seconds=entry.get("duration_seconds", 0.0),
                    success=entry.get("success", False),
                    comparison_result=ComparisonResult(entry["comparison_result"]) if entry.get("comparison_result") else None,
                ))

            return items

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error loading replay index: {e}")
            return []

    def get_replay(self, replay_id: str) -> Optional[ReplayResult]:
        """Get full replay result by ID."""
        replay_dir = self.replays_dir / replay_id
        report_path = replay_dir / "report.json"

        if not report_path.exists():
            return None

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ReplayResult.from_dict(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error loading replay {replay_id}: {e}")
            return None

    def delete_replay(self, replay_id: str) -> bool:
        """Delete a replay and its artifacts."""
        replay_dir = self.replays_dir / replay_id

        if not replay_dir.exists():
            return False

        try:
            shutil.rmtree(replay_dir)

            # Update index
            index_file = self.replays_dir / "index.json"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)

                index = [e for e in index if e.get("replay_id") != replay_id]

                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(index, f, indent=2, ensure_ascii=False)

            logger.info(f"Deleted replay: {replay_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting replay: {e}")
            return False


def get_replay_engine(workspace_path: Path) -> ReplayEngine:
    """Factory function to create a ReplayEngine."""
    return ReplayEngine(workspace_path)
