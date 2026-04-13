"""Tests for checkpoints panel and related modules."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from orchestrator.checkpoint_index import (
    CheckpointDecisionStatus,
    CheckpointMetrics,
    CheckpointSeverity,
    CheckpointSummary,
    CheckpointFilter,
)


class TestCheckpointsModels:
    """Tests for checkpoints GUI models."""

    def test_checkpoint_ui_state(self):
        """Test CheckpointUIState."""
        from gui.checkpoints_models import CheckpointUIState

        state = CheckpointUIState()
        assert state.checkpoints == []
        assert state.is_loading is False

    def test_checkpoint_ui_state_get_selected(self):
        """Test getting selected checkpoint."""
        from gui.checkpoints_models import CheckpointUIState

        cp1 = CheckpointSummary(
            checkpoint_id="cp-001",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )
        cp2 = CheckpointSummary(
            checkpoint_id="cp-002",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.INFO,
        )

        state = CheckpointUIState(
            checkpoints=[cp1, cp2],
            selected_checkpoint_id="cp-002",
        )

        selected = state.get_selected_checkpoint()
        assert selected is not None
        assert selected.checkpoint_id == "cp-002"

    def test_checkpoint_ui_state_apply_filter(self):
        """Test applying filter to checkpoints."""
        from gui.checkpoints_models import CheckpointUIState

        cp1 = CheckpointSummary(
            checkpoint_id="cp-001",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )
        cp2 = CheckpointSummary(
            checkpoint_id="cp-002",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.INFO,
        )

        state = CheckpointUIState(
            checkpoints=[cp1, cp2],
            filter=CheckpointFilter(status_filter=[CheckpointDecisionStatus.PENDING]),
        )

        filtered = state.apply_filter()
        assert len(filtered) == 1
        assert filtered[0].status == CheckpointDecisionStatus.PENDING

    def test_checkpoint_ui_state_get_pending(self):
        """Test getting pending checkpoints."""
        from gui.checkpoints_models import CheckpointUIState

        cp1 = CheckpointSummary(
            checkpoint_id="cp-001",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )
        cp2 = CheckpointSummary(
            checkpoint_id="cp-002",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.INFO,
        )

        state = CheckpointUIState(checkpoints=[cp1, cp2])
        pending = state.get_pending_checkpoints()

        assert len(pending) == 1
        assert pending[0].checkpoint_id == "cp-001"

    def test_checkpoint_ui_state_get_history(self):
        """Test getting history checkpoints."""
        from gui.checkpoints_models import CheckpointUIState

        cp1 = CheckpointSummary(
            checkpoint_id="cp-001",
            run_id="run-001",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.INFO,
        )
        cp2 = CheckpointSummary(
            checkpoint_id="cp-002",
            run_id="run-002",
            reason="test",
            reason_display="Test",
            description="",
            status=CheckpointDecisionStatus.APPROVED,
            severity=CheckpointSeverity.INFO,
        )

        state = CheckpointUIState(checkpoints=[cp1, cp2])
        history = state.get_history_checkpoints()

        assert len(history) == 1
        assert history[0].checkpoint_id == "cp-002"

    def test_checkpoint_ui_state_status_counts(self):
        """Test counting by status."""
        from gui.checkpoints_models import CheckpointUIState

        checkpoints = [
            CheckpointSummary(
                checkpoint_id="1",
                run_id="r1",
                reason="t",
                reason_display="T",
                description="",
                status=CheckpointDecisionStatus.PENDING,
                severity=CheckpointSeverity.INFO,
            ),
            CheckpointSummary(
                checkpoint_id="2",
                run_id="r2",
                reason="t",
                reason_display="T",
                description="",
                status=CheckpointDecisionStatus.PENDING,
                severity=CheckpointSeverity.INFO,
            ),
            CheckpointSummary(
                checkpoint_id="3",
                run_id="r3",
                reason="t",
                reason_display="T",
                description="",
                status=CheckpointDecisionStatus.APPROVED,
                severity=CheckpointSeverity.INFO,
            ),
        ]

        state = CheckpointUIState(checkpoints=checkpoints)
        counts = state.get_status_counts()

        assert counts[CheckpointDecisionStatus.PENDING] == 2
        assert counts[CheckpointDecisionStatus.APPROVED] == 1
        assert counts[CheckpointDecisionStatus.REJECTED] == 0

    def test_metric_card_from_metrics(self):
        """Test creating metric cards from metrics."""
        from gui.checkpoints_models import MetricCard

        metrics = CheckpointMetrics(
            total_checkpoints=10,
            pending_checkpoints=3,
            approved_checkpoints=5,
            rejected_checkpoints=2,
            critical_pending=1,
            high_risk_pending=2,
        )

        cards = MetricCard.from_metrics(metrics)

        assert len(cards) == 6
        assert cards[0].label == "Total"
        assert cards[0].value == 10
        assert cards[1].label == "Pendentes"
        assert cards[1].value == 3

    def test_get_status_display(self):
        """Test getting status display info."""
        from gui.checkpoints_models import get_status_display

        text, color = get_status_display(CheckpointDecisionStatus.PENDING)
        assert text == "Pendente"
        assert color == "#f59e0b"

        text, color = get_status_display(CheckpointDecisionStatus.APPROVED)
        assert text == "Aprovado"
        assert color == "#22c55e"

        text, color = get_status_display(CheckpointDecisionStatus.REJECTED)
        assert text == "Rejeitado"
        assert color == "#ef4444"

    def test_get_severity_display(self):
        """Test getting severity display info."""
        from gui.checkpoints_models import get_severity_display

        text, color = get_severity_display(CheckpointSeverity.CRITICAL)
        assert text == "Critico"
        assert color == "#dc2626"

        text, color = get_severity_display(CheckpointSeverity.HIGH_RISK)
        assert text == "Alto Risco"
        assert color == "#ea580c"

        text, color = get_severity_display(CheckpointSeverity.WARNING)
        assert text == "Alerta"
        assert color == "#f59e0b"

    def test_format_duration(self):
        """Test duration formatting."""
        from gui.checkpoints_models import format_duration

        assert format_duration(30) == "30s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3700) == "1h 1m"

    def test_format_datetime(self):
        """Test datetime formatting."""
        from gui.checkpoints_models import format_datetime

        # None
        assert format_datetime(None) == "-"

        # Now
        now = datetime.now()
        result = format_datetime(now)
        assert "Agora" in result or "m atras" in result

        # Yesterday
        yesterday = now - timedelta(days=1)
        result = format_datetime(yesterday)
        assert "Ontem" in result

    def test_get_reason_display(self):
        """Test reason display text."""
        from gui.checkpoints_models import get_reason_display

        assert get_reason_display("destructive_operation") == "Operacao Destrutiva"
        assert get_reason_display("migration") == "Migracao"
        assert get_reason_display("unknown_reason") == "Unknown Reason"


class TestCheckpointsWorker:
    """Tests for checkpoints worker."""

    def test_worker_signals_exist(self):
        """Test worker signals are defined."""
        from gui.checkpoints_worker import CheckpointWorkerSignals

        signals = CheckpointWorkerSignals()
        assert hasattr(signals, "loading_started")
        assert hasattr(signals, "data_loaded")
        assert hasattr(signals, "loading_failed")
        assert hasattr(signals, "action_completed")

    def test_checkpoint_load_worker_creation(self):
        """Test creating CheckpointLoadWorker."""
        from gui.checkpoints_worker import CheckpointLoadWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            worker = CheckpointLoadWorker(workspace_path=workspace)

            assert worker is not None
            assert worker.signals is not None

    def test_checkpoint_manager_creation(self):
        """Test creating CheckpointManager."""
        from gui.checkpoints_worker import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            manager = CheckpointManager(workspace_path=workspace)

            assert manager is not None
            assert manager.is_loading is False

    def test_checkpoint_manager_set_filter(self):
        """Test setting filter on manager."""
        from gui.checkpoints_worker import CheckpointManager

        manager = CheckpointManager()
        filter_criteria = CheckpointFilter(status_filter=[CheckpointDecisionStatus.PENDING])
        manager.set_filter(filter_criteria)

        assert manager._filter == filter_criteria

    def test_checkpoint_manager_get_clipboard_summary(self):
        """Test getting clipboard summary."""
        from gui.checkpoints_worker import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()

            manager = CheckpointManager(workspace_path=workspace)
            summary = manager.get_clipboard_summary()

            assert "AI Orchestrator" in summary
            assert "Total:" in summary


class TestCheckpointsPanel:
    """Smoke tests for checkpoints panel."""

    def test_imports(self):
        """Test checkpoints panel can be imported."""
        from gui.checkpoints_panel import (
            CheckpointsPanel,
            MetricCardWidget,
            MetricsBar,
            FilterBar,
            CheckpointsTable,
            CheckpointDetailPanel,
            SeverityBadge,
            StatusBadge,
        )

        assert CheckpointsPanel is not None
        assert MetricCardWidget is not None
        assert MetricsBar is not None
        assert FilterBar is not None
        assert CheckpointsTable is not None
        assert CheckpointDetailPanel is not None

    def test_metric_card_widget_creation(self):
        """Test creating MetricCardWidget."""
        from gui.checkpoints_panel import MetricCardWidget

        card = MetricCardWidget(label="Test", value=42, color="#ffffff")
        assert card is not None

    def test_metric_card_update(self):
        """Test updating MetricCardWidget."""
        from gui.checkpoints_panel import MetricCardWidget

        card = MetricCardWidget(label="Test", value=0, color="#ffffff")
        card.update_value(100)

        assert card.value_label.text() == "100"

    def test_metrics_bar_creation(self):
        """Test creating MetricsBar."""
        from gui.checkpoints_panel import MetricsBar

        bar = MetricsBar()
        assert bar is not None
        assert len(bar._cards) == 6

    def test_metrics_bar_update(self):
        """Test updating MetricsBar."""
        from gui.checkpoints_panel import MetricsBar

        bar = MetricsBar()
        metrics = CheckpointMetrics(
            total_checkpoints=10,
            pending_checkpoints=3,
            approved_checkpoints=5,
            rejected_checkpoints=2,
        )

        bar.update_metrics(metrics)

        assert bar._cards["total"].value_label.text() == "10"
        assert bar._cards["pending"].value_label.text() == "3"

    def test_filter_bar_creation(self):
        """Test creating FilterBar."""
        from gui.checkpoints_panel import FilterBar

        bar = FilterBar()
        assert bar is not None
        assert bar.search_edit is not None
        assert bar.status_combo is not None

    def test_filter_bar_get_filter(self):
        """Test getting filter from FilterBar."""
        from gui.checkpoints_panel import FilterBar

        bar = FilterBar()
        bar.search_edit.setText("migration")

        f = bar.get_filter()
        assert f.search_text == "migration"

    def test_filter_bar_clear(self):
        """Test clearing FilterBar."""
        from gui.checkpoints_panel import FilterBar

        bar = FilterBar()
        bar.search_edit.setText("test")

        bar.clear_filters()

        assert bar.search_edit.text() == ""

    def test_checkpoints_table_creation(self):
        """Test creating CheckpointsTable."""
        from gui.checkpoints_panel import CheckpointsTable

        table = CheckpointsTable()
        assert table is not None
        assert table.columnCount() == 7

    def test_checkpoints_table_set_checkpoints(self):
        """Test setting checkpoints on table."""
        from gui.checkpoints_panel import CheckpointsTable

        table = CheckpointsTable()
        checkpoints = [
            CheckpointSummary(
                checkpoint_id="cp-001",
                run_id="run-001",
                reason="destructive_operation",
                reason_display="Operacao Destrutiva",
                description="Test",
                status=CheckpointDecisionStatus.PENDING,
                severity=CheckpointSeverity.HIGH_RISK,
            ),
            CheckpointSummary(
                checkpoint_id="cp-002",
                run_id="run-002",
                reason="migration",
                reason_display="Migracao",
                description="Another test",
                status=CheckpointDecisionStatus.APPROVED,
                severity=CheckpointSeverity.WARNING,
            ),
        ]

        table.set_checkpoints(checkpoints)

        assert table.rowCount() == 2

    def test_checkpoint_detail_panel_creation(self):
        """Test creating CheckpointDetailPanel."""
        from gui.checkpoints_panel import CheckpointDetailPanel

        panel = CheckpointDetailPanel()
        assert panel is not None

    def test_checkpoint_detail_panel_set_checkpoint(self):
        """Test setting checkpoint on panel."""
        from gui.checkpoints_panel import CheckpointDetailPanel
        from orchestrator.checkpoint_index import CheckpointDetail

        panel = CheckpointDetailPanel()

        detail = CheckpointDetail(
            checkpoint_id="cp-001",
            run_id="run-001",
            reason="destructive_operation",
            reason_display="Operacao Destrutiva",
            description="Delete all data",
            status=CheckpointDecisionStatus.PENDING,
            severity=CheckpointSeverity.HIGH_RISK,
            iteration=2,
            max_iterations=3,
            plan_objective="Fix the bug",
            estimated_risk="Alto",
            system_recommendation="Review carefully",
            suggested_action="Consider rejecting",
        )

        panel.set_checkpoint(detail)

        assert "run-001" in panel.title_label.text()

    def test_checkpoint_detail_panel_clear(self):
        """Test clearing detail panel."""
        from gui.checkpoints_panel import CheckpointDetailPanel

        panel = CheckpointDetailPanel()
        panel.set_checkpoint(None)

        assert panel.title_label.text() == "Selecione um checkpoint"

    def test_checkpoints_panel_creation(self):
        """Test creating CheckpointsPanel."""
        from gui.checkpoints_panel import CheckpointsPanel

        panel = CheckpointsPanel()
        assert panel is not None
        assert panel.metrics_bar is not None
        assert panel.filter_bar is not None
        assert panel.table is not None
        assert panel.detail_panel is not None


class TestIntegration:
    """Integration tests."""

    @pytest.fixture
    def temp_workspace_with_checkpoints(self):
        """Create workspace with sample checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "state").mkdir()
            (workspace / "runs").mkdir()
            (workspace / "logs").mkdir()

            # Create sample states with checkpoints
            states = [
                {
                    "run_id": "run-001",
                    "status": "checkpoint",
                    "created_at": "2026-01-15T10:00:00",
                    "task": {"description": "Task 1", "profile": "python"},
                    "checkpoint": {
                        "reason": "destructive_operation",
                        "description": "Delete operation",
                        "created_at": "2026-01-15T10:00:00",
                        "resolved": False,
                    },
                },
                {
                    "run_id": "run-002",
                    "status": "completed",
                    "created_at": "2026-01-14T10:00:00",
                    "task": {"description": "Task 2", "profile": "flutter"},
                    "checkpoint": {
                        "reason": "migration",
                        "description": "Migration",
                        "created_at": "2026-01-14T10:00:00",
                        "resolved": True,
                        "resolved_at": "2026-01-14T10:30:00",
                        "resolution": "approved",
                    },
                },
            ]

            for state in states:
                state_file = workspace / "state" / f"{state['run_id']}.json"
                with open(state_file, "w") as f:
                    json.dump(state, f)

            yield workspace

    def test_full_checkpoint_flow(self, temp_workspace_with_checkpoints):
        """Test full checkpoint data flow."""
        from orchestrator.checkpoint_index import get_checkpoint_index
        from gui.checkpoints_models import CheckpointUIState

        # Load data
        index = get_checkpoint_index(temp_workspace_with_checkpoints)
        checkpoints = index.get_all_checkpoints()
        metrics = index.get_metrics()

        # Create UI state
        state = CheckpointUIState(
            checkpoints=checkpoints,
            metrics=metrics,
        )

        # Verify
        assert len(state.checkpoints) == 2
        assert state.metrics.total_checkpoints == 2
        assert state.metrics.pending_checkpoints == 1

    def test_filter_integration(self, temp_workspace_with_checkpoints):
        """Test filtering integration."""
        from orchestrator.checkpoint_index import get_checkpoint_index
        from gui.checkpoints_models import CheckpointUIState

        index = get_checkpoint_index(temp_workspace_with_checkpoints)
        checkpoints = index.get_all_checkpoints()

        state = CheckpointUIState(
            checkpoints=checkpoints,
            filter=CheckpointFilter(status_filter=[CheckpointDecisionStatus.PENDING]),
        )

        filtered = state.apply_filter()
        assert len(filtered) == 1
        assert filtered[0].status == CheckpointDecisionStatus.PENDING
