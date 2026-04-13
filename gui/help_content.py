"""Structured help content for the in-app manual."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpSection:
    key: str
    title: str
    summary: str
    content: str


HELP_SECTIONS = [
    HelpSection(
        key="overview",
        title="Visão Geral",
        summary="O que o AI Orchestrator faz e qual é o fluxo principal.",
        content="""
<h2>Visão Geral</h2>
<p>O AI Orchestrator coordena um fluxo de desenvolvimento assistido por IA com foco em execução local e controle do usuário.</p>
<p><b>Fluxo básico:</b> tarefa → planner → executor → review → validação → commit/push</p>
<p>Na prática, você descreve o objetivo, o planner organiza a estratégia, o executor implementa, o reviewer confere, a validação roda os checks do projeto e o Git fecha o ciclo quando configurado.</p>
""",
    ),
    HelpSection(
        key="getting_started",
        title="Primeiros Passos",
        summary="Como sair da primeira abertura até a primeira tarefa.",
        content="""
<h2>Primeiros Passos</h2>
<ol>
<li>Abra o onboarding e escolha a pasta do projeto.</li>
<li>Selecione o perfil do projeto: flutter, python ou generic.</li>
<li>Configure a chave da OpenAI.</li>
<li>Confirme o comando do Claude executor.</li>
<li>Revise o checklist mínimo e siga para Nova Tarefa.</li>
</ol>
<p>Se preferir, você pode reabrir o onboarding em <b>Configurações</b>.</p>
""",
    ),
    HelpSection(
        key="tasks",
        title="Como Criar Uma Tarefa",
        summary="O que escrever e como decidir entre simples e avançado.",
        content="""
<h2>Como Criar Uma Tarefa</h2>
<p>No modo simples, você precisa apenas da descrição da tarefa e do botão <b>Executar</b>.</p>
<p>Abra o modo avançado quando quiser escolher diretório, perfil, número de iterações ou automações como validação, commit e push.</p>
<p>Uma boa tarefa descreve: problema, resultado esperado e restrições importantes.</p>
""",
    ),
    HelpSection(
        key="roles",
        title="Planner, Executor e Reviewer",
        summary="O papel de cada etapa do pipeline.",
        content="""
<h2>Planner, Executor e Reviewer</h2>
<p><b>Planner:</b> entende o pedido e propõe a estratégia.</p>
<p><b>Executor:</b> aplica as mudanças no código usando o comando configurado.</p>
<p><b>Reviewer:</b> faz a revisão final e destaca riscos, pendências e qualidade.</p>
<p>Essas etapas existem para reduzir tentativa e erro e manter rastreabilidade.</p>
""",
    ),
    HelpSection(
        key="checkpoints",
        title="Checkpoints",
        summary="Quando a execução pausa para pedir aprovação.",
        content="""
<h2>Checkpoints</h2>
<p>O app cria checkpoints quando detecta ações sensíveis, como exclusões, migrações ou comandos destrutivos.</p>
<p>Quando isso acontece, a execução pausa e pede sua aprovação antes de continuar.</p>
<p>No modo simples, pense neles como uma proteção extra. No avançado, você pode ajustar os gatilhos.</p>
""",
    ),
    HelpSection(
        key="policies",
        title="Policies",
        summary="Regras adicionais para governança e segurança.",
        content="""
<h2>Policies</h2>
<p>Policies permitem analisar execuções com regras mais detalhadas. Esse painel é mais útil para times ou fluxos que exigem governança explícita.</p>
<p>No modo simples ele fica oculto para reduzir ruído.</p>
""",
    ),
    HelpSection(
        key="replay",
        title="Replay",
        summary="Simular ou reexecutar fluxos antigos.",
        content="""
<h2>Replay</h2>
<p>O replay permite reproduzir uma execução anterior para comparar resultado, entender regressões ou analisar o comportamento do fluxo.</p>
<p>É uma ferramenta avançada e por isso fica fora do modo simples.</p>
""",
    ),
    HelpSection(
        key="diagnostics",
        title="Diagnóstico",
        summary="Como validar ambiente, OpenAI, executor, workspace e Git.",
        content="""
<h2>Diagnóstico</h2>
<p>Use a tela de Diagnóstico para testar o ambiente inteiro ou checks individuais.</p>
<p>Ela é o melhor lugar para confirmar se OpenAI, Claude, workspace e Git estão prontos antes de iniciar automações mais agressivas.</p>
""",
    ),
    HelpSection(
        key="openai",
        title="Configurar OpenAI",
        summary="Onde informar a chave e como validar a conexão.",
        content="""
<h2>Configurar OpenAI</h2>
<p>Você pode informar a chave em <b>Configurações → Ambiente</b> ou criar um arquivo <code>.env</code> com <code>OPENAI_API_KEY=...</code>.</p>
<p>Depois, use o teste da tela Ambiente ou do onboarding para validar a configuração.</p>
""",
    ),
    HelpSection(
        key="claude",
        title="Configurar Claude",
        summary="Como confirmar o executor e o comando correto.",
        content="""
<h2>Configurar Claude</h2>
<p>Defina o comando do executor em <b>Configurações → Executor</b>. O padrão é <code>claude</code>.</p>
<p>Se o comando não estiver disponível no PATH, o checklist mínimo e o onboarding vão alertar você.</p>
""",
    ),
    HelpSection(
        key="git",
        title="Configurar Git",
        summary="Remote, branch, proteção e quando o Git é opcional.",
        content="""
<h2>Configurar Git</h2>
<p>Git é recomendado para usar commit e push automáticos, mas o app ainda consegue executar tarefas sem repositório.</p>
<p>Em <b>Configurações → Git</b> você ajusta remote, branch, branches protegidas e automações.</p>
""",
    ),
    HelpSection(
        key="modes",
        title="Modo Simples vs Avançado",
        summary="Quando usar cada modo da interface.",
        content="""
<h2>Modo Simples vs Avançado</h2>
<p><b>Modo simples:</b> mostra o essencial para começar rápido.</p>
<p><b>Modo avançado:</b> libera painéis técnicos, opções raras e ajustes detalhados.</p>
<p>Você pode alternar em Configurações ou pelo cabeçalho da própria tela.</p>
""",
    ),
    HelpSection(
        key="faq",
        title="FAQ",
        summary="Respostas curtas para dúvidas comuns.",
        content="""
<h2>FAQ</h2>
<p><b>Preciso de Git para usar?</b> Não, mas commit e push automáticos dependem disso.</p>
<p><b>O que é configuração mínima?</b> Projeto, perfil, OpenAI, executor e workspace funcionando.</p>
<p><b>Posso reabrir o onboarding?</b> Sim. Use o botão em Configurações.</p>
""",
    ),
    HelpSection(
        key="troubleshooting",
        title="Solução de Problemas",
        summary="O que verificar quando algo não inicia como esperado.",
        content="""
<h2>Solução de Problemas</h2>
<ul>
<li>Se a OpenAI falhar, revise a chave e teste novamente.</li>
<li>Se o executor falhar, confirme o comando do Claude e o PATH.</li>
<li>Se o workspace falhar, troque para uma pasta com permissão de escrita.</li>
<li>Se o Git estiver ausente, o app continua funcionando, mas sem automações Git.</li>
</ul>
""",
    ),
]


def find_help_section(key: str) -> HelpSection:
    """Return a section by key, defaulting to overview."""
    for section in HELP_SECTIONS:
        if section.key == key:
            return section
    return HELP_SECTIONS[0]
