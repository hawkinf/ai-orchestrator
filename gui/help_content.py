"""Structured help content for the in-app manual."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HelpSection:
    key: str
    title: str
    summary: str
    content: str


# Contextual help definitions for tooltips and field helpers
CONTEXTUAL_HELP = {
    "profile": {
        "label": "Perfil do projeto",
        "short": "Define validações e contexto padrão.",
        "detail": "Use flutter para apps Flutter, python para projetos Python e generic para fluxos sem linguagem específica.",
    },
    "max_iterations": {
        "label": "Máximo de iterações",
        "short": "Tentativas automáticas antes de parar.",
        "detail": "Aumente apenas quando quiser que o sistema insista mais em resolver o problema automaticamente.",
    },
    "auto_validate": {
        "label": "Validar automaticamente",
        "short": "Executa testes ao final.",
        "detail": "Roda os comandos de validação do perfil (como flutter analyze ou pytest) quando a tarefa termina.",
    },
    "auto_commit": {
        "label": "Commit automático",
        "short": "Cria commit se a validação passar.",
        "detail": "Só funciona com Git configurado. O commit usa a descrição da tarefa como mensagem.",
    },
    "auto_push": {
        "label": "Push automático",
        "short": "Envia para o remoto ao final.",
        "detail": "Só funciona com commit automático ativo e Git com remote configurado.",
    },
    "require_approval": {
        "label": "Exigir aprovação",
        "short": "Pausa antes de ações críticas.",
        "detail": "Cria checkpoints quando detecta exclusões, migrações ou outras ações destrutivas.",
    },
    "planner_model": {
        "label": "Modelo do planner",
        "short": "Modelo OpenAI para planejamento.",
        "detail": "O planner entende sua tarefa e propõe a estratégia. Modelos maiores tendem a produzir planos melhores.",
    },
    "reviewer_model": {
        "label": "Modelo do reviewer",
        "short": "Modelo OpenAI para revisão.",
        "detail": "O reviewer verifica a execução e destaca riscos, qualidade e pendências.",
    },
    "planner_timeout": {
        "label": "Timeout do planner",
        "short": "Tempo máximo de espera.",
        "detail": "Quanto tempo esperar pela resposta do planner antes de considerar timeout.",
    },
    "reviewer_timeout": {
        "label": "Timeout do reviewer",
        "short": "Tempo máximo de espera.",
        "detail": "Quanto tempo esperar pela resposta do reviewer antes de considerar timeout.",
    },
    "executor_command": {
        "label": "Comando do executor",
        "short": "Como chamar o Claude CLI.",
        "detail": "O comando usado para invocar o Claude Code CLI. Geralmente é 'claude'.",
    },
    "executor_timeout": {
        "label": "Timeout do executor",
        "short": "Tempo máximo da execução.",
        "detail": "Quanto tempo esperar pela conclusão da execução antes de considerar timeout.",
    },
    "workspace": {
        "label": "Workspace",
        "short": "Pasta para logs e artefatos.",
        "detail": "O workspace guarda histórico de execuções, logs e relatórios. Precisa de permissão de escrita.",
    },
    "command_allowlist": {
        "label": "Allowlist de comandos",
        "short": "Comandos permitidos pelo executor.",
        "detail": "Lista de comandos que o executor pode rodar. Use para restringir ações em ambientes sensíveis.",
    },
    "replay_mode": {
        "label": "Modo replay",
        "short": "Reproduzir execuções antigas.",
        "detail": "Permite simular ou reexecutar fluxos anteriores para comparar resultados ou entender regressões.",
    },
    "policy_engine": {
        "label": "Policy engine",
        "short": "Regras de governança.",
        "detail": "Permite definir políticas que analisam execuções com regras mais detalhadas. Útil para times.",
    },
}


def get_contextual_help(key: str) -> Optional[dict]:
    """Return contextual help for a given field key."""
    return CONTEXTUAL_HELP.get(key)


HELP_SECTIONS = [
    HelpSection(
        key="overview",
        title="Visão Geral",
        summary="O que o AI Orchestrator faz e qual é o fluxo principal.",
        content="""
<h2>Visão Geral</h2>
<p>O AI Orchestrator coordena um fluxo de desenvolvimento assistido por IA com foco em execução local e controle do usuário.</p>

<h3>Fluxo básico</h3>
<p><b>tarefa → planner → executor → review → validação → commit/push</b></p>

<h3>O que cada etapa faz</h3>
<ol>
<li><b>Tarefa:</b> você descreve o objetivo de forma clara</li>
<li><b>Planner:</b> a IA organiza a estratégia de implementação</li>
<li><b>Executor:</b> o Claude Code aplica as mudanças no código</li>
<li><b>Reviewer:</b> a IA confere o resultado e destaca riscos</li>
<li><b>Validação:</b> os checks do projeto rodam (testes, lint, etc)</li>
<li><b>Git:</b> commit e push quando configurado</li>
</ol>

<h3>Por que usar?</h3>
<ul>
<li>Mantém rastreabilidade de tudo que foi feito</li>
<li>Reduz tentativa e erro manual</li>
<li>Cria checkpoints antes de ações destrutivas</li>
<li>Valida automaticamente antes de commitar</li>
</ul>
""",
    ),
    HelpSection(
        key="getting_started",
        title="Primeiros Passos",
        summary="Como sair da primeira abertura até a primeira tarefa.",
        content="""
<h2>Primeiros Passos</h2>

<h3>Checklist de primeira execução</h3>
<ol>
<li>✓ Abra o <b>onboarding</b> e escolha a pasta do projeto</li>
<li>✓ Selecione o <b>perfil</b>: flutter, python ou generic</li>
<li>✓ Configure a <b>chave da OpenAI</b></li>
<li>✓ Confirme o <b>comando do Claude</b> executor</li>
<li>✓ Revise o <b>checklist mínimo</b> em Configurações</li>
</ol>

<h3>Dica rápida</h3>
<p>Se você fechou o onboarding ou quer refazer, use o botão <b>Executar onboarding novamente</b> em Configurações.</p>

<h3>Configuração mínima recomendada</h3>
<ul>
<li><b>Projeto:</b> pasta raiz do código</li>
<li><b>Perfil:</b> flutter, python ou generic</li>
<li><b>OpenAI:</b> chave válida configurada</li>
<li><b>Executor:</b> comando claude disponível</li>
<li><b>Workspace:</b> pasta com permissão de escrita</li>
<li><b>Git:</b> opcional, mas recomendado para commit/push</li>
</ul>
""",
    ),
    HelpSection(
        key="first_task",
        title="Sua Primeira Tarefa",
        summary="Guia completo para executar sua primeira tarefa com sucesso.",
        content="""
<h2>Sua Primeira Tarefa</h2>

<h3>O que esperar</h3>
<p>A primeira tarefa é o momento de conhecer o fluxo do sistema. Recomendamos começar com algo:</p>
<ul>
<li><b>Pequeno:</b> uma única funcionalidade ou correção</li>
<li><b>Seguro:</b> sem exclusões ou migrações</li>
<li><b>Observável:</b> onde você pode verificar o resultado facilmente</li>
</ul>

<h3>Exemplos recomendados por perfil</h3>

<p><b>Flutter:</b></p>
<ul>
<li>"Revise a tela inicial, rode flutter analyze e flutter test, corrija erros simples."</li>
<li>"Adicione comentários explicativos nas funções principais do projeto."</li>
</ul>

<p><b>Python:</b></p>
<ul>
<li>"Revise o módulo principal, execute pytest e ruff check, corrija falhas simples."</li>
<li>"Adicione docstrings e type hints nas funções que estão faltando."</li>
</ul>

<p><b>Generic:</b></p>
<ul>
<li>"Analise a estrutura do projeto e sugira melhorias de organização."</li>
<li>"Gere um relatório com os principais arquivos e suas responsabilidades."</li>
</ul>

<h3>O que evitar na primeira vez</h3>
<ul>
<li>Tarefas muito grandes ou ambiciosas</li>
<li>Exclusões de arquivos ou dados</li>
<li>Migrações de banco de dados</li>
<li>Mudanças em branches protegidas</li>
</ul>

<h3>Passo a passo</h3>
<ol>
<li>Ao final do onboarding, clique em <b>Criar minha primeira tarefa</b></li>
<li>Escolha o perfil do seu projeto</li>
<li>Selecione um exemplo ou escreva sua própria tarefa</li>
<li>Revise os detalhes e clique em <b>Executar</b></li>
<li>Acompanhe o progresso no dashboard</li>
<li>Ao final, veja o relatório e os artefatos gerados</li>
</ol>

<h3>Depois da primeira tarefa</h3>
<p>Após completar sua primeira execução, você poderá:</p>
<ul>
<li>Ver os artefatos gerados na pasta de runs</li>
<li>Criar novas tarefas com mais confiança</li>
<li>Explorar o modo avançado quando precisar de mais controle</li>
</ul>
""",
    ),
    HelpSection(
        key="tasks",
        title="Como Criar Uma Tarefa",
        summary="O que escrever e como decidir entre simples e avançado.",
        content="""
<h2>Como Criar Uma Tarefa</h2>

<h3>Modo simples</h3>
<p>Basta escrever a descrição e clicar <b>Executar</b>. O sistema usa os padrões.</p>

<h3>Modo avançado</h3>
<p>Abra quando precisar ajustar:</p>
<ul>
<li>Diretório específico</li>
<li>Perfil diferente</li>
<li>Número de iterações</li>
<li>Automações (validar, commit, push)</li>
</ul>

<h3>Como escrever uma boa tarefa</h3>
<p>Uma tarefa bem escrita inclui:</p>
<ol>
<li><b>O problema ou objetivo:</b> o que precisa ser feito</li>
<li><b>O resultado esperado:</b> como saber se funcionou</li>
<li><b>Restrições importantes:</b> o que não pode acontecer</li>
</ol>

<h3>Exemplos de tarefas</h3>
<p><b>Boa:</b> "Corrigir o bug de login onde o usuário não consegue entrar quando a senha tem caractere especial. Adicionar teste para esse caso."</p>
<p><b>Ruim:</b> "Corrigir login"</p>

<p><b>Boa:</b> "Criar endpoint GET /api/users com paginação. Retornar no máximo 20 itens por página. Incluir contagem total no header X-Total-Count."</p>
<p><b>Ruim:</b> "Criar API de usuários"</p>
""",
    ),
    HelpSection(
        key="understanding_runs",
        title="Entendendo uma Run",
        summary="Como acompanhar e entender o que aconteceu em cada execução.",
        content="""
<h2>Entendendo uma Run</h2>

<h3>O que é uma Run?</h3>
<p>Uma run é uma execução completa do pipeline para uma tarefa. Ela inclui todas as etapas desde o planejamento até a finalização.</p>

<h3>Timeline da Run</h3>
<p>A timeline mostra visualmente cada etapa da execução em ordem cronológica:</p>

<ol>
<li><b>📋 Planejamento:</b> O sistema analisa sua tarefa e cria um plano de execução, identificando arquivos afetados, riscos e passos de validação.</li>
<li><b>⚙️ Execução:</b> O código é modificado automaticamente pelo executor (Claude), seguindo o plano definido.</li>
<li><b>🔍 Revisão:</b> O resultado é analisado pelo revisor (OpenAI) para identificar problemas, regressões ou melhorias necessárias.</li>
<li><b>✓ Validação:</b> São executados testes e verificações do projeto conforme o perfil configurado.</li>
<li><b>📦 Git:</b> As alterações são registradas no Git com commit e/ou push.</li>
<li><b>🏁 Finalização:</b> A run é finalizada e os artefatos são salvos.</li>
</ol>

<h3>Status dos Eventos</h3>
<ul>
<li><b style="color: #6b7280;">● Pendente:</b> Etapa ainda não iniciada</li>
<li><b style="color: #3b82f6;">● Em andamento:</b> Etapa em execução</li>
<li><b style="color: #22c55e;">● Concluído:</b> Etapa finalizada com sucesso</li>
<li><b style="color: #ef4444;">● Falhou:</b> Etapa com erro</li>
</ul>

<h3>Detalhes Expansíveis</h3>
<p>Cada evento na timeline pode ser expandido para ver:</p>
<ul>
<li><b>Logs:</b> Saída completa do processo</li>
<li><b>Comandos:</b> Lista de comandos executados</li>
<li><b>Arquivos:</b> Arquivos criados ou modificados</li>
<li><b>Erros:</b> Detalhes de falhas quando houver</li>
</ul>

<h3>Eventos Especiais</h3>
<ul>
<li><b>⚠️ Checkpoint:</b> Pausa para aprovação antes de ação arriscada</li>
<li><b>🔄 Nova Iteração:</b> Início de uma nova tentativa de refinar o resultado</li>
<li><b>❌ Erro:</b> Algo falhou durante a execução</li>
</ul>

<h3>Como usar a Timeline</h3>
<ol>
<li>Acesse a aba <b>Execuções</b> no menu lateral</li>
<li>Selecione uma run na lista</li>
<li>A aba <b>Timeline</b> mostra todos os eventos</li>
<li>Clique em "Mostrar detalhes" para expandir cada evento</li>
</ol>

<h3>Dicas</h3>
<ul>
<li>Use a timeline para entender o que aconteceu em runs com erro</li>
<li>Verifique a duração de cada etapa para identificar gargalos</li>
<li>Expanda os detalhes para ver logs e comandos executados</li>
<li>A timeline é atualizada automaticamente durante a execução</li>
</ul>
""",
    ),
    HelpSection(
        key="system_insights",
        title="Como Interpretar os Insights do Sistema",
        summary="Leia padrões do histórico recente e transforme sinais em ações práticas.",
        content="""
<h2>Como Interpretar os Insights do Sistema</h2>

<p>Os <b>Insights do Sistema</b> olham várias runs ao mesmo tempo para resumir o estado operacional recente do AI Orchestrator.</p>

<h3>O que eles analisam</h3>
<ul>
<li><b>Confiabilidade:</b> taxa de sucesso, aumento de falhas e estabilidade geral</li>
<li><b>Validação:</b> falhas recorrentes em testes, lint e checks finais</li>
<li><b>Execução e review:</b> runs com muitas iterações ou follow-ups frequentes</li>
<li><b>Checkpoint:</b> quantas runs exigiram intervenção manual</li>
<li><b>Git:</b> problemas de commit, push ou estado do repositório</li>
<li><b>Performance:</b> duração média e perfis mais lentos</li>
</ul>

<h3>Como ler o resumo executivo</h3>
<p>O resumo executivo responde a pergunta: <b>"como o sistema tem se comportado nas últimas runs?"</b></p>
<ul>
<li><b>Sistema estável:</b> sem concentração de falhas ou gargalos claros</li>
<li><b>Sistema utilizável com alertas:</b> funciona, mas há sinais para acompanhar</li>
<li><b>Sistema degradado:</b> falhas, duração ou checkpoints acima do esperado</li>
<li><b>Sistema com falhas recorrentes:</b> o histórico recente pede correção antes de escalar o uso</li>
</ul>

<h3>Exemplos de interpretação</h3>
<ul>
<li><b>"Falhas recorrentes em validação":</b> revise comandos do profile e rode diagnóstico antes da próxima task</li>
<li><b>"Checkpoints frequentes":</b> o escopo pode estar arriscado demais ou as policies estão rígidas</li>
<li><b>"Profile Flutter está mais lento":</b> compare comandos de validação e tamanho médio das tarefas desse profile</li>
<li><b>"Aumento recente de falhas":</b> use replay nas últimas falhas antes de insistir no mesmo tipo de tarefa</li>
</ul>

<h3>Boas práticas</h3>
<ol>
<li>Comece pelo <b>resumo executivo</b></li>
<li>Veja as <b>métricas agregadas</b> para entender tendência</li>
<li>Leia os <b>alertas e recomendações</b> priorizados</li>
<li>Use <b>Replay</b> e <b>Diagnóstico</b> quando houver repetição de falhas</li>
<li>Compare os perfis para descobrir onde o fluxo está mais previsível</li>
</ol>
""",
    ),
    HelpSection(
        key="command_center",
        title="Entendendo o Command Center",
        summary="Use a tela inicial para decidir rapidamente a próxima ação operacional.",
        content="""
<h2>Entendendo o Command Center</h2>

<p>O <b>Command Center</b> é a tela inicial do AI Orchestrator. Ele resume o estado atual do sistema e aponta o melhor próximo passo.</p>

<h3>O que aparece ali</h3>
<ul>
<li><b>Saúde do sistema:</b> leitura curta do momento operacional</li>
<li><b>Próxima ação:</b> o que merece atenção primeiro</li>
<li><b>Runs recentes:</b> últimas execuções com status, etapa e duração</li>
<li><b>Alertas e checkpoints:</b> itens que podem bloquear a próxima run</li>
<li><b>Ações recomendadas:</b> atalhos clicáveis para agir sem procurar a tela certa</li>
</ul>

<h3>Como usar</h3>
<ol>
<li>Leia o <b>resumo executivo</b> para entender se o sistema está saudável</li>
<li>Se houver uma <b>próxima ação</b>, comece por ela</li>
<li>Revise as <b>runs recentes</b> quando quiser contexto rápido</li>
<li>Abra <b>Checkpoints</b> ou <b>Diagnóstico</b> se houver alertas operacionais</li>
</ol>

<h3>Modo simples vs avançado</h3>
<ul>
<li><b>Simples:</b> mostra só status, ação principal, CTA e runs essenciais</li>
<li><b>Avançado:</b> expõe mais detalhes de saúde e sinais operacionais</li>
</ul>
""",
    ),
    HelpSection(
        key="recommended_actions",
        title="Como usar as Ações Recomendadas",
        summary="Transforme sinais e alertas em próximos passos práticos dentro da aplicação.",
        content="""
<h2>Como usar as Ações Recomendadas</h2>

<p>As <b>Ações Recomendadas</b> aparecem quando o app já conseguiu interpretar uma run ou o histórico recente do sistema.</p>

<h3>O que elas fazem</h3>
<ul>
<li>Levam você para a <b>tela certa</b> da aplicação</li>
<li>Abrem a <b>aba correta</b> quando isso ajuda</li>
<li>Reduzem a dúvida sobre <b>o que fazer agora</b></li>
</ul>

<h3>Exemplos práticos</h3>
<ul>
<li><b>Falha de validação:</b> abrir a aba Validação da run ou enviar para Replay</li>
<li><b>Problema de Git:</b> abrir Configurações &gt; Git ou Diagnóstico</li>
<li><b>Checkpoints frequentes:</b> abrir o Centro de Checkpoints ou Policies</li>
<li><b>Aumento de falhas:</b> filtrar o Dashboard por runs com falha</li>
</ul>

<h3>Prioridades</h3>
<ul>
<li><b>Agora:</b> ação de impacto imediato, geralmente para destravar o fluxo</li>
<li><b>Recomendado:</b> melhora a chance da próxima run dar certo</li>
<li><b>Opcional:</b> aprofundamento ou ajuste fino</li>
</ul>

<h3>Como decidir</h3>
<ol>
<li>Comece pelas ações <b>Agora</b></li>
<li>Depois execute as ações <b>Recomendadas</b></li>
<li>Use as <b>Opcionais</b> quando quiser explorar a causa com mais calma</li>
</ol>
""",
    ),
    HelpSection(
        key="insights",
        title="Como Interpretar os Insights",
        summary="Entenda os insights gerados após cada execução.",
        content="""
<h2>Como Interpretar os Insights da Run</h2>

<h3>O que são Insights?</h3>
<p>Insights são análises automáticas que ajudam você a entender o que aconteceu na execução e o que pode melhorar.</p>

<h3>Sumário Executivo</h3>
<p>No topo da aba Insights você verá um resumo com:</p>
<ul>
<li><b>Resultado geral:</b> sucesso, sucesso com avisos, falha ou interrompido</li>
<li><b>Resumo em uma frase:</b> o que aconteceu de mais importante</li>
<li><b>Métricas:</b> duração, etapas concluídas, arquivos alterados</li>
</ul>

<h3>Níveis de Severidade</h3>
<ul>
<li><b style="color: #3b82f6;">ℹ Informação:</b> Dados úteis, sem ação necessária</li>
<li><b style="color: #22c55e;">✓ Sucesso:</b> Algo funcionou bem, parabéns</li>
<li><b style="color: #f59e0b;">⚠ Aviso:</b> Atenção recomendada, pode melhorar</li>
<li><b style="color: #ef4444;">✗ Erro:</b> Problema que precisa de correção</li>
</ul>

<h3>Categorias de Insights</h3>
<ul>
<li><b>Validação:</b> Resultados de testes e análise estática</li>
<li><b>Execução:</b> O que o executor fez e como</li>
<li><b>Revisão:</b> Feedback do revisor sobre qualidade</li>
<li><b>Checkpoint:</b> Pausas que exigiram aprovação</li>
<li><b>Git:</b> Commits, branches e operações de versionamento</li>
<li><b>Performance:</b> Tempo de execução e gargalos</li>
<li><b>Confiabilidade:</b> Erros, retentativas e estabilidade</li>
</ul>

<h3>Recomendações</h3>
<p>Cada insight pode incluir uma recomendação prática. Exemplos:</p>
<ul>
<li>"Revise os testes que falharam antes de commitar"</li>
<li>"Considere aumentar o timeout para tarefas longas"</li>
<li>"Verifique os arquivos modificados antes do push"</li>
</ul>

<h3>Exportar Insights</h3>
<p>Os insights são salvos automaticamente na pasta da run em dois formatos:</p>
<ul>
<li><b>insights.json:</b> Dados estruturados para automação</li>
<li><b>insights.md:</b> Relatório legível para humanos</li>
</ul>

<h3>Dicas de Uso</h3>
<ul>
<li>Comece pelo sumário executivo para ter uma visão geral</li>
<li>Priorize insights de erro (vermelho) e aviso (amarelo)</li>
<li>Use as recomendações como guia de próximos passos</li>
<li>Compare insights entre runs para ver evolução</li>
</ul>
""",
    ),
    HelpSection(
        key="roles",
        title="Planner, Executor e Reviewer",
        summary="O papel de cada etapa do pipeline.",
        content="""
<h2>Planner, Executor e Reviewer</h2>

<h3>Planner (OpenAI)</h3>
<ul>
<li>Entende o pedido e analisa o contexto</li>
<li>Propõe a estratégia de implementação</li>
<li>Define o escopo e os passos necessários</li>
<li>Identifica riscos e dependências</li>
</ul>
<p><i>Modelo padrão: gpt-4o</i></p>

<h3>Executor (Claude Code)</h3>
<ul>
<li>Aplica as mudanças no código</li>
<li>Segue o plano definido pelo planner</li>
<li>Cria, edita e remove arquivos</li>
<li>Executa comandos quando necessário</li>
</ul>
<p><i>Comando padrão: claude</i></p>

<h3>Reviewer (OpenAI)</h3>
<ul>
<li>Analisa o resultado da execução</li>
<li>Verifica qualidade e completude</li>
<li>Destaca riscos e pendências</li>
<li>Decide se aprova ou pede correções</li>
</ul>
<p><i>Modelo padrão: gpt-4o</i></p>

<h3>Por que três etapas?</h3>
<p>Separar planejamento, execução e revisão reduz erros, mantém rastreabilidade e permite que cada etapa use o modelo mais adequado.</p>
""",
    ),
    HelpSection(
        key="checkpoints",
        title="Checkpoints",
        summary="Quando a execução pausa para pedir aprovação.",
        content="""
<h2>Checkpoints</h2>

<h3>O que são</h3>
<p>Checkpoints são pontos de pausa onde o sistema pede sua aprovação antes de continuar.</p>

<h3>Quando acontecem</h3>
<p>O app cria checkpoints quando detecta:</p>
<ul>
<li><b>Exclusões:</b> delete, remove, drop</li>
<li><b>Migrações:</b> migration, migrate</li>
<li><b>Ações destrutivas:</b> force push, reset</li>
<li><b>Gatilhos customizados:</b> configuráveis em Segurança</li>
</ul>

<h3>Como aprovar</h3>
<ol>
<li>Uma notificação aparece no topo da tela</li>
<li>Revise a descrição do checkpoint</li>
<li>Clique em <b>Aprovar</b> ou <b>Rejeitar</b></li>
<li>Opcionalmente, adicione uma nota</li>
</ol>

<h3>Gerenciando checkpoints</h3>
<p>Use a tela <b>Checkpoints</b> para ver todos os checkpoints pendentes e histórico de aprovações.</p>

<h3>Configuração</h3>
<p>Em <b>Configurações → Segurança</b> você pode:</p>
<ul>
<li>Ativar/desativar aprovação obrigatória</li>
<li>Adicionar gatilhos customizados</li>
</ul>
""",
    ),
    HelpSection(
        key="policies",
        title="Policies",
        summary="Regras adicionais para governança e segurança.",
        content="""
<h2>Policies</h2>

<h3>O que são</h3>
<p>Policies são regras que analisam execuções com critérios mais detalhados que os checkpoints padrão.</p>

<h3>Quando usar</h3>
<ul>
<li>Times que precisam de governança explícita</li>
<li>Ambientes com requisitos de compliance</li>
<li>Fluxos que exigem auditoria detalhada</li>
</ul>

<h3>Exemplos de policies</h3>
<ul>
<li>Bloquear push para branches protegidas</li>
<li>Exigir revisão para mudanças em arquivos sensíveis</li>
<li>Limitar comandos que podem ser executados</li>
</ul>

<h3>Onde encontrar</h3>
<p>O painel <b>Políticas</b> fica no menu lateral, mas só aparece no <b>modo avançado</b>.</p>
""",
    ),
    HelpSection(
        key="replay",
        title="Replay",
        summary="Simular ou reexecutar fluxos antigos.",
        content="""
<h2>Replay</h2>

<h3>O que é</h3>
<p>O replay permite reproduzir uma execução anterior para análise ou comparação.</p>

<h3>Quando usar</h3>
<ul>
<li>Entender o que aconteceu em uma execução passada</li>
<li>Comparar resultados entre execuções</li>
<li>Analisar regressões</li>
<li>Testar mudanças em policies</li>
</ul>

<h3>Como usar</h3>
<ol>
<li>Vá para o painel <b>Replay</b></li>
<li>Selecione uma execução anterior</li>
<li>Escolha o modo de replay</li>
<li>Execute e compare os resultados</li>
</ol>

<h3>Onde encontrar</h3>
<p>O painel <b>Replay</b> fica no menu lateral, mas só aparece no <b>modo avançado</b>.</p>
""",
    ),
    HelpSection(
        key="diagnostics",
        title="Diagnóstico",
        summary="Como validar ambiente, OpenAI, executor, workspace e Git.",
        content="""
<h2>Diagnóstico</h2>

<h3>O que verifica</h3>
<ul>
<li><b>OpenAI:</b> chave válida e conectividade</li>
<li><b>Claude:</b> executor disponível e funcional</li>
<li><b>Workspace:</b> pasta acessível com permissão de escrita</li>
<li><b>Git:</b> repositório, remote e branch</li>
<li><b>Perfil:</b> comandos de validação configurados</li>
</ul>

<h3>Quando usar</h3>
<ul>
<li>Antes de começar a usar o app</li>
<li>Quando algo parar de funcionar</li>
<li>Depois de mudar configurações</li>
<li>Para confirmar que tudo está pronto</li>
</ul>

<h3>Como interpretar</h3>
<ul>
<li><span style='color:#22c55e'>Verde:</span> OK, pronto para uso</li>
<li><span style='color:#f59e0b'>Amarelo:</span> Warning, funciona mas com limitações</li>
<li><span style='color:#ef4444'>Vermelho:</span> Erro, precisa corrigir antes de usar</li>
</ul>
""",
    ),
    HelpSection(
        key="openai",
        title="Configurar OpenAI",
        summary="Onde informar a chave e como validar a conexão.",
        content="""
<h2>Configurar OpenAI</h2>

<h3>Onde configurar</h3>
<ul>
<li><b>Onboarding:</b> na etapa de OpenAI</li>
<li><b>Configurações → Ambiente:</b> campo de API Key</li>
<li><b>Arquivo .env:</b> <code>OPENAI_API_KEY=sk-...</code></li>
<li><b>Variável de sistema:</b> OPENAI_API_KEY</li>
</ul>

<h3>Prioridade de resolução</h3>
<ol>
<li>Variável de ambiente do sistema</li>
<li>Arquivo .env na pasta do projeto</li>
</ol>

<h3>Como testar</h3>
<ol>
<li>Vá em <b>Configurações → Ambiente</b></li>
<li>Clique em <b>Testar Conexão</b></li>
<li>Verifique se o status fica verde</li>
</ol>

<h3>Problemas comuns</h3>
<ul>
<li><b>Chave inválida:</b> revise o formato sk-...</li>
<li><b>Chave expirada:</b> gere uma nova no painel da OpenAI</li>
<li><b>Sem créditos:</b> adicione créditos na conta OpenAI</li>
</ul>
""",
    ),
    HelpSection(
        key="claude",
        title="Configurar Claude",
        summary="Como confirmar o executor e o comando correto.",
        content="""
<h2>Configurar Claude</h2>

<h3>Requisitos</h3>
<ul>
<li>Claude Code CLI instalado</li>
<li>Comando disponível no PATH</li>
<li>Autenticação configurada</li>
</ul>

<h3>Onde configurar</h3>
<ul>
<li><b>Onboarding:</b> na etapa de Executor</li>
<li><b>Configurações → Executor:</b> campo de comando</li>
</ul>

<h3>Como testar</h3>
<ol>
<li>Abra um terminal</li>
<li>Digite <code>claude --version</code></li>
<li>Verifique se retorna a versão</li>
</ol>

<h3>Problemas comuns</h3>
<ul>
<li><b>Comando não encontrado:</b> instale o Claude Code CLI</li>
<li><b>Não autenticado:</b> rode <code>claude auth</code></li>
<li><b>PATH incorreto:</b> adicione o diretório do claude ao PATH</li>
</ul>

<h3>Comando alternativo</h3>
<p>Se o comando não é <code>claude</code>, informe o caminho completo ou o nome correto em Configurações.</p>
""",
    ),
    HelpSection(
        key="git",
        title="Configurar Git",
        summary="Remote, branch, proteção e quando o Git é opcional.",
        content="""
<h2>Configurar Git</h2>

<h3>Git é obrigatório?</h3>
<p><b>Não.</b> O app funciona sem Git, mas você perde:</p>
<ul>
<li>Commit automático</li>
<li>Push automático</li>
<li>Proteção de branches</li>
</ul>

<h3>Configurações disponíveis</h3>
<ul>
<li><b>Remote:</b> nome do remote (padrão: origin)</li>
<li><b>Branch:</b> branch preferida para operações</li>
<li><b>Branches protegidas:</b> main, master, etc</li>
</ul>

<h3>Automações</h3>
<ul>
<li><b>Auto commit:</b> cria commit quando validação passa</li>
<li><b>Auto push:</b> envia para remote após commit</li>
</ul>

<h3>Segurança</h3>
<p>Branches protegidas criam checkpoints antes de push. Configure em <b>Configurações → Git</b>.</p>
""",
    ),
    HelpSection(
        key="modes",
        title="Modo Simples vs Avançado",
        summary="Quando usar cada modo da interface.",
        content="""
<h2>Modo Simples vs Avançado</h2>

<h3>Modo Simples</h3>
<p>Ideal para começar e para uso diário básico.</p>
<ul>
<li>Interface limpa e focada</li>
<li>Opções essenciais visíveis</li>
<li>Painéis técnicos ocultos</li>
<li>Menos decisões a tomar</li>
</ul>

<h3>Modo Avançado</h3>
<p>Para quem precisa de controle total.</p>
<ul>
<li>Todas as opções visíveis</li>
<li>Painéis de Políticas e Replay</li>
<li>Configurações detalhadas</li>
<li>Logs e diagnósticos completos</li>
</ul>

<h3>O que muda entre os modos</h3>
<table style='border-collapse:collapse;width:100%'>
<tr style='border-bottom:1px solid #3d4451'>
<td><b>Recurso</b></td><td><b>Simples</b></td><td><b>Avançado</b></td>
</tr>
<tr><td>Nova Tarefa</td><td>Essencial</td><td>Completo</td></tr>
<tr><td>Configurações</td><td>Básico</td><td>Detalhado</td></tr>
<tr><td>Políticas</td><td>Oculto</td><td>Visível</td></tr>
<tr><td>Replay</td><td>Oculto</td><td>Visível</td></tr>
<tr><td>Logs</td><td>Oculto</td><td>Visível</td></tr>
</table>

<h3>Como alternar</h3>
<ul>
<li>Botão no cabeçalho de Configurações</li>
<li>A preferência é salva automaticamente</li>
</ul>
""",
    ),
    HelpSection(
        key="faq",
        title="FAQ",
        summary="Respostas curtas para dúvidas comuns.",
        content="""
<h2>FAQ</h2>

<h3>Preciso de Git para usar?</h3>
<p>Não. O app funciona sem Git, mas commit e push automáticos dependem dele.</p>

<h3>O que é configuração mínima?</h3>
<p>Projeto, perfil, OpenAI, executor e workspace funcionando. Git é recomendado mas opcional.</p>

<h3>Posso reabrir o onboarding?</h3>
<p>Sim. Use o botão em <b>Configurações</b>.</p>

<h3>O que acontece se o executor falhar?</h3>
<p>A execução para e você pode retomar depois de corrigir o problema.</p>

<h3>Como faço para parar uma execução?</h3>
<p>O botão de cancelar aparece na barra de status durante a execução.</p>

<h3>Posso usar outro modelo além do gpt-4o?</h3>
<p>Sim. Configure em <b>Configurações → Modelos</b> no modo avançado.</p>

<h3>O que são checkpoints?</h3>
<p>Pontos de pausa onde o sistema pede aprovação antes de ações sensíveis.</p>

<h3>Como vejo o histórico de execuções?</h3>
<p>Use a tela <b>Execuções</b> no menu lateral.</p>

<h3>Onde ficam os logs?</h3>
<p>Na pasta workspace/logs. Você também pode ver em <b>Diagnóstico</b>.</p>
""",
    ),
    HelpSection(
        key="troubleshooting",
        title="Solução de Problemas",
        summary="O que verificar quando algo não inicia como esperado.",
        content="""
<h2>Solução de Problemas</h2>

<h3>OpenAI não conecta</h3>
<ol>
<li>Revise a chave em <b>Configurações → Ambiente</b></li>
<li>Clique em <b>Testar Conexão</b></li>
<li>Verifique se a chave começa com sk-</li>
<li>Confirme se tem créditos na conta OpenAI</li>
</ol>

<h3>Executor não encontrado</h3>
<ol>
<li>Abra um terminal e digite <code>claude --version</code></li>
<li>Se não funcionar, instale o Claude Code CLI</li>
<li>Se instalou mas não funciona, adicione ao PATH</li>
<li>Rode <code>claude auth</code> para autenticar</li>
</ol>

<h3>Workspace sem permissão</h3>
<ol>
<li>Escolha uma pasta onde você pode criar arquivos</li>
<li>Evite pastas do sistema ou protegidas</li>
<li>Use a pasta do projeto ou uma subpasta workspace</li>
</ol>

<h3>Git não detectado</h3>
<ol>
<li>Confirme que git está instalado: <code>git --version</code></li>
<li>Verifique se o projeto é um repositório Git</li>
<li>Se não for, rode <code>git init</code> na pasta do projeto</li>
</ol>

<h3>Execução trava</h3>
<ol>
<li>Verifique os logs em <b>Diagnóstico</b></li>
<li>Confirme que o executor está respondendo</li>
<li>Aumente o timeout em <b>Configurações</b> se necessário</li>
</ol>

<h3>Ainda com problemas?</h3>
<p>Rode o <b>Diagnóstico</b> completo e verifique cada item.</p>
""",
    ),
]


def find_help_section(key: str) -> HelpSection:
    """Return a section by key, defaulting to overview."""
    for section in HELP_SECTIONS:
        if section.key == key:
            return section
    return HELP_SECTIONS[0]
