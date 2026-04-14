"""Replay panel for run simulation and comparison.

Provides UI for replaying runs and viewing comparisons.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QRunnable, QObject, QThreadPool, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QTabWidget,
    QMessageBox,
    QFrame,
    QTextEdit,
    QProgressBar,
    QSpinBox,
)

from orchestrator.replay_engine import ReplayEngine
from orchestrator.replay_models import (
    ReplayMode,
    ReplayStage,
    ReplayStatus,
    ReplayConfig,
    ReplayResult,
    ReplayListItem,
    ComparisonResult,
)
from orchestrator.state_store import StateStore

logger = logging.getLogger("ai_orchestrator.gui.replay_panel")


# =============================================================================
# Worker Signals and Classes
# =============================================================================


class ReplayWorkerSignals(QObject):
    """Signals for replay workers."""
    finished = Signal()
    error = Signal(str)
    progress = Signal(str, float)  # message, percent
    result = Signal(object)  # ReplayResult
    replays_loaded = Signal(list)  # List[ReplayListItem]
    runs_loaded = Signal(list)  # List of run summaries


class ReplayWorker(QRunnable):
    """Worker to execute a replay."""

    def __init__(self, engine: ReplayEngine, run_id: str, config: ReplayConfig):
        super().__init__()
        self.engine = engine
        self.run_id = run_id
        self.config = config
        self.signals = ReplayWorkerSignals()

    def run(self):
        try:
            result = self.engine.replay(
                self.run_id,
                self.config,
                progress_callback=self._on_progress,
            )
            self.signals.result.emit(result)
        except Exception as e:
            logger.error(f"Replay worker error: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

    def _on_progress(self, message: str, percent: float):
        self.signals.progress.emit(message, percent)


class LoadReplaysWorker(QRunnable):
    """Worker to load replay history."""

    def __init__(self, engine: ReplayEngine, limit: int = 50):
        super().__init__()
        self.engine = engine
        self.limit = limit
        self.signals = ReplayWorkerSignals()

    def run(self):
        try:
            replays = self.engine.list_replays(limit=self.limit)
            self.signals.replays_loaded.emit(replays)
        except Exception as e:
            logger.error(f"Error loading replays: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class LoadRunsWorker(QRunnable):
    """Worker to load available runs."""

    def __init__(self, store: StateStore, limit: int = 50):
        super().__init__()
        self.store = store
        self.limit = limit
        self.signals = ReplayWorkerSignals()

    def run(self):
        try:
            runs = self.store.list_runs(limit=self.limit)
            self.signals.runs_loaded.emit(runs)
        except Exception as e:
            logger.error(f"Error loading runs: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# =============================================================================
# Status Badge
# =============================================================================


class StatusBadge(QLabel):
    """Badge showing replay status."""

    COLORS = {
        ReplayStatus.PENDING: ("#666", "#444"),
        ReplayStatus.RUNNING: ("#2196f3", "#1565c0"),
        ReplayStatus.COMPLETED: ("#4caf50", "#1b5e20"),
        ReplayStatus.FAILED: ("#f44336", "#b71c1c"),
        ReplayStatus.CANCELLED: ("#ff9800", "#e65100"),
    }

    def __init__(self, status: ReplayStatus, parent=None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: ReplayStatus):
        bg, border = self.COLORS.get(status, ("#666", "#444"))
        self.setText(status.value.replace("_", " ").title())
        self.setStyleSheet(f"""
            background: {bg};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)


class ComparisonBadge(QLabel):
    """Badge showing comparison result."""

    COLORS = {
        ComparisonResult.IDENTICAL: ("#4caf50", "#1b5e20"),
        ComparisonResult.DIFFERENT: ("#ff9800", "#e65100"),
        ComparisonResult.ORIGINAL_ONLY: ("#f44336", "#b71c1c"),
        ComparisonResult.REPLAY_ONLY: ("#2196f3", "#1565c0"),
    }

    def __init__(self, result: ComparisonResult, parent=None):
        super().__init__(parent)
        self.set_result(result)

    def set_result(self, result: ComparisonResult):
        bg, border = self.COLORS.get(result, ("#666", "#444"))
        self.setText(result.value.replace("_", " ").title())
        self.setStyleSheet(f"""
            background: {bg};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)


# =============================================================================
# Replay Config Panel
# =============================================================================


class ReplayConfigPanel(QGroupBox):
    """Panel for configuring replay options."""

    def __init__(self, parent=None):
        super().__init__("Replay Configuration", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Run selection
        self.run_combo = QComboBox()
        self.run_combo.setMinimumWidth(200)
        layout.addRow("Run:", self.run_combo)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Dry Run (simulated)", ReplayMode.DRY_RUN)
        self.mode_combo.addItem("Partial (specific stages)", ReplayMode.PARTIAL)
        self.mode_combo.addItem("Full (sandbox)", ReplayMode.FULL)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addRow("Mode:", self.mode_combo)

        # Stage selection (for partial mode)
        self.stages_group = QGroupBox("Stages to Replay")
        stages_layout = QVBoxLayout(self.stages_group)
        self.stage_checks = {}
        for stage in [ReplayStage.PLANNING, ReplayStage.EXECUTION, ReplayStage.REVIEW, ReplayStage.VALIDATION]:
            cb = QCheckBox(stage.value.title())
            cb.setChecked(True)
            self.stage_checks[stage] = cb
            stages_layout.addWidget(cb)
        self.stages_group.setVisible(False)
        layout.addRow(self.stages_group)

        # Sandbox option
        self.sandbox_check = QCheckBox("Use sandbox (isolated execution)")
        self.sandbox_check.setToolTip("Copy project to temporary directory")
        layout.addRow(self.sandbox_check)

        # Mock options
        self.mock_executor_check = QCheckBox("Mock executor (no real commands)")
        self.mock_executor_check.setChecked(True)
        layout.addRow(self.mock_executor_check)

        self.mock_planner_check = QCheckBox("Mock planner (use original plan)")
        layout.addRow(self.mock_planner_check)

        self.mock_reviewer_check = QCheckBox("Mock reviewer (use original review)")
        layout.addRow(self.mock_reviewer_check)

        # Checkpoint handling
        self.auto_approve_check = QCheckBox("Auto-approve all checkpoints")
        self.auto_approve_check.setChecked(True)
        layout.addRow(self.auto_approve_check)

        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(60, 3600)
        self.timeout_spin.setValue(600)
        self.timeout_spin.setSuffix(" seconds")
        layout.addRow("Timeout:", self.timeout_spin)

    def _on_mode_changed(self, index: int):
        mode = self.mode_combo.currentData()
        self.stages_group.setVisible(mode == ReplayMode.PARTIAL)
        self.sandbox_check.setEnabled(mode == ReplayMode.FULL)
        if mode == ReplayMode.FULL:
            self.sandbox_check.setChecked(True)

    def set_runs(self, runs: List[dict]):
        """Set available runs for selection."""
        self.run_combo.clear()
        for run in runs:
            run_id = run.get("run_id", "")
            task = run.get("task_summary", run_id)[:50]
            self.run_combo.addItem(f"{run_id} - {task}", run_id)

    def select_run(self, run_id: str):
        """Select a specific run in the combo box."""
        for index in range(self.run_combo.count()):
            if self.run_combo.itemData(index) == run_id:
                self.run_combo.setCurrentIndex(index)
                break

    def get_config(self) -> tuple:
        """Get the configured replay settings."""
        run_id = self.run_combo.currentData()
        if not run_id:
            return None, None

        mode = self.mode_combo.currentData()
        stages = [ReplayStage.ALL]
        if mode == ReplayMode.PARTIAL:
            stages = [stage for stage, cb in self.stage_checks.items() if cb.isChecked()]

        config = ReplayConfig(
            mode=mode,
            stages=stages,
            use_sandbox=self.sandbox_check.isChecked(),
            mock_executor=self.mock_executor_check.isChecked(),
            mock_planner=self.mock_planner_check.isChecked(),
            mock_reviewer=self.mock_reviewer_check.isChecked(),
            auto_approve_checkpoints=self.auto_approve_check.isChecked(),
            timeout_seconds=self.timeout_spin.value(),
        )

        return run_id, config


# =============================================================================
# Replay History Table
# =============================================================================


class ReplayHistoryTable(QTableWidget):
    """Table showing replay history."""

    replay_selected = Signal(str)  # replay_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Replay ID", "Original Run", "Mode", "Status", "Result", "Duration"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(2, 100)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 100)
        self.setColumnWidth(5, 80)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self._replays: dict = {}

    def load_replays(self, replays: List[ReplayListItem]):
        self.setRowCount(0)
        self._replays.clear()

        for replay in replays:
            self._add_replay_row(replay)

    def _add_replay_row(self, replay: ReplayListItem):
        row = self.rowCount()
        self.insertRow(row)
        self._replays[row] = replay

        # Replay ID
        self.setItem(row, 0, QTableWidgetItem(replay.replay_id))

        # Original Run
        self.setItem(row, 1, QTableWidgetItem(replay.original_run_id))

        # Mode
        mode_item = QTableWidgetItem(replay.mode.value.replace("_", " ").title())
        self.setItem(row, 2, mode_item)

        # Status badge
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.addWidget(StatusBadge(replay.status))
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.setContentsMargins(4, 4, 4, 4)
        self.setCellWidget(row, 3, status_widget)

        # Result badge
        if replay.comparison_result:
            result_widget = QWidget()
            result_layout = QHBoxLayout(result_widget)
            result_layout.addWidget(ComparisonBadge(replay.comparison_result))
            result_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            result_layout.setContentsMargins(4, 4, 4, 4)
            self.setCellWidget(row, 4, result_widget)
        else:
            self.setItem(row, 4, QTableWidgetItem("-"))

        # Duration
        duration = f"{replay.duration_seconds:.1f}s"
        self.setItem(row, 5, QTableWidgetItem(duration))

    def _on_selection_changed(self):
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            replay = self._replays.get(row)
            if replay:
                self.replay_selected.emit(replay.replay_id)


# =============================================================================
# Comparison View
# =============================================================================


class ComparisonView(QGroupBox):
    """Panel showing replay comparison details."""

    def __init__(self, parent=None):
        super().__init__("Comparison", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 13px; padding: 8px;")
        layout.addWidget(self.summary_label)

        # Stats
        stats_layout = QHBoxLayout()

        self.time_label = QLabel("Time: -")
        stats_layout.addWidget(self.time_label)

        self.files_label = QLabel("Files: -")
        stats_layout.addWidget(self.files_label)

        self.checkpoints_label = QLabel("Checkpoints: -")
        stats_layout.addWidget(self.checkpoints_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Diff view
        self.diff_text = QTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setFont(self.diff_text.font())
        self.diff_text.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace;")
        layout.addWidget(self.diff_text, 1)

    def show_result(self, result: ReplayResult):
        """Display replay result."""
        if not result:
            self.clear()
            return

        # Summary
        status_text = f"Status: {result.status.value}"
        if result.comparison:
            status_text += f" | Result: {result.comparison.overall_result.value}"
            self.summary_label.setText(f"{status_text}\n{result.comparison.summary}")
        else:
            self.summary_label.setText(status_text)

        # Stats
        self.time_label.setText(f"Duration: {result.duration_seconds:.1f}s")

        if result.comparison:
            comp = result.comparison
            self.files_label.setText(
                f"Files: {comp.files_identical} identical, {comp.files_different} different"
            )
            self.checkpoints_label.setText(
                f"Checkpoints: {comp.checkpoints_identical} identical, {comp.checkpoints_different} different"
            )

            # Time comparison
            if comp.original_total_time > 0:
                diff_pct = comp.time_difference_percent
                sign = "+" if diff_pct > 0 else ""
                self.time_label.setText(
                    f"Duration: {result.duration_seconds:.1f}s ({sign}{diff_pct:.1f}% vs original)"
                )

        # Diff
        diff_lines = []
        if result.comparison:
            for sc in result.comparison.stage_comparisons:
                if sc.output_diff:
                    diff_lines.append(f"=== Stage: {sc.stage.value} ===")
                    diff_lines.extend(sc.output_diff)
                    diff_lines.append("")

        if diff_lines:
            self.diff_text.setPlainText("\n".join(diff_lines))
        else:
            self.diff_text.setPlainText("No differences found")

    def clear(self):
        self.summary_label.setText("")
        self.time_label.setText("Time: -")
        self.files_label.setText("Files: -")
        self.checkpoints_label.setText("Checkpoints: -")
        self.diff_text.clear()


# =============================================================================
# Main Replay Panel
# =============================================================================


class ReplayPanel(QWidget):
    """Main replay management panel."""

    replay_started = Signal(str)  # replay_id
    replay_completed = Signal(str, bool)  # replay_id, success

    def __init__(self, workspace_path: Path, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self.engine: Optional[ReplayEngine] = None
        self.store: Optional[StateStore] = None
        self.thread_pool = QThreadPool()
        self._current_result: Optional[ReplayResult] = None

        self._setup_ui()
        self._init_engine()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Replay / Simulation")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_all)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # New Replay tab
        new_replay_widget = QWidget()
        new_replay_layout = QVBoxLayout(new_replay_widget)
        new_replay_layout.setContentsMargins(0, 8, 0, 0)

        # Config panel
        self.config_panel = ReplayConfigPanel()
        new_replay_layout.addWidget(self.config_panel)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v")
        self.progress_bar.setVisible(False)
        new_replay_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888;")
        self.progress_label.setVisible(False)
        new_replay_layout.addWidget(self.progress_label)

        # Execute button
        btn_layout = QHBoxLayout()
        self.execute_btn = QPushButton("Execute Replay")
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background: #4caf50;
                color: white;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #388e3c;
            }
            QPushButton:disabled {
                background: #666;
            }
        """)
        self.execute_btn.clicked.connect(self._execute_replay)
        btn_layout.addStretch()
        btn_layout.addWidget(self.execute_btn)
        btn_layout.addStretch()
        new_replay_layout.addLayout(btn_layout)

        new_replay_layout.addStretch()
        self.tabs.addTab(new_replay_widget, "New Replay")

        # History tab
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 8, 0, 0)

        # Splitter for table and detail
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.history_table = ReplayHistoryTable()
        self.history_table.replay_selected.connect(self._on_replay_selected)
        splitter.addWidget(self.history_table)

        self.comparison_view = ComparisonView()
        splitter.addWidget(self.comparison_view)

        splitter.setSizes([300, 200])
        history_layout.addWidget(splitter, 1)

        # History actions
        history_actions = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        history_actions.addWidget(self.delete_btn)
        history_actions.addStretch()
        history_layout.addLayout(history_actions)

        self.tabs.addTab(history_widget, "History")

    def _init_engine(self):
        """Initialize the replay engine."""
        try:
            self.engine = ReplayEngine(self.workspace_path)
            self.store = StateStore.from_workspace(self.workspace_path)
            self._refresh_all()
        except Exception as e:
            logger.error(f"Failed to initialize replay engine: {e}")

    def _refresh_all(self):
        """Refresh runs and replay history."""
        if not self.engine or not self.store:
            return

        # Load runs
        runs_worker = LoadRunsWorker(self.store)
        runs_worker.signals.runs_loaded.connect(self._on_runs_loaded)
        self.thread_pool.start(runs_worker)

        # Load replays
        replays_worker = LoadReplaysWorker(self.engine)
        replays_worker.signals.replays_loaded.connect(self._on_replays_loaded)
        self.thread_pool.start(replays_worker)

    @Slot(list)
    def _on_runs_loaded(self, runs: list):
        # Transform runs to include task summary
        run_data = []
        for run in runs:
            run_id = run.get("run_id", "")
            try:
                state = self.store.load_state(run_id)
                task_summary = ""
                if state and state.task:
                    task_summary = state.task.description[:50] if state.task.description else ""
                run_data.append({"run_id": run_id, "task_summary": task_summary})
            except Exception:
                run_data.append({"run_id": run_id, "task_summary": ""})

        self.config_panel.set_runs(run_data)

    @Slot(list)
    def _on_replays_loaded(self, replays: list):
        self.history_table.load_replays(replays)

    def _execute_replay(self):
        """Execute the configured replay."""
        if not self.engine:
            QMessageBox.warning(self, "Error", "Replay engine not initialized")
            return

        run_id, config = self.config_panel.get_config()
        if not run_id:
            QMessageBox.warning(self, "Error", "Please select a run to replay")
            return

        # Disable button and show progress
        self.execute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting replay...")

        # Start worker
        worker = ReplayWorker(self.engine, run_id, config)
        worker.signals.progress.connect(self._on_replay_progress)
        worker.signals.result.connect(self._on_replay_result)
        worker.signals.error.connect(self._on_replay_error)
        worker.signals.finished.connect(self._on_replay_finished)

        self.thread_pool.start(worker)
        self.replay_started.emit(run_id)

    @Slot(str, float)
    def _on_replay_progress(self, message: str, percent: float):
        self.progress_bar.setValue(int(percent * 100))
        self.progress_label.setText(message)

    @Slot(object)
    def _on_replay_result(self, result: ReplayResult):
        self._current_result = result

        if result.success:
            QMessageBox.information(
                self,
                "Replay Complete",
                f"Replay completed successfully!\n\n"
                f"Result: {result.comparison.overall_result.value if result.comparison else 'N/A'}\n"
                f"Duration: {result.duration_seconds:.1f}s"
            )
        else:
            QMessageBox.warning(
                self,
                "Replay Failed",
                f"Replay failed: {result.error or 'Unknown error'}"
            )

        self.replay_completed.emit(result.replay_id, result.success)
        self._refresh_all()

        # Switch to history tab
        self.tabs.setCurrentIndex(1)

    @Slot(str)
    def _on_replay_error(self, error: str):
        QMessageBox.critical(self, "Error", f"Replay error: {error}")

    def _on_replay_finished(self):
        self.execute_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    def _on_replay_selected(self, replay_id: str):
        """Handle replay selection in history."""
        if not self.engine:
            return

        self.delete_btn.setEnabled(True)

        result = self.engine.get_replay(replay_id)
        if result:
            self._current_result = result
            self.comparison_view.show_result(result)
        else:
            self.comparison_view.clear()

    def select_run(self, run_id: str):
        """Select a run in the replay configuration and show the setup tab."""
        self.tabs.setCurrentIndex(0)
        self.config_panel.select_run(run_id)

    def _delete_selected(self):
        """Delete selected replay."""
        if not self._current_result or not self.engine:
            return

        reply = QMessageBox.question(
            self,
            "Delete Replay",
            f"Delete replay '{self._current_result.replay_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.engine.delete_replay(self._current_result.replay_id):
                self._current_result = None
                self.comparison_view.clear()
                self.delete_btn.setEnabled(False)
                self._refresh_all()
