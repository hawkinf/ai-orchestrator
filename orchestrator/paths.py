"""Path management for the orchestrator."""

from pathlib import Path
from typing import Optional


class OrchestratorPaths:
    """Centralized path management."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path("./workspace")
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create workspace directory structure."""
        dirs = [
            self.tasks_dir,
            self.runs_dir,
            self.prompts_dir,
            self.reports_dir,
            self.audits_dir,
            self.logs_dir,
            self.state_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def tasks_dir(self) -> Path:
        return self.workspace_root / "tasks"

    @property
    def runs_dir(self) -> Path:
        return self.workspace_root / "runs"

    @property
    def prompts_dir(self) -> Path:
        return self.workspace_root / "prompts"

    @property
    def reports_dir(self) -> Path:
        return self.workspace_root / "reports"

    @property
    def audits_dir(self) -> Path:
        return self.workspace_root / "audits"

    @property
    def logs_dir(self) -> Path:
        return self.workspace_root / "logs"

    @property
    def state_dir(self) -> Path:
        return self.workspace_root / "state"

    def run_dir(self, run_id: str) -> Path:
        """Get directory for a specific run."""
        path = self.runs_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_execution_dir(self, run_id: str) -> Path:
        """Get execution subdirectory for a run."""
        path = self.run_dir(run_id) / "execution"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_review_dir(self, run_id: str) -> Path:
        """Get review subdirectory for a run."""
        path = self.run_dir(run_id) / "review"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_validation_dir(self, run_id: str) -> Path:
        """Get validation subdirectory for a run."""
        path = self.run_dir(run_id) / "validation"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_git_dir(self, run_id: str) -> Path:
        """Get git subdirectory for a run."""
        path = self.run_dir(run_id) / "git"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_final_dir(self, run_id: str) -> Path:
        """Get final report subdirectory for a run."""
        path = self.run_dir(run_id) / "final"
        path.mkdir(parents=True, exist_ok=True)
        return path
