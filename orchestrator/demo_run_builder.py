"""Build fictional demo scenarios for the interactive product tour."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class DemoTimelineEvent:
    title: str
    stage: str
    status: str
    description: str


@dataclass(frozen=True)
class DemoInsight:
    title: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class DemoAction:
    title: str
    reason: str
    target_label: str


@dataclass(frozen=True)
class DemoArtifact:
    label: str
    description: str


@dataclass(frozen=True)
class DemoScenario:
    key: str
    title: str
    summary: str
    task_text: str
    profile: str
    outcome: str
    executive_summary: str
    timeline: List[DemoTimelineEvent] = field(default_factory=list)
    insights: List[DemoInsight] = field(default_factory=list)
    actions: List[DemoAction] = field(default_factory=list)
    artifacts: List[DemoArtifact] = field(default_factory=list)


def build_demo_scenarios() -> dict[str, DemoScenario]:
    """Return the built-in fictional demo scenarios."""
    success = DemoScenario(
        key="success",
        title="Demo de uso normal",
        summary="Uma tarefa pequena, validações passando e fechamento limpo da run.",
        task_text=(
            "Revise a tela de login do projeto Flutter, rode flutter analyze e flutter test, "
            "corrija apenas problemas seguros e gere relatório final."
        ),
        profile="flutter",
        outcome="success",
        executive_summary=(
            "A run fictícia mostra o fluxo ideal: objetivo claro, execução pequena, "
            "review rápido e validação passando."
        ),
        timeline=[
            DemoTimelineEvent("Planejamento criado", "planner", "ok", "O planner definiu um escopo pequeno e seguro."),
            DemoTimelineEvent("Executor alterou arquivos fictícios", "executor", "ok", "Foram simuladas mudanças em login_screen.dart e auth_service.dart."),
            DemoTimelineEvent("Reviewer aprovou com observações", "review", "warning", "A revisão sugeriu manter o escopo pequeno na próxima iteração."),
            DemoTimelineEvent("Validação executada", "validation", "ok", "flutter analyze e flutter test passaram no cenário fictício."),
            DemoTimelineEvent("Run concluída", "git", "ok", "O relatório final foi gerado sem tocar no projeto real."),
        ],
        insights=[
            DemoInsight("Escopo bem definido", "A tarefa informa objetivo, limite e resultado esperado.", "Use tarefas pequenas nas primeiras runs."),
            DemoInsight("Validação saudável", "As verificações do perfil passaram sem retrabalho.", "Mantenha auto validação ligada quando possível."),
        ],
        actions=[
            DemoAction("Abrir Timeline", "Boa para entender a ordem dos eventos.", "Timeline"),
            DemoAction("Ver Insights", "Resume o que deu certo e o que merece atenção.", "Insights"),
            DemoAction("Ler artefatos", "Mostra o relatório final e os arquivos simulados.", "Artefatos"),
        ],
        artifacts=[
            DemoArtifact("report.md", "Resumo final da execução fictícia."),
            DemoArtifact("validation.txt", "Saída fictícia de flutter analyze e flutter test."),
        ],
    )

    failure = DemoScenario(
        key="failure",
        title="Demo de falha",
        summary="Uma run com erro de validação, insight gerado e ação recomendada de diagnóstico.",
        task_text=(
            "Corrigir a tela de login, mas a validação fictícia encontra um teste quebrado "
            "e a run termina com alerta."
        ),
        profile="flutter",
        outcome="failure",
        executive_summary=(
            "Quando a validação falha, o app aponta onde olhar primeiro: Timeline, Insights, "
            "Ações Recomendadas e Diagnóstico."
        ),
        timeline=[
            DemoTimelineEvent("Planejamento criado", "planner", "ok", "O plano identificou a validação obrigatória."),
            DemoTimelineEvent("Executor concluiu a mudança fictícia", "executor", "ok", "As alterações simuladas ficaram restritas à tela de login."),
            DemoTimelineEvent("Validação falhou", "validation", "failed", "flutter test simulou falha em teste de sessão expirada."),
            DemoTimelineEvent("Ação recomendada gerada", "insights", "warning", "O sistema sugeriu abrir Diagnóstico e Replay."),
        ],
        insights=[
            DemoInsight("Falha de validação", "A mudança simulada não passou em todos os checks do perfil.", "Abra Timeline e Diagnóstico antes de repetir a run."),
            DemoInsight("Retrabalho previsível", "A recomendação aponta o próximo passo em vez de deixar o usuário adivinhar.", "Use o replay para revisar o fluxo com calma."),
        ],
        actions=[
            DemoAction("Abrir Diagnóstico", "Ajuda a separar erro de ambiente de erro da run.", "Diagnóstico"),
            DemoAction("Abrir Replay", "Permite revisar a execução sem risco.", "Replay"),
            DemoAction("Filtrar runs com falha", "Mostra se o padrão já aconteceu antes.", "Dashboard"),
        ],
        artifacts=[
            DemoArtifact("validation_failure.txt", "Saída fictícia com teste falhando."),
            DemoArtifact("review_notes.md", "Resumo fictício do reviewer sobre o problema."),
        ],
    )

    checkpoint = DemoScenario(
        key="checkpoint",
        title="Demo de checkpoint",
        summary="Uma operação sensível dispara aprovação humana antes de continuar.",
        task_text=(
            "Refatorar um fluxo que inclui remover código legado e atualizar configurações sensíveis."
        ),
        profile="python",
        outcome="checkpoint",
        executive_summary=(
            "Quando o risco aumenta, o AI Orchestrator pede confirmação humana em vez de seguir no escuro."
        ),
        timeline=[
            DemoTimelineEvent("Planejamento detectou risco", "planner", "warning", "O plano marcou uma mudança sensível no escopo."),
            DemoTimelineEvent("Checkpoint aberto", "checkpoint", "warning", "A execução parou antes de seguir com a alteração delicada."),
            DemoTimelineEvent("Aguardando aprovação", "checkpoint", "pending", "O operador decide se a run continua ou se precisa ser revista."),
        ],
        insights=[
            DemoInsight("Controle humano preservado", "O checkpoint evita ações destrutivas automáticas.", "Revise a justificativa antes de aprovar."),
            DemoInsight("Policy ativa", "A operação foi tratada como sensível pelo fluxo.", "Use Policies para ajustar o gatilho quando necessário."),
        ],
        actions=[
            DemoAction("Abrir Checkpoints", "Mostra o motivo e o impacto antes de aprovar.", "Checkpoints"),
            DemoAction("Revisar Policies", "Ajuda a entender por que o checkpoint foi disparado.", "Policies"),
        ],
        artifacts=[
            DemoArtifact("checkpoint_request.md", "Resumo fictício do pedido de aprovação."),
        ],
    )

    return {scenario.key: scenario for scenario in (success, failure, checkpoint)}
