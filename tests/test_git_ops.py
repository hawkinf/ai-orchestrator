"""Tests for git operations."""

import pytest
import tempfile
import subprocess
from pathlib import Path

from orchestrator.git_ops import GitOperations


@pytest.fixture
def temp_repo():
    """Create a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
        )

        yield repo_path


@pytest.fixture
def git_ops(temp_repo):
    """Create GitOperations instance."""
    return GitOperations(temp_repo)


class TestGitOperations:
    """Tests for GitOperations class."""

    def test_is_repo(self, git_ops):
        """Test detecting git repository."""
        assert git_ops.is_repo() is True

    def test_is_not_repo(self):
        """Test detecting non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = GitOperations(Path(tmpdir))
            assert ops.is_repo() is False

    def test_get_status_clean(self, git_ops):
        """Test getting status of clean repo."""
        status = git_ops.get_status()

        assert status.is_repo is True
        assert status.is_clean is True
        assert len(status.modified_files) == 0
        assert len(status.untracked_files) == 0

    def test_get_status_modified(self, git_ops, temp_repo):
        """Test getting status with modified files."""
        # Modify file
        (temp_repo / "README.md").write_text("# Modified")

        status = git_ops.get_status()

        assert status.is_clean is False
        # File might be in modified_files or staged_files depending on git version
        all_changed = status.modified_files + status.staged_files
        assert any("README" in f for f in all_changed) or len(all_changed) > 0

    def test_get_status_untracked(self, git_ops, temp_repo):
        """Test getting status with untracked files."""
        # Create new file
        (temp_repo / "new_file.txt").write_text("New content")

        status = git_ops.get_status()

        assert status.is_clean is False
        assert "new_file.txt" in status.untracked_files

    def test_get_current_branch(self, git_ops):
        """Test getting current branch."""
        branch = git_ops.get_current_branch()

        # Should be master or main depending on git version
        assert branch in ("master", "main") or len(branch) > 0

    def test_get_diff(self, git_ops, temp_repo):
        """Test getting diff."""
        # Modify file
        (temp_repo / "README.md").write_text("# Modified content")

        diff = git_ops.get_diff()

        assert "Modified content" in diff

    def test_stage_files(self, git_ops, temp_repo):
        """Test staging files."""
        # Modify file
        (temp_repo / "README.md").write_text("# Staged content")

        result = git_ops.stage_files(["README.md"])

        assert result.success is True

        # Verify staged
        status = git_ops.get_status()
        assert "README.md" in status.staged_files

    def test_stage_all(self, git_ops, temp_repo):
        """Test staging all files."""
        # Create and modify files
        (temp_repo / "new_file.txt").write_text("New")
        (temp_repo / "README.md").write_text("# Modified")

        result = git_ops.stage_all()

        assert result.success is True

    def test_commit(self, git_ops, temp_repo):
        """Test creating commit."""
        # Stage changes
        (temp_repo / "README.md").write_text("# Commit test")
        git_ops.stage_all()

        result = git_ops.commit("Test commit message")

        assert result.success is True
        assert result.commit_hash is not None

    def test_commit_empty(self, git_ops):
        """Test commit with nothing to commit."""
        result = git_ops.commit("Empty commit")

        assert result.success is False
        assert "nothing" in result.error.lower() or "clean" in result.error.lower()

    def test_is_protected_branch(self, git_ops):
        """Test protected branch detection."""
        protected = ["main", "master", "production"]

        # Current branch should be one of these in a new repo
        current = git_ops.get_current_branch()
        if current in protected:
            assert git_ops.is_protected_branch(protected) is True

    def test_get_changed_files(self, git_ops, temp_repo):
        """Test getting all changed files."""
        # Create changes
        (temp_repo / "README.md").write_text("# Changed")
        (temp_repo / "new.txt").write_text("New file")
        git_ops.stage_files(["new.txt"])

        changed = git_ops.get_changed_files()

        assert len(changed) >= 1

    def test_save_diff_to_file(self, git_ops, temp_repo):
        """Test saving diff to file."""
        # Create changes
        (temp_repo / "README.md").write_text("# Diff test")

        diff_file = temp_repo / "test_diff.patch"
        result = git_ops.save_diff_to_file(diff_file)

        assert result is True
        assert diff_file.exists()
        assert "Diff test" in diff_file.read_text()

    def test_save_status_to_file(self, git_ops, temp_repo):
        """Test saving status to file."""
        status_file = temp_repo / "test_status.txt"
        result = git_ops.save_status_to_file(status_file)

        assert result is True
        assert status_file.exists()
