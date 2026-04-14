"""Run insights analyzer.

Analyzes run timelines to generate actionable insights,
executive summaries, and practical recommendations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .run_timeline import (
    RunTimeline,
    RunTimelineEvent,
    TimelineEventStatus,
    TimelineEventType,
    TimelineBuilder,
)

logger = logging.getLogger("ai_orchestrator.run_insights")


class InsightSeverity(Enum):
    """Severity level of an insight."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class InsightCategory(Enum):
    """Category of insight."""
    VALIDATION = "validation"
    EXECUTION = "execution"
    REVIEW = "review"
    CHECKPOINT = "checkpoint"
    GIT = "git"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SUMMARY = "summary"


class RunOutcome(Enum):
    """Overall outcome of a run."""
    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "success_with_warnings"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    NEEDS_ATTENTION = "needs_attention"
    IN_PROGRESS = "in_progress"


# Display names for outcomes
OUTCOME_DISPLAY = {
    RunOutcome.SUCCESS: "Sucesso",
    RunOutcome.SUCCESS_WITH_WARNINGS: "Sucesso com avisos",
    RunOutcome.FAILED: "Falhou",
    RunOutcome.INTERRUPTED: "Interrompida",
    RunOutcome.NEEDS_ATTENTION: "Requer atenção",
    RunOutcome.IN_PROGRESS: "Em andamento",
}

# Short labels for dashboard
OUTCOME_SHORT_LABELS = {
    RunOutcome.SUCCESS: "Tudo OK",
    RunOutcome.SUCCESS_WITH_WARNINGS: "OK com avisos",
    RunOutcome.FAILED: "Falhou",
    RunOutcome.INTERRUPTED: "Interrompida",
    RunOutcome.NEEDS_ATTENTION: "Atenção",
    RunOutcome.IN_PROGRESS: "Executando",
}


# Recommendations mapped to actions
RECOMMENDATIONS = {
    "open_artifacts": "Abra os artefatos da run para ver detalhes completos.",
    "review_validation": "Revise os resultados da validação para identificar o problema.",
    "check_configuration": "Verifique a configuração do projeto e do perfil ativo.",
    "reduce_scope": "Considere dividir a tarefa em partes menores.",
    "use_advanced_mode": "Use o modo avançado para ajustar parâmetros da execução.",
    "run_diagnostics": "Execute o diagnóstico para verificar problemas de ambiente.",
    "use_replay": "Use a funcionalidade de replay para tentar novamente.",
    "review_policies": "Revise as policies configuradas se checkpoints estão frequentes.",
    "check_git": "Verifique permissões e configuração do Git.",
    "wait_approval": "Aguarde a aprovação do checkpoint para continuar.",
    "check_executor": "Verifique se o executor (Claude) está configurado corretamente.",
    "check_openai": "Verifique a chave da OpenAI e limites de uso.",
}


@dataclass
class RunInsight:
    """A single insight about a run."""
    id: str
    category: InsightCategory
    severity: InsightSeverity
    title: str
    message: str
    recommendation: str = ""
    recommendation_key: str = ""
    related_event_types: List[TimelineEventType] = field(default_factory=list)
    related_stage: str = ""
    confidence: float = 1.0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "recommendation": self.recommendation,
            "recommendation_key": self.recommendation_key,
            "related_event_types": [e.value for e in self.related_event_types],
            "related_stage": self.related_stage,
            "confidence": self.confidence,
            "data": self.data,
        }


@dataclass
class RunInsightReport:
    """Complete insight report for a run."""
    run_id: str
    outcome: RunOutcome
    executive_summary: str
    short_label: str
    insights: List[RunInsight] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    iteration_count: int = 1
    checkpoint_count: int = 0
    validation_passed: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def get_by_category(self, category: InsightCategory) -> List[RunInsight]:
        """Get insights by category."""
        return [i for i in self.insights if i.category == category]

    def get_by_severity(self, severity: InsightSeverity) -> List[RunInsight]:
        """Get insights by severity."""
        return [i for i in self.insights if i.severity == severity]

    def has_errors(self) -> bool:
        """Check if report has error-level insights."""
        return any(i.severity == InsightSeverity.ERROR for i in self.insights)

    def has_warnings(self) -> bool:
        """Check if report has warning-level insights."""
        return any(i.severity == InsightSeverity.WARNING for i in self.insights)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "outcome": self.outcome.value,
            "executive_summary": self.executive_summary,
            "short_label": self.short_label,
            "insights": [i.to_dict() for i in self.insights],
            "total_duration_seconds": self.total_duration_seconds,
            "iteration_count": self.iteration_count,
            "checkpoint_count": self.checkpoint_count,
            "validation_passed": self.validation_passed,
            "created_at": self.created_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Export to Markdown format."""
        lines = [
            f"# Insights da Run: {self.run_id}",
            "",
            f"**Resultado:** {OUTCOME_DISPLAY.get(self.outcome, self.outcome.value)}",
            "",
            "## Resumo Executivo",
            "",
            self.executive_summary,
            "",
            "---",
            "",
            "## Métricas",
            "",
            f"- **Duração:** {self._format_duration(self.total_duration_seconds)}",
            f"- **Iterações:** {self.iteration_count}",
            f"- **Checkpoints:** {self.checkpoint_count}",
            f"- **Validação:** {'Passou' if self.validation_passed else 'Falhou'}",
            "",
        ]

        if self.insights:
            lines.extend([
                "---",
                "",
                "## Insights",
                "",
            ])

            for insight in self.insights:
                severity_icon = {
                    InsightSeverity.INFO: "ℹ️",
                    InsightSeverity.SUCCESS: "✅",
                    InsightSeverity.WARNING: "⚠️",
                    InsightSeverity.ERROR: "❌",
                }.get(insight.severity, "•")

                lines.append(f"### {severity_icon} {insight.title}")
                lines.append("")
                lines.append(insight.message)
                lines.append("")
                if insight.recommendation:
                    lines.append(f"**Recomendação:** {insight.recommendation}")
                    lines.append("")

        lines.extend([
            "---",
            "",
            f"*Gerado em: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """Format duration for display."""
        if seconds < 60:
            return f"{int(seconds)}s"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"


class InsightsAnalyzer:
    """Analyzes run timelines to generate insights."""

    # Thresholds for performance insights
    LONG_DURATION_THRESHOLD = 300  # 5 minutes
    LONG_STAGE_RATIO = 0.5  # Stage takes >50% of total time

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = workspace_path
        self._insight_counter = 0

    def analyze(self, timeline: RunTimeline) -> RunInsightReport:
        """Analyze a timeline and generate insights report."""
        self._insight_counter = 0

        report = RunInsightReport(
            run_id=timeline.run_id,
            outcome=RunOutcome.IN_PROGRESS,
            executive_summary="",
            short_label="",
            total_duration_seconds=timeline.total_duration_seconds,
        )

        # Gather metrics
        self._gather_metrics(report, timeline)

        # Generate insights by category
        self._analyze_validation(report, timeline)
        self._analyze_execution(report, timeline)
        self._analyze_review(report, timeline)
        self._analyze_checkpoints(report, timeline)
        self._analyze_git(report, timeline)
        self._analyze_performance(report, timeline)
        self._analyze_reliability(report, timeline)

        # Determine outcome and summary
        self._determine_outcome(report, timeline)
        self._generate_summary(report, timeline)

        return report

    def analyze_from_run_id(self, run_id: str) -> Optional[RunInsightReport]:
        """Analyze a run by ID using workspace path."""
        if not self.workspace_path:
            return None

        builder = TimelineBuilder(self.workspace_path)
        timeline = builder.build_timeline(run_id)

        if not timeline:
            return None

        return self.analyze(timeline)

    def _next_id(self) -> str:
        """Generate next insight ID."""
        self._insight_counter += 1
        return f"insight_{self._insight_counter}"

    def _gather_metrics(self, report: RunInsightReport, timeline: RunTimeline):
        """Gather basic metrics from timeline."""
        # Count iterations
        iteration_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.ITERATION_START
        ]
        execution_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.EXECUTION
        ]
        report.iteration_count = max(1, len(iteration_events) + 1 if iteration_events else len(execution_events))

        # Count checkpoints
        checkpoint_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.CHECKPOINT
        ]
        report.checkpoint_count = len(checkpoint_events)

        # Check validation
        validation_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.VALIDATION
        ]
        if validation_events:
            last_validation = validation_events[-1]
            report.validation_passed = last_validation.status == TimelineEventStatus.COMPLETED

    def _analyze_validation(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate validation-related insights."""
        validation_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.VALIDATION
        ]

        if not validation_events:
            return

        last_validation = validation_events[-1]

        if last_validation.status == TimelineEventStatus.COMPLETED:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.VALIDATION,
                severity=InsightSeverity.SUCCESS,
                title="Validação bem-sucedida",
                message="Todas as validações passaram com sucesso.",
                related_event_types=[TimelineEventType.VALIDATION],
                related_stage="validation",
            ))
        elif last_validation.status == TimelineEventStatus.FAILED:
            # Check if run completed despite validation failure
            finalization = [
                e for e in timeline.events
                if e.event_type == TimelineEventType.FINALIZATION
            ]

            if finalization and finalization[-1].status == TimelineEventStatus.COMPLETED:
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.VALIDATION,
                    severity=InsightSeverity.WARNING,
                    title="Run concluída com falha na validação",
                    message="A run foi concluída, mas a validação não passou. O código pode conter problemas.",
                    recommendation=RECOMMENDATIONS["review_validation"],
                    recommendation_key="review_validation",
                    related_event_types=[TimelineEventType.VALIDATION],
                    related_stage="validation",
                ))
            else:
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.VALIDATION,
                    severity=InsightSeverity.ERROR,
                    title="Falha na validação",
                    message="A validação falhou. Verifique os comandos executados e os erros reportados.",
                    recommendation=RECOMMENDATIONS["review_validation"],
                    recommendation_key="review_validation",
                    related_event_types=[TimelineEventType.VALIDATION],
                    related_stage="validation",
                    data={"errors": last_validation.errors},
                ))

    def _analyze_execution(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate execution-related insights."""
        execution_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.EXECUTION
        ]

        if not execution_events:
            return

        # Check for multiple iterations
        if len(execution_events) > 1:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.EXECUTION,
                severity=InsightSeverity.INFO,
                title="Múltiplas iterações de execução",
                message=f"A tarefa exigiu {len(execution_events)} iterações de execução, indicando possível complexidade ou necessidade de ajustes.",
                recommendation=RECOMMENDATIONS["reduce_scope"],
                recommendation_key="reduce_scope",
                related_event_types=[TimelineEventType.EXECUTION],
                related_stage="execution",
                data={"iteration_count": len(execution_events)},
            ))

        # Check for execution failures
        failed_executions = [
            e for e in execution_events
            if e.status == TimelineEventStatus.FAILED
        ]

        if failed_executions:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.EXECUTION,
                severity=InsightSeverity.ERROR,
                title="Falha na execução",
                message="Uma ou mais execuções falharam. Verifique os logs para mais detalhes.",
                recommendation=RECOMMENDATIONS["open_artifacts"],
                recommendation_key="open_artifacts",
                related_event_types=[TimelineEventType.EXECUTION],
                related_stage="execution",
            ))

        # Check for successful execution
        last_execution = execution_events[-1]
        if last_execution.status == TimelineEventStatus.COMPLETED and not failed_executions:
            if len(execution_events) == 1:
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.EXECUTION,
                    severity=InsightSeverity.SUCCESS,
                    title="Execução concluída na primeira tentativa",
                    message="O executor completou a tarefa com sucesso na primeira iteração.",
                    related_event_types=[TimelineEventType.EXECUTION],
                    related_stage="execution",
                ))

    def _analyze_review(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate review-related insights."""
        review_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.REVIEW
        ]

        if not review_events:
            return

        last_review = review_events[-1]

        # Check for follow-up requests
        followup_reviews = [
            e for e in review_events
            if "ajustes" in e.description.lower() or "followup" in e.description.lower()
        ]

        if followup_reviews:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.REVIEW,
                severity=InsightSeverity.INFO,
                title="Revisão solicitou ajustes",
                message="O reviewer identificou ajustes necessários antes da aprovação final.",
                related_event_types=[TimelineEventType.REVIEW],
                related_stage="review",
            ))

        if last_review.status == TimelineEventStatus.COMPLETED:
            if "aprovada" in last_review.description.lower():
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.REVIEW,
                    severity=InsightSeverity.SUCCESS,
                    title="Revisão aprovada",
                    message="A revisão aprovou a alteração sem novas pendências.",
                    related_event_types=[TimelineEventType.REVIEW],
                    related_stage="review",
                ))
        elif last_review.status == TimelineEventStatus.FAILED:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.REVIEW,
                severity=InsightSeverity.ERROR,
                title="Revisão bloqueou a execução",
                message="O reviewer bloqueou a continuação da run. Verifique os achados da revisão.",
                recommendation=RECOMMENDATIONS["open_artifacts"],
                recommendation_key="open_artifacts",
                related_event_types=[TimelineEventType.REVIEW],
                related_stage="review",
            ))

    def _analyze_checkpoints(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate checkpoint-related insights."""
        checkpoint_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.CHECKPOINT
        ]

        if not checkpoint_events:
            return

        unresolved = [e for e in checkpoint_events if not e.checkpoint_resolved]
        resolved = [e for e in checkpoint_events if e.checkpoint_resolved]

        if unresolved:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.CHECKPOINT,
                severity=InsightSeverity.WARNING,
                title="Checkpoint aguardando aprovação",
                message=f"Esta run tem {len(unresolved)} checkpoint(s) pendente(s) de aprovação.",
                recommendation=RECOMMENDATIONS["wait_approval"],
                recommendation_key="wait_approval",
                related_event_types=[TimelineEventType.CHECKPOINT],
                related_stage="checkpoint",
                data={"pending_count": len(unresolved)},
            ))

        if resolved:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.CHECKPOINT,
                severity=InsightSeverity.INFO,
                title="Checkpoint resolvido",
                message=f"Esta run exigiu {len(resolved)} checkpoint(s) com aprovação humana.",
                related_event_types=[TimelineEventType.CHECKPOINT],
                related_stage="checkpoint",
                data={"resolved_count": len(resolved)},
            ))

    def _analyze_git(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate git-related insights."""
        git_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.GIT
        ]

        if not git_events:
            return

        last_git = git_events[-1]

        if last_git.status == TimelineEventStatus.COMPLETED:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.GIT,
                severity=InsightSeverity.SUCCESS,
                title="Git concluído com sucesso",
                message="Commit e/ou push foram concluídos com sucesso.",
                related_event_types=[TimelineEventType.GIT],
                related_stage="git",
            ))
        elif last_git.status == TimelineEventStatus.FAILED:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.GIT,
                severity=InsightSeverity.ERROR,
                title="Falha no Git",
                message="A implementação foi concluída, mas houve falha na etapa de Git.",
                recommendation=RECOMMENDATIONS["check_git"],
                recommendation_key="check_git",
                related_event_types=[TimelineEventType.GIT],
                related_stage="git",
                data={"errors": last_git.errors},
            ))

    def _analyze_performance(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate performance-related insights."""
        if timeline.total_duration_seconds <= 0:
            return

        # Check for long total duration
        if timeline.total_duration_seconds > self.LONG_DURATION_THRESHOLD:
            mins = int(timeline.total_duration_seconds // 60)
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.PERFORMANCE,
                severity=InsightSeverity.INFO,
                title="Duração acima do esperado",
                message=f"A run teve duração total de {mins} minutos, acima do esperado.",
                recommendation=RECOMMENDATIONS["reduce_scope"],
                recommendation_key="reduce_scope",
                related_event_types=[],
                related_stage="performance",
                data={"duration_seconds": timeline.total_duration_seconds},
            ))

        # Find slowest stage
        stage_durations = {}
        for event in timeline.events:
            if event.duration_seconds and event.duration_seconds > 0:
                stage = event.event_type.value
                if stage not in stage_durations:
                    stage_durations[stage] = 0
                stage_durations[stage] += event.duration_seconds

        if stage_durations:
            slowest_stage = max(stage_durations, key=stage_durations.get)
            slowest_duration = stage_durations[slowest_stage]
            ratio = slowest_duration / timeline.total_duration_seconds if timeline.total_duration_seconds > 0 else 0

            if ratio > self.LONG_STAGE_RATIO and timeline.total_duration_seconds > 60:
                stage_names = {
                    "execution": "Execução",
                    "validation": "Validação",
                    "review": "Revisão",
                    "planning": "Planejamento",
                    "git": "Git",
                }
                stage_name = stage_names.get(slowest_stage, slowest_stage)
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.PERFORMANCE,
                    severity=InsightSeverity.INFO,
                    title=f"{stage_name} foi a etapa mais demorada",
                    message=f"A etapa de {stage_name.lower()} consumiu {int(ratio * 100)}% do tempo total da run.",
                    related_event_types=[],
                    related_stage=slowest_stage,
                    data={"stage": slowest_stage, "ratio": ratio},
                ))

    def _analyze_reliability(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate reliability-related insights."""
        # Check for errors in events
        error_events = [
            e for e in timeline.events
            if e.status == TimelineEventStatus.FAILED
        ]

        planning_events = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.PLANNING
        ]

        # Check for planning failure (configuration issue)
        if planning_events:
            last_planning = planning_events[-1]
            if last_planning.status == TimelineEventStatus.FAILED:
                report.insights.append(RunInsight(
                    id=self._next_id(),
                    category=InsightCategory.CONFIGURATION,
                    severity=InsightSeverity.ERROR,
                    title="Falha no planejamento",
                    message="A run falhou na etapa de planejamento. Pode indicar problema de configuração ou API.",
                    recommendation=RECOMMENDATIONS["check_openai"],
                    recommendation_key="check_openai",
                    related_event_types=[TimelineEventType.PLANNING],
                    related_stage="planning",
                ))

        # Check for multiple failures (reliability issue)
        if len(error_events) > 2:
            report.insights.append(RunInsight(
                id=self._next_id(),
                category=InsightCategory.RELIABILITY,
                severity=InsightSeverity.WARNING,
                title="Múltiplas falhas detectadas",
                message=f"Esta run teve {len(error_events)} eventos com falha, indicando possível instabilidade.",
                recommendation=RECOMMENDATIONS["run_diagnostics"],
                recommendation_key="run_diagnostics",
                related_event_types=[],
                related_stage="reliability",
                data={"error_count": len(error_events)},
            ))

    def _determine_outcome(self, report: RunInsightReport, timeline: RunTimeline):
        """Determine the overall outcome of the run."""
        # Check if still in progress
        if not timeline.is_complete:
            current = timeline.get_current_event()
            if current and current.event_type == TimelineEventType.CHECKPOINT:
                report.outcome = RunOutcome.NEEDS_ATTENTION
            else:
                report.outcome = RunOutcome.IN_PROGRESS
            return

        # Check finalization status
        finalization = [
            e for e in timeline.events
            if e.event_type == TimelineEventType.FINALIZATION
        ]

        if finalization:
            last_final = finalization[-1]
            if last_final.status == TimelineEventStatus.SKIPPED:
                report.outcome = RunOutcome.INTERRUPTED
                return
            elif last_final.status == TimelineEventStatus.FAILED:
                report.outcome = RunOutcome.FAILED
                return

        # Check for errors
        if timeline.has_errors:
            report.outcome = RunOutcome.FAILED
            return

        # Check for warnings
        has_warnings = (
            report.has_warnings() or
            not report.validation_passed or
            report.checkpoint_count > 0 or
            report.iteration_count > 2
        )

        if has_warnings:
            report.outcome = RunOutcome.SUCCESS_WITH_WARNINGS
        else:
            report.outcome = RunOutcome.SUCCESS

    def _generate_summary(self, report: RunInsightReport, timeline: RunTimeline):
        """Generate executive summary and short label."""
        report.short_label = OUTCOME_SHORT_LABELS.get(report.outcome, "Desconhecido")

        # Build summary parts
        parts = []

        # Main outcome
        if report.outcome == RunOutcome.SUCCESS:
            parts.append("Run concluída com sucesso")
        elif report.outcome == RunOutcome.SUCCESS_WITH_WARNINGS:
            parts.append("Run concluída com sucesso")
        elif report.outcome == RunOutcome.FAILED:
            # Find main failure reason
            if not report.validation_passed:
                parts.append("Run falhou na validação")
            else:
                error_insights = report.get_by_severity(InsightSeverity.ERROR)
                if error_insights:
                    parts.append(f"Run falhou: {error_insights[0].title.lower()}")
                else:
                    parts.append("Run falhou")
        elif report.outcome == RunOutcome.INTERRUPTED:
            parts.append("Run foi interrompida ou cancelada")
        elif report.outcome == RunOutcome.NEEDS_ATTENTION:
            parts.append("Run aguarda ação do usuário")
        elif report.outcome == RunOutcome.IN_PROGRESS:
            current = timeline.get_current_event()
            if current:
                parts.append(f"Run em andamento: {current.title.lower()}")
            else:
                parts.append("Run em andamento")

        # Add modifiers
        modifiers = []

        if report.checkpoint_count > 0:
            modifiers.append(f"{report.checkpoint_count} checkpoint(s)")

        if report.iteration_count > 1:
            modifiers.append(f"{report.iteration_count} iterações")

        if not report.validation_passed and report.outcome != RunOutcome.FAILED:
            modifiers.append("validação falhou")

        if modifiers:
            parts.append(f"com {', '.join(modifiers)}")

        report.executive_summary = " ".join(parts) + "."

    def export_to_file(self, report: RunInsightReport, run_dir: Path) -> Dict[str, Path]:
        """Export insights to files in run directory."""
        final_dir = run_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        exported = {}

        # Export JSON
        json_path = final_dir / "run_insights.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        exported["json"] = json_path

        # Export Markdown
        md_path = final_dir / "run_insights.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())
        exported["markdown"] = md_path

        logger.info(f"Exported insights to: {final_dir}")
        return exported


def get_insights_analyzer(workspace_path: Optional[Path] = None) -> InsightsAnalyzer:
    """Factory function to create an InsightsAnalyzer."""
    return InsightsAnalyzer(workspace_path)
