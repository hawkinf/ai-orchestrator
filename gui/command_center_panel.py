"""Command Center panel for unified operational overview."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from orchestrator.checkpoint_index import CheckpointIndex, CheckpointSummary
from orchestrator.config import OrchestratorConfig
from orchestrator.recommended_actions import RecommendedAction, RecommendedActionsEngine
from orchestrator.run_index import RunIndex, RunMetrics, RunStatus, RunSummary
from orchestrator.setup_validator import SetupValidationResult, SetupValidator
from orchestrator.system_insights import (
    SystemHealthStatus,
    SystemInsightReport,
    SystemInsightsAnalyzer,
    health_status_display,
)

from .dashboard_models import format_datetime, format_duration, get_status_display
from .mode_manager import MODE_ADVANCED, MODE_SIMPLE
from .recommended_actions_widget import RecommendedActionsWidget


HEALTH_STYLES = {
    "ok": ("OK", "#22c55e"),
    "warning": ("Warning", "#f59e0b"),
    "failed": ("Falha", "#ef4444"),
}


@dataclass
class CommandCenterSnapshot:
    runs: list[RunSummary]
    metrics: RunMetrics
    pending_checkpoints: list[CheckpointSummary]
    system_report: Optional[SystemInsightReport]
    setup_result: Optional[SetupValidationResult]
    primary_action: Optional[RecommendedAction]
    recommended_actions_count: int


class SummaryCard(QFrame):
    """Compact top-level metric card."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.value_label = QLabel("-")
        self.value_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #e6edf3;")
        layout.addWidget(self.value_label)

        self.label_label = QLabel(label)
        self.label_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(self.label_label)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        layout.addWidget(self.detail_label)

    def set_content(self, value: str, detail: str = "", color: str = "#e6edf3"):
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {color};")
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))


class PrimaryActionCard(QFrame):
    """Top action highlight."""

    action_requested = Signal(object)
    new_task_requested = Signal()
    first_task_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._action: Optional[RecommendedAction] = None
        self._first_task_pending = False
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        eyebrow = QLabel("Próxima ação")
        eyebrow.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: 600;")
        layout.addWidget(eyebrow)

        self.title_label = QLabel("Nenhuma urgência detectada.")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #e6edf3;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.reason_label = QLabel("Quando houver um sinal operacional importante, ele aparecerá aqui.")
        self.reason_label.setWordWrap(True)
        self.reason_label.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        layout.addWidget(self.reason_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.primary_button = QPushButton("Nova Tarefa")
        self.primary_button.clicked.connect(self._emit_primary_action)
        button_row.addWidget(self.primary_button)

        self.secondary_button = QPushButton("Criar primeira tarefa guiada")
        self.secondary_button.setProperty("secondary", True)
        self.secondary_button.clicked.connect(self.first_task_requested.emit)
        button_row.addWidget(self.secondary_button)

        button_row.addStretch()
        layout.addLayout(button_row)

    def set_action(self, action: Optional[RecommendedAction], *, first_task_pending: bool):
        self._action = action
        self._first_task_pending = first_task_pending

        if action:
            self.title_label.setText(action.title)
            self.reason_label.setText(action.recommendation_reason or action.description)
            self.primary_button.setText("Executar ação")
        else:
            if first_task_pending:
                self.title_label.setText("Crie sua primeira tarefa guiada.")
                self.reason_label.setText("O ambiente já está configurado o suficiente para começar com uma execução pequena e segura.")
                self.primary_button.setText("Criar primeira tarefa guiada")
            else:
                self.title_label.setText("Sistema pronto para a próxima execução.")
                self.reason_label.setText("Se não houver alertas urgentes, comece uma nova tarefa ou revise as execuções recentes.")
                self.primary_button.setText("Nova Tarefa")

        self.secondary_button.setVisible(first_task_pending and action is not None)

    def _emit_primary_action(self):
        if self._action:
            self.action_requested.emit(self._action)
            return
        if self._first_task_pending:
            self.first_task_requested.emit()
            return
        self.new_task_requested.emit()


class RecentRunRow(QFrame):
    """Compact recent-run row."""

    open_requested = Signal(str)

    def __init__(self, run: RunSummary, parent=None):
        super().__init__(parent)
        self.run = run
        self.setStyleSheet(
            """
            QFrame {
                background-color: #0f141b;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(2)

        title = QLabel(run.task_summary or run.plan_objective or run.run_id)
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e6edf3;")
        title.setWordWrap(True)
        left.addWidget(title)

        subtitle = QLabel(f"{run.run_id[:12]} · {run.project_type or 'generic'}")
        subtitle.setStyleSheet("font-size: 11px; color: #8b949e;")
        left.addWidget(subtitle)
        layout.addLayout(left, 1)

        status_text, status_color = get_status_display(run.status)
        status = QLabel(status_text)
        status.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {status_color}; background-color: {status_color}20; padding: 2px 8px; border-radius: 10px;"
        )
        layout.addWidget(status)

        meta = QLabel(f"{run.current_stage or '-'} · {format_duration(run.duration_seconds)}")
        meta.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(meta)

        open_btn = QPushButton("Abrir")
        open_btn.setProperty("secondary", True)
        open_btn.clicked.connect(lambda: self.open_requested.emit(run.run_id))
        layout.addWidget(open_btn)


class HealthStatusItem(QFrame):
    """Health check chip."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #0f141b;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 12px; color: #c9d1d9; font-weight: 600;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.status_badge = QLabel("")
        layout.addWidget(self.status_badge)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(self.summary_label)

    def set_item(self, title: str, status_key: str, summary: str):
        label, color = HEALTH_STYLES[status_key]
        self.title_label.setText(title)
        self.summary_label.setText(summary)
        self.status_badge.setText(label)
        self.status_badge.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {color}; background-color: {color}20; padding: 2px 7px; border-radius: 8px;"
        )


class CommandCenterPanel(QWidget):
    """Unified cockpit for operational overview."""

    run_selected = Signal(str)
    navigate_to_new_task = Signal()
    start_first_task = Signal()
    open_checkpoints = Signal()
    open_diagnostics = Signal()
    open_system_insights = Signal()
    open_runs = Signal()
    recommended_action_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_path: Optional[Path] = None
        self._project_path: Optional[Path] = None
        self._config: Optional[OrchestratorConfig] = None
        self._interface_mode = MODE_SIMPLE
        self._first_task_pending = False
        self._snapshot: Optional[CommandCenterSnapshot] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 20, 24, 20)
        self.content_layout.setSpacing(16)
        scroll.setWidget(content)

        header = QVBoxLayout()
        header.setSpacing(6)

        title = QLabel("Command Center")
        title.setProperty("heading", True)
        header.addWidget(title)

        subtitle = QLabel("Visão operacional rápida para decidir o que fazer agora.")
        subtitle.setProperty("subheading", True)
        subtitle.setWordWrap(True)
        header.addWidget(subtitle)
        self.content_layout.addLayout(header)

        self.overview_frame = QFrame()
        self.overview_frame.setProperty("card", True)
        overview_layout = QVBoxLayout(self.overview_frame)
        overview_layout.setContentsMargins(18, 16, 18, 16)
        overview_layout.setSpacing(14)

        self.executive_summary = QLabel("Aguardando dados do workspace.")
        self.executive_summary.setWordWrap(True)
        self.executive_summary.setStyleSheet("font-size: 13px; color: #c9d1d9;")
        overview_layout.addWidget(self.executive_summary)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)

        self.summary_cards = {
            "health": SummaryCard("Saúde do sistema"),
            "runs": SummaryCard("Runs recentes"),
            "failures": SummaryCard("Falhas recentes"),
            "checkpoints": SummaryCard("Checkpoints pendentes"),
            "actions": SummaryCard("Ações prioritárias"),
            "last_run": SummaryCard("Última run"),
        }

        positions = [
            ("health", 0, 0),
            ("runs", 0, 1),
            ("failures", 0, 2),
            ("checkpoints", 1, 0),
            ("actions", 1, 1),
            ("last_run", 1, 2),
        ]
        for key, row, col in positions:
            summary_grid.addWidget(self.summary_cards[key], row, col)

        overview_layout.addLayout(summary_grid)
        self.content_layout.addWidget(self.overview_frame)

        self.primary_action_card = PrimaryActionCard()
        self.primary_action_card.action_requested.connect(self.recommended_action_requested.emit)
        self.primary_action_card.new_task_requested.connect(self.navigate_to_new_task.emit)
        self.primary_action_card.first_task_requested.connect(self.start_first_task.emit)
        self.content_layout.addWidget(self.primary_action_card)

        cta_row = QHBoxLayout()
        cta_row.setSpacing(10)

        self.new_task_btn = QPushButton("Nova Tarefa")
        self.new_task_btn.clicked.connect(self.navigate_to_new_task.emit)
        cta_row.addWidget(self.new_task_btn)

        self.first_task_btn = QPushButton("Criar primeira tarefa guiada")
        self.first_task_btn.setProperty("secondary", True)
        self.first_task_btn.clicked.connect(self.start_first_task.emit)
        cta_row.addWidget(self.first_task_btn)

        self.refresh_btn = QPushButton("Atualizar visão")
        self.refresh_btn.setProperty("secondary", True)
        self.refresh_btn.clicked.connect(self.refresh)
        cta_row.addWidget(self.refresh_btn)
        cta_row.addStretch()
        self.content_layout.addLayout(cta_row)

        body_grid = QGridLayout()
        body_grid.setHorizontalSpacing(16)
        body_grid.setVerticalSpacing(16)

        self.recent_runs_frame = QFrame()
        self.recent_runs_frame.setProperty("card", True)
        recent_layout = QVBoxLayout(self.recent_runs_frame)
        recent_layout.setContentsMargins(16, 14, 16, 14)
        recent_layout.setSpacing(10)

        recent_header = QHBoxLayout()
        recent_title = QLabel("Runs recentes")
        recent_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #e6edf3;")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()

        recent_all_btn = QPushButton("Ver todas")
        recent_all_btn.setProperty("secondary", True)
        recent_all_btn.clicked.connect(lambda: self.navigate_to_new_task.emit() if False else None)
        recent_header.addWidget(recent_all_btn)
        self._recent_all_btn = recent_all_btn
        recent_layout.addLayout(recent_header)

        self.recent_runs_hint = QLabel("As últimas execuções aparecem aqui com status e duração.")
        self.recent_runs_hint.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.recent_runs_hint.setWordWrap(True)
        recent_layout.addWidget(self.recent_runs_hint)

        self.recent_runs_list = QVBoxLayout()
        self.recent_runs_list.setSpacing(8)
        recent_layout.addLayout(self.recent_runs_list)
        body_grid.addWidget(self.recent_runs_frame, 0, 0)

        self.alerts_frame = QFrame()
        self.alerts_frame.setProperty("card", True)
        alerts_layout = QVBoxLayout(self.alerts_frame)
        alerts_layout.setContentsMargins(16, 14, 16, 14)
        alerts_layout.setSpacing(10)

        alerts_title = QLabel("Alertas e checkpoints")
        alerts_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #e6edf3;")
        alerts_layout.addWidget(alerts_title)

        self.alerts_summary = QLabel("Nenhum alerta carregado ainda.")
        self.alerts_summary.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.alerts_summary.setWordWrap(True)
        alerts_layout.addWidget(self.alerts_summary)

        self.alerts_list = QVBoxLayout()
        self.alerts_list.setSpacing(8)
        alerts_layout.addLayout(self.alerts_list)

        alert_actions = QHBoxLayout()
        checkpoints_btn = QPushButton("Abrir Checkpoints")
        checkpoints_btn.setProperty("secondary", True)
        checkpoints_btn.clicked.connect(self.open_checkpoints.emit)
        alert_actions.addWidget(checkpoints_btn)

        diagnostics_btn = QPushButton("Abrir Diagnóstico")
        diagnostics_btn.setProperty("secondary", True)
        diagnostics_btn.clicked.connect(self.open_diagnostics.emit)
        alert_actions.addWidget(diagnostics_btn)
        alert_actions.addStretch()
        alerts_layout.addLayout(alert_actions)
        body_grid.addWidget(self.alerts_frame, 0, 1)

        self.actions_widget = RecommendedActionsWidget()
        self.actions_widget.action_requested.connect(self.recommended_action_requested.emit)
        body_grid.addWidget(self.actions_widget, 1, 0, 1, 2)

        self.health_frame = QFrame()
        self.health_frame.setProperty("card", True)
        health_layout = QVBoxLayout(self.health_frame)
        health_layout.setContentsMargins(16, 14, 16, 14)
        health_layout.setSpacing(10)

        health_header = QHBoxLayout()
        health_title = QLabel("Saúde do sistema")
        health_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #e6edf3;")
        health_header.addWidget(health_title)
        health_header.addStretch()

        insights_btn = QPushButton("Abrir insights completos")
        insights_btn.setProperty("secondary", True)
        insights_btn.clicked.connect(self.open_system_insights.emit)
        health_header.addWidget(insights_btn)
        health_layout.addLayout(health_header)

        self.health_items_layout = QVBoxLayout()
        self.health_items_layout.setSpacing(8)
        health_layout.addLayout(self.health_items_layout)
        body_grid.addWidget(self.health_frame, 2, 0, 1, 2)

        body_grid.setColumnStretch(0, 3)
        body_grid.setColumnStretch(1, 2)
        self.content_layout.addLayout(body_grid)

        self._recent_all_btn.clicked.connect(lambda: self.run_selected.emit(""))

    def set_workspace(self, workspace_path: Optional[Path]):
        self._workspace_path = workspace_path
        self.refresh()

    def set_runtime_context(
        self,
        *,
        config: Optional[OrchestratorConfig],
        project_path: Optional[Path],
        first_task_pending: bool,
    ):
        self._config = config
        self._project_path = project_path
        self._first_task_pending = first_task_pending
        self.refresh()

    def set_interface_mode(self, mode: str):
        self._interface_mode = mode
        show_advanced = mode == MODE_ADVANCED
        self.health_frame.setVisible(show_advanced)
        self.summary_cards["last_run"].setVisible(show_advanced)
        self.refresh()

    def refresh(self):
        snapshot = self._build_snapshot()
        self._snapshot = snapshot
        self._render_snapshot(snapshot)

    def _build_snapshot(self) -> CommandCenterSnapshot:
        empty_metrics = RunMetrics()
        if not self._workspace_path:
            return CommandCenterSnapshot([], empty_metrics, [], None, None, None, 0)

        run_index = RunIndex(self._workspace_path)
        runs = run_index.get_all_runs(limit=8)
        metrics = run_index.get_metrics()

        pending_checkpoints: list[CheckpointSummary] = []
        try:
            checkpoint_index = CheckpointIndex(self._workspace_path)
            pending_checkpoints = checkpoint_index.get_pending_checkpoints()[:4]
        except Exception:
            pending_checkpoints = []

        system_report: Optional[SystemInsightReport] = None
        primary_action: Optional[RecommendedAction] = None
        actions_count = 0
        actions_group = None
        if runs:
            try:
                system_report = SystemInsightsAnalyzer(self._workspace_path).analyze(limit=min(max(len(runs), 10), 20))
                actions_group = RecommendedActionsEngine().from_system_report(system_report)
                if actions_group.actions:
                    primary_action = actions_group.actions[0]
                    actions_count = len(actions_group.actions)
            except Exception:
                system_report = None

        setup_result = self._validate_setup()
        return CommandCenterSnapshot(
            runs=runs,
            metrics=metrics,
            pending_checkpoints=pending_checkpoints,
            system_report=system_report,
            setup_result=setup_result,
            primary_action=primary_action,
            recommended_actions_count=actions_count,
        )

    def _validate_setup(self) -> Optional[SetupValidationResult]:
        if not self._config:
            return None

        project_path = Path(self._config.project_path or self._project_path or Path.cwd())
        workspace_path = Path(self._config.workspace_path)
        validator = SetupValidator(project_path)
        return validator.validate_minimum_configuration(
            project_path=project_path,
            workspace_path=workspace_path,
            profile=self._config.active_profile,
            executor_command=self._config.executor.command,
        )

    def _render_snapshot(self, snapshot: CommandCenterSnapshot):
        system_report = snapshot.system_report

        if system_report:
            self.executive_summary.setText(system_report.executive_summary)
            health_value = health_status_display(system_report.health_status)
            health_color = self._health_color_from_status(system_report.health_status)
        else:
            self.executive_summary.setText("Ainda não há histórico suficiente para formar uma leitura operacional completa.")
            health_value = "Sem histórico"
            health_color = "#8b949e"

        self.summary_cards["health"].set_content(health_value, "Estado operacional recente", health_color)
        self.summary_cards["runs"].set_content(str(snapshot.metrics.total_runs), "Últimas execuções lidas")
        self.summary_cards["failures"].set_content(str(snapshot.metrics.failed_runs), "Falhas no histórico recente", "#ef4444")
        self.summary_cards["checkpoints"].set_content(str(len(snapshot.pending_checkpoints)), "Aguardando decisão", "#f59e0b")
        self.summary_cards["actions"].set_content(str(snapshot.recommended_actions_count), "Próximas ações sugeridas", "#4f8cff")

        last_run = snapshot.runs[0] if snapshot.runs else None
        if last_run:
            self.summary_cards["last_run"].set_content(
                last_run.run_id[:10],
                f"{get_status_display(last_run.status)[0]} · {format_datetime(last_run.created_at)}",
                get_status_display(last_run.status)[1],
            )
        else:
            self.summary_cards["last_run"].set_content("-", "Nenhuma run concluída ainda")

        self.primary_action_card.set_action(snapshot.primary_action, first_task_pending=self._first_task_pending)
        self.first_task_btn.setVisible(self._first_task_pending)

        self._rebuild_recent_runs(snapshot.runs)
        self._rebuild_alerts(snapshot)
        self._rebuild_actions(snapshot)
        self._rebuild_health(snapshot.setup_result)

    def _rebuild_recent_runs(self, runs: list[RunSummary]):
        while self.recent_runs_list.count():
            item = self.recent_runs_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not runs:
            empty = QLabel("Nenhuma run ainda. Use Nova Tarefa para começar.")
            empty.setStyleSheet("font-size: 12px; color: #8b949e; padding: 4px 0;")
            self.recent_runs_list.addWidget(empty)
            return

        limit = 3 if self._interface_mode == MODE_SIMPLE else 5
        for run in runs[:limit]:
            row = RecentRunRow(run)
            row.open_requested.connect(self.run_selected.emit)
            self.recent_runs_list.addWidget(row)

    def _rebuild_alerts(self, snapshot: CommandCenterSnapshot):
        while self.alerts_list.count():
            item = self.alerts_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alert_lines: list[str] = []
        if snapshot.pending_checkpoints:
            alert_lines.append(f"{len(snapshot.pending_checkpoints)} checkpoint(s) pendente(s) exigem decisão.")
            for cp in snapshot.pending_checkpoints[:3]:
                alert_lines.append(f"{cp.reason_display}: {cp.task_summary or cp.run_id}")

        failed_runs = [run for run in snapshot.runs if run.status == RunStatus.FAILED]
        if failed_runs:
            alert_lines.append(f"{len(failed_runs)} run(s) recente(s) com falha.")

        if snapshot.system_report and snapshot.system_report.health_status in {
            SystemHealthStatus.DEGRADED,
            SystemHealthStatus.RECURRING_FAILURES,
        }:
            alert_lines.append("O sistema está degradado e merece revisão antes da próxima execução.")

        if not alert_lines:
            self.alerts_summary.setText("Nenhum alerta crítico no momento. O sistema segue utilizável.")
            ok = QLabel("Sem bloqueios imediatos.")
            ok.setStyleSheet("font-size: 12px; color: #22c55e;")
            self.alerts_list.addWidget(ok)
            return

        self.alerts_summary.setText("Sinais que merecem atenção agora.")
        for line in alert_lines[:4]:
            label = QLabel(f"• {line}")
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 12px; color: #c9d1d9;")
            self.alerts_list.addWidget(label)

    def _rebuild_actions(self, snapshot: CommandCenterSnapshot):
        if snapshot.system_report:
            group = RecommendedActionsEngine().from_system_report(snapshot.system_report)
            group.actions = group.actions[: (3 if self._interface_mode == MODE_SIMPLE else 5)]
            self.actions_widget.set_group(group)
        else:
            self.actions_widget.clear_group()

    def _rebuild_health(self, result: Optional[SetupValidationResult]):
        while self.health_items_layout.count():
            item = self.health_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not result:
            label = QLabel("Configure projeto, OpenAI e executor para liberar o resumo de saúde.")
            label.setStyleSheet("font-size: 12px; color: #8b949e;")
            self.health_items_layout.addWidget(label)
            return

        config_checks = [result.by_key("project_path"), result.by_key("profile")]
        config_ok = all(check.ok for check in config_checks if check)
        config_summary = "Projeto e perfil prontos." if config_ok else "Projeto ou perfil exigem ajuste."

        items = [
            ("Config", "ok" if config_ok else "failed", config_summary),
            ("OpenAI", "ok" if result.by_key("openai") and result.by_key("openai").ok else "failed", result.by_key("openai").summary if result.by_key("openai") else "-"),
            ("Executor", "ok" if result.by_key("executor") and result.by_key("executor").ok else "failed", result.by_key("executor").summary if result.by_key("executor") else "-"),
            ("Workspace", "ok" if result.by_key("workspace") and result.by_key("workspace").ok else "failed", result.by_key("workspace").summary if result.by_key("workspace") else "-"),
            ("Git", "ok" if result.by_key("git") and result.by_key("git").ok else "warning", result.by_key("git").summary if result.by_key("git") else "-"),
        ]

        for title, status_key, summary in items:
            item = HealthStatusItem()
            item.set_item(title, status_key, summary)
            self.health_items_layout.addWidget(item)

    def _health_color_from_status(self, status: SystemHealthStatus) -> str:
        if status == SystemHealthStatus.STABLE:
            return "#22c55e"
        if status == SystemHealthStatus.USABLE_WITH_ALERTS:
            return "#f59e0b"
        if status == SystemHealthStatus.DEGRADED:
            return "#f97316"
        return "#ef4444"
