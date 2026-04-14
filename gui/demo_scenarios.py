"""Static step definitions for the interactive demo."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Optional

from orchestrator.demo_run_builder import DemoScenario, build_demo_scenarios


@dataclass(frozen=True)
class DemoStep:
    key: str
    title: str
    body: str
    panel: Optional[str] = None
    target_key: Optional[str] = None
    setup_key: Optional[str] = None
    content_html: str = ""
    primary_hint: Optional[str] = None


def _list_html(items: list[str]) -> str:
    rendered = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<ul>{rendered}</ul>" if rendered else ""


def _scenario_html(scenario: DemoScenario) -> str:
    timeline = "".join(
        f"<li><b>{escape(event.title)}</b> · {escape(event.description)}</li>"
        for event in scenario.timeline
    )
    insights = "".join(
        f"<li><b>{escape(item.title)}</b> · {escape(item.message)}</li>"
        for item in scenario.insights
    )
    actions = "".join(
        f"<li><b>{escape(item.title)}</b> · {escape(item.reason)} "
        f"<span style='color:#8b949e'>(abre {escape(item.target_label)})</span></li>"
        for item in scenario.actions
    )
    artifacts = "".join(
        f"<li><b>{escape(item.label)}</b> · {escape(item.description)}</li>"
        for item in scenario.artifacts
    )
    return (
        f"<p><b>{escape(scenario.title)}</b><br/>{escape(scenario.summary)}</p>"
        f"<p><b>Tarefa fictícia:</b> {escape(scenario.task_text)}</p>"
        f"<p><b>Timeline simulada</b></p><ul>{timeline}</ul>"
        f"<p><b>Insights simulados</b></p><ul>{insights}</ul>"
        f"<p><b>Ações recomendadas</b></p><ul>{actions}</ul>"
        f"<p><b>Artefatos simulados</b></p><ul>{artifacts}</ul>"
    )


def build_demo_steps() -> list[DemoStep]:
    """Return the fixed interactive-demo journey."""
    scenarios = build_demo_scenarios()
    success = scenarios["success"]
    failure = scenarios["failure"]
    checkpoint = scenarios["checkpoint"]

    return [
        DemoStep(
            key="intro",
            title="O que é o AI Orchestrator",
            body=(
                "O app transforma uma tarefa em linguagem natural em um fluxo guiado com "
                "planejamento, execução, revisão, validação e acompanhamento."
            ),
            panel="command_center",
            target_key="command_center.overview",
            setup_key="show_command_center",
            content_html=(
                "<p><b>Exemplo fictício</b></p>"
                "<p>Corrigir a tela de login, rodar validações e gerar relatório final.</p>"
                "<p>Durante a demo, nada será executado de verdade: sem OpenAI real, sem Claude real e sem alterar projeto do usuário.</p>"
            ),
            primary_hint="Comece entendendo o fluxo geral antes de configurar qualquer coisa.",
        ),
        DemoStep(
            key="command_center",
            title="Command Center",
            body="Esta é a tela inicial. Ela responde rapidamente se o sistema está saudável e qual é a melhor próxima ação.",
            panel="command_center",
            target_key="command_center.overview",
            setup_key="show_command_center",
            content_html=_list_html(
                [
                    "Use o topo para ler saúde do sistema, falhas recentes e a última run.",
                    "O bloco Próxima ação aponta o que fazer agora.",
                    "A parte de baixo resume runs, alertas e ações recomendadas.",
                ]
            ),
        ),
        DemoStep(
            key="new_task",
            title="Nova Tarefa",
            body="Aqui você descreve o objetivo. A tela começa simples e deixa as opções avançadas fora do caminho.",
            panel="new_task",
            target_key="task.task_edit",
            setup_key="show_task_example_simple",
            content_html=(
                "<p><b>Boa tarefa:</b> clara, pequena e com resultado esperado.</p>"
                "<p><b>Evite:</b> pedir muitas mudanças grandes na primeira execução.</p>"
                f"<p><b>Exemplo usado na demo:</b> {escape(success.task_text)}</p>"
            ),
            primary_hint="Comece com um pedido pequeno e seguro.",
        ),
        DemoStep(
            key="task_advanced",
            title="Opções avançadas",
            body="Quando precisar de mais controle, abra o avançado para ajustar perfil, iterações e automações.",
            panel="new_task",
            target_key="task.settings",
            setup_key="show_task_example_advanced",
            content_html=_list_html(
                [
                    "Perfil define o contexto e as validações padrão.",
                    "Iterações limitam quantas tentativas automáticas o sistema pode fazer.",
                    "Validar automaticamente ajuda a encerrar a run com mais previsibilidade.",
                    "Exigir aprovação protege ações sensíveis.",
                ]
            ),
        ),
        DemoStep(
            key="dashboard",
            title="Dashboard e histórico",
            body="O dashboard ajuda a comparar runs recentes, status, duração e padrões que merecem atenção.",
            panel="dashboard",
            target_key="sidebar.dashboard",
            setup_key="show_dashboard",
            content_html=_list_html(
                [
                    "Use filtros para separar falhas, perfis e runs com checkpoint.",
                    "Veja tendências antes de repetir uma automação problemática.",
                ]
            ),
        ),
        DemoStep(
            key="checkpoints",
            title="Checkpoints",
            body="Quando a run detecta risco, ela pode pausar e pedir aprovação humana antes de continuar.",
            panel="checkpoints",
            target_key="sidebar.checkpoints",
            setup_key="show_checkpoints",
            content_html=_scenario_html(checkpoint),
            primary_hint="Checkpoint é um freio de segurança, não um erro.",
        ),
        DemoStep(
            key="diagnostics",
            title="Diagnóstico",
            body="O diagnóstico valida OpenAI, executor, workspace, Git e configuração mínima recomendada.",
            panel="diagnostics",
            target_key="sidebar.diagnostics",
            setup_key="show_diagnostics",
            content_html=_list_html(
                [
                    "Abra aqui quando a run falhar e você não souber se o problema é de ambiente ou de tarefa.",
                    "No fluxo real, é uma boa primeira ação antes de insistir em novas execuções.",
                ]
            ),
        ),
        DemoStep(
            key="config",
            title="Configuração sem risco",
            body="Na demo, a tela de configuração é preenchida só visualmente para mostrar o que seria ajustado em um caso real.",
            panel="settings",
            target_key="config.setup_card",
            setup_key="show_config_example",
            content_html=_list_html(
                [
                    "Projeto e workspace apontam onde o app vai operar e guardar histórico.",
                    "OpenAI e executor definem os dois motores principais do fluxo.",
                    "O checklist mostra o mínimo recomendado para começar bem.",
                ]
            ),
        ),
        DemoStep(
            key="help",
            title="Ajuda e manual",
            body="O manual embutido explica telas, conceitos e solução de problemas sem depender de documentação externa.",
            panel="help",
            target_key="help.section_list",
            setup_key="show_help",
            content_html=_list_html(
                [
                    "Use o índice para navegar por Command Center, Replay, Policies e Diagnóstico.",
                    "A busca ajuda a encontrar um assunto específico mais rápido.",
                    "A demo pode ser aberta quantas vezes você quiser.",
                ]
            ),
        ),
        DemoStep(
            key="success_run",
            title="Run fictícia bem-sucedida",
            body="Agora o app simula uma execução completa para mostrar o fluxo ideal sem tocar no projeto real.",
            panel="runs",
            target_key="run.timeline",
            setup_key="show_success_run",
            content_html=_scenario_html(success),
            primary_hint="Use esta leitura para entender o caminho feliz do produto.",
        ),
        DemoStep(
            key="success_results",
            title="Como ler o resultado",
            body="Depois da run, Timeline, Insights e Ações Recomendadas ajudam a entender rapidamente o que aconteceu.",
            panel="runs",
            target_key="run.recommended_actions",
            setup_key="show_success_results",
            content_html=_list_html(
                [
                    "Timeline mostra a ordem dos eventos.",
                    "Insights resumem os sinais mais úteis.",
                    "Ações Recomendadas dizem qual é o melhor próximo passo.",
                    "Artefatos guardam relatórios e saídas importantes.",
                ]
            ),
        ),
        DemoStep(
            key="failure_run",
            title="Run fictícia com problema",
            body="Este cenário mostra como o sistema responde quando a validação falha e como ele orienta o próximo passo.",
            panel="runs",
            target_key="run.insights",
            setup_key="show_failure_run",
            content_html=_scenario_html(failure),
            primary_hint="Quando algo dá errado, olhe primeiro Timeline, Insights e Diagnóstico.",
        ),
        DemoStep(
            key="conclusion",
            title="Fim da demonstração",
            body="Agora você já viu o fluxo básico, os pontos de diagnóstico e como o app reage a sucesso, falha e checkpoint.",
            panel="command_center",
            target_key="command_center.primary_action",
            setup_key="show_command_center",
            content_html=_list_html(
                [
                    "Abrir Diagnóstico para validar o ambiente real.",
                    "Criar sua primeira tarefa real com escopo pequeno.",
                    "Abrir o manual para revisar uma tela específica.",
                    "Repetir a demonstração quando quiser.",
                ]
            ),
            primary_hint="O próximo passo real recomendado costuma ser validar o ambiente e criar uma tarefa pequena.",
        ),
    ]
