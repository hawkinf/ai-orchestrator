"""Executor client for running Claude Code or similar."""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ExecutionResult


class ExecutorClient:
    """
    Client for executing tasks via Claude Code CLI.

    Wraps subprocess calls with proper timeout, logging, and error handling.
    """

    def __init__(
        self,
        command: str = "claude",
        working_dir: Optional[Path] = None,
        timeout_seconds: int = 300,
    ):
        self.command = command
        self.working_dir = working_dir or Path(".")
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        prompt: str,
        run_id: str,
        iteration: int,
    ) -> ExecutionResult:
        """
        Execute a task with the configured executor.

        Args:
            prompt: Execution prompt
            run_id: Run identifier for context
            iteration: Current iteration number

        Returns:
            ExecutionResult with stdout/stderr/exit code
        """
        started_at = datetime.now()

        try:
            # Build command - assumes claude CLI accepts prompt via stdin or -p
            # Adjust based on actual claude CLI interface
            result = subprocess.run(
                [self.command, "-p", prompt],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            ended_at = datetime.now()
            duration = (ended_at - started_at).total_seconds()

            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                started_at=started_at,
                ended_at=ended_at,
            )

        except subprocess.TimeoutExpired as e:
            ended_at = datetime.now()
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout=e.stdout or "" if hasattr(e, 'stdout') else "",
                stderr=f"Execution timed out after {self.timeout_seconds} seconds",
                duration_seconds=self.timeout_seconds,
                started_at=started_at,
                ended_at=ended_at,
            )

        except FileNotFoundError:
            ended_at = datetime.now()
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Executor command not found: {self.command}",
                duration_seconds=0,
                started_at=started_at,
                ended_at=ended_at,
            )

        except Exception as e:
            ended_at = datetime.now()
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                duration_seconds=(ended_at - started_at).total_seconds(),
                started_at=started_at,
                ended_at=ended_at,
            )

    def is_available(self) -> bool:
        """Check if the executor command is available."""
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False


class ManualExecutorClient(ExecutorClient):
    """
    Executor client for manual workflow with Claude Code.

    Instead of calling CLI directly, it:
    1. Saves the prompt to a file
    2. Waits for manual execution
    3. Reads the response from a file
    """

    def __init__(
        self,
        prompts_dir: Path = Path("workspace/prompts"),
        responses_dir: Path = Path("workspace/prompts"),
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.prompts_dir = prompts_dir
        self.responses_dir = responses_dir
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        prompt: str,
        run_id: str,
        iteration: int,
    ) -> ExecutionResult:
        """
        Prepare execution by saving prompt file.

        The user should:
        1. Copy the prompt from the file
        2. Run claude code manually
        3. Copy the output to response file
        4. Resume the run
        """
        started_at = datetime.now()

        # Save prompt to file
        prompt_file = self.prompts_dir / f"executor_{run_id}_iter{iteration}.txt"
        prompt_file.write_text(self._format_prompt(prompt), encoding="utf-8")

        # Check for response file
        response_file = self.responses_dir / f"executor_{run_id}_iter{iteration}_response.txt"

        if response_file.exists():
            # Response available, read and process
            response = response_file.read_text(encoding="utf-8")
            response_file.unlink()  # Remove after reading

            ended_at = datetime.now()
            return ExecutionResult(
                success=True,
                exit_code=0,
                stdout=response,
                stderr="",
                duration_seconds=(ended_at - started_at).total_seconds(),
                started_at=started_at,
                ended_at=ended_at,
            )

        # No response yet - return pending status
        return ExecutionResult(
            success=False,
            exit_code=-2,  # Special code for "pending"
            stdout="",
            stderr=f"PENDING: Execute manually and save response to {response_file}",
            duration_seconds=0,
            started_at=started_at,
            ended_at=None,
        )

    def _format_prompt(self, prompt: str) -> str:
        """Format prompt with instructions for manual use."""
        return f"""
═══════════════════════════════════════════════════════════════
MANUAL EXECUTOR WORKFLOW
═══════════════════════════════════════════════════════════════

1. Copy the prompt below (or use this file with claude CLI)
2. Run: claude < this_file.txt
3. Copy the output
4. Save to the response file indicated in the error
5. Run: python -m orchestrator.main resume --run-id <id>

═══════════════════════════════════════════════════════════════
PROMPT:
═══════════════════════════════════════════════════════════════

{prompt}
"""

    def get_pending_response_path(self, run_id: str, iteration: int) -> Path:
        """Get path where response should be saved."""
        return self.responses_dir / f"executor_{run_id}_iter{iteration}_response.txt"
