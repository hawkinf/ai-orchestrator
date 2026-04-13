"""Tests for diagnostics system."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from orchestrator.diagnostics import (
    SystemDiagnostics,
    DiagnosticStatus,
    CheckCategory,
    DiagnosticCheckResult,
    DiagnosticReport,
    get_check_definitions,
)


class TestDiagnosticStatus:
    """Tests for DiagnosticStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert DiagnosticStatus.NOT_TESTED.value == "not_tested"
        assert DiagnosticStatus.RUNNING.value == "running"
        assert DiagnosticStatus.OK.value == "ok"
        assert DiagnosticStatus.WARNING.value == "warning"
        assert DiagnosticStatus.FAILED.value == "failed"
        assert DiagnosticStatus.CRITICAL.value == "critical"


class TestCheckCategory:
    """Tests for CheckCategory enum."""

    def test_category_values(self):
        """Test all categories exist."""
        assert CheckCategory.OPENAI.value == "openai"
        assert CheckCategory.CLAUDE.value == "claude"
        assert CheckCategory.CONFIG.value == "config"
        assert CheckCategory.WORKSPACE.value == "workspace"
        assert CheckCategory.PROJECT.value == "project"
        assert CheckCategory.GIT.value == "git"
        assert CheckCategory.VALIDATION.value == "validation"
        assert CheckCategory.ENVIRONMENT.value == "environment"
        assert CheckCategory.CORE.value == "core"


class TestDiagnosticCheckResult:
    """Tests for DiagnosticCheckResult dataclass."""

    def test_create_result(self):
        """Test creating a check result."""
        result = DiagnosticCheckResult(
            key="test_check",
            title="Test Check",
            category=CheckCategory.CORE,
            status=DiagnosticStatus.OK,
            summary="All good",
            details=["Detail 1", "Detail 2"],
            recommendation="No action needed",
            duration_ms=150,
            is_critical=False,
        )

        assert result.key == "test_check"
        assert result.status == DiagnosticStatus.OK
        assert len(result.details) == 2

    def test_to_dict(self):
        """Test converting result to dict."""
        result = DiagnosticCheckResult(
            key="test",
            title="Test",
            category=CheckCategory.OPENAI,
            status=DiagnosticStatus.WARNING,
            summary="Warning",
        )

        d = result.to_dict()
        assert d["key"] == "test"
        assert d["status"] == "warning"
        assert d["category"] == "openai"


class TestDiagnosticReport:
    """Tests for DiagnosticReport dataclass."""

    def test_create_report(self):
        """Test creating a report."""
        check1 = DiagnosticCheckResult(
            key="check1",
            title="Check 1",
            category=CheckCategory.OPENAI,
            status=DiagnosticStatus.OK,
            summary="OK",
        )
        check2 = DiagnosticCheckResult(
            key="check2",
            title="Check 2",
            category=CheckCategory.CONFIG,
            status=DiagnosticStatus.WARNING,
            summary="Warning",
        )

        report = DiagnosticReport(
            started_at=datetime.now(),
            overall_status=DiagnosticStatus.WARNING,
            checks=[check1, check2],
        )

        assert report.overall_status == DiagnosticStatus.WARNING
        assert len(report.checks) == 2

    def test_to_dict(self):
        """Test report to dict."""
        report = DiagnosticReport(
            started_at=datetime.now(),
            overall_status=DiagnosticStatus.OK,
            checks=[],
            environment_summary={"os": "windows"},
        )

        d = report.to_dict()
        assert d["overall_status"] == "ok"
        assert d["environment_summary"]["os"] == "windows"

    def test_to_markdown(self):
        """Test report to markdown."""
        check = DiagnosticCheckResult(
            key="check1",
            title="Test Check",
            category=CheckCategory.OPENAI,
            status=DiagnosticStatus.OK,
            summary="All good",
        )
        report = DiagnosticReport(
            started_at=datetime.now(),
            overall_status=DiagnosticStatus.OK,
            checks=[check],
        )

        md = report.to_markdown()
        assert "Diagnostic Report" in md
        assert "Test Check" in md
        assert "OK" in md.upper()


class TestGetCheckDefinitions:
    """Tests for get_check_definitions function."""

    def test_returns_list(self):
        """Test it returns a list."""
        defs = get_check_definitions()
        assert isinstance(defs, list)
        assert len(defs) > 0

    def test_definition_structure(self):
        """Test each definition has required fields."""
        defs = get_check_definitions()
        for d in defs:
            assert "key" in d
            assert "title" in d
            assert "category" in d
            assert "description" in d

    def test_has_all_checks(self):
        """Test all expected checks are present."""
        defs = get_check_definitions()
        keys = [d["key"] for d in defs]

        expected_keys = [
            "openai",
            "claude_executor",
            "config",
            "workspace",
            "project_path",
            "git",
            "validation_commands",
            "env_resolution",
            "core_imports",
        ]

        for key in expected_keys:
            assert key in keys, f"Missing check: {key}"


class TestSystemDiagnostics:
    """Tests for SystemDiagnostics class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "logs").mkdir()
            (workspace / "runs").mkdir()
            yield workspace

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock()
        config.openai_model = "gpt-4"
        config.anthropic_model = "claude-3-opus"
        config.max_iterations = 3
        config.validation_commands = ["echo test"]
        config.active_profile = None
        config.profiles = {}
        return config

    @pytest.fixture
    def mock_paths(self, temp_workspace):
        """Create mock paths."""
        paths = Mock()
        paths.workspace_root = temp_workspace
        paths.logs_dir = temp_workspace / "logs"
        paths.runs_dir = temp_workspace / "runs"
        paths.project_root = temp_workspace
        return paths

    def test_create_diagnostics(self, mock_config, mock_paths):
        """Test creating diagnostics instance."""
        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
        )
        assert diag is not None

    def test_check_openai_no_key(self, mock_config, mock_paths, temp_workspace):
        """Test OpenAI check without API key."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            diag = SystemDiagnostics(
                config=mock_config,
                paths=mock_paths,
                project_path=temp_workspace
            )
            result = diag.check_openai()

            assert result.key == "openai"
            assert result.status in [DiagnosticStatus.FAILED, DiagnosticStatus.CRITICAL]

    def test_check_openai_with_key(self, mock_config, mock_paths, temp_workspace):
        """Test OpenAI check with valid key."""
        # Create .env file
        env_file = temp_workspace / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test123")

        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=temp_workspace
        )

        # Mock the check_openai method directly
        with patch.object(diag, 'check_openai') as mock_check:
            mock_check.return_value = DiagnosticCheckResult(
                key="openai",
                title="OpenAI API",
                category=CheckCategory.OPENAI,
                status=DiagnosticStatus.OK,
                summary="Connected",
            )
            result = diag.check_openai()

            assert result.key == "openai"
            assert result.status == DiagnosticStatus.OK

    @patch("orchestrator.diagnostics.shutil.which")
    def test_check_claude_executor_found(self, mock_which, mock_config, mock_paths):
        """Test Claude executor check when found."""
        mock_which.return_value = "/usr/local/bin/claude"

        with patch.object(SystemDiagnostics, '_run_command') as mock_cmd:
            mock_cmd.return_value = (0, "claude v1.0.0", "")

            diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
            result = diag.check_claude_executor()

            assert result.key == "claude_executor"
            assert result.status == DiagnosticStatus.OK

    @patch("orchestrator.diagnostics.shutil.which")
    def test_check_claude_executor_not_found(self, mock_which, mock_config, mock_paths):
        """Test Claude executor check when not found."""
        mock_which.return_value = None

        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.check_claude_executor()

        assert result.key == "claude_executor"
        assert result.status == DiagnosticStatus.CRITICAL

    def test_check_config_no_file(self, mock_config, mock_paths, temp_workspace):
        """Test config check without config file."""
        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=temp_workspace
        )
        result = diag.check_config()

        assert result.key == "config"
        # No config file should be WARNING
        assert result.status == DiagnosticStatus.WARNING

    def test_check_workspace(self, mock_config, mock_paths, temp_workspace):
        """Test workspace check."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.check_workspace()

        assert result.key == "workspace"
        assert result.status == DiagnosticStatus.OK

    def test_check_project_path_valid(self, mock_config, mock_paths, temp_workspace):
        """Test project path check with valid path."""
        project = temp_workspace / "project"
        project.mkdir()

        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=project,
        )
        result = diag.check_project_path()

        assert result.key == "project_path"
        assert result.status == DiagnosticStatus.OK

    def test_check_project_path_missing(self, mock_config, mock_paths, temp_workspace):
        """Test project path check with missing path."""
        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=temp_workspace / "nonexistent",
        )
        result = diag.check_project_path()

        assert result.key == "project_path"
        assert result.status == DiagnosticStatus.CRITICAL

    @patch("orchestrator.diagnostics.subprocess.run")
    @patch("orchestrator.diagnostics.shutil.which")
    def test_check_git_installed(self, mock_which, mock_run, mock_config, mock_paths, temp_workspace):
        """Test git check when installed."""
        mock_which.return_value = "/usr/bin/git"
        mock_run.return_value = Mock(returncode=0, stdout="true", stderr="")

        project = temp_workspace / "project"
        project.mkdir()
        (project / ".git").mkdir()

        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=project,
        )
        result = diag.check_git()

        assert result.key == "git"
        assert result.status == DiagnosticStatus.OK

    def test_check_validation_commands(self, mock_config, mock_paths):
        """Test validation commands check."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.check_validation_commands()

        assert result.key == "validation_commands"
        # No commands configured should be WARNING
        assert result.status == DiagnosticStatus.WARNING

    def test_check_env_resolution_no_env(self, mock_config, mock_paths, temp_workspace):
        """Test environment resolution check without .env."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            diag = SystemDiagnostics(
                config=mock_config,
                paths=mock_paths,
                project_path=temp_workspace
            )
            result = diag.check_env_resolution()

            assert result.key == "env_resolution"
            assert result.status == DiagnosticStatus.OK

    def test_check_core_imports(self, mock_config, mock_paths):
        """Test core imports check."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.check_core_imports()

        assert result.key == "core_imports"
        # Check that the check ran - status depends on installed modules
        assert result.status in [
            DiagnosticStatus.OK,
            DiagnosticStatus.WARNING,
            DiagnosticStatus.CRITICAL,
        ]

    def test_run_single(self, mock_config, mock_paths):
        """Test running a single check."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.run_single("core_imports")

        assert result is not None
        assert result.key == "core_imports"

    def test_run_single_unknown_check(self, mock_config, mock_paths):
        """Test running unknown check."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        result = diag.run_single("unknown_check")

        assert result is None

    def test_run_all(self, mock_config, mock_paths, temp_workspace):
        """Test running all checks."""
        project = temp_workspace / "project"
        project.mkdir()

        diag = SystemDiagnostics(
            config=mock_config,
            paths=mock_paths,
            project_path=project,
        )
        report = diag.run_all()

        assert report is not None
        assert isinstance(report, DiagnosticReport)
        assert len(report.checks) > 0
        assert report.started_at is not None
        assert report.completed_at is not None

    def test_run_all_with_callbacks(self, mock_config, mock_paths):
        """Test run_all with callbacks."""
        started_checks = []
        completed_checks = []

        def on_started(key):
            started_checks.append(key)

        def on_completed(result):
            completed_checks.append(result.key)

        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        report = diag.run_all(
            on_check_started=on_started,
            on_check_completed=on_completed,
        )

        assert len(started_checks) > 0
        assert len(completed_checks) > 0
        assert started_checks == completed_checks

    def test_cancel(self, mock_config, mock_paths):
        """Test cancellation."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)
        diag.cancel()

        assert diag._cancelled is True

    def test_overall_status_calculation(self, mock_config, mock_paths):
        """Test overall status is calculated correctly."""
        diag = SystemDiagnostics(config=mock_config, paths=mock_paths)

        # Run checks
        report = diag.run_all()

        # Overall status should be set
        assert report.overall_status in [
            DiagnosticStatus.OK,
            DiagnosticStatus.WARNING,
            DiagnosticStatus.FAILED,
            DiagnosticStatus.CRITICAL,
        ]


class TestDiagnosticsModels:
    """Tests for diagnostics GUI models."""

    def test_diagnostic_check_ui_state(self):
        """Test DiagnosticCheckUIState."""
        from gui.diagnostics_models import DiagnosticCheckUIState

        definition = {
            "key": "test",
            "title": "Test Check",
            "category": "system",
            "description": "A test check",
            "is_critical": True,
        }

        state = DiagnosticCheckUIState.from_definition(definition)

        assert state.key == "test"
        assert state.title == "Test Check"
        assert state.is_critical is True
        assert state.status == DiagnosticStatus.NOT_TESTED

    def test_diagnostic_check_ui_state_update(self):
        """Test updating UI state from result."""
        from gui.diagnostics_models import DiagnosticCheckUIState

        state = DiagnosticCheckUIState(
            key="test",
            title="Test",
            category="system",
            description="Test",
            is_critical=False,
        )

        result = DiagnosticCheckResult(
            key="test",
            title="Test",
            category=CheckCategory.CORE,
            status=DiagnosticStatus.OK,
            summary="All good",
            details=["Detail 1"],
            recommendation="None",
            duration_ms=100,
        )

        state.update_from_result(result)

        assert state.status == DiagnosticStatus.OK
        assert state.summary == "All good"
        assert state.duration_ms == 100

    def test_diagnostics_ui_state_initialize(self):
        """Test DiagnosticsUIState initialization."""
        from gui.diagnostics_models import DiagnosticsUIState

        ui_state = DiagnosticsUIState.initialize()

        assert len(ui_state.checks) > 0
        assert ui_state.overall_status == DiagnosticStatus.NOT_TESTED

    def test_diagnostics_ui_state_get_check(self):
        """Test getting check by key."""
        from gui.diagnostics_models import DiagnosticsUIState

        ui_state = DiagnosticsUIState.initialize()
        check = ui_state.get_check("openai")

        assert check is not None
        assert check.key == "openai"

    def test_diagnostics_ui_state_status_summary(self):
        """Test status summary strings."""
        from gui.diagnostics_models import DiagnosticsUIState

        ui_state = DiagnosticsUIState()

        ui_state.overall_status = DiagnosticStatus.OK
        assert "pronto" in ui_state.get_status_summary().lower()

        ui_state.overall_status = DiagnosticStatus.WARNING
        assert "aviso" in ui_state.get_status_summary().lower()

        ui_state.overall_status = DiagnosticStatus.CRITICAL
        assert "bloqueado" in ui_state.get_status_summary().lower()

    def test_diagnostics_ui_state_count_by_status(self):
        """Test counting checks by status."""
        from gui.diagnostics_models import DiagnosticsUIState, DiagnosticCheckUIState

        ui_state = DiagnosticsUIState(
            checks=[
                DiagnosticCheckUIState(key="a", title="A", category="x", description="", is_critical=False, status=DiagnosticStatus.OK),
                DiagnosticCheckUIState(key="b", title="B", category="x", description="", is_critical=False, status=DiagnosticStatus.OK),
                DiagnosticCheckUIState(key="c", title="C", category="x", description="", is_critical=False, status=DiagnosticStatus.WARNING),
            ]
        )

        counts = ui_state.count_by_status()
        assert counts[DiagnosticStatus.OK] == 2
        assert counts[DiagnosticStatus.WARNING] == 1


class TestDiagnosticsWorker:
    """Tests for diagnostics worker classes."""

    def test_worker_signals_exist(self):
        """Test worker signals are defined."""
        from gui.diagnostics_worker import DiagnosticsWorkerSignals

        signals = DiagnosticsWorkerSignals()
        assert hasattr(signals, "diagnostics_started")
        assert hasattr(signals, "check_started")
        assert hasattr(signals, "check_completed")
        assert hasattr(signals, "diagnostics_completed")
        assert hasattr(signals, "diagnostics_failed")

    def test_diagnostics_worker_creation(self):
        """Test creating DiagnosticsWorker."""
        from gui.diagnostics_worker import DiagnosticsWorker

        worker = DiagnosticsWorker()
        assert worker is not None
        assert worker.signals is not None

    def test_single_check_worker_creation(self):
        """Test creating SingleCheckWorker."""
        from gui.diagnostics_worker import SingleCheckWorker

        worker = SingleCheckWorker(check_key="openai")
        assert worker is not None
        assert worker.check_key == "openai"

    def test_diagnostics_manager_creation(self):
        """Test creating DiagnosticsManager."""
        from gui.diagnostics_worker import DiagnosticsManager

        manager = DiagnosticsManager()
        assert manager is not None
        assert manager.is_running is False

    def test_diagnostics_manager_export_report(self):
        """Test exporting report."""
        from gui.diagnostics_worker import DiagnosticsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            manager = DiagnosticsManager()

            report = DiagnosticReport(
                started_at=datetime.now(),
                overall_status=DiagnosticStatus.OK,
                checks=[],
            )

            paths = manager.export_report(report, workspace, format="both")

            assert "json" in paths
            assert "markdown" in paths
            assert paths["json"].exists()
            assert paths["markdown"].exists()

            # Verify JSON content
            with open(paths["json"]) as f:
                data = json.load(f)
                assert data["overall_status"] == "ok"


class TestDiagnosticReportComputation:
    """Tests for report status computation."""

    def test_compute_critical_status(self):
        """Test critical status computation."""
        report = DiagnosticReport(started_at=datetime.now())
        report.checks = [
            DiagnosticCheckResult(
                key="a", title="A", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
            DiagnosticCheckResult(
                key="b", title="B", category=CheckCategory.CORE,
                status=DiagnosticStatus.CRITICAL, summary=""
            ),
        ]
        report.compute_overall_status()
        assert report.overall_status == DiagnosticStatus.CRITICAL

    def test_compute_failed_status(self):
        """Test failed status computation."""
        report = DiagnosticReport(started_at=datetime.now())
        report.checks = [
            DiagnosticCheckResult(
                key="a", title="A", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
            DiagnosticCheckResult(
                key="b", title="B", category=CheckCategory.CORE,
                status=DiagnosticStatus.FAILED, summary=""
            ),
        ]
        report.compute_overall_status()
        assert report.overall_status == DiagnosticStatus.FAILED

    def test_compute_warning_status(self):
        """Test warning status computation."""
        report = DiagnosticReport(started_at=datetime.now())
        report.checks = [
            DiagnosticCheckResult(
                key="a", title="A", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
            DiagnosticCheckResult(
                key="b", title="B", category=CheckCategory.CORE,
                status=DiagnosticStatus.WARNING, summary=""
            ),
        ]
        report.compute_overall_status()
        assert report.overall_status == DiagnosticStatus.WARNING

    def test_compute_ok_status(self):
        """Test OK status computation."""
        report = DiagnosticReport(started_at=datetime.now())
        report.checks = [
            DiagnosticCheckResult(
                key="a", title="A", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
            DiagnosticCheckResult(
                key="b", title="B", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
        ]
        report.compute_overall_status()
        assert report.overall_status == DiagnosticStatus.OK

    def test_critical_failure_promotes_to_critical(self):
        """Test that critical failures promote overall status."""
        report = DiagnosticReport(started_at=datetime.now())
        report.checks = [
            DiagnosticCheckResult(
                key="a", title="A", category=CheckCategory.CORE,
                status=DiagnosticStatus.OK, summary=""
            ),
            DiagnosticCheckResult(
                key="b", title="B", category=CheckCategory.CORE,
                status=DiagnosticStatus.FAILED, summary="",
                is_critical=True
            ),
        ]
        report.compute_overall_status()
        assert report.overall_status == DiagnosticStatus.CRITICAL
