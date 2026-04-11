"""Git operations for the orchestrator."""

import subprocess
from pathlib import Path
from typing import Optional

from .models import GitResult, GitStatus


class GitOperations:
    """
    Git repository operations.

    Provides safe wrappers around git commands with proper error handling.
    """

    def __init__(self, repo_path: Path, timeout: int = 60):
        self.repo_path = repo_path
        self.timeout = timeout

    def _run_git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        """
        Run a git command.

        Args:
            *args: Git command arguments
            check: Whether to raise on non-zero exit

        Returns:
            CompletedProcess instance
        """
        cmd = ["git", *args]
        return subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=check,
        )

    def is_repo(self) -> bool:
        """Check if path is a git repository."""
        try:
            result = self._run_git("rev-parse", "--git-dir")
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_status(self) -> GitStatus:
        """
        Get comprehensive git status.

        Returns:
            GitStatus with current repo state
        """
        if not self.is_repo():
            return GitStatus(is_repo=False)

        status = GitStatus(is_repo=True)

        # Get branch
        try:
            result = self._run_git("branch", "--show-current")
            status.branch = result.stdout.strip()
        except subprocess.SubprocessError:
            status.branch = "unknown"

        # Get file status
        try:
            result = self._run_git("status", "--porcelain")
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

            for line in lines:
                if len(line) < 3:
                    continue
                xy = line[:2]
                filepath = line[3:]

                if xy[0] in "MADRCT":
                    status.staged_files.append(filepath)
                if xy[1] in "MD":
                    status.modified_files.append(filepath)
                if xy == "??":
                    status.untracked_files.append(filepath)

            status.is_clean = len(lines) == 0
        except subprocess.SubprocessError:
            pass

        # Get ahead/behind
        try:
            result = self._run_git("rev-list", "--left-right", "--count", "@{u}...HEAD")
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    status.behind = int(parts[0])
                    status.ahead = int(parts[1])
        except (subprocess.SubprocessError, ValueError):
            pass

        return status

    def get_diff(self, staged: bool = False) -> str:
        """
        Get git diff.

        Args:
            staged: If True, get staged changes only

        Returns:
            Diff output
        """
        try:
            args = ["diff"]
            if staged:
                args.append("--staged")
            result = self._run_git(*args)
            return result.stdout
        except subprocess.SubprocessError:
            return ""

    def get_diff_summary(self) -> str:
        """Get a summary of changes (stat format)."""
        try:
            result = self._run_git("diff", "--stat")
            staged = self._run_git("diff", "--staged", "--stat")
            return f"Unstaged:\n{result.stdout}\nStaged:\n{staged.stdout}"
        except subprocess.SubprocessError:
            return ""

    def stage_files(self, files: list[str]) -> GitResult:
        """
        Stage files for commit.

        Args:
            files: List of file paths to stage

        Returns:
            GitResult with operation status
        """
        if not files:
            return GitResult(
                operation="add",
                success=False,
                error="No files specified"
            )

        try:
            result = self._run_git("add", *files)
            return GitResult(
                operation="add",
                success=result.returncode == 0,
                message=f"Staged {len(files)} files",
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.SubprocessError as e:
            return GitResult(operation="add", success=False, error=str(e))

    def stage_all(self) -> GitResult:
        """Stage all changes."""
        try:
            result = self._run_git("add", "-A")
            return GitResult(
                operation="add",
                success=result.returncode == 0,
                message="Staged all changes",
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.SubprocessError as e:
            return GitResult(operation="add", success=False, error=str(e))

    def commit(self, message: str) -> GitResult:
        """
        Create a commit.

        Args:
            message: Commit message

        Returns:
            GitResult with commit hash on success
        """
        if not message:
            return GitResult(operation="commit", success=False, error="Empty commit message")

        # Check if there's anything to commit
        status = self.get_status()
        if status.is_clean:
            return GitResult(
                operation="commit",
                success=False,
                error="Nothing to commit (working tree clean)"
            )

        try:
            result = self._run_git("commit", "-m", message)
            if result.returncode == 0:
                # Get commit hash
                hash_result = self._run_git("rev-parse", "HEAD")
                commit_hash = hash_result.stdout.strip()[:8]
                return GitResult(
                    operation="commit",
                    success=True,
                    message=f"Committed: {commit_hash}",
                    commit_hash=commit_hash,
                )
            return GitResult(
                operation="commit",
                success=False,
                error=result.stderr or result.stdout,
            )
        except subprocess.SubprocessError as e:
            return GitResult(operation="commit", success=False, error=str(e))

    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        set_upstream: bool = False,
    ) -> GitResult:
        """
        Push commits to remote.

        Args:
            remote: Remote name
            branch: Branch name (uses current if None)
            set_upstream: Whether to set upstream tracking

        Returns:
            GitResult with operation status
        """
        try:
            args = ["push"]
            if set_upstream:
                args.append("-u")
            args.append(remote)
            if branch:
                args.append(branch)

            result = self._run_git(*args)
            if result.returncode == 0:
                return GitResult(
                    operation="push",
                    success=True,
                    message=f"Pushed to {remote}",
                )
            return GitResult(
                operation="push",
                success=False,
                error=result.stderr or result.stdout,
            )
        except subprocess.SubprocessError as e:
            return GitResult(operation="push", success=False, error=str(e))

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        """
        Pull from remote.

        Args:
            remote: Remote name
            branch: Branch name

        Returns:
            GitResult with operation status
        """
        try:
            args = ["pull", remote]
            if branch:
                args.append(branch)

            result = self._run_git(*args)
            return GitResult(
                operation="pull",
                success=result.returncode == 0,
                message=result.stdout if result.returncode == 0 else None,
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.SubprocessError as e:
            return GitResult(operation="pull", success=False, error=str(e))

    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            result = self._run_git("branch", "--show-current")
            return result.stdout.strip() or "HEAD"
        except subprocess.SubprocessError:
            return "unknown"

    def is_protected_branch(self, protected: list[str]) -> bool:
        """Check if current branch is in protected list."""
        current = self.get_current_branch()
        return current in protected

    def get_changed_files(self) -> list[str]:
        """Get list of all changed files (staged + unstaged)."""
        status = self.get_status()
        all_files = set()
        all_files.update(status.staged_files)
        all_files.update(status.modified_files)
        return list(all_files)

    def save_diff_to_file(self, filepath: Path) -> bool:
        """
        Save current diff to a file.

        Args:
            filepath: Path to save diff

        Returns:
            True if saved successfully
        """
        try:
            diff = self.get_diff()
            staged_diff = self.get_diff(staged=True)
            content = f"=== UNSTAGED CHANGES ===\n{diff}\n\n=== STAGED CHANGES ===\n{staged_diff}"
            filepath.write_text(content, encoding="utf-8")
            return True
        except (subprocess.SubprocessError, IOError):
            return False

    def save_status_to_file(self, filepath: Path) -> bool:
        """
        Save git status to a file.

        Args:
            filepath: Path to save status

        Returns:
            True if saved successfully
        """
        try:
            result = self._run_git("status")
            filepath.write_text(result.stdout, encoding="utf-8")
            return True
        except (subprocess.SubprocessError, IOError):
            return False
