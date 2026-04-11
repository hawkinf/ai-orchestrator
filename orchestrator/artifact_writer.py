"""Artifact writing for run outputs."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import FinalReport, RunState, TaskStatus
from .paths import OrchestratorPaths


class ArtifactWriter:
    """
    Writes artifacts and reports for runs.

    All artifacts are saved to the run directory structure.
    """

    def __init__(self, paths: OrchestratorPaths):
        self.paths = paths

    def write_task(self, run_id: str, task_data: dict) -> Path:
        """Write task.json for a run."""
        run_dir = self.paths.run_dir(run_id)
        filepath = run_dir / "task.json"
        filepath.write_text(
            json.dumps(task_data, indent=2, default=str),
            encoding="utf-8"
        )
        return filepath

    def write_plan(self, run_id: str, plan_data: dict) -> Path:
        """Write plan.json for a run."""
        run_dir = self.paths.run_dir(run_id)
        filepath = run_dir / "plan.json"
        filepath.write_text(
            json.dumps(plan_data, indent=2, default=str),
            encoding="utf-8"
        )
        return filepath

    def write_execution_log(
        self,
        run_id: str,
        iteration: int,
        stdout: str,
        stderr: str,
    ) -> tuple[Path, Path]:
        """Write execution logs for an iteration."""
        exec_dir = self.paths.run_execution_dir(run_id)
        stdout_path = exec_dir / f"iteration_{iteration}_stdout.log"
        stderr_path = exec_dir / f"iteration_{iteration}_stderr.log"

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        return stdout_path, stderr_path

    def write_execution_report(
        self,
        run_id: str,
        iteration: int,
        report_content: str,
    ) -> Path:
        """Write execution report markdown for an iteration."""
        exec_dir = self.paths.run_execution_dir(run_id)
        filepath = exec_dir / f"iteration_{iteration}_report.md"
        filepath.write_text(report_content, encoding="utf-8")
        return filepath

    def write_review(
        self,
        run_id: str,
        iteration: int,
        review_data: dict,
    ) -> Path:
        """Write review response for an iteration."""
        review_dir = self.paths.run_review_dir(run_id)
        filepath = review_dir / f"iteration_{iteration}_review.json"
        filepath.write_text(
            json.dumps(review_data, indent=2, default=str),
            encoding="utf-8"
        )
        return filepath

    def write_validation(
        self,
        run_id: str,
        command_name: str,
        content: str,
    ) -> Path:
        """Write validation command output."""
        val_dir = self.paths.run_validation_dir(run_id)
        # Sanitize command name for filename
        safe_name = "".join(c if c.isalnum() else "_" for c in command_name)
        filepath = val_dir / f"{safe_name}.log"
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def write_git_diff(self, run_id: str, diff_content: str) -> Path:
        """Write git diff."""
        git_dir = self.paths.run_git_dir(run_id)
        filepath = git_dir / "diff.patch"
        filepath.write_text(diff_content, encoding="utf-8")
        return filepath

    def write_git_status(self, run_id: str, status_content: str) -> Path:
        """Write git status."""
        git_dir = self.paths.run_git_dir(run_id)
        filepath = git_dir / "git_status.txt"
        filepath.write_text(status_content, encoding="utf-8")
        return filepath

    def write_final_report(self, state: RunState) -> tuple[Path, Path]:
        """
        Write final report in both JSON and Markdown formats.

        Args:
            state: Completed run state

        Returns:
            Tuple of (json_path, md_path)
        """
        final_dir = self.paths.run_final_dir(state.run_id)

        # Collect all files changed across iterations
        all_files = set()
        all_commands = []
        for iteration in state.iterations:
            if iteration.execution_report:
                all_files.update(iteration.execution_report.files_changed)
                all_commands.extend(iteration.execution_report.commands_executed)

        # Build validations list
        validations = []
        if state.validation_final:
            for v in state.validation_final.results:
                validations.append({
                    "command": v.command,
                    "success": v.success,
                    "exit_code": v.exit_code,
                })

        # Calculate duration
        duration = 0.0
        if state.completed_at and state.created_at:
            duration = (state.completed_at - state.created_at).total_seconds()

        # Build final report
        report = FinalReport(
            run_id=state.run_id,
            objective=state.task.description,
            status=state.status,
            plan_summary=state.plan.scope if state.plan else None,
            total_iterations=len(state.iterations),
            files_changed=list(all_files),
            commands_executed=all_commands,
            validations=validations,
            commit_hash=state.git_result_final.commit_hash if state.git_result_final else None,
            duration_seconds=duration,
            created_at=state.created_at,
            completed_at=state.completed_at,
            artifacts=self._list_artifacts(state.run_id),
        )

        # Write JSON
        json_path = final_dir / "final_report.json"
        json_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8"
        )

        # Write Markdown
        md_path = final_dir / "final_report.md"
        md_content = self._generate_markdown_report(report, state)
        md_path.write_text(md_content, encoding="utf-8")

        return json_path, md_path

    def _list_artifacts(self, run_id: str) -> list[str]:
        """List all artifacts for a run."""
        run_dir = self.paths.run_dir(run_id)
        artifacts = []
        for f in run_dir.rglob("*"):
            if f.is_file():
                artifacts.append(str(f.relative_to(run_dir)))
        return sorted(artifacts)

    def _generate_markdown_report(self, report: FinalReport, state: RunState) -> str:
        """Generate markdown format report."""
        lines = [
            f"# Run Report: {report.run_id}",
            "",
            f"**Status:** {report.status.value}",
            f"**Duration:** {report.duration_seconds:.1f} seconds",
            f"**Created:** {report.created_at.isoformat() if report.created_at else 'N/A'}",
            f"**Completed:** {report.completed_at.isoformat() if report.completed_at else 'N/A'}",
            "",
            "## Objective",
            "",
            report.objective,
            "",
        ]

        if report.plan_summary:
            lines.extend([
                "## Plan Summary",
                "",
                report.plan_summary,
                "",
            ])

        lines.extend([
            "## Execution Summary",
            "",
            f"- **Total Iterations:** {report.total_iterations}",
            f"- **Files Changed:** {len(report.files_changed)}",
            f"- **Commands Executed:** {len(report.commands_executed)}",
            "",
        ])

        if report.files_changed:
            lines.extend(["### Files Changed", ""])
            for f in report.files_changed:
                lines.append(f"- `{f}`")
            lines.append("")

        if report.validations:
            lines.extend(["## Validations", ""])
            for v in report.validations:
                status = "✓" if v["success"] else "✗"
                lines.append(f"- {status} `{v['command']}` (exit: {v['exit_code']})")
            lines.append("")

        if report.commit_hash:
            lines.extend([
                "## Git",
                "",
                f"**Commit:** `{report.commit_hash}`",
                "",
            ])

        if state.error_message:
            lines.extend([
                "## Error",
                "",
                f"```\n{state.error_message}\n```",
                "",
            ])

        if report.artifacts:
            lines.extend(["## Artifacts", ""])
            for a in report.artifacts[:20]:  # Limit display
                lines.append(f"- `{a}`")
            if len(report.artifacts) > 20:
                lines.append(f"- ... and {len(report.artifacts) - 20} more")
            lines.append("")

        lines.extend([
            "---",
            f"*Generated by AI Orchestrator at {datetime.now().isoformat()}*",
        ])

        return "\n".join(lines)
