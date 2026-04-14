"""Map insights to practical actions for the GUI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from orchestrator.run_insights import InsightCategory, InsightSeverity, RunInsightReport
from orchestrator.system_insights import SystemInsightReport


class ActionPriority(Enum):
    IMMEDIATE = "immediate"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class ActionTarget(Enum):
    RUNS = "runs"
    DASHBOARD = "dashboard"
    SETTINGS = "settings"
    DIAGNOSTICS = "diagnostics"
    CHECKPOINTS = "checkpoints"
    POLICIES = "policies"
    REPLAY = "replay"
    HELP = "help"
    LOGS = "logs"
    SYSTEM_INSIGHTS = "system_insights"


@dataclass
class ActionContext:
    run_id: Optional[str] = None
    profile: Optional[str] = None
    status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class RecommendedAction:
    id: str
    title: str
    description: str
    priority: ActionPriority
    source_type: str
    source_id: str
    target: ActionTarget
    action_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    recommendation_reason: str = ""
    confidence: float = 1.0
    context: ActionContext = field(default_factory=ActionContext)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target": self.target.value,
            "action_type": self.action_type,
            "payload": self.payload,
            "recommendation_reason": self.recommendation_reason,
            "confidence": self.confidence,
            "context": self.context.to_dict(),
        }


@dataclass
class RecommendedActionGroup:
    title: str
    summary: str
    actions: List[RecommendedAction] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "generated_at": self.generated_at.isoformat(),
            "actions": [action.to_dict() for action in self.actions],
        }


class RecommendedActionsEngine:
    """Generate actions from run and system insights."""

    def __init__(self):
        self._counter = 0

    def from_run_report(self, report: RunInsightReport) -> RecommendedActionGroup:
        self._counter = 0
        actions: List[RecommendedAction] = []

        for insight in report.insights:
            actions.extend(self._map_run_insight(report, insight))

        if report.checkpoint_count > 0:
            actions.append(self._make_action(
                title="Abrir Centro de Checkpoints",
                description="Revise checkpoints pendentes e destrave a execução se ainda houver aprovação aguardando.",
                priority=ActionPriority.IMMEDIATE if report.outcome.value in {"needs_attention", "in_progress"} else ActionPriority.RECOMMENDED,
                source_type="run_insight",
                source_id=report.run_id,
                target=ActionTarget.CHECKPOINTS,
                action_type="navigate",
                payload={},
                reason="A run registrou checkpoint e pode depender de ação manual.",
                confidence=0.9,
                context=ActionContext(run_id=report.run_id),
            ))

        actions.append(self._make_action(
            title="Abrir Timeline da Run",
            description="Veja a sequência completa da execução para localizar a etapa exata onde o fluxo mudou.",
            priority=ActionPriority.RECOMMENDED,
            source_type="run_insight",
            source_id=report.run_id,
            target=ActionTarget.RUNS,
            action_type="open_run_tab",
            payload={"run_id": report.run_id, "tab": "Timeline"},
            reason="A timeline é o melhor ponto de partida para entender a run.",
            confidence=0.75,
            context=ActionContext(run_id=report.run_id),
        ))

        return RecommendedActionGroup(
            title="Próximas ações recomendadas",
            summary="Use estas ações para avançar a partir do que a run mostrou.",
            actions=self._dedupe_and_sort(actions)[:5],
        )

    def from_system_report(self, report: SystemInsightReport) -> RecommendedActionGroup:
        self._counter = 0
        actions: List[RecommendedAction] = []
        for insight in report.insights:
            actions.extend(self._map_system_insight(report, insight))

        actions.append(self._make_action(
            title="Abrir Insights do Sistema completos",
            description="Veja a análise agregada completa com métricas, tendências e evidências do histórico recente.",
            priority=ActionPriority.RECOMMENDED,
            source_type="system_insight",
            source_id=report.report_id,
            target=ActionTarget.SYSTEM_INSIGHTS,
            action_type="open_system_insights",
            payload={},
            reason="Ajuda a validar o contexto completo antes de agir.",
            confidence=0.8,
        ))

        return RecommendedActionGroup(
            title="Ações recomendadas do sistema",
            summary="Estas ações priorizam o que tende a melhorar mais o fluxo operacional agora.",
            actions=self._dedupe_and_sort(actions)[:5],
        )

    def export_group(self, group: RecommendedActionGroup, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(group.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def _map_run_insight(self, report: RunInsightReport, insight) -> List[RecommendedAction]:
        actions: List[RecommendedAction] = []
        base_context = ActionContext(run_id=report.run_id, metadata={"insight_id": insight.id})

        if insight.category == InsightCategory.VALIDATION or insight.recommendation_key == "review_validation":
            actions.extend([
                self._make_action(
                    title="Abrir validação da run",
                    description="Abra a aba de validação para ver os comandos e localizar o erro com precisão.",
                    priority=ActionPriority.IMMEDIATE,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.RUNS,
                    action_type="open_run_tab",
                    payload={"run_id": report.run_id, "tab": "Validacao"},
                    reason=insight.message,
                    confidence=insight.confidence,
                    context=base_context,
                ),
                self._make_action(
                    title="Abrir replay desta run",
                    description="Reproduza a run para comparar o comportamento e validar uma nova tentativa.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.REPLAY,
                    action_type="navigate_replay",
                    payload={"run_id": report.run_id},
                    reason="Replay ajuda a confirmar se a falha é reproduzível.",
                    confidence=0.78,
                    context=base_context,
                ),
            ])

        if insight.category == InsightCategory.GIT or insight.recommendation_key == "check_git":
            actions.extend([
                self._make_action(
                    title="Abrir Configurações > Git",
                    description="Revise branch, remoto e parâmetros de Git usados pela automação.",
                    priority=ActionPriority.IMMEDIATE,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.SETTINGS,
                    action_type="open_settings_tab",
                    payload={"tab": "Git"},
                    reason=insight.message,
                    confidence=0.88,
                    context=base_context,
                ),
                self._make_action(
                    title="Abrir diagnóstico",
                    description="Execute o diagnóstico para validar o ambiente e o estado operacional antes da próxima tentativa.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.DIAGNOSTICS,
                    action_type="navigate",
                    payload={},
                    reason="Problemas de Git costumam vir com contexto ambiental ou de workspace.",
                    confidence=0.76,
                    context=base_context,
                ),
                self._make_action(
                    title="Abrir aba Git da run",
                    description="Veja o resumo e os dados de Git capturados nesta execução.",
                    priority=ActionPriority.OPTIONAL,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.RUNS,
                    action_type="open_run_tab",
                    payload={"run_id": report.run_id, "tab": "Git"},
                    reason="Ajuda a comparar o erro com o estado salvo da run.",
                    confidence=0.72,
                    context=base_context,
                ),
            ])

        if insight.category == InsightCategory.CHECKPOINT or insight.recommendation_key in {"wait_approval", "review_policies"}:
            actions.extend([
                self._make_action(
                    title="Abrir Centro de Checkpoints",
                    description="Revise aprovações pendentes e destrave execuções que pararam por segurança.",
                    priority=ActionPriority.IMMEDIATE,
                    source_type="checkpoint",
                    source_id=insight.id,
                    target=ActionTarget.CHECKPOINTS,
                    action_type="navigate",
                    payload={},
                    reason=insight.message,
                    confidence=0.9,
                    context=base_context,
                ),
                self._make_action(
                    title="Revisar policies",
                    description="Abra as policies para ajustar regras se o fluxo está parando com frequência.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="checkpoint",
                    source_id=insight.id,
                    target=ActionTarget.POLICIES,
                    action_type="navigate",
                    payload={},
                    reason="Policies podem estar conservadoras demais para o perfil atual.",
                    confidence=0.7,
                    context=base_context,
                ),
            ])

        if insight.recommendation_key in {"check_openai", "check_executor"} or insight.category == InsightCategory.CONFIGURATION:
            settings_tab = "Ambiente" if insight.recommendation_key == "check_openai" else "Executor"
            actions.extend([
                self._make_action(
                    title=f"Abrir Configurações > {settings_tab}",
                    description="Revise a configuração essencial associada a esta falha antes de tentar de novo.",
                    priority=ActionPriority.IMMEDIATE,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.SETTINGS,
                    action_type="open_settings_tab",
                    payload={"tab": settings_tab},
                    reason=insight.message,
                    confidence=0.86,
                    context=base_context,
                ),
                self._make_action(
                    title="Abrir diagnóstico",
                    description="Valide o ambiente e confirme se dependências externas estão disponíveis.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="diagnostic",
                    source_id=insight.id,
                    target=ActionTarget.DIAGNOSTICS,
                    action_type="navigate",
                    payload={},
                    reason="O diagnóstico reduz tentativa e erro em falhas de configuração.",
                    confidence=0.73,
                    context=base_context,
                ),
            ])

        if insight.recommendation_key == "open_artifacts":
            actions.append(self._make_action(
                title="Abrir artefatos da run",
                description="Veja relatórios, diffs e arquivos produzidos pela execução.",
                priority=ActionPriority.RECOMMENDED,
                source_type="run_insight",
                source_id=insight.id,
                target=ActionTarget.RUNS,
                action_type="open_run_tab",
                payload={"run_id": report.run_id, "tab": "Artefatos"},
                reason=insight.message,
                confidence=0.75,
                context=base_context,
            ))

        if insight.recommendation_key in {"run_diagnostics", "use_replay", "reduce_scope"}:
            if insight.recommendation_key == "run_diagnostics":
                actions.append(self._make_action(
                    title="Executar diagnóstico",
                    description="Abra o diagnóstico para verificar ambiente, executor e validações antes da próxima run.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="diagnostic",
                    source_id=insight.id,
                    target=ActionTarget.DIAGNOSTICS,
                    action_type="navigate",
                    payload={},
                    reason=insight.message,
                    confidence=0.78,
                    context=base_context,
                ))
            elif insight.recommendation_key == "use_replay":
                actions.append(self._make_action(
                    title="Abrir replay desta run",
                    description="Tente reproduzir a execução com o contexto atual para confirmar o problema.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.REPLAY,
                    action_type="navigate_replay",
                    payload={"run_id": report.run_id},
                    reason=insight.message,
                    confidence=0.74,
                    context=base_context,
                ))
            else:
                actions.append(self._make_action(
                    title="Criar próxima tarefa mais enxuta",
                    description="Volte para Nova Tarefa e reduza o escopo para diminuir risco e iterações.",
                    priority=ActionPriority.OPTIONAL,
                    source_type="run_insight",
                    source_id=insight.id,
                    target=ActionTarget.DASHBOARD,
                    action_type="navigate_new_task",
                    payload={},
                    reason=insight.message,
                    confidence=0.65,
                    context=base_context,
                ))

        return actions

    def _map_system_insight(self, report: SystemInsightReport, insight) -> List[RecommendedAction]:
        actions: List[RecommendedAction] = []
        priority = ActionPriority.IMMEDIATE if insight.severity == "error" else ActionPriority.RECOMMENDED

        if insight.category == "validation":
            actions.extend([
                self._make_action(
                    title="Abrir dashboard com falhas",
                    description="Filtre o dashboard para ver rapidamente as runs com falha mais recentes.",
                    priority=priority,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.DASHBOARD,
                    action_type="filter_dashboard",
                    payload={"status": "failed"},
                    reason=insight.message,
                    confidence=insight.confidence,
                ),
                self._make_action(
                    title="Abrir replay das falhas recentes",
                    description="Vá ao Replay para reproduzir as runs com falha e comparar o comportamento.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.REPLAY,
                    action_type="navigate",
                    payload={},
                    reason="Replay ajuda a validar padrões recorrentes de falha.",
                    confidence=0.75,
                ),
            ])

        if insight.category == "git":
            actions.extend([
                self._make_action(
                    title="Abrir Configurações > Git",
                    description="Revise branch, remoto e automações de commit/push.",
                    priority=priority,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.SETTINGS,
                    action_type="open_settings_tab",
                    payload={"tab": "Git"},
                    reason=insight.message,
                    confidence=0.88,
                ),
                self._make_action(
                    title="Abrir diagnóstico",
                    description="Confirme o estado do ambiente antes de insistir em novas execuções com Git automático.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="diagnostic",
                    source_id=insight.id,
                    target=ActionTarget.DIAGNOSTICS,
                    action_type="navigate",
                    payload={},
                    reason="Ajuda a separar erro de config de erro pontual de run.",
                    confidence=0.72,
                ),
                self._make_action(
                    title="Abrir logs",
                    description="Vá aos logs para inspecionar falhas persistentes fora do contexto de uma única run.",
                    priority=ActionPriority.OPTIONAL,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.LOGS,
                    action_type="navigate",
                    payload={},
                    reason="Útil quando a falha aparece em mais de uma execução.",
                    confidence=0.61,
                ),
            ])

        if insight.category == "checkpoint":
            actions.extend([
                self._make_action(
                    title="Abrir Centro de Checkpoints",
                    description="Veja onde o fluxo está parando e trate aprovações pendentes primeiro.",
                    priority=priority,
                    source_type="checkpoint",
                    source_id=insight.id,
                    target=ActionTarget.CHECKPOINTS,
                    action_type="navigate",
                    payload={},
                    reason=insight.message,
                    confidence=0.9,
                ),
                self._make_action(
                    title="Revisar policies",
                    description="Ajuste regras se checkpoints estão frequentes demais para o perfil atual.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.POLICIES,
                    action_type="navigate",
                    payload={},
                    reason="Checkpoints frequentes costumam indicar políticas rígidas ou tarefas arriscadas.",
                    confidence=0.7,
                ),
            ])

        if insight.category == "trends":
            actions.extend([
                self._make_action(
                    title="Filtrar dashboard por falhas recentes",
                    description="Concentre a análise nas runs com falha para ver o padrão mais recente.",
                    priority=priority,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.DASHBOARD,
                    action_type="filter_dashboard",
                    payload={"status": "failed"},
                    reason=insight.message,
                    confidence=0.84,
                ),
                self._make_action(
                    title="Abrir Insights do Sistema completos",
                    description="Abra a visão completa para correlacionar a tendência com perfis e métricas agregadas.",
                    priority=ActionPriority.RECOMMENDED,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.SYSTEM_INSIGHTS,
                    action_type="open_system_insights",
                    payload={},
                    reason="Ajuda a validar se o aumento de falhas é localizado ou sistêmico.",
                    confidence=0.8,
                ),
            ])

        if insight.category == "performance":
            actions.extend([
                self._make_action(
                    title="Abrir runs para comparar timelines",
                    description="Abra a central de runs e compare as execuções mais lentas pela timeline.",
                    priority=priority,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.RUNS,
                    action_type="navigate",
                    payload={},
                    reason=insight.message,
                    confidence=0.77,
                ),
                self._make_action(
                    title="Revisar escopo da próxima tarefa",
                    description="Volte para Nova Tarefa e reduza o escopo se a duração média estiver em alta.",
                    priority=ActionPriority.OPTIONAL,
                    source_type="system_insight",
                    source_id=insight.id,
                    target=ActionTarget.DASHBOARD,
                    action_type="navigate_new_task",
                    payload={},
                    reason="Tarefas menores melhoram previsibilidade e tempo de ciclo.",
                    confidence=0.63,
                ),
            ])

        return actions

    def _make_action(
        self,
        *,
        title: str,
        description: str,
        priority: ActionPriority,
        source_type: str,
        source_id: str,
        target: ActionTarget,
        action_type: str,
        payload: Dict[str, Any],
        reason: str,
        confidence: float,
        context: Optional[ActionContext] = None,
    ) -> RecommendedAction:
        self._counter += 1
        return RecommendedAction(
            id=f"recommended_action_{self._counter}",
            title=title,
            description=description,
            priority=priority,
            source_type=source_type,
            source_id=source_id,
            target=target,
            action_type=action_type,
            payload=payload,
            recommendation_reason=reason,
            confidence=confidence,
            context=context or ActionContext(),
        )

    def _dedupe_and_sort(self, actions: Iterable[RecommendedAction]) -> List[RecommendedAction]:
        seen = set()
        result: List[RecommendedAction] = []
        for action in actions:
            key = (action.title, action.target.value, action.action_type, json.dumps(action.payload, sort_keys=True))
            if key not in seen:
                seen.add(key)
                result.append(action)
        priority_order = {
            ActionPriority.IMMEDIATE: 0,
            ActionPriority.RECOMMENDED: 1,
            ActionPriority.OPTIONAL: 2,
        }
        result.sort(key=lambda item: (priority_order[item.priority], -item.confidence, item.title))
        return result
