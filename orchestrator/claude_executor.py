"""Claude Code executor via subprocess."""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ExecutionResult
from .git_ops import GitOperations


class ClaudeExecutor:
    """
    Executes tasks using Claude Code CLI.

    Calls Claude via subprocess, captures output, and collects results.
    """

    def __init__(
        self,
        command: str = "claude",
        working_dir: Optional[Path] = None,
        timeout_seconds: int = 600,
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
        Execute a task with Claude Code.

        Args:
            prompt: Execution prompt for Claude
            run_id: Run identifier
            iteration: Current iteration number

        Returns:
            ExecutionResult with full execution details
        """
        started_at = datetime.now()

        # Get git status before execution
        git = GitOperations(self.working_dir)
        files_before = set(git.get_changed_files()) if git.is_repo() else set()

        try:
            # Execute Claude Code
            # Using -p flag for prompt, --yes for auto-accept
            result = subprocess.run(
                [self.command, "-p", prompt, "--yes"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=None,  # Inherit environment
            )

            ended_at = datetime.now()
            duration = (ended_at - started_at).total_seconds()

            # Get files changed after execution
            files_after = set(git.get_changed_files()) if git.is_repo() else set()
            files_changed = list(files_after - files_before) + list(files_after & files_before)

            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                files_changed=files_changed,
                commands_run=[f"{self.command} -p <prompt> --yes"],
                started_at=started_at,
                ended_at=ended_at,
            )

        except subprocess.TimeoutExpired as e:
            ended_at = datetime.now()
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = f"Execution timed out after {self.timeout_seconds} seconds"

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=self.timeout_seconds,
                files_changed=[],
                commands_run=[f"{self.command} -p <prompt> --yes (TIMEOUT)"],
                started_at=started_at,
                ended_at=ended_at,
            )

        except FileNotFoundError:
            ended_at = datetime.now()
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Claude command not found: {self.command}. "
                       f"Ensure Claude Code CLI is installed and in PATH.",
                duration_seconds=0,
                files_changed=[],
                commands_run=[],
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
                files_changed=[],
                commands_run=[],
                started_at=started_at,
                ended_at=ended_at,
            )

    def is_available(self) -> bool:
        """Check if Claude Code CLI is available."""
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_version(self) -> Optional[str]:
        """Get Claude Code CLI version."""
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None


class MockClaudeExecutor(ClaudeExecutor):
    """
    Mock executor for testing without Claude Code.

    Returns simulated responses based on prompt content.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.call_history = []

    def execute(
        self,
        prompt: str,
        run_id: str,
        iteration: int,
    ) -> ExecutionResult:
        """Return mock execution result."""
        started_at = datetime.now()
        time.sleep(0.1)  # Simulate some work
        ended_at = datetime.now()

        self.call_history.append({
            "prompt": prompt,
            "run_id": run_id,
            "iteration": iteration,
        })

        mock_response = f"""## 1. RESUMO
Mock execution for run {run_id}, iteration {iteration}. Task analyzed and simulated.

## 2. ARQUIVOS ALTERADOS
- mock_file.py - simulated changes

## 3. O QUE FOI FEITO
- Passo 1: Analyzed the task requirements
- Passo 2: Simulated code changes
- Passo 3: Generated mock response

## 4. VALIDAÇÕES EXECUTADAS
- mock test: passed

## 5. RESULTADO DAS VALIDAÇÕES
PASSOU - All mock validations passed

## 6. PENDÊNCIAS
Nenhuma pendência (mock)

## 7. RISCOS REMANESCENTES
Nenhum risco identificado (mock)

## 8. PRÓXIMO PASSO RECOMENDADO
Tarefa concluída - nenhum próximo passo necessário (mock)
"""

        return ExecutionResult(
            success=True,
            exit_code=0,
            stdout=mock_response,
            stderr="",
            duration_seconds=(ended_at - started_at).total_seconds(),
            files_changed=["mock_file.py"],
            commands_run=["mock_command"],
            started_at=started_at,
            ended_at=ended_at,
        )

    def is_available(self) -> bool:
        """Mock executor is always available."""
        return True
