"""Replay engine models for run simulation and comparison.

Defines models for replay modes, results, and comparisons.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("ai_orchestrator.replay_models")


class ReplayMode(Enum):
    """Available replay modes."""
    DRY_RUN = "dry_run"  # No real execution, simulate everything
    PARTIAL = "partial"  # Execute only specific stages
    FULL = "full"  # Full replay in sandbox


class ReplayStage(Enum):
    """Pipeline stages that can be replayed."""
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    VALIDATION = "validation"
    COMMIT = "commit"
    ALL = "all"


class ReplayStatus(Enum):
    """Status of a replay operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonResult(Enum):
    """Result of comparing original vs replay."""
    IDENTICAL = "identical"
    DIFFERENT = "different"
    ORIGINAL_ONLY = "original_only"
    REPLAY_ONLY = "replay_only"


@dataclass
class ReplayConfig:
    """Configuration for a replay operation."""
    mode: ReplayMode = ReplayMode.DRY_RUN
    stages: List[ReplayStage] = field(default_factory=lambda: [ReplayStage.ALL])
    use_sandbox: bool = False
    sandbox_path: Optional[Path] = None

    # Override options
    override_config: Dict[str, Any] = field(default_factory=dict)
    mock_executor: bool = True  # Always mock by default for safety
    mock_planner: bool = False
    mock_reviewer: bool = False

    # Checkpoint simulation
    auto_approve_checkpoints: bool = True
    checkpoint_decisions: Dict[str, str] = field(default_factory=dict)  # checkpoint_id -> "approve"/"reject"

    # Limits
    max_iterations: Optional[int] = None
    timeout_seconds: int = 600

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "stages": [s.value for s in self.stages],
            "use_sandbox": self.use_sandbox,
            "sandbox_path": str(self.sandbox_path) if self.sandbox_path else None,
            "override_config": self.override_config,
            "mock_executor": self.mock_executor,
            "mock_planner": self.mock_planner,
            "mock_reviewer": self.mock_reviewer,
            "auto_approve_checkpoints": self.auto_approve_checkpoints,
            "checkpoint_decisions": self.checkpoint_decisions,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayConfig":
        return cls(
            mode=ReplayMode(data.get("mode", "dry_run")),
            stages=[ReplayStage(s) for s in data.get("stages", ["all"])],
            use_sandbox=data.get("use_sandbox", False),
            sandbox_path=Path(data["sandbox_path"]) if data.get("sandbox_path") else None,
            override_config=data.get("override_config", {}),
            mock_executor=data.get("mock_executor", True),
            mock_planner=data.get("mock_planner", False),
            mock_reviewer=data.get("mock_reviewer", False),
            auto_approve_checkpoints=data.get("auto_approve_checkpoints", True),
            checkpoint_decisions=data.get("checkpoint_decisions", {}),
            max_iterations=data.get("max_iterations"),
            timeout_seconds=data.get("timeout_seconds", 600),
        )


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    stage: ReplayStage
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None
    output_summary: str = ""

    # Stage-specific data
    tokens_used: int = 0
    api_calls: int = 0
    files_affected: int = 0

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error": self.error,
            "output_summary": self.output_summary,
            "tokens_used": self.tokens_used,
            "api_calls": self.api_calls,
            "files_affected": self.files_affected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StageMetrics":
        started_at = None
        completed_at = None
        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                pass
        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            stage=ReplayStage(data["stage"]),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=data.get("duration_seconds", 0.0),
            success=data.get("success", False),
            error=data.get("error"),
            output_summary=data.get("output_summary", ""),
            tokens_used=data.get("tokens_used", 0),
            api_calls=data.get("api_calls", 0),
            files_affected=data.get("files_affected", 0),
        )


@dataclass
class FileDiff:
    """Difference between original and replay for a file."""
    file_path: str
    comparison: ComparisonResult
    original_content: Optional[str] = None
    replay_content: Optional[str] = None
    diff_lines: List[str] = field(default_factory=list)

    # Stats
    lines_added: int = 0
    lines_removed: int = 0
    lines_changed: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "comparison": self.comparison.value,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "lines_changed": self.lines_changed,
            "diff_lines": self.diff_lines[:100],  # Limit stored diff lines
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileDiff":
        return cls(
            file_path=data["file_path"],
            comparison=ComparisonResult(data["comparison"]),
            lines_added=data.get("lines_added", 0),
            lines_removed=data.get("lines_removed", 0),
            lines_changed=data.get("lines_changed", 0),
            diff_lines=data.get("diff_lines", []),
        )


@dataclass
class CheckpointComparison:
    """Comparison of checkpoint decisions."""
    checkpoint_id: str
    checkpoint_type: str
    original_decision: Optional[str] = None  # approve/reject/require_human
    replay_decision: Optional[str] = None
    comparison: ComparisonResult = ComparisonResult.IDENTICAL
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_type": self.checkpoint_type,
            "original_decision": self.original_decision,
            "replay_decision": self.replay_decision,
            "comparison": self.comparison.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointComparison":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            checkpoint_type=data["checkpoint_type"],
            original_decision=data.get("original_decision"),
            replay_decision=data.get("replay_decision"),
            comparison=ComparisonResult(data.get("comparison", "identical")),
            notes=data.get("notes", ""),
        )


@dataclass
class StageComparison:
    """Comparison of a stage between original and replay."""
    stage: ReplayStage
    original_metrics: Optional[StageMetrics] = None
    replay_metrics: Optional[StageMetrics] = None
    comparison: ComparisonResult = ComparisonResult.IDENTICAL

    # Differences
    output_diff: List[str] = field(default_factory=list)
    time_difference_seconds: float = 0.0
    time_difference_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "original_metrics": self.original_metrics.to_dict() if self.original_metrics else None,
            "replay_metrics": self.replay_metrics.to_dict() if self.replay_metrics else None,
            "comparison": self.comparison.value,
            "output_diff": self.output_diff[:50],
            "time_difference_seconds": self.time_difference_seconds,
            "time_difference_percent": self.time_difference_percent,
        }


@dataclass
class ReplayComparison:
    """Full comparison between original run and replay."""
    original_run_id: str
    replay_id: str

    # Overall status
    overall_result: ComparisonResult = ComparisonResult.IDENTICAL
    summary: str = ""

    # Stage comparisons
    stage_comparisons: List[StageComparison] = field(default_factory=list)

    # File differences
    file_diffs: List[FileDiff] = field(default_factory=list)
    files_identical: int = 0
    files_different: int = 0
    files_new_in_replay: int = 0
    files_missing_in_replay: int = 0

    # Checkpoint differences
    checkpoint_comparisons: List[CheckpointComparison] = field(default_factory=list)
    checkpoints_identical: int = 0
    checkpoints_different: int = 0

    # Time comparison
    original_total_time: float = 0.0
    replay_total_time: float = 0.0
    time_difference_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original_run_id": self.original_run_id,
            "replay_id": self.replay_id,
            "overall_result": self.overall_result.value,
            "summary": self.summary,
            "stage_comparisons": [sc.to_dict() for sc in self.stage_comparisons],
            "file_diffs": [fd.to_dict() for fd in self.file_diffs],
            "files_identical": self.files_identical,
            "files_different": self.files_different,
            "files_new_in_replay": self.files_new_in_replay,
            "files_missing_in_replay": self.files_missing_in_replay,
            "checkpoint_comparisons": [cc.to_dict() for cc in self.checkpoint_comparisons],
            "checkpoints_identical": self.checkpoints_identical,
            "checkpoints_different": self.checkpoints_different,
            "original_total_time": self.original_total_time,
            "replay_total_time": self.replay_total_time,
            "time_difference_percent": self.time_difference_percent,
        }


@dataclass
class ReplayResult:
    """Result of a replay operation."""
    replay_id: str
    original_run_id: str
    config: ReplayConfig
    status: ReplayStatus = ReplayStatus.PENDING

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Results
    success: bool = False
    error: Optional[str] = None
    stage_metrics: List[StageMetrics] = field(default_factory=list)

    # Comparison
    comparison: Optional[ReplayComparison] = None

    # Artifacts
    replay_dir: Optional[Path] = None
    report_path: Optional[Path] = None
    diff_path: Optional[Path] = None
    metrics_path: Optional[Path] = None

    # Sandbox info
    sandbox_cleaned: bool = False

    def __post_init__(self):
        if not self.replay_id:
            self.replay_id = f"replay-{uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "replay_id": self.replay_id,
            "original_run_id": self.original_run_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error": self.error,
            "stage_metrics": [sm.to_dict() for sm in self.stage_metrics],
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "replay_dir": str(self.replay_dir) if self.replay_dir else None,
            "report_path": str(self.report_path) if self.report_path else None,
            "diff_path": str(self.diff_path) if self.diff_path else None,
            "metrics_path": str(self.metrics_path) if self.metrics_path else None,
            "sandbox_cleaned": self.sandbox_cleaned,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayResult":
        started_at = None
        completed_at = None
        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                pass
        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except (ValueError, TypeError):
                pass

        stage_metrics = []
        for sm_data in data.get("stage_metrics", []):
            stage_metrics.append(StageMetrics.from_dict(sm_data))

        comparison = None
        if data.get("comparison"):
            comparison = ReplayComparison(
                original_run_id=data["comparison"]["original_run_id"],
                replay_id=data["comparison"]["replay_id"],
            )
            # Load basic comparison fields
            comparison.overall_result = ComparisonResult(
                data["comparison"].get("overall_result", "identical")
            )
            comparison.summary = data["comparison"].get("summary", "")

        return cls(
            replay_id=data["replay_id"],
            original_run_id=data["original_run_id"],
            config=ReplayConfig.from_dict(data.get("config", {})),
            status=ReplayStatus(data.get("status", "pending")),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=data.get("duration_seconds", 0.0),
            success=data.get("success", False),
            error=data.get("error"),
            stage_metrics=stage_metrics,
            comparison=comparison,
            replay_dir=Path(data["replay_dir"]) if data.get("replay_dir") else None,
            report_path=Path(data["report_path"]) if data.get("report_path") else None,
            diff_path=Path(data["diff_path"]) if data.get("diff_path") else None,
            metrics_path=Path(data["metrics_path"]) if data.get("metrics_path") else None,
            sandbox_cleaned=data.get("sandbox_cleaned", False),
        )


@dataclass
class ReplayListItem:
    """Summary item for replay list."""
    replay_id: str
    original_run_id: str
    mode: ReplayMode
    status: ReplayStatus
    created_at: datetime
    duration_seconds: float = 0.0
    success: bool = False
    comparison_result: Optional[ComparisonResult] = None
    task_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "replay_id": self.replay_id,
            "original_run_id": self.original_run_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "comparison_result": self.comparison_result.value if self.comparison_result else None,
            "task_summary": self.task_summary,
        }
