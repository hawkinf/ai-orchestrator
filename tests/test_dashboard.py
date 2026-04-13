"""Tests for dashboard panel and related modules."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from orchestrator.run_index import RunStatus, RunSummary, RunMetrics, RunFilter


class TestDashboardModels:
    """Tests for dashboard GUI models."""

    def test_dashboard_ui_state(self):
        """Test DashboardUIState."""
        from gui.dashboard_models import DashboardUIState

        state = DashboardUIState()
        assert state.runs == []
        assert state.is_loading is False

    def test_dashboard_ui_state_get_selected_run(self):
        """Test getting selected run."""
        from gui.dashboard_models import DashboardUIState

        run1 = RunSummary(run_id="test-001", status=RunStatus.COMPLETED)
        run2 = RunSummary(run_id="test-002", status=RunStatus.FAILED)

        state = DashboardUIState(
            runs=[run1, run2],
            selected_run_id="test-002",
        )

        selected = state.get_selected_run()
        assert selected is not None
        assert selected.run_id == "test-002"

    def test_dashboard_ui_state_apply_filter(self):
        """Test applying filter to runs."""
        from gui.dashboard_models import DashboardUIState

        run1 = RunSummary(run_id="test-001", status=RunStatus.COMPLETED)
        run2 = RunSummary(run_id="test-002", status=RunStatus.FAILED)
        run3 = RunSummary(run_id="test-003", status=RunStatus.COMPLETED)

        state = DashboardUIState(
            runs=[run1, run2, run3],
            filter=RunFilter(status_filter=[RunStatus.COMPLETED]),
        )

        filtered = state.apply_filter()
        assert len(filtered) == 2
        assert all(r.status == RunStatus.COMPLETED for r in filtered)

    def test_dashboard_ui_state_status_counts(self):
        """Test counting by status."""
        from gui.dashboard_models import DashboardUIState

        runs = [
            RunSummary(run_id="1", status=RunStatus.COMPLETED),
            RunSummary(run_id="2", status=RunStatus.COMPLETED),
            RunSummary(run_id="3", status=RunStatus.FAILED),
            RunSummary(run_id="4", status=RunStatus.RUNNING),
        ]

        state = DashboardUIState(runs=runs)
        counts = state.get_status_counts()

        assert counts[RunStatus.COMPLETED] == 2
        assert counts[RunStatus.FAILED] == 1
        assert counts[RunStatus.RUNNING] == 1

    def test_metric_card_from_metrics(self):
        """Test creating metric cards from metrics."""
        from gui.dashboard_models import MetricCard

        metrics = RunMetrics(
            total_runs=10,
            running_runs=2,
            completed_runs=5,
            failed_runs=3,
            checkpoint_runs=0,
            blocked_runs=0,
        )

        cards = MetricCard.from_metrics(metrics)

        assert len(cards) == 6
        assert cards[0].label == "Total"
        assert cards[0].value == 10
        assert cards[2].label == "Concluidas"
        assert cards[2].value == 5

    def test_get_status_display(self):
        """Test getting status display info."""
        from gui.dashboard_models import get_status_display

        text, color = get_status_display(RunStatus.COMPLETED)
        assert text == "Concluido"
        assert color == "#22c55e"

        text, color = get_status_display(RunStatus.FAILED)
        assert text == "Falhou"
        assert color == "#ef4444"

    def test_format_duration(self):
        """Test duration formatting."""
        from gui.dashboard_models import format_duration

        assert format_duration(30) == "30s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3700) == "1h 1m"

    def test_format_datetime(self):
        """Test datetime formatting."""
        from gui.dashboard_models import format_datetime

        # None
        assert format_datetime(None) == "-"

        # Today
        now = datetime.now()
        result = format_datetime(now)
        assert ":" in result  # Should show time

        # Yesterday
        yesterday = now - timedelta(days=1)
        result = format_datetime(yesterday)
        assert "Ontem" in result

        # Last week
        last_week = now - timedelta(days=5)
        result = format_datetime(last_week)
        assert "dias" in result


class TestDashboardWorker:
    """Tests for dashboard worker."""

    def test_worker_signals_exist(self):
        """Test worker signals are defined."""
        from gui.dashboard_worker import DashboardWorkerSignals

        signals = DashboardWorkerSignals()
        assert hasattr(signals, "loading_started")
        assert hasattr(signals, "data_loaded")
        assert hasattr(signals, "loading_failed")

    def test_dashboard_load_worker_creation(self):
        """Test creating DashboardLoadWorker."""
        from gui.dashboard_worker import DashboardLoadWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            worker = DashboardLoadWorker(workspace_path=workspace)

            assert worker is not None
            assert worker.signals is not None

    def test_export_worker_creation(self):
        """Test creating ExportWorker."""
        from gui.dashboard_worker import ExportWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            output_dir = workspace / "logs"

            worker = ExportWorker(
                workspace_path=workspace,
                output_dir=output_dir,
                format="both",
            )

            assert worker is not None

    def test_dashboard_manager_creation(self):
        """Test creating DashboardManager."""
        from gui.dashboard_worker import DashboardManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            manager = DashboardManager(workspace_path=workspace)

            assert manager is not None
            assert manager.is_loading is False

    def test_dashboard_manager_set_filter(self):
        """Test setting filter on manager."""
        from gui.dashboard_worker import DashboardManager

        manager = DashboardManager()
        filter_criteria = RunFilter(status_filter=[RunStatus.FAILED])
        manager.set_filter(filter_criteria)

        assert manager._filter == filter_criteria

    def test_dashboard_manager_get_clipboard_summary(self):
        """Test getting clipboard summary."""
        from gui.dashboard_worker import DashboardManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()

            manager = DashboardManager(workspace_path=workspace)
            summary = manager.get_clipboard_summary()

            assert "AI Orchestrator" in summary
            assert "Total:" in summary


class TestDashboardPanel:
    """Smoke tests for dashboard panel."""

    def test_imports(self):
        """Test dashboard panel can be imported."""
        from gui.dashboard_panel import (
            DashboardPanel,
            MetricCardWidget,
            MetricsBar,
            FilterBar,
            RunsTable,
            RunDetailPreview,
        )

        assert DashboardPanel is not None
        assert MetricCardWidget is not None
        assert MetricsBar is not None
        assert FilterBar is not None
        assert RunsTable is not None
        assert RunDetailPreview is not None

    def test_metric_card_widget_creation(self):
        """Test creating MetricCardWidget."""
        from gui.dashboard_panel import MetricCardWidget

        card = MetricCardWidget(label="Test", value=42, color="#ffffff")
        assert card is not None

    def test_metric_card_update(self):
        """Test updating MetricCardWidget."""
        from gui.dashboard_panel import MetricCardWidget

        card = MetricCardWidget(label="Test", value=0, color="#ffffff")
        card.update_value(100)

        assert card.value_label.text() == "100"

    def test_metrics_bar_creation(self):
        """Test creating MetricsBar."""
        from gui.dashboard_panel import MetricsBar

        bar = MetricsBar()
        assert bar is not None
        assert len(bar._cards) == 6

    def test_metrics_bar_update(self):
        """Test updating MetricsBar."""
        from gui.dashboard_panel import MetricsBar

        bar = MetricsBar()
        metrics = RunMetrics(
            total_runs=10,
            running_runs=2,
            completed_runs=5,
            failed_runs=3,
        )

        bar.update_metrics(metrics)

        assert bar._cards["total"].value_label.text() == "10"
        assert bar._cards["completed"].value_label.text() == "5"

    def test_filter_bar_creation(self):
        """Test creating FilterBar."""
        from gui.dashboard_panel import FilterBar

        bar = FilterBar()
        assert bar is not None
        assert bar.search_edit is not None
        assert bar.status_combo is not None

    def test_filter_bar_get_filter(self):
        """Test getting filter from FilterBar."""
        from gui.dashboard_panel import FilterBar

        bar = FilterBar()
        bar.search_edit.setText("login")
        bar.checkpoint_cb.setChecked(True)

        f = bar.get_filter()
        assert f.search_text == "login"
        assert f.has_checkpoint is True

    def test_filter_bar_clear(self):
        """Test clearing FilterBar."""
        from gui.dashboard_panel import FilterBar

        bar = FilterBar()
        bar.search_edit.setText("test")
        bar.checkpoint_cb.setChecked(True)

        bar.clear_filters()

        assert bar.search_edit.text() == ""
        assert bar.checkpoint_cb.isChecked() is False

    def test_runs_table_creation(self):
        """Test creating RunsTable."""
        from gui.dashboard_panel import RunsTable

        table = RunsTable()
        assert table is not None
        assert table.columnCount() == 8

    def test_runs_table_set_runs(self):
        """Test setting runs on table."""
        from gui.dashboard_panel import RunsTable

        table = RunsTable()
        runs = [
            RunSummary(
                run_id="test-001",
                task_summary="Test task",
                status=RunStatus.COMPLETED,
                project_type="flutter",
            ),
            RunSummary(
                run_id="test-002",
                task_summary="Another task",
                status=RunStatus.FAILED,
                project_type="python",
            ),
        ]

        table.set_runs(runs)

        assert table.rowCount() == 2

    def test_run_detail_preview_creation(self):
        """Test creating RunDetailPreview."""
        from gui.dashboard_panel import RunDetailPreview

        preview = RunDetailPreview()
        assert preview is not None

    def test_run_detail_preview_set_run(self):
        """Test setting run on preview."""
        from gui.dashboard_panel import RunDetailPreview

        preview = RunDetailPreview()

        run = RunSummary(
            run_id="test-001",
            full_task="Fix the login bug",
            status=RunStatus.COMPLETED,
            iteration=2,
            max_iterations=3,
            duration_seconds=120,
        )

        preview.set_run(run)

        assert "test-001" in preview.title_label.text()

    def test_run_detail_preview_clear(self):
        """Test clearing preview."""
        from gui.dashboard_panel import RunDetailPreview

        preview = RunDetailPreview()
        preview.set_run(None)

        assert preview.title_label.text() == "Selecione uma run"

    def test_dashboard_panel_creation(self):
        """Test creating DashboardPanel."""
        from gui.dashboard_panel import DashboardPanel

        panel = DashboardPanel()
        assert panel is not None
        assert panel.metrics_bar is not None
        assert panel.filter_bar is not None
        assert panel.runs_table is not None
        assert panel.detail_preview is not None


class TestIntegration:
    """Integration tests."""

    @pytest.fixture
    def temp_workspace_with_runs(self):
        """Create workspace with sample runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()
            (workspace / "logs").mkdir()

            # Create sample runs
            for i, status in enumerate(["completed", "failed", "running"]):
                state = {
                    "run_id": f"test-{i:03d}",
                    "created_at": f"2026-01-{15-i:02d}T10:00:00",
                    "status": status,
                    "task": {
                        "description": f"Task {i}",
                        "profile": "flutter" if i % 2 == 0 else "python",
                    },
                }
                state_file = workspace / "state" / f"test-{i:03d}.json"
                with open(state_file, "w") as f:
                    json.dump(state, f)

            yield workspace

    def test_full_dashboard_flow(self, temp_workspace_with_runs):
        """Test full dashboard data flow."""
        from orchestrator.run_index import get_run_index
        from gui.dashboard_models import DashboardUIState

        # Load data
        index = get_run_index(temp_workspace_with_runs)
        runs = index.get_all_runs()
        metrics = index.get_metrics()
        profiles = index.get_profiles()

        # Create UI state
        state = DashboardUIState(
            runs=runs,
            metrics=metrics,
            available_profiles=profiles,
        )

        # Verify
        assert len(state.runs) == 3
        assert state.metrics.total_runs == 3
        assert "flutter" in state.available_profiles
        assert "python" in state.available_profiles

    def test_filter_integration(self, temp_workspace_with_runs):
        """Test filtering integration."""
        from orchestrator.run_index import get_run_index
        from gui.dashboard_models import DashboardUIState

        index = get_run_index(temp_workspace_with_runs)
        runs = index.get_all_runs()

        state = DashboardUIState(
            runs=runs,
            filter=RunFilter(status_filter=[RunStatus.COMPLETED]),
        )

        filtered = state.apply_filter()
        assert len(filtered) == 1
        assert filtered[0].status == RunStatus.COMPLETED
