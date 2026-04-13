"""Policy management panel for the AI Orchestrator GUI.

Provides UI for managing policy rules and viewing decision history.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    QLineEdit,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QTabWidget,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QScrollArea,
)

from orchestrator.policy_engine import PolicyEngine
from orchestrator.policy_models import (
    PolicyAction,
    PolicyRule,
    PolicyDecision,
    PolicyCondition,
    ConditionOperator,
    PolicyStats,
)

logger = logging.getLogger("ai_orchestrator.gui.policy_panel")


# =============================================================================
# Worker Signals and Classes
# =============================================================================


class PolicyWorkerSignals(QObject):
    """Signals for policy workers."""
    finished = Signal()
    error = Signal(str)
    rules_loaded = Signal(list)  # List[PolicyRule]
    decisions_loaded = Signal(list)  # List[PolicyDecision]
    stats_loaded = Signal(object)  # PolicyStats
    rule_saved = Signal(object)  # PolicyRule


class LoadRulesWorker(QRunnable):
    """Worker to load policy rules."""

    def __init__(self, engine: PolicyEngine):
        super().__init__()
        self.engine = engine
        self.signals = PolicyWorkerSignals()

    def run(self):
        try:
            rules = self.engine.get_rules()
            self.signals.rules_loaded.emit(rules)
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class LoadDecisionsWorker(QRunnable):
    """Worker to load decision history."""

    def __init__(self, engine: PolicyEngine, limit: int = 100):
        super().__init__()
        self.engine = engine
        self.limit = limit
        self.signals = PolicyWorkerSignals()

    def run(self):
        try:
            decisions = self.engine.get_decisions(limit=self.limit)
            self.signals.decisions_loaded.emit(decisions)
        except Exception as e:
            logger.error(f"Error loading decisions: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class LoadStatsWorker(QRunnable):
    """Worker to load policy statistics."""

    def __init__(self, engine: PolicyEngine):
        super().__init__()
        self.engine = engine
        self.signals = PolicyWorkerSignals()

    def run(self):
        try:
            stats = self.engine.get_stats()
            self.signals.stats_loaded.emit(stats)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# =============================================================================
# Stats Card Widget
# =============================================================================


class StatsCard(QFrame):
    """Card displaying a single statistic."""

    def __init__(self, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("statsCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#statsCard {
                background: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4fc3f7;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 12px; color: #888;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


# =============================================================================
# Stats Bar Widget
# =============================================================================


class PolicyStatsBar(QWidget):
    """Bar showing policy statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.total_card = StatsCard("Total Decisions")
        self.approved_card = StatsCard("Auto-Approved")
        self.rejected_card = StatsCard("Auto-Rejected")
        self.human_card = StatsCard("Required Human")
        self.override_card = StatsCard("Override Rate")

        layout.addWidget(self.total_card)
        layout.addWidget(self.approved_card)
        layout.addWidget(self.rejected_card)
        layout.addWidget(self.human_card)
        layout.addWidget(self.override_card)
        layout.addStretch()

    def update_stats(self, stats: PolicyStats):
        self.total_card.set_value(str(stats.total_decisions))
        self.approved_card.set_value(str(stats.auto_approved))
        self.rejected_card.set_value(str(stats.auto_rejected))
        self.human_card.set_value(str(stats.required_human))
        self.override_card.set_value(f"{stats.override_rate:.1f}%")


# =============================================================================
# Action Badge
# =============================================================================


class ActionBadge(QLabel):
    """Badge showing policy action."""

    COLORS = {
        PolicyAction.APPROVE: ("#4caf50", "#1b5e20"),
        PolicyAction.REJECT: ("#f44336", "#b71c1c"),
        PolicyAction.REQUIRE_HUMAN: ("#ff9800", "#e65100"),
    }

    def __init__(self, action: PolicyAction, parent=None):
        super().__init__(parent)
        self.set_action(action)

    def set_action(self, action: PolicyAction):
        bg, border = self.COLORS.get(action, ("#666", "#444"))
        self.setText(action.value.replace("_", " ").title())
        self.setStyleSheet(f"""
            background: {bg};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)


# =============================================================================
# Rules Table
# =============================================================================


class RulesTable(QTableWidget):
    """Table displaying policy rules."""

    rule_selected = Signal(object)  # PolicyRule
    rule_toggle = Signal(str, bool)  # rule_id, enabled
    rule_delete = Signal(str)  # rule_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Enabled", "Priority", "Name", "Action", "Conditions", "Builtin"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(0, 60)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(5, 60)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self._rules: dict = {}

    def load_rules(self, rules: list):
        self.setRowCount(0)
        self._rules.clear()

        for rule in rules:
            self._add_rule_row(rule)

    def _add_rule_row(self, rule: PolicyRule):
        row = self.rowCount()
        self.insertRow(row)
        self._rules[row] = rule

        # Enabled checkbox
        enabled_cb = QCheckBox()
        enabled_cb.setChecked(rule.enabled)
        enabled_cb.stateChanged.connect(
            lambda state, r=rule: self.rule_toggle.emit(r.id, state == Qt.CheckState.Checked.value)
        )
        enabled_widget = QWidget()
        enabled_layout = QHBoxLayout(enabled_widget)
        enabled_layout.addWidget(enabled_cb)
        enabled_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        enabled_layout.setContentsMargins(0, 0, 0, 0)
        self.setCellWidget(row, 0, enabled_widget)

        # Priority
        priority_item = QTableWidgetItem(str(rule.priority))
        priority_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 1, priority_item)

        # Name
        name_item = QTableWidgetItem(rule.name)
        self.setItem(row, 2, name_item)

        # Action badge
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.addWidget(ActionBadge(rule.action))
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.setContentsMargins(4, 4, 4, 4)
        self.setCellWidget(row, 3, action_widget)

        # Conditions summary
        conditions_text = "; ".join(
            f"{c.field} {c.operator.value}" for c in rule.conditions[:2]
        )
        if len(rule.conditions) > 2:
            conditions_text += f" (+{len(rule.conditions) - 2} more)"
        conditions_item = QTableWidgetItem(conditions_text)
        self.setItem(row, 4, conditions_item)

        # Builtin
        builtin_item = QTableWidgetItem("✓" if rule.builtin else "")
        builtin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 5, builtin_item)

    def _on_selection_changed(self):
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            rule = self._rules.get(row)
            if rule:
                self.rule_selected.emit(rule)


# =============================================================================
# Rule Detail Panel
# =============================================================================


class RuleDetailPanel(QGroupBox):
    """Panel showing rule details."""

    def __init__(self, parent=None):
        super().__init__("Rule Details", parent)
        layout = QFormLayout(self)

        self.id_label = QLabel("-")
        self.name_label = QLabel("-")
        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        self.action_label = QLabel("-")
        self.priority_label = QLabel("-")
        self.enabled_label = QLabel("-")
        self.builtin_label = QLabel("-")
        self.conditions_list = QListWidget()
        self.conditions_list.setMaximumHeight(100)

        layout.addRow("ID:", self.id_label)
        layout.addRow("Name:", self.name_label)
        layout.addRow("Description:", self.description_label)
        layout.addRow("Action:", self.action_label)
        layout.addRow("Priority:", self.priority_label)
        layout.addRow("Enabled:", self.enabled_label)
        layout.addRow("Builtin:", self.builtin_label)
        layout.addRow("Conditions:", self.conditions_list)

    def show_rule(self, rule: PolicyRule):
        self.id_label.setText(rule.id)
        self.name_label.setText(rule.name)
        self.description_label.setText(rule.description or "-")
        self.action_label.setText(rule.action.value)
        self.priority_label.setText(str(rule.priority))
        self.enabled_label.setText("Yes" if rule.enabled else "No")
        self.builtin_label.setText("Yes" if rule.builtin else "No")

        self.conditions_list.clear()
        for cond in rule.conditions:
            text = f"{cond.field} {cond.operator.value}"
            if cond.value is not None:
                text += f" {cond.value}"
            self.conditions_list.addItem(text)

    def clear(self):
        self.id_label.setText("-")
        self.name_label.setText("-")
        self.description_label.setText("-")
        self.action_label.setText("-")
        self.priority_label.setText("-")
        self.enabled_label.setText("-")
        self.builtin_label.setText("-")
        self.conditions_list.clear()


# =============================================================================
# Decisions Table
# =============================================================================


class DecisionsTable(QTableWidget):
    """Table displaying decision history."""

    decision_selected = Signal(object)  # PolicyDecision

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Time", "Checkpoint", "Rule", "Decision", "Overridden", "Reason"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.setColumnWidth(0, 140)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(4, 80)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        self._decisions: dict = {}

    def load_decisions(self, decisions: list):
        self.setRowCount(0)
        self._decisions.clear()

        for decision in decisions:
            self._add_decision_row(decision)

    def _add_decision_row(self, decision: PolicyDecision):
        row = self.rowCount()
        self.insertRow(row)
        self._decisions[row] = decision

        # Timestamp
        time_str = decision.timestamp.strftime("%Y-%m-%d %H:%M") if decision.timestamp else "-"
        time_item = QTableWidgetItem(time_str)
        self.setItem(row, 0, time_item)

        # Checkpoint ID (abbreviated)
        cp_id = decision.checkpoint_id[:8] if decision.checkpoint_id else "-"
        cp_item = QTableWidgetItem(cp_id)
        self.setItem(row, 1, cp_item)

        # Rule name
        rule_item = QTableWidgetItem(decision.rule_name or "(no match)")
        self.setItem(row, 2, rule_item)

        # Decision badge
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.addWidget(ActionBadge(decision.decision))
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.setContentsMargins(4, 4, 4, 4)
        self.setCellWidget(row, 3, action_widget)

        # Overridden
        override_item = QTableWidgetItem("✓" if decision.was_overridden else "")
        override_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 4, override_item)

        # Reason (truncated)
        reason = decision.reason[:50] + "..." if len(decision.reason) > 50 else decision.reason
        reason_item = QTableWidgetItem(reason)
        self.setItem(row, 5, reason_item)


# =============================================================================
# Rule Editor Dialog
# =============================================================================


class RuleEditorDialog(QDialog):
    """Dialog for creating/editing policy rules."""

    def __init__(self, rule: Optional[PolicyRule] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Rule" if rule else "New Rule")
        self.setMinimumWidth(500)
        self.rule = rule
        self._setup_ui()

        if rule:
            self._load_rule(rule)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Basic info
        form = QFormLayout()

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("unique_rule_id")
        if self.rule:
            self.id_edit.setEnabled(False)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Rule Name")

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Description...")

        self.action_combo = QComboBox()
        for action in PolicyAction:
            self.action_combo.addItem(action.value, action)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 1000)
        self.priority_spin.setValue(100)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)

        form.addRow("ID:", self.id_edit)
        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.description_edit)
        form.addRow("Action:", self.action_combo)
        form.addRow("Priority:", self.priority_spin)
        form.addRow("", self.enabled_check)

        layout.addLayout(form)

        # Conditions
        conditions_group = QGroupBox("Conditions (all must match)")
        conditions_layout = QVBoxLayout(conditions_group)

        self.conditions_list = QListWidget()
        self.conditions_list.setMaximumHeight(120)
        conditions_layout.addWidget(self.conditions_list)

        cond_buttons = QHBoxLayout()
        self.add_condition_btn = QPushButton("Add Condition")
        self.add_condition_btn.clicked.connect(self._add_condition)
        self.remove_condition_btn = QPushButton("Remove")
        self.remove_condition_btn.clicked.connect(self._remove_condition)

        cond_buttons.addWidget(self.add_condition_btn)
        cond_buttons.addWidget(self.remove_condition_btn)
        cond_buttons.addStretch()
        conditions_layout.addLayout(cond_buttons)

        layout.addWidget(conditions_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._conditions: list = []

    def _load_rule(self, rule: PolicyRule):
        self.id_edit.setText(rule.id)
        self.name_edit.setText(rule.name)
        self.description_edit.setPlainText(rule.description or "")
        self.priority_spin.setValue(rule.priority)
        self.enabled_check.setChecked(rule.enabled)

        idx = self.action_combo.findData(rule.action)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)

        self._conditions = list(rule.conditions)
        self._refresh_conditions_list()

    def _refresh_conditions_list(self):
        self.conditions_list.clear()
        for cond in self._conditions:
            text = f"{cond.field} {cond.operator.value}"
            if cond.value is not None:
                text += f" {cond.value}"
            self.conditions_list.addItem(text)

    def _add_condition(self):
        dialog = ConditionEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            condition = dialog.get_condition()
            if condition:
                self._conditions.append(condition)
                self._refresh_conditions_list()

    def _remove_condition(self):
        row = self.conditions_list.currentRow()
        if row >= 0 and row < len(self._conditions):
            del self._conditions[row]
            self._refresh_conditions_list()

    def get_rule(self) -> Optional[PolicyRule]:
        """Get the rule from the dialog."""
        rule_id = self.id_edit.text().strip()
        name = self.name_edit.text().strip()

        if not rule_id or not name:
            QMessageBox.warning(self, "Validation", "ID and Name are required.")
            return None

        if not self._conditions:
            QMessageBox.warning(self, "Validation", "At least one condition is required.")
            return None

        return PolicyRule(
            id=rule_id,
            name=name,
            description=self.description_edit.toPlainText().strip(),
            conditions=self._conditions,
            action=self.action_combo.currentData(),
            priority=self.priority_spin.value(),
            enabled=self.enabled_check.isChecked(),
            builtin=self.rule.builtin if self.rule else False,
        )


# =============================================================================
# Condition Editor Dialog
# =============================================================================


class ConditionEditorDialog(QDialog):
    """Dialog for editing a condition."""

    COMMON_FIELDS = [
        "checkpoint.type",
        "checkpoint.severity",
        "has_delete",
        "has_migration",
        "has_force_push",
        "has_destructive_git",
        "affected_files_count",
        "git_diff_size",
        "failure_count",
        "command_name",
        "project_type",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Condition")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.field_combo = QComboBox()
        self.field_combo.setEditable(True)
        for field in self.COMMON_FIELDS:
            self.field_combo.addItem(field)

        self.operator_combo = QComboBox()
        for op in ConditionOperator:
            self.operator_combo.addItem(op.value, op)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value (optional for IS_TRUE/IS_FALSE)")

        layout.addRow("Field:", self.field_combo)
        layout.addRow("Operator:", self.operator_combo)
        layout.addRow("Value:", self.value_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_condition(self) -> Optional[PolicyCondition]:
        field = self.field_combo.currentText().strip()
        if not field:
            return None

        operator = self.operator_combo.currentData()
        value_text = self.value_edit.text().strip()

        # Parse value
        value = None
        if value_text:
            # Try to parse as number
            try:
                if "." in value_text:
                    value = float(value_text)
                else:
                    value = int(value_text)
            except ValueError:
                # Keep as string
                value = value_text

        return PolicyCondition(field=field, operator=operator, value=value)


# =============================================================================
# Policy Panel
# =============================================================================


class PolicyPanel(QWidget):
    """Main policy management panel."""

    rule_changed = Signal()  # Emitted when rules are modified

    def __init__(self, workspace_path: Path, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self.engine: Optional[PolicyEngine] = None
        self.thread_pool = QThreadPool()

        self._setup_ui()
        self._init_engine()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Policy Engine")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_all)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        # Stats bar
        self.stats_bar = PolicyStatsBar()
        layout.addWidget(self.stats_bar)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Rules tab
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        rules_layout.setContentsMargins(0, 8, 0, 0)

        # Rules toolbar
        rules_toolbar = QHBoxLayout()
        self.new_rule_btn = QPushButton("New Rule")
        self.new_rule_btn.clicked.connect(self._new_rule)
        self.edit_rule_btn = QPushButton("Edit")
        self.edit_rule_btn.clicked.connect(self._edit_rule)
        self.edit_rule_btn.setEnabled(False)
        self.delete_rule_btn = QPushButton("Delete")
        self.delete_rule_btn.clicked.connect(self._delete_rule)
        self.delete_rule_btn.setEnabled(False)

        rules_toolbar.addWidget(self.new_rule_btn)
        rules_toolbar.addWidget(self.edit_rule_btn)
        rules_toolbar.addWidget(self.delete_rule_btn)
        rules_toolbar.addStretch()

        self.reset_defaults_btn = QPushButton("Reset to Defaults")
        self.reset_defaults_btn.clicked.connect(self._reset_defaults)
        rules_toolbar.addWidget(self.reset_defaults_btn)

        rules_layout.addLayout(rules_toolbar)

        # Rules splitter
        rules_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.rules_table = RulesTable()
        self.rules_table.rule_selected.connect(self._on_rule_selected)
        self.rules_table.rule_toggle.connect(self._on_rule_toggle)
        rules_splitter.addWidget(self.rules_table)

        self.rule_detail = RuleDetailPanel()
        rules_splitter.addWidget(self.rule_detail)

        rules_splitter.setSizes([600, 300])
        rules_layout.addWidget(rules_splitter, 1)

        self.tabs.addTab(rules_widget, "Rules")

        # History tab
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 8, 0, 0)

        self.decisions_table = DecisionsTable()
        history_layout.addWidget(self.decisions_table, 1)

        self.tabs.addTab(history_widget, "Decision History")

        self._selected_rule: Optional[PolicyRule] = None

    def _init_engine(self):
        """Initialize the policy engine."""
        try:
            self.engine = PolicyEngine(self.workspace_path)
            self._refresh_all()
        except Exception as e:
            logger.error(f"Failed to initialize policy engine: {e}")

    def _refresh_all(self):
        """Refresh all data."""
        if not self.engine:
            return

        # Load rules
        worker = LoadRulesWorker(self.engine)
        worker.signals.rules_loaded.connect(self._on_rules_loaded)
        self.thread_pool.start(worker)

        # Load decisions
        decisions_worker = LoadDecisionsWorker(self.engine)
        decisions_worker.signals.decisions_loaded.connect(self._on_decisions_loaded)
        self.thread_pool.start(decisions_worker)

        # Load stats
        stats_worker = LoadStatsWorker(self.engine)
        stats_worker.signals.stats_loaded.connect(self._on_stats_loaded)
        self.thread_pool.start(stats_worker)

    @Slot(list)
    def _on_rules_loaded(self, rules: list):
        self.rules_table.load_rules(rules)
        self.rule_detail.clear()
        self._selected_rule = None
        self.edit_rule_btn.setEnabled(False)
        self.delete_rule_btn.setEnabled(False)

    @Slot(list)
    def _on_decisions_loaded(self, decisions: list):
        self.decisions_table.load_decisions(decisions)

    @Slot(object)
    def _on_stats_loaded(self, stats: PolicyStats):
        self.stats_bar.update_stats(stats)

    def _on_rule_selected(self, rule: PolicyRule):
        self._selected_rule = rule
        self.rule_detail.show_rule(rule)
        self.edit_rule_btn.setEnabled(True)
        self.delete_rule_btn.setEnabled(not rule.builtin)

    def _on_rule_toggle(self, rule_id: str, enabled: bool):
        if self.engine:
            try:
                self.engine.enable_rule(rule_id, enabled)
                self.rule_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to toggle rule: {e}")

    def _new_rule(self):
        dialog = RuleEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule = dialog.get_rule()
            if rule and self.engine:
                try:
                    self.engine.create_rule(rule)
                    self._refresh_all()
                    self.rule_changed.emit()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create rule: {e}")

    def _edit_rule(self):
        if not self._selected_rule:
            return

        dialog = RuleEditorDialog(rule=self._selected_rule, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule = dialog.get_rule()
            if rule and self.engine:
                try:
                    self.engine.update_rule(rule)
                    self._refresh_all()
                    self.rule_changed.emit()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to update rule: {e}")

    def _delete_rule(self):
        if not self._selected_rule or self._selected_rule.builtin:
            return

        reply = QMessageBox.question(
            self,
            "Delete Rule",
            f"Are you sure you want to delete rule '{self._selected_rule.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes and self.engine:
            try:
                self.engine.delete_rule(self._selected_rule.id)
                self._refresh_all()
                self.rule_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete rule: {e}")

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "This will reset all builtin rules to their default settings and disable custom rules. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes and self.engine:
            try:
                self.engine.store.reset_to_defaults()
                self._refresh_all()
                self.rule_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset: {e}")
