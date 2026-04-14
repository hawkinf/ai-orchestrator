"""Aggregate system insights across multiple runs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from orchestrator.run_index import RunFilter, RunIndex, RunStatus, RunSummary, get_run_index
from orchestrator.run_insights import InsightCategory, InsightSeverity, InsightsAnalyzer, RunInsightReport
from orchestrator.run_timeline import TimelineBuilder, TimelineEventStatus, TimelineEventType

logger = logging.getLogger("ai_orchestrator.system_insights")


class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    MIXED = "mixed"


class SystemHealthStatus(Enum):
    STABLE = "stable"
    USABLE_WITH_ALERTS = "usable_with_alerts"
    DEGRADED = "degraded"
    RECURRING_FAILURES = "recurring_failures"


@dataclass
class AggregateMetric:
    key: str
    label: str
    value: float
    display_value: str
    direction: TrendDirection = TrendDirection.STABLE
    delta: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "display_value": self.display_value,
            "direction": self.direction.value,
            "delta": self.delta,
            "details": self.details,
        }


@dataclass
class SystemInsight:
    id: str
    category: str
    severity: str
    title: str
    message: str
    recommendation: str
    affected_run_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0
    supporting_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "recommendation": self.recommendation,
            "affected_run_ids": self.affected_run_ids,
            "confidence": self.confidence,
            "supporting_metrics": self.supporting_metrics,
        }


@dataclass
class SystemInsightReport:
    report_id: str
    generated_at: datetime
    health_status: SystemHealthStatus
    executive_summary: str
    analysis_window: Dict[str, Any]
    insights: List[SystemInsight] = field(default_factory=list)
    metrics: List[AggregateMetric] = field(default_factory=list)
    top_recommendations: List[str] = field(default_factory=list)
    total_runs: int = 0
    analyzed_run_ids: List[str] = field(default_factory=list)
    profile_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_by_severity(self, severity: str) -> List[SystemInsight]:
        return [item for item in self.insights if item.severity == severity]

    def get_by_category(self, category: str) -> List[SystemInsight]:
        return [item for item in self.insights if item.category == category]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "health_status": self.health_status.value,
            "executive_summary": self.executive_summary,
            "analysis_window": self.analysis_window,
            "insights": [item.to_dict() for item in self.insights],
            "metrics": [item.to_dict() for item in self.metrics],
            "top_recommendations": self.top_recommendations,
            "total_runs": self.total_runs,
            "analyzed_run_ids": self.analyzed_run_ids,
            "profile_breakdown": self.profile_breakdown,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Insights do Sistema",
            "",
            f"**Gerado em:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Janela analisada:** {self.analysis_window.get('label', '-')}",
            f"**Saúde do sistema:** {health_status_display(self.health_status)}",
            "",
            "## Resumo Executivo",
            "",
            self.executive_summary,
            "",
            "## Métricas Agregadas",
            "",
            "| Métrica | Valor | Tendência |",
            "|---------|-------|-----------|",
        ]
        for metric in self.metrics:
            lines.append(f"| {metric.label} | {metric.display_value} | {trend_direction_display(metric.direction)} |")

        if self.insights:
            lines.extend(["", "## Insights", ""])
            for insight in self.insights:
                lines.append(f"### {severity_icon(insight.severity)} {insight.title}")
                lines.append("")
                lines.append(insight.message)
                lines.append("")
                if insight.recommendation:
                    lines.append(f"**Recomendação:** {insight.recommendation}")
                    lines.append("")

        if self.top_recommendations:
            lines.extend(["## Ações Recomendadas", ""])
            for item in self.top_recommendations:
                lines.append(f"- {item}")

        return "\n".join(lines) + "\n"


@dataclass
class _AnalyzedRun:
    run: RunSummary
    report: Optional[RunInsightReport]
    has_validation_failure: bool = False
    has_git_failure: bool = False
    checkpoint_count: int = 0
    iteration_count: int = 1
    has_warnings: bool = False
    has_errors: bool = False


class SystemInsightsAnalyzer:
    """Aggregate operational insights across multiple runs."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.index: RunIndex = get_run_index(workspace_path)
        self.timeline_builder = TimelineBuilder(workspace_path)
        self.insights_analyzer = InsightsAnalyzer(workspace_path)
        self._insight_counter = 0

    def analyze(
        self,
        *,
        limit: int = 10,
        run_filter: Optional[RunFilter] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        profile: Optional[str] = None,
        statuses: Optional[List[RunStatus]] = None,
    ) -> SystemInsightReport:
        effective_filter = RunFilter(
            search_text=run_filter.search_text if run_filter else "",
            status_filter=statuses or (run_filter.status_filter if run_filter else None),
            profile_filter=profile or (run_filter.profile_filter if run_filter else None),
            has_checkpoint=run_filter.has_checkpoint if run_filter else None,
            has_error=run_filter.has_error if run_filter else None,
            date_from=date_from or (run_filter.date_from if run_filter else None),
            date_to=date_to or (run_filter.date_to if run_filter else None),
        )
        self.index.refresh()
        has_filter = any(
            [
                effective_filter.search_text,
                effective_filter.status_filter,
                effective_filter.profile_filter,
                effective_filter.has_checkpoint is not None,
                effective_filter.has_error is not None,
                effective_filter.date_from,
                effective_filter.date_to,
            ]
        )
        runs = self.index.filter_runs(effective_filter, limit=limit) if has_filter else self.index.get_all_runs(limit=limit)
        analyzed_runs = [self._analyze_run(run) for run in runs]
        return self._build_report(analyzed_runs, effective_filter, limit)

    def export_report(self, report: SystemInsightReport, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
        export_dir = output_dir or (self.workspace_path / "logs")
        export_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_dir / f"system_insights_{timestamp}.json"
        md_path = export_dir / f"system_insights_{timestamp}.md"
        json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        return {"json": json_path, "markdown": md_path}

    def _analyze_run(self, run: RunSummary) -> _AnalyzedRun:
        report = self.insights_analyzer.analyze_from_run_id(run.run_id)
        analyzed = _AnalyzedRun(run=run, report=report)
        state_data = self._load_state(run.run_id)
        if report:
            analyzed.checkpoint_count = report.checkpoint_count
            analyzed.iteration_count = report.iteration_count
            analyzed.has_warnings = report.has_warnings()
            analyzed.has_errors = report.has_errors()
            validation_insights = report.get_by_category(InsightCategory.VALIDATION)
            analyzed.has_validation_failure = any(item.severity == InsightSeverity.ERROR for item in validation_insights)
            git_insights = report.get_by_category(InsightCategory.GIT)
            analyzed.has_git_failure = any(item.severity == InsightSeverity.ERROR for item in git_insights)
            self._apply_state_fallbacks(analyzed, state_data)
            return analyzed

        timeline = self.timeline_builder.build_timeline(run.run_id)
        if timeline:
            for event in timeline.events:
                if event.event_type == TimelineEventType.CHECKPOINT:
                    analyzed.checkpoint_count += 1
                elif event.event_type == TimelineEventType.VALIDATION and event.status == TimelineEventStatus.FAILED:
                    analyzed.has_validation_failure = True
                elif event.event_type == TimelineEventType.GIT and event.status == TimelineEventStatus.FAILED:
                    analyzed.has_git_failure = True
                elif event.event_type == TimelineEventType.ITERATION_START:
                    analyzed.iteration_count += 1
        self._apply_state_fallbacks(analyzed, state_data)
        return analyzed

    def _load_state(self, run_id: str) -> Dict[str, Any]:
        state_file = self.workspace_path / "state" / f"{run_id}.json"
        if not state_file.exists():
            return {}
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _apply_state_fallbacks(self, analyzed: _AnalyzedRun, state_data: Dict[str, Any]):
        validation = state_data.get("validation")
        if isinstance(validation, dict) and validation.get("status") == "failed":
            analyzed.has_validation_failure = True
        git_data = state_data.get("git")
        if isinstance(git_data, dict) and git_data.get("status") == "failed":
            analyzed.has_git_failure = True
        checkpoint = state_data.get("checkpoint")
        if isinstance(checkpoint, dict) and analyzed.checkpoint_count == 0:
            analyzed.checkpoint_count = 1
        current_iteration = state_data.get("current_iteration")
        if isinstance(current_iteration, int) and current_iteration > analyzed.iteration_count:
            analyzed.iteration_count = current_iteration

    def _build_report(self, analyzed_runs: List[_AnalyzedRun], run_filter: RunFilter, limit: int) -> SystemInsightReport:
        self._insight_counter = 0
        now = datetime.now()
        metrics = self._build_metrics(analyzed_runs)
        insights = self._build_insights(analyzed_runs)
        health = self._determine_health(metrics, insights)
        return SystemInsightReport(
            report_id=f"system_insights_{now.strftime('%Y%m%d_%H%M%S')}",
            generated_at=now,
            health_status=health,
            executive_summary=self._build_summary(health, analyzed_runs, insights, metrics),
            analysis_window={
                "label": self._build_window_label(analyzed_runs, run_filter, limit),
                "limit": limit,
                "date_from": run_filter.date_from.isoformat() if run_filter.date_from else None,
                "date_to": run_filter.date_to.isoformat() if run_filter.date_to else None,
                "profile": run_filter.profile_filter,
                "statuses": [item.value for item in run_filter.status_filter or []],
            },
            insights=insights,
            metrics=metrics,
            top_recommendations=self._collect_recommendations(insights),
            total_runs=len(analyzed_runs),
            analyzed_run_ids=[item.run.run_id for item in analyzed_runs],
            profile_breakdown=self._build_profile_breakdown(analyzed_runs),
        )

    def _build_metrics(self, analyzed_runs: List[_AnalyzedRun]) -> List[AggregateMetric]:
        total_runs = len(analyzed_runs)
        if total_runs == 0:
            return [
                AggregateMetric("success_rate", "Taxa de sucesso", 0.0, "0%"),
                AggregateMetric("warning_rate", "Runs com alertas", 0.0, "0%"),
                AggregateMetric("avg_duration", "Duração média", 0.0, "-"),
                AggregateMetric("checkpoint_rate", "Runs com checkpoint", 0.0, "0%"),
                AggregateMetric("failure_rate", "Taxa de falha", 0.0, "0%"),
            ]

        completed_runs = [item for item in analyzed_runs if item.run.status == RunStatus.COMPLETED]
        failed_runs = [item for item in analyzed_runs if item.run.status == RunStatus.FAILED]
        warning_runs = [item for item in analyzed_runs if item.has_warnings or item.run.status in {RunStatus.CHECKPOINT, RunStatus.BLOCKED}]
        checkpoint_runs = [item for item in analyzed_runs if item.checkpoint_count > 0]
        durations = [item.run.duration_seconds for item in analyzed_runs if item.run.duration_seconds > 0]
        current_half, previous_half = split_recent_windows(analyzed_runs)
        current_avg_duration = average([item.run.duration_seconds for item in current_half if item.run.duration_seconds > 0])
        previous_avg_duration = average([item.run.duration_seconds for item in previous_half if item.run.duration_seconds > 0])
        current_fail_rate = percentage(len([item for item in current_half if item.run.status == RunStatus.FAILED]), len(current_half))
        previous_fail_rate = percentage(len([item for item in previous_half if item.run.status == RunStatus.FAILED]), len(previous_half))

        return [
            AggregateMetric(
                "success_rate",
                "Taxa de sucesso",
                percentage(len(completed_runs), total_runs),
                format_percent(len(completed_runs), total_runs),
                direction=trend_from_delta(
                    percentage(len([item for item in current_half if item.run.status == RunStatus.COMPLETED]), len(current_half)),
                    percentage(len([item for item in previous_half if item.run.status == RunStatus.COMPLETED]), len(previous_half)),
                    improve_when_higher=True,
                ),
            ),
            AggregateMetric(
                "warning_rate",
                "Runs com alertas",
                percentage(len(warning_runs), total_runs),
                format_percent(len(warning_runs), total_runs),
                direction=trend_from_delta(
                    percentage(len([item for item in current_half if item.has_warnings]), len(current_half)),
                    percentage(len([item for item in previous_half if item.has_warnings]), len(previous_half)),
                    improve_when_higher=False,
                ),
            ),
            AggregateMetric(
                "avg_duration",
                "Duração média",
                average(durations),
                format_duration(average(durations)),
                direction=trend_from_delta(current_avg_duration, previous_avg_duration, improve_when_higher=False),
            ),
            AggregateMetric(
                "checkpoint_rate",
                "Runs com checkpoint",
                percentage(len(checkpoint_runs), total_runs),
                format_percent(len(checkpoint_runs), total_runs),
                direction=trend_from_delta(
                    percentage(len([item for item in current_half if item.checkpoint_count > 0]), len(current_half)),
                    percentage(len([item for item in previous_half if item.checkpoint_count > 0]), len(previous_half)),
                    improve_when_higher=False,
                ),
            ),
            AggregateMetric(
                "failure_rate",
                "Taxa de falha",
                percentage(len(failed_runs), total_runs),
                format_percent(len(failed_runs), total_runs),
                direction=trend_from_delta(current_fail_rate, previous_fail_rate, improve_when_higher=False),
            ),
        ]

    def _build_insights(self, analyzed_runs: List[_AnalyzedRun]) -> List[SystemInsight]:
        if not analyzed_runs:
            return [
                self._make_insight(
                    category="trends",
                    severity="info",
                    title="Sem histórico suficiente",
                    message="Ainda não há runs suficientes para gerar padrões operacionais agregados.",
                    recommendation="Execute algumas tarefas e volte ao dashboard para ver tendências do sistema.",
                    confidence=1.0,
                )
            ]

        insights: List[SystemInsight] = []
        total_runs = len(analyzed_runs)
        validation_fail_runs = [item for item in analyzed_runs if item.has_validation_failure]
        git_fail_runs = [item for item in analyzed_runs if item.has_git_failure]
        checkpoint_runs = [item for item in analyzed_runs if item.checkpoint_count > 0]
        review_followups = [item for item in analyzed_runs if item.iteration_count >= 3]
        failed_runs = [item for item in analyzed_runs if item.run.status == RunStatus.FAILED]
        current_half, previous_half = split_recent_windows(analyzed_runs)
        current_fail_rate = percentage(len([item for item in current_half if item.run.status == RunStatus.FAILED]), len(current_half))
        previous_fail_rate = percentage(len([item for item in previous_half if item.run.status == RunStatus.FAILED]), len(previous_half))
        current_avg_duration = average([item.run.duration_seconds for item in current_half if item.run.duration_seconds > 0])
        previous_avg_duration = average([item.run.duration_seconds for item in previous_half if item.run.duration_seconds > 0])

        if len(validation_fail_runs) >= 2:
            insights.append(self._make_insight(
                category="validation",
                severity="warning" if len(validation_fail_runs) < 4 else "error",
                title="Falhas recorrentes em validação",
                message=f"{len(validation_fail_runs)} de {total_runs} runs recentes falharam em validação. Isso indica regressão recorrente na etapa final de checks.",
                recommendation="Revisar os comandos de validação do profile afetado e rodar diagnóstico antes da próxima run.",
                affected_runs=validation_fail_runs,
                confidence=0.88,
                supporting_metrics={"validation_failures": len(validation_fail_runs), "total_runs": total_runs},
            ))

        if len(checkpoint_runs) >= 3:
            insights.append(self._make_insight(
                category="checkpoint",
                severity="warning",
                title="Checkpoints frequentes",
                message=f"{len(checkpoint_runs)} runs recentes acionaram checkpoint. O fluxo está pedindo intervenção manual com frequência acima do ideal.",
                recommendation="Revisar políticas de checkpoint e reduzir o escopo inicial das tarefas mais arriscadas.",
                affected_runs=checkpoint_runs,
                confidence=0.82,
                supporting_metrics={"checkpoint_runs": len(checkpoint_runs)},
            ))

        if len(git_fail_runs) >= 2:
            insights.append(self._make_insight(
                category="git",
                severity="error" if len(git_fail_runs) >= 3 else "warning",
                title="Falhas recorrentes em Git",
                message=f"{len(git_fail_runs)} runs recentes encontraram problema na etapa de Git. Isso reduz previsibilidade de finalização e histórico.",
                recommendation="Verificar estado do repositório, branch atual e permissões antes da próxima execução automatizada.",
                affected_runs=git_fail_runs,
                confidence=0.9,
                supporting_metrics={"git_failures": len(git_fail_runs)},
            ))

        if current_fail_rate - previous_fail_rate >= 20:
            insights.append(self._make_insight(
                category="trends",
                severity="error" if current_fail_rate >= 50 else "warning",
                title="Aumento recente de falhas",
                message=f"A taxa de falha subiu de {previous_fail_rate:.0f}% para {current_fail_rate:.0f}% na metade mais recente da janela analisada.",
                recommendation="Avaliar replay nas runs recentes com falha e confirmar configuração do executor antes da próxima tarefa.",
                affected_runs=current_half,
                confidence=0.85,
                supporting_metrics={"previous_failure_rate": previous_fail_rate, "current_failure_rate": current_fail_rate},
            ))

        if current_avg_duration > 0 and previous_avg_duration > 0 and current_avg_duration - previous_avg_duration >= 120:
            insights.append(self._make_insight(
                category="performance",
                severity="warning",
                title="Duração média em alta",
                message=f"A duração média subiu de {format_duration(previous_avg_duration)} para {format_duration(current_avg_duration)} na metade mais recente das runs.",
                recommendation="Reduzir escopo das tarefas iniciais e revisar se o profile está rodando validações além do necessário.",
                affected_runs=current_half,
                confidence=0.8,
                supporting_metrics={"previous_avg_duration": previous_avg_duration, "current_avg_duration": current_avg_duration},
            ))

        return self._append_secondary_insights(insights, analyzed_runs, review_followups, failed_runs)

    def _append_secondary_insights(
        self,
        insights: List[SystemInsight],
        analyzed_runs: List[_AnalyzedRun],
        review_followups: List[_AnalyzedRun],
        failed_runs: List[_AnalyzedRun],
    ) -> List[SystemInsight]:
        slowest_profile = self._slowest_profile(analyzed_runs)
        if slowest_profile:
            insights.append(self._make_insight(
                category="performance",
                severity="info",
                title=f"Profile {slowest_profile['profile']} está mais lento",
                message=f"O profile {slowest_profile['profile']} tem duração média de {format_duration(slowest_profile['avg_duration'])}, acima dos demais perfis analisados.",
                recommendation=f"Revisar comandos de validação e escopo típico das tarefas em {slowest_profile['profile']}.",
                affected_runs=slowest_profile["runs"],
                confidence=0.77,
                supporting_metrics={"profile": slowest_profile["profile"], "avg_duration": slowest_profile["avg_duration"]},
            ))

        if len(review_followups) >= 2:
            insights.append(self._make_insight(
                category="review",
                severity="warning",
                title="Muitas runs exigindo follow-up",
                message=f"{len(review_followups)} runs precisaram de 3 ou mais iterações. Isso sugere tarefas largas demais ou revisão detectando ajustes repetidos.",
                recommendation="Quebrar tarefas grandes em objetivos menores e revisar as instruções dadas ao planner.",
                affected_runs=review_followups,
                confidence=0.78,
                supporting_metrics={"follow_up_runs": len(review_followups)},
            ))

        if failed_runs and len(failed_runs) <= 1:
            insights.append(self._make_insight(
                category="reliability",
                severity="info",
                title="Sistema utilizável com falha isolada",
                message="Há uma falha recente, mas sem padrão recorrente claro nas últimas runs.",
                recommendation="Revisar a run com falha e seguir com tarefas menores para confirmar estabilidade.",
                affected_runs=failed_runs,
                confidence=0.72,
                supporting_metrics={"failed_runs": len(failed_runs)},
            ))

        if not insights:
            extra = ""
            ranking = self._profile_success_summary(analyzed_runs)
            if ranking:
                extra = f" O melhor resultado recente aparece em {ranking[0]}."
            insights.append(self._make_insight(
                category="reliability",
                severity="success",
                title="Histórico recente estável",
                message=f"As runs recentes não mostram concentração de falhas, checkpoints excessivos ou degradação clara de duração.{extra}",
                recommendation="Manter o fluxo atual e usar replay apenas em regressões pontuais.",
                affected_runs=analyzed_runs,
                confidence=0.8,
                supporting_metrics={"failed_runs": len(failed_runs)},
            ))

        return sort_insights(insights)

    def _determine_health(self, metrics: List[AggregateMetric], insights: List[SystemInsight]) -> SystemHealthStatus:
        failure_rate = metric_value(metrics, "failure_rate")
        warning_rate = metric_value(metrics, "warning_rate")
        checkpoint_rate = metric_value(metrics, "checkpoint_rate")
        severe_levels = {item.severity for item in insights}
        if "error" in severe_levels or failure_rate >= 45:
            return SystemHealthStatus.RECURRING_FAILURES
        if failure_rate >= 25 or checkpoint_rate >= 40:
            return SystemHealthStatus.DEGRADED
        if warning_rate >= 20 or "warning" in severe_levels:
            return SystemHealthStatus.USABLE_WITH_ALERTS
        return SystemHealthStatus.STABLE

    def _build_summary(self, health: SystemHealthStatus, analyzed_runs: List[_AnalyzedRun], insights: List[SystemInsight], metrics: List[AggregateMetric]) -> str:
        total_runs = len(analyzed_runs)
        if total_runs == 0:
            return "Ainda não há runs suficientes para resumir o comportamento operacional recente do sistema."
        failure_rate = metric_value(metrics, "failure_rate")
        warning_rate = metric_value(metrics, "warning_rate")
        checkpoint_rate = metric_value(metrics, "checkpoint_rate")
        avg_duration = metric_value(metrics, "avg_duration")
        if health == SystemHealthStatus.STABLE:
            return f"As últimas {total_runs} runs mostram um sistema estável, com taxa de falha de {failure_rate:.0f}% e duração média de {format_duration(avg_duration)}."
        if health == SystemHealthStatus.USABLE_WITH_ALERTS:
            top = insights[0].message if insights else "Há alertas operacionais recentes."
            return f"O sistema está utilizável com alertas. {top} {warning_rate:.0f}% das runs recentes registraram avisos relevantes."
        if health == SystemHealthStatus.DEGRADED:
            return f"O sistema está degradado nas últimas {total_runs} runs, com {failure_rate:.0f}% de falhas e {checkpoint_rate:.0f}% de runs exigindo checkpoint."
        return f"As últimas {total_runs} runs indicam falhas recorrentes. A taxa de falha chegou a {failure_rate:.0f}% e os principais sinais pedem correção antes de ampliar o volume de tarefas."

    def _collect_recommendations(self, insights: List[SystemInsight]) -> List[str]:
        seen: List[str] = []
        for insight in insights:
            if insight.recommendation and insight.recommendation not in seen:
                seen.append(insight.recommendation)
        return seen[:5]

    def _build_profile_breakdown(self, analyzed_runs: List[_AnalyzedRun]) -> Dict[str, Dict[str, Any]]:
        breakdown: Dict[str, Dict[str, Any]] = {}
        for item in analyzed_runs:
            profile = item.run.project_type or "generic"
            entry = breakdown.setdefault(profile, {"run_count": 0, "completed": 0, "failed": 0, "warning_runs": 0, "_durations": []})
            entry["run_count"] += 1
            if item.run.status == RunStatus.COMPLETED:
                entry["completed"] += 1
            elif item.run.status == RunStatus.FAILED:
                entry["failed"] += 1
            if item.has_warnings:
                entry["warning_runs"] += 1
            if item.run.duration_seconds > 0:
                entry["_durations"].append(item.run.duration_seconds)
        for profile, entry in breakdown.items():
            durations = entry.pop("_durations")
            entry["avg_duration_seconds"] = average(durations)
            entry["success_rate"] = percentage(entry["completed"], entry["run_count"])
        return breakdown

    def _slowest_profile(self, analyzed_runs: List[_AnalyzedRun]) -> Optional[Dict[str, Any]]:
        groups: Dict[str, List[_AnalyzedRun]] = {}
        for item in analyzed_runs:
            if item.run.duration_seconds > 0:
                groups.setdefault(item.run.project_type or "generic", []).append(item)
        ranked = []
        for profile, items in groups.items():
            if len(items) >= 2:
                ranked.append({"profile": profile, "avg_duration": average([item.run.duration_seconds for item in items]), "runs": items})
        if not ranked:
            return None
        ranked.sort(key=lambda item: item["avg_duration"], reverse=True)
        return ranked[0]

    def _profile_success_summary(self, analyzed_runs: List[_AnalyzedRun]) -> List[str]:
        breakdown = self._build_profile_breakdown(analyzed_runs)
        ranking = sorted(breakdown.items(), key=lambda item: item[1]["success_rate"], reverse=True)
        return [f"{profile} ({data['success_rate']:.0f}% de sucesso)" for profile, data in ranking[:2]]

    def _build_window_label(self, analyzed_runs: List[_AnalyzedRun], run_filter: RunFilter, limit: int) -> str:
        if run_filter.date_from or run_filter.date_to:
            start = run_filter.date_from.strftime("%d/%m/%Y") if run_filter.date_from else "início"
            end = run_filter.date_to.strftime("%d/%m/%Y") if run_filter.date_to else "agora"
            return f"Período {start} até {end}"
        if run_filter.profile_filter:
            return f"Últimas {limit} runs do profile {run_filter.profile_filter}"
        if run_filter.status_filter:
            labels = ", ".join(item.value for item in run_filter.status_filter)
            return f"Últimas {limit} runs com status {labels}"
        return f"Últimas {len(analyzed_runs)} runs"

    def _make_insight(self, *, category: str, severity: str, title: str, message: str, recommendation: str, affected_runs: Optional[Iterable[_AnalyzedRun]] = None, confidence: float = 1.0, supporting_metrics: Optional[Dict[str, Any]] = None) -> SystemInsight:
        self._insight_counter += 1
        return SystemInsight(
            id=f"system_insight_{self._insight_counter}",
            category=category,
            severity=severity,
            title=title,
            message=message,
            recommendation=recommendation,
            affected_run_ids=[item.run.run_id for item in affected_runs or []][:10],
            confidence=confidence,
            supporting_metrics=supporting_metrics or {},
        )


def average(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentage(part: int, total: int) -> float:
    return (part / total * 100.0) if total else 0.0


def format_percent(part: int, total: int) -> str:
    return f"{percentage(part, total):.0f}%"


def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"


def split_recent_windows(analyzed_runs: List[_AnalyzedRun]) -> tuple[List[_AnalyzedRun], List[_AnalyzedRun]]:
    midpoint = max(1, len(analyzed_runs) // 2)
    return analyzed_runs[:midpoint], analyzed_runs[midpoint:]


def trend_from_delta(current: float, previous: float, *, improve_when_higher: bool) -> TrendDirection:
    delta = current - previous
    if abs(delta) < 0.01:
        return TrendDirection.STABLE
    if improve_when_higher:
        return TrendDirection.UP if delta > 0 else TrendDirection.DOWN
    return TrendDirection.DOWN if delta > 0 else TrendDirection.UP


def trend_direction_display(direction: TrendDirection) -> str:
    return {
        TrendDirection.UP: "Melhorando",
        TrendDirection.DOWN: "Piorando",
        TrendDirection.STABLE: "Estável",
        TrendDirection.MIXED: "Misto",
    }[direction]


def health_status_display(status: SystemHealthStatus) -> str:
    return {
        SystemHealthStatus.STABLE: "Sistema estável",
        SystemHealthStatus.USABLE_WITH_ALERTS: "Sistema utilizável com alertas",
        SystemHealthStatus.DEGRADED: "Sistema degradado",
        SystemHealthStatus.RECURRING_FAILURES: "Sistema com falhas recorrentes",
    }[status]


def severity_icon(severity: str) -> str:
    return {"success": "✅", "info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(severity, "•")


def metric_value(metrics: List[AggregateMetric], key: str) -> float:
    for metric in metrics:
        if metric.key == key:
            return metric.value
    return 0.0


def sort_insights(insights: List[SystemInsight]) -> List[SystemInsight]:
    priority = {"error": 0, "warning": 1, "info": 2, "success": 3}
    return sorted(insights, key=lambda item: (priority.get(item.severity, 99), item.title))


def get_system_insights_analyzer(workspace_path: Path) -> SystemInsightsAnalyzer:
    return SystemInsightsAnalyzer(workspace_path)
