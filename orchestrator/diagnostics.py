"""System diagnostics for AI Orchestrator.

Provides comprehensive health checks for all system components.
This module contains the core logic - GUI should only visualize results.
"""

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

logger = logging.getLogger("ai_orchestrator.diagnostics")


class DiagnosticStatus(Enum):
    """Status of a diagnostic check."""
    NOT_TESTED = "not_tested"
    RUNNING = "running"
    OK = "ok"
    WARNING = "warning"
    FAILED = "failed"
    CRITICAL = "critical"


class CheckCategory(Enum):
    """Category of diagnostic checks."""
    OPENAI = "openai"
    CLAUDE = "claude"
    CONFIG = "config"
    WORKSPACE = "workspace"
    PROJECT = "project"
    GIT = "git"
    VALIDATION = "validation"
    ENVIRONMENT = "environment"
    CORE = "core"


@dataclass
class DiagnosticCheckResult:
    """Result of a single diagnostic check."""
    key: str
    title: str
    category: CheckCategory
    status: DiagnosticStatus
    summary: str
    details: List[str] = field(default_factory=list)
    recommendation: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    is_critical: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "title": self.title,
            "category": self.category.value,
            "status": self.status.value,
            "summary": self.summary,
            "details": self.details,
            "recommendation": self.recommendation,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "is_critical": self.is_critical,
        }


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_status: DiagnosticStatus = DiagnosticStatus.NOT_TESTED
    checks: List[DiagnosticCheckResult] = field(default_factory=list)
    environment_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "environment_summary": self.environment_summary,
        }

    def to_markdown(self) -> str:
        """Convert to markdown report."""
        lines = [
            "# AI Orchestrator - Diagnostic Report",
            "",
            f"**Generated:** {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Overall Status:** {self.overall_status.value.upper()}",
            "",
            "---",
            "",
            "## Environment Summary",
            "",
        ]

        for key, value in self.environment_summary.items():
            lines.append(f"- **{key}:** {value}")

        lines.extend(["", "---", "", "## Check Results", ""])

        for check in self.checks:
            status_icon = {
                DiagnosticStatus.OK: "[OK]",
                DiagnosticStatus.WARNING: "[WARN]",
                DiagnosticStatus.FAILED: "[FAIL]",
                DiagnosticStatus.CRITICAL: "[CRIT]",
                DiagnosticStatus.NOT_TESTED: "[----]",
                DiagnosticStatus.RUNNING: "[....]",
            }.get(check.status, "[????]")

            lines.append(f"### {status_icon} {check.title}")
            lines.append("")
            lines.append(f"**Category:** {check.category.value}")
            lines.append(f"**Summary:** {check.summary}")

            if check.details:
                lines.append("")
                lines.append("**Details:**")
                for detail in check.details:
                    lines.append(f"- {detail}")

            if check.recommendation:
                lines.append("")
                lines.append(f"**Recommendation:** {check.recommendation}")

            lines.append("")

        return "\n".join(lines)

    def compute_overall_status(self):
        """Compute overall status from check results."""
        if not self.checks:
            self.overall_status = DiagnosticStatus.NOT_TESTED
            return

        statuses = [c.status for c in self.checks]

        if DiagnosticStatus.CRITICAL in statuses:
            self.overall_status = DiagnosticStatus.CRITICAL
        elif any(c.status == DiagnosticStatus.FAILED and c.is_critical for c in self.checks):
            self.overall_status = DiagnosticStatus.CRITICAL
        elif DiagnosticStatus.FAILED in statuses:
            self.overall_status = DiagnosticStatus.FAILED
        elif DiagnosticStatus.WARNING in statuses:
            self.overall_status = DiagnosticStatus.WARNING
        elif DiagnosticStatus.RUNNING in statuses:
            self.overall_status = DiagnosticStatus.RUNNING
        elif all(s == DiagnosticStatus.OK for s in statuses):
            self.overall_status = DiagnosticStatus.OK
        else:
            self.overall_status = DiagnosticStatus.NOT_TESTED


class SystemDiagnostics:
    """
    Runs diagnostic checks for all system components.

    Usage:
        diag = SystemDiagnostics(config, paths)
        report = diag.run_all()
        # or
        result = diag.check_openai()
    """

    def __init__(
        self,
        config=None,
        paths=None,
        project_path: Optional[Path] = None,
    ):
        self.config = config
        self.paths = paths
        self.project_path = project_path or (paths.project_root if paths else Path.cwd())
        self._cancelled = False

    def cancel(self):
        """Cancel running diagnostics."""
        self._cancelled = True

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 10,
        cwd: Optional[Path] = None
    ) -> tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                shell=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return -3, "", str(e)

    # -------------------------------------------------------------------------
    # OpenAI Checks
    # -------------------------------------------------------------------------

    def check_openai(self) -> DiagnosticCheckResult:
        """Check OpenAI API configuration and connectivity."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            from .env_file import get_env_resolution, mask_secret

            # Check key resolution
            env_path = self.project_path / ".env" if self.project_path else None
            resolution = get_env_resolution("OPENAI_API_KEY", env_path)

            if resolution.source == "none":
                status = DiagnosticStatus.CRITICAL
                summary = "API key not found"
                details.append("OPENAI_API_KEY not found in environment or .env")
                recommendation = "Set OPENAI_API_KEY in environment variables or create a .env file"
            elif not resolution.value or not resolution.value.strip():
                status = DiagnosticStatus.CRITICAL
                summary = "API key is empty"
                details.append(f"Source: {resolution.source}")
                details.append("Key value is empty or whitespace")
                recommendation = "Set a valid OPENAI_API_KEY value"
            else:
                key_preview = mask_secret(resolution.value)
                details.append(f"Source: {resolution.source}")
                details.append(f"Key: {key_preview}")

                # Try to initialize client
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=resolution.value)
                    details.append("Client initialized successfully")

                    # Quick connectivity test (optional - don't fail if rate limited)
                    try:
                        import httpx
                        client_with_timeout = OpenAI(
                            api_key=resolution.value,
                            timeout=httpx.Timeout(5.0)
                        )
                        models = client_with_timeout.models.list()
                        model_count = len(list(models))
                        details.append(f"API connection OK ({model_count} models available)")
                        status = DiagnosticStatus.OK
                        summary = f"Connected ({resolution.source})"
                    except Exception as conn_err:
                        # Connection failed but client initialized
                        err_msg = str(conn_err)
                        if "rate" in err_msg.lower():
                            status = DiagnosticStatus.WARNING
                            summary = "Rate limited (key valid)"
                            details.append("Rate limit hit during test")
                            recommendation = "Wait a few minutes before running tasks"
                        elif "auth" in err_msg.lower() or "401" in err_msg:
                            status = DiagnosticStatus.CRITICAL
                            summary = "Invalid API key"
                            details.append("Authentication failed")
                            recommendation = "Check that your API key is valid and not revoked"
                        else:
                            status = DiagnosticStatus.WARNING
                            summary = "Client OK, network issue"
                            details.append(f"Connection error: {err_msg[:100]}")
                            recommendation = "Check internet connection and firewall"

                except ImportError:
                    status = DiagnosticStatus.CRITICAL
                    summary = "OpenAI library not installed"
                    details.append("pip install openai required")
                    recommendation = "Run: pip install openai"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="openai",
            title="OpenAI API",
            category=CheckCategory.OPENAI,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=True,
        )

    # -------------------------------------------------------------------------
    # Claude Executor Checks
    # -------------------------------------------------------------------------

    def check_claude_executor(self) -> DiagnosticCheckResult:
        """Check Claude Code CLI availability."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            # Get configured command
            executor_cmd = "claude"
            if self.config and hasattr(self.config, "executor"):
                executor_cmd = getattr(self.config.executor, "command", "claude")

            details.append(f"Configured command: {executor_cmd}")

            # Check if command exists in PATH
            cmd_path = shutil.which(executor_cmd)

            if cmd_path:
                details.append(f"Found at: {cmd_path}")

                # Try to get version
                returncode, stdout, stderr = self._run_command(
                    [executor_cmd, "--version"],
                    timeout=10
                )

                if returncode == 0:
                    version = stdout.strip() or stderr.strip()
                    if version:
                        details.append(f"Version: {version[:100]}")
                    status = DiagnosticStatus.OK
                    summary = "Available"
                elif returncode == -1:
                    status = DiagnosticStatus.WARNING
                    summary = "Found but slow"
                    details.append("Command timed out getting version")
                else:
                    # Command exists but --version failed
                    # This might be OK for some tools
                    status = DiagnosticStatus.OK
                    summary = "Available (no version info)"
                    details.append("Could not get version info")
            else:
                status = DiagnosticStatus.CRITICAL
                summary = "Not found in PATH"
                details.append(f"'{executor_cmd}' not found in system PATH")
                recommendation = f"Install Claude Code CLI or check that '{executor_cmd}' is in your PATH"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="claude_executor",
            title="Claude Executor",
            category=CheckCategory.CLAUDE,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=True,
        )

    # -------------------------------------------------------------------------
    # Configuration Checks
    # -------------------------------------------------------------------------

    def check_config(self) -> DiagnosticCheckResult:
        """Check configuration file and settings."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            # Check if config exists
            config_path = self.project_path / "config.yaml"

            if not config_path.exists():
                # Also check workspace
                if self.paths:
                    config_path = self.paths.workspace_root / "config.yaml"

            if config_path.exists():
                details.append(f"Config file: {config_path}")

                # Try to load config
                try:
                    from .config import load_config
                    loaded_config = load_config(config_path)

                    # Check required fields
                    issues = []

                    if not getattr(loaded_config, "project_path", None):
                        issues.append("project_path not set")

                    if not getattr(loaded_config, "workspace_path", None):
                        issues.append("workspace_path not set")

                    max_iter = getattr(loaded_config, "max_iterations", 0)
                    if max_iter <= 0:
                        issues.append("max_iterations should be > 0")

                    timeout = getattr(loaded_config, "iteration_timeout_seconds", 0)
                    if timeout <= 0:
                        issues.append("iteration_timeout_seconds should be > 0")

                    # Check profile
                    active_profile = getattr(loaded_config, "active_profile", None)
                    if active_profile:
                        details.append(f"Active profile: {active_profile}")
                        profiles = getattr(loaded_config, "profiles", {})
                        if active_profile not in profiles:
                            issues.append(f"Profile '{active_profile}' not defined in profiles")
                    else:
                        details.append("No active profile set")

                    if issues:
                        status = DiagnosticStatus.WARNING
                        summary = f"{len(issues)} issue(s)"
                        details.extend([f"Issue: {i}" for i in issues])
                        recommendation = "Review config.yaml settings"
                    else:
                        status = DiagnosticStatus.OK
                        summary = "Valid"
                        details.append("All required fields present")

                except Exception as load_err:
                    status = DiagnosticStatus.FAILED
                    summary = "Load error"
                    details.append(f"Error loading config: {str(load_err)}")
                    recommendation = "Check config.yaml syntax (YAML format)"

            else:
                status = DiagnosticStatus.WARNING
                summary = "Not found"
                details.append("config.yaml not found in project or workspace")
                recommendation = "Create config.yaml from config.yaml.example"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="config",
            title="Configuration",
            category=CheckCategory.CONFIG,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=False,
        )

    # -------------------------------------------------------------------------
    # Workspace Checks
    # -------------------------------------------------------------------------

    def check_workspace(self) -> DiagnosticCheckResult:
        """Check workspace directories and permissions."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            workspace_root = None

            if self.paths:
                workspace_root = self.paths.workspace_root
            else:
                workspace_root = self.project_path / "workspace"

            details.append(f"Workspace: {workspace_root}")

            issues = []
            created = []

            # Check/create directories
            dirs_to_check = [
                workspace_root,
                workspace_root / "runs",
                workspace_root / "logs",
                workspace_root / "state",
            ]

            for dir_path in dirs_to_check:
                if dir_path.exists():
                    details.append(f"[OK] {dir_path.name}/")
                else:
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        created.append(dir_path.name)
                        details.append(f"[CREATED] {dir_path.name}/")
                    except PermissionError:
                        issues.append(f"Cannot create {dir_path.name}/")
                    except Exception as e:
                        issues.append(f"Error creating {dir_path.name}/: {e}")

            # Check write permissions
            test_file = workspace_root / "logs" / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                details.append("Write permission: OK")
            except Exception as write_err:
                issues.append(f"Cannot write to logs/: {write_err}")

            if issues:
                status = DiagnosticStatus.FAILED
                summary = f"{len(issues)} permission issue(s)"
                details.extend([f"Error: {i}" for i in issues])
                recommendation = "Check directory permissions"
            elif created:
                status = DiagnosticStatus.OK
                summary = f"OK ({len(created)} created)"
            else:
                status = DiagnosticStatus.OK
                summary = "Ready"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="workspace",
            title="Workspace",
            category=CheckCategory.WORKSPACE,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=True,
        )

    # -------------------------------------------------------------------------
    # Project Path Checks
    # -------------------------------------------------------------------------

    def check_project_path(self) -> DiagnosticCheckResult:
        """Check project directory and structure."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            project_path = self.project_path
            details.append(f"Project path: {project_path}")

            if not project_path.exists():
                status = DiagnosticStatus.CRITICAL
                summary = "Path does not exist"
                recommendation = "Check project_path in config"
            elif not project_path.is_dir():
                status = DiagnosticStatus.CRITICAL
                summary = "Not a directory"
                recommendation = "project_path must be a directory"
            else:
                details.append("Directory exists")

                # Detect project type
                profile = None
                if self.config:
                    profile = getattr(self.config, "active_profile", None)

                project_type = profile or "generic"
                details.append(f"Profile: {project_type}")

                # Check profile-specific markers
                if project_type == "flutter":
                    pubspec = project_path / "pubspec.yaml"
                    if pubspec.exists():
                        details.append("[OK] pubspec.yaml found")
                        # Check flutter command
                        flutter_path = shutil.which("flutter")
                        if flutter_path:
                            details.append(f"[OK] flutter at: {flutter_path}")
                            status = DiagnosticStatus.OK
                            summary = "Flutter project ready"
                        else:
                            status = DiagnosticStatus.WARNING
                            summary = "Flutter project (flutter not in PATH)"
                            recommendation = "Install Flutter SDK and add to PATH"
                    else:
                        status = DiagnosticStatus.WARNING
                        summary = "Flutter project (no pubspec.yaml)"
                        recommendation = "Verify this is a Flutter project"

                elif project_type == "python":
                    markers = ["pyproject.toml", "requirements.txt", "setup.py"]
                    found = [m for m in markers if (project_path / m).exists()]

                    if found:
                        details.append(f"[OK] Found: {', '.join(found)}")
                        python_path = shutil.which("python") or shutil.which("python3")
                        if python_path:
                            details.append(f"[OK] python at: {python_path}")
                            status = DiagnosticStatus.OK
                            summary = "Python project ready"
                        else:
                            status = DiagnosticStatus.WARNING
                            summary = "Python project (python not in PATH)"
                            recommendation = "Install Python and add to PATH"
                    else:
                        status = DiagnosticStatus.WARNING
                        summary = "Python project (no markers)"
                        recommendation = "Add pyproject.toml or requirements.txt"

                else:  # generic
                    status = DiagnosticStatus.OK
                    summary = "Generic project"
                    details.append("No specific project markers required")

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="project_path",
            title="Project Directory",
            category=CheckCategory.PROJECT,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=False,
        )

    # -------------------------------------------------------------------------
    # Git Checks
    # -------------------------------------------------------------------------

    def check_git(self) -> DiagnosticCheckResult:
        """Check Git availability and repository status."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            # Check git in PATH
            git_path = shutil.which("git")

            if not git_path:
                status = DiagnosticStatus.CRITICAL
                summary = "Git not found"
                recommendation = "Install Git and add to PATH"
                return DiagnosticCheckResult(
                    key="git",
                    title="Git",
                    category=CheckCategory.GIT,
                    status=status,
                    summary=summary,
                    details=details,
                    recommendation=recommendation,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_critical=True,
                )

            details.append(f"Git found: {git_path}")

            # Check if project is a git repo
            returncode, stdout, stderr = self._run_command(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.project_path
            )

            if returncode != 0:
                status = DiagnosticStatus.WARNING
                summary = "Not a git repository"
                recommendation = "Initialize with: git init"
            else:
                details.append("Inside git repository")

                # Get branch
                returncode, stdout, _ = self._run_command(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_path
                )
                if returncode == 0 and stdout.strip():
                    branch = stdout.strip()
                    details.append(f"Branch: {branch}")

                # Get remote
                returncode, stdout, _ = self._run_command(
                    ["git", "remote", "-v"],
                    cwd=self.project_path
                )
                if returncode == 0 and stdout.strip():
                    remotes = stdout.strip().split("\n")
                    if remotes:
                        details.append(f"Remote: {remotes[0][:80]}")
                else:
                    details.append("No remote configured")

                # Check working tree status
                returncode, stdout, _ = self._run_command(
                    ["git", "status", "--porcelain"],
                    cwd=self.project_path
                )
                if returncode == 0:
                    changes = len([l for l in stdout.strip().split("\n") if l])
                    if changes > 0:
                        details.append(f"Working tree: {changes} changes")
                    else:
                        details.append("Working tree: clean")

                status = DiagnosticStatus.OK
                summary = "Ready"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="git",
            title="Git",
            category=CheckCategory.GIT,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=True,
        )

    # -------------------------------------------------------------------------
    # Validation Commands Checks
    # -------------------------------------------------------------------------

    def check_validation_commands(self) -> DiagnosticCheckResult:
        """Check configured validation commands."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            commands = []

            # Get commands from config
            if self.config:
                active_profile = getattr(self.config, "active_profile", None)
                profiles = getattr(self.config, "profiles", {})

                if active_profile and active_profile in profiles:
                    profile_config = profiles[active_profile]
                    if hasattr(profile_config, "validation_commands"):
                        commands = profile_config.validation_commands
                    elif isinstance(profile_config, dict):
                        commands = profile_config.get("validation_commands", [])

                details.append(f"Profile: {active_profile or 'none'}")
                details.append(f"Commands configured: {len(commands)}")

            if not commands:
                status = DiagnosticStatus.WARNING
                summary = "No commands configured"
                recommendation = "Add validation_commands to your profile in config.yaml"
            else:
                issues = []
                valid = []

                for cmd in commands:
                    # Extract command name (first word)
                    cmd_name = cmd.split()[0] if isinstance(cmd, str) else str(cmd)
                    cmd_path = shutil.which(cmd_name)

                    if cmd_path:
                        valid.append(cmd_name)
                        details.append(f"[OK] {cmd_name}")
                    else:
                        issues.append(cmd_name)
                        details.append(f"[NOT FOUND] {cmd_name}")

                if issues:
                    status = DiagnosticStatus.WARNING
                    summary = f"{len(valid)}/{len(commands)} available"
                    recommendation = f"Install missing commands: {', '.join(issues)}"
                else:
                    status = DiagnosticStatus.OK
                    summary = f"All {len(commands)} ready"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="validation_commands",
            title="Validation Commands",
            category=CheckCategory.VALIDATION,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=False,
        )

    # -------------------------------------------------------------------------
    # Environment Checks
    # -------------------------------------------------------------------------

    def check_env_resolution(self) -> DiagnosticCheckResult:
        """Check .env file and environment variables."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        try:
            from .env_file import get_env_resolution, mask_secret

            env_path = self.project_path / ".env"

            # Check .env file
            if env_path.exists():
                details.append(f".env file: {env_path}")

                # Read and check for conflicts
                env_in_file = False
                try:
                    content = env_path.read_text()
                    if "OPENAI_API_KEY" in content:
                        env_in_file = True
                        details.append("OPENAI_API_KEY defined in .env")
                except Exception:
                    pass

                # Check environment variable
                env_in_system = os.environ.get("OPENAI_API_KEY")

                if env_in_file and env_in_system:
                    details.append("OPENAI_API_KEY also in system environment")
                    details.append("Priority: system environment (overrides .env)")
                    status = DiagnosticStatus.WARNING
                    summary = "Conflict detected"
                    recommendation = "Remove from one source to avoid confusion"
                elif env_in_file:
                    status = DiagnosticStatus.OK
                    summary = ".env configured"
                elif env_in_system:
                    status = DiagnosticStatus.OK
                    summary = "System env configured"
                else:
                    status = DiagnosticStatus.WARNING
                    summary = "No API key found"
                    recommendation = "Set OPENAI_API_KEY in .env or system environment"

            else:
                details.append(".env file not found")
                env_in_system = os.environ.get("OPENAI_API_KEY")

                if env_in_system:
                    details.append("OPENAI_API_KEY found in system environment")
                    status = DiagnosticStatus.OK
                    summary = "System env only"
                else:
                    status = DiagnosticStatus.WARNING
                    summary = "No .env, no system key"
                    recommendation = "Create .env file or set OPENAI_API_KEY environment variable"

        except Exception as e:
            status = DiagnosticStatus.FAILED
            summary = f"Check failed: {str(e)[:50]}"
            details.append(f"Error: {str(e)}")

        return DiagnosticCheckResult(
            key="env_resolution",
            title="Environment & .env",
            category=CheckCategory.ENVIRONMENT,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=False,
        )

    # -------------------------------------------------------------------------
    # Core Imports Check
    # -------------------------------------------------------------------------

    def check_core_imports(self) -> DiagnosticCheckResult:
        """Check that core orchestrator modules can be imported."""
        start_time = time.time()
        details = []
        status = DiagnosticStatus.NOT_TESTED
        summary = ""
        recommendation = None

        modules_to_check = [
            ("orchestrator.integrated_engine", "IntegratedTaskEngine"),
            ("orchestrator.state_store", "StateStore"),
            ("orchestrator.config", "load_config"),
            ("orchestrator.models", "TaskState"),
            ("orchestrator.git_ops", "GitOps"),
            ("orchestrator.validation", "ValidationRunner"),
            ("orchestrator.report_parser", "ReportParser"),
            ("orchestrator.env_validator", "EnvironmentValidator"),
        ]

        issues = []
        success = []

        for module_name, item_name in modules_to_check:
            try:
                module = __import__(module_name, fromlist=[item_name])
                getattr(module, item_name)
                success.append(item_name)
                details.append(f"[OK] {item_name}")
            except ImportError as e:
                issues.append(f"{item_name}: {str(e)[:50]}")
                details.append(f"[FAIL] {item_name}")
            except AttributeError:
                issues.append(f"{item_name}: not found in module")
                details.append(f"[FAIL] {item_name}")

        if issues:
            status = DiagnosticStatus.CRITICAL
            summary = f"{len(issues)} import failure(s)"
            recommendation = "Check installation: pip install -e ."
        else:
            status = DiagnosticStatus.OK
            summary = f"All {len(success)} modules OK"

        return DiagnosticCheckResult(
            key="core_imports",
            title="Core Modules",
            category=CheckCategory.CORE,
            status=status,
            summary=summary,
            details=details,
            recommendation=recommendation,
            duration_ms=int((time.time() - start_time) * 1000),
            is_critical=True,
        )

    # -------------------------------------------------------------------------
    # Run All Diagnostics
    # -------------------------------------------------------------------------

    def run_all(
        self,
        on_check_started: Optional[Callable[[str], None]] = None,
        on_check_completed: Optional[Callable[[DiagnosticCheckResult], None]] = None,
    ) -> DiagnosticReport:
        """
        Run all diagnostic checks.

        Args:
            on_check_started: Callback when a check starts (receives check key)
            on_check_completed: Callback when a check completes (receives result)

        Returns:
            Complete diagnostic report
        """
        report = DiagnosticReport(started_at=datetime.now())

        # Environment summary
        report.environment_summary = {
            "platform": os.name,
            "python": os.sys.version.split()[0],
            "project_path": str(self.project_path),
            "cwd": str(Path.cwd()),
        }

        # List of checks to run
        checks = [
            ("openai", self.check_openai),
            ("claude_executor", self.check_claude_executor),
            ("config", self.check_config),
            ("workspace", self.check_workspace),
            ("project_path", self.check_project_path),
            ("git", self.check_git),
            ("validation_commands", self.check_validation_commands),
            ("env_resolution", self.check_env_resolution),
            ("core_imports", self.check_core_imports),
        ]

        for check_key, check_fn in checks:
            if self._cancelled:
                break

            if on_check_started:
                on_check_started(check_key)

            try:
                result = check_fn()
                report.checks.append(result)

                if on_check_completed:
                    on_check_completed(result)

            except Exception as e:
                error_result = DiagnosticCheckResult(
                    key=check_key,
                    title=check_key.replace("_", " ").title(),
                    category=CheckCategory.CORE,
                    status=DiagnosticStatus.FAILED,
                    summary=f"Error: {str(e)[:50]}",
                    details=[f"Exception: {str(e)}"],
                )
                report.checks.append(error_result)

                if on_check_completed:
                    on_check_completed(error_result)

        report.completed_at = datetime.now()
        report.compute_overall_status()

        return report

    def run_single(self, check_key: str) -> Optional[DiagnosticCheckResult]:
        """Run a single diagnostic check by key."""
        check_map = {
            "openai": self.check_openai,
            "claude_executor": self.check_claude_executor,
            "config": self.check_config,
            "workspace": self.check_workspace,
            "project_path": self.check_project_path,
            "git": self.check_git,
            "validation_commands": self.check_validation_commands,
            "env_resolution": self.check_env_resolution,
            "core_imports": self.check_core_imports,
        }

        if check_key in check_map:
            return check_map[check_key]()
        return None


def get_check_definitions() -> List[dict]:
    """Get list of available checks with metadata."""
    return [
        {
            "key": "openai",
            "title": "OpenAI API",
            "category": "openai",
            "description": "Verifies API key configuration and connectivity",
            "is_critical": True,
        },
        {
            "key": "claude_executor",
            "title": "Claude Executor",
            "category": "claude",
            "description": "Checks Claude Code CLI availability",
            "is_critical": True,
        },
        {
            "key": "config",
            "title": "Configuration",
            "category": "config",
            "description": "Validates config.yaml structure and settings",
            "is_critical": False,
        },
        {
            "key": "workspace",
            "title": "Workspace",
            "category": "workspace",
            "description": "Checks workspace directories and permissions",
            "is_critical": True,
        },
        {
            "key": "project_path",
            "title": "Project Directory",
            "category": "project",
            "description": "Validates project structure for current profile",
            "is_critical": False,
        },
        {
            "key": "git",
            "title": "Git",
            "category": "git",
            "description": "Checks Git availability and repository status",
            "is_critical": True,
        },
        {
            "key": "validation_commands",
            "title": "Validation Commands",
            "category": "validation",
            "description": "Verifies configured validation commands exist",
            "is_critical": False,
        },
        {
            "key": "env_resolution",
            "title": "Environment & .env",
            "category": "environment",
            "description": "Checks environment variables and .env configuration",
            "is_critical": False,
        },
        {
            "key": "core_imports",
            "title": "Core Modules",
            "category": "core",
            "description": "Verifies orchestrator modules can be imported",
            "is_critical": True,
        },
    ]
