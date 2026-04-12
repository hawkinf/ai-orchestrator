"""Local validation commands execution."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ValidationResult, ValidationSummary
from .config import OrchestratorConfig


class ValidationRunner:
    """
    Runs validation commands for the project.

    Executes configured validation commands and collects results.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        working_dir: Optional[Path] = None,
    ):
        self.config = config
        self.working_dir = working_dir or config.project_path

    def run_all(self) -> ValidationSummary:
        """
        Run all validation commands for the active profile.

        Returns:
            ValidationSummary with all results
        """
        commands = self.config.get_validation_commands()
        results = []
        total_duration = 0.0

        for cmd in commands:
            result = self.run_command(cmd)
            results.append(result)
            total_duration += result.duration_seconds

        all_passed = all(r.success for r in results)

        return ValidationSummary(
            all_passed=all_passed,
            results=results,
            total_duration=total_duration,
        )

    def run_command(self, command: str) -> ValidationResult:
        """
        Run a single validation command.

        Args:
            command: Command to execute

        Returns:
            ValidationResult with command output
        """
        timeout = self.config.iteration_timeout_seconds

        try:
            start = datetime.now()

            # Use shell=True for complex commands
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (datetime.now() - start).total_seconds()

            return ValidationResult(
                command=command,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                duration_seconds=timeout,
            )

        except Exception as e:
            return ValidationResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=0,
            )

    def run_setup(self) -> ValidationSummary:
        """
        Run setup commands for the active profile.

        Returns:
            ValidationSummary with setup results
        """
        commands = self.config.get_setup_commands()
        results = []
        total_duration = 0.0

        for cmd in commands:
            result = self.run_command(cmd)
            results.append(result)
            total_duration += result.duration_seconds

            # Stop on first failure for setup
            if not result.success:
                break

        all_passed = all(r.success for r in results)

        return ValidationSummary(
            all_passed=all_passed,
            results=results,
            total_duration=total_duration,
        )
