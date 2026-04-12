"""Help panel with user guide, FAQ, and documentation."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QSplitter, QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


# ============================================================================
# CONTENT - User Guide, FAQ, Function Descriptions
# ============================================================================

ABOUT_CONTENT = """
<h2>AI Orchestrator</h2>
<p><b>Versao:</b> 0.1.0</p>
<p><b>Autor:</b> Hawk Informatica</p>

<h3>O que e este programa?</h3>
<p>O AI Orchestrator e um sistema de orquestracao local para desenvolvimento assistido por IA.
Ele coordena o fluxo de trabalho entre diferentes modelos de IA para automatizar tarefas de programacao.</p>

<h3>Como funciona?</h3>
<p>O sistema usa tres componentes principais:</p>
<ul>
<li><b>Planner (OpenAI GPT-4o):</b> Analisa a tarefa e cria um plano de execucao</li>
<li><b>Executor (Claude Code):</b> Implementa as mudancas no codigo</li>
<li><b>Reviewer (OpenAI GPT-4o):</b> Revisa as alteracoes e aprova commits</li>
</ul>

<h3>Pipeline de Execucao</h3>
<pre>
TAREFA -> PLANO -> EXECUCAO -> REVISAO -> VALIDACAO -> COMMIT -> PUSH
</pre>

<h3>Principais Beneficios</h3>
<ul>
<li>Automatiza tarefas repetitivas de desenvolvimento</li>
<li>Garante revisao sistematica de codigo</li>
<li>Executa validacoes automaticas (flutter analyze, pytest, etc.)</li>
<li>Mantem historico completo de todas as execucoes</li>
<li>Checkpoints de seguranca para mudancas destrutivas</li>
</ul>
"""

GUIDE_CONTENT = """
<h2>Guia Rapido de Utilizacao</h2>

<h3>1. Iniciando uma Nova Tarefa</h3>
<ol>
<li>Clique em <b>"Nova Tarefa"</b> no menu lateral</li>
<li>Digite a descricao da tarefa no campo de texto grande</li>
<li>Selecione o <b>perfil do projeto</b> (Flutter, Python, etc.)</li>
<li>Configure as opcoes desejadas:
    <ul>
    <li><b>Auto Validar:</b> Executa flutter analyze/pytest automaticamente</li>
    <li><b>Auto Commit:</b> Faz commit das alteracoes se validacao passar</li>
    <li><b>Auto Push:</b> Envia para o repositorio remoto</li>
    </ul>
</li>
<li>Clique no botao <b>"Executar"</b></li>
</ol>

<h3>2. Acompanhando a Execucao</h3>
<ul>
<li>O progresso aparece na barra de status inferior</li>
<li>A lista de execucoes mostra o status atual</li>
<li>Clique em uma execucao para ver detalhes</li>
</ul>

<h3>3. Visualizando Resultados</h3>
<p>Na tela de <b>Execucoes</b>, clique em uma run para ver:</p>
<ul>
<li><b>Visao Geral:</b> Resumo da tarefa e status</li>
<li><b>Plano:</b> O que o Planner decidiu fazer</li>
<li><b>Execucao:</b> O que o Claude implementou</li>
<li><b>Review:</b> Analise do Reviewer</li>
<li><b>Validacao:</b> Resultados dos testes</li>
<li><b>Git:</b> Informacoes do commit</li>
</ul>

<h3>4. Aprovando Checkpoints</h3>
<p>Quando uma acao requer aprovacao humana:</p>
<ol>
<li>Um alerta amarelo aparece no topo da tela</li>
<li>Clique em <b>"Revisar"</b> para ver os detalhes</li>
<li>Escolha <b>"Aprovar"</b> ou <b>"Rejeitar"</b></li>
<li>Adicione uma observacao se desejar</li>
</ol>

<h3>5. Configuracoes</h3>
<p>Na tela de <b>Configuracoes</b> voce pode ajustar:</p>
<ul>
<li>Caminhos do projeto e workspace</li>
<li>Modelos de IA (GPT-4o, etc.)</li>
<li>Timeouts de execucao</li>
<li>Comandos de validacao</li>
<li>Configuracoes do Git</li>
<li>Triggers de checkpoint</li>
</ul>

<h3>6. Logs e Relatorios</h3>
<p>Na tela de <b>Logs / Relatorios</b>:</p>
<ul>
<li>Selecione uma run no dropdown</li>
<li>Navegue pelos arquivos gerados</li>
<li>Copie ou exporte conteudo</li>
<li>Abra a pasta da run no explorador</li>
</ul>
"""

FUNCTIONS_CONTENT = {
    "Nova Tarefa": {
        "desc": "Tela para criar e submeter novas tarefas de desenvolvimento",
        "items": {
            "Campo de Texto": "Area grande para descrever a tarefa. Suporta texto longo e multiplas linhas.",
            "Perfil": "Tipo do projeto (Flutter, Python, C#, Generic). Define quais comandos de validacao serao usados.",
            "Modo": "Execucao Completa (padrao), Somente Planejar, ou Planejar + Executar.",
            "Auto Validar": "Se marcado, executa os comandos de validacao do perfil (flutter analyze, pytest, etc.).",
            "Auto Commit": "Se marcado, cria commit automaticamente quando validacao passar.",
            "Auto Push": "Se marcado, envia commit para o repositorio remoto.",
            "Exigir Aprovacao": "Se marcado, pausa a execucao quando detectar acoes destrutivas.",
            "Max Iteracoes": "Numero maximo de tentativas de execucao (1-10).",
            "Botao Executar": "Inicia a execucao da tarefa.",
            "Botao Limpar": "Limpa o formulario.",
        }
    },
    "Execucoes": {
        "desc": "Lista de todas as execucoes (runs) e seus detalhes",
        "items": {
            "Lista de Runs": "Tabela com todas as execucoes. Mostra ID, tarefa, status, iteracao e data.",
            "Filtro": "Filtra runs por status (Todos, Em Andamento, Concluidos, Falhas, Checkpoints).",
            "Busca": "Pesquisa por texto no ID ou descricao da tarefa.",
            "Botao Ver": "Abre os detalhes da run selecionada.",
            "Botao Retomar": "Retoma uma run pausada ou interrompida.",
            "Aba Visao Geral": "Resumo da tarefa, status, arquivos alterados, riscos.",
            "Aba Plano": "Objetivo, escopo e passos planejados.",
            "Aba Execucao": "Resumo do que foi feito e comandos executados.",
            "Aba Review": "Analise do revisor e status de aprovacao.",
            "Aba Validacao": "Resultados dos comandos de validacao.",
            "Aba Git": "Branch, commit hash e diff.",
        }
    },
    "Logs / Relatorios": {
        "desc": "Visualizador de logs, relatorios e artefatos gerados",
        "items": {
            "Seletor de Run": "Escolha qual run deseja visualizar.",
            "Lista de Arquivos": "Todos os arquivos gerados pela run.",
            "Visualizador": "Exibe o conteudo do arquivo selecionado.",
            "Botao Copiar": "Copia o conteudo para a area de transferencia.",
            "Botao Exportar": "Salva o conteudo em um arquivo.",
            "Botao Abrir Pasta": "Abre a pasta da run no explorador de arquivos.",
        }
    },
    "Configuracoes": {
        "desc": "Configuracoes do sistema organizadas em abas",
        "items": {
            "Aba Geral": "Caminhos do projeto, workspace, perfil ativo e max iteracoes.",
            "Aba Modelos": "Configuracao dos modelos OpenAI (planner e reviewer).",
            "Aba Executor": "Comando do Claude e timeout de execucao.",
            "Aba Validacao": "Comandos de validacao por perfil (Flutter, Python).",
            "Aba Git": "Remote, branch, branches protegidas, auto commit/push.",
            "Aba Seguranca": "Exigir aprovacao humana, triggers de checkpoint.",
            "Botao Restaurar": "Restaura todas as configuracoes para os valores padrao.",
            "Botao Validar": "Verifica se a configuracao atual e valida.",
            "Botao Salvar": "Salva as configuracoes.",
        }
    },
    "Checkpoints": {
        "desc": "Sistema de aprovacao para acoes que requerem revisao humana",
        "items": {
            "Notificacao": "Alerta amarelo no topo quando ha checkpoint pendente.",
            "Dialog de Aprovacao": "Mostra detalhes da acao e permite aprovar/rejeitar.",
            "Campo Observacao": "Permite adicionar nota explicando a decisao.",
            "Triggers": "Acoes que disparam checkpoint: delete, migration, force push, etc.",
        }
    },
    "Barra de Status": {
        "desc": "Barra inferior mostrando status da execucao atual",
        "items": {
            "Run ID": "Identificador da run em execucao.",
            "Status": "Estado atual (executando, concluido, falhou, etc.).",
            "Fase": "Etapa atual do pipeline (planning, executing, reviewing, etc.).",
            "Iteracao": "Numero da tentativa atual.",
            "Indicador de Progresso": "Animacao mostrando que ha atividade.",
        }
    },
}

FAQ_CONTENT = [
    {
        "q": "O que e necessario para usar o AI Orchestrator?",
        "a": """Para usar o AI Orchestrator voce precisa:
<ul>
<li><b>Python 3.11+</b> instalado</li>
<li><b>Chave de API OpenAI</b> configurada na variavel OPENAI_API_KEY</li>
<li><b>Claude Code CLI</b> instalado e no PATH</li>
<li>Dependencias instaladas: <code>pip install -r requirements.txt</code></li>
</ul>"""
    },
    {
        "q": "Como configuro a chave da API OpenAI?",
        "a": """Existem duas formas:
<ol>
<li><b>Variavel de ambiente:</b>
<pre>set OPENAI_API_KEY=sk-sua-chave   # Windows
export OPENAI_API_KEY=sk-sua-chave  # Linux/Mac</pre>
</li>
<li><b>Arquivo .env:</b> Crie um arquivo .env na raiz do projeto com:
<pre>OPENAI_API_KEY=sk-sua-chave</pre>
</li>
</ol>"""
    },
    {
        "q": "O que sao os perfis (Flutter, Python, etc.)?",
        "a": """Perfis definem quais comandos de validacao serao executados:
<ul>
<li><b>Flutter:</b> flutter analyze, flutter test</li>
<li><b>Python:</b> python -m pytest, ruff check .</li>
<li><b>C#:</b> dotnet build, dotnet test</li>
<li><b>Generic:</b> Nenhum comando de validacao</li>
</ul>
Voce pode personalizar os comandos na tela de Configuracoes."""
    },
    {
        "q": "O que e um checkpoint?",
        "a": """Checkpoint e uma pausa automatica que requer aprovacao humana antes de continuar.
Isso acontece quando o sistema detecta acoes potencialmente perigosas como:
<ul>
<li>Delecao de arquivos</li>
<li>Migracoes de banco de dados</li>
<li>Force push no Git</li>
<li>Reset --hard</li>
<li>Mudancas de infraestrutura</li>
</ul>
Voce pode aprovar ou rejeitar a acao no dialog que aparece."""
    },
    {
        "q": "Posso usar o programa sem interface grafica?",
        "a": """Sim! O AI Orchestrator tambem funciona via linha de comando (CLI):
<pre>
# Execucao automatica
python -m orchestrator.main run "Sua tarefa aqui"

# Modo manual (copy/paste)
python -m orchestrator.main start --task "Sua tarefa"

# Ver status
python -m orchestrator.main status

# Listar runs
python -m orchestrator.main list
</pre>"""
    },
    {
        "q": "Onde ficam salvos os logs e relatorios?",
        "a": """Todos os artefatos ficam na pasta <code>workspace/runs/</code>:
<pre>
workspace/runs/[run_id]/
  task.json          # Tarefa original
  plan.json          # Plano do Planner
  execution/         # Logs de execucao
  review/            # Analise do Reviewer
  validation/        # Resultados de validacao
  git/               # Diff e status git
  final/             # Relatorio final
</pre>
Voce pode abrir esta pasta pelo botao "Abrir Pasta" na interface."""
    },
    {
        "q": "O que fazer se a execucao falhar?",
        "a": """Quando uma execucao falha:
<ol>
<li>Verifique a mensagem de erro na tela de detalhes</li>
<li>Consulte os logs em Logs / Relatorios</li>
<li>Verifique se as configuracoes estao corretas</li>
<li>Tente retomar a execucao com o botao ">>"</li>
<li>Se necessario, inicie uma nova tarefa com instrucoes mais claras</li>
</ol>"""
    },
    {
        "q": "Posso cancelar uma execucao em andamento?",
        "a": """Atualmente nao ha um botao de cancelar na interface.
Se precisar interromper, voce pode:
<ol>
<li>Fechar a aplicacao (a execucao sera interrompida)</li>
<li>A run ficara com status incompleto</li>
<li>Voce pode retomar depois ou iniciar uma nova</li>
</ol>"""
    },
    {
        "q": "Como funciona o Auto Commit?",
        "a": """Quando Auto Commit esta ativado:
<ol>
<li>Apos a validacao passar, o sistema faz <code>git add .</code></li>
<li>Cria um commit com mensagem descritiva incluindo o run_id</li>
<li>Se Auto Push tambem estiver ativo, faz <code>git push</code></li>
</ol>
<b>Importante:</b> O sistema nao faz commit em branches protegidas (main, master) sem aprovacao."""
    },
    {
        "q": "O que significa cada status?",
        "a": """<ul>
<li><b style="color:#f59e0b">PENDING:</b> Aguardando inicio</li>
<li><b style="color:#3b82f6">PLANNING:</b> Gerando plano de execucao</li>
<li><b style="color:#3b82f6">EXECUTING:</b> Claude implementando mudancas</li>
<li><b style="color:#8b5cf6">REVIEWING:</b> Revisando alteracoes</li>
<li><b style="color:#06b6d4">VALIDATING:</b> Executando validacoes</li>
<li><b style="color:#10b981">COMMITTING:</b> Criando commit</li>
<li><b style="color:#22c55e">COMPLETED:</b> Concluido com sucesso</li>
<li><b style="color:#ef4444">FAILED:</b> Falhou</li>
<li><b style="color:#f59e0b">CHECKPOINT:</b> Aguardando aprovacao</li>
</ul>"""
    },
]


# ============================================================================
# WIDGETS
# ============================================================================

class HelpPanel(QWidget):
    """Main help panel with tabs for different help sections."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Ajuda")
        header.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()

        # About tab
        about_tab = self._create_html_tab(ABOUT_CONTENT)
        self.tabs.addTab(about_tab, "Sobre")

        # Guide tab
        guide_tab = self._create_html_tab(GUIDE_CONTENT)
        self.tabs.addTab(guide_tab, "Guia Rapido")

        # Functions tab
        functions_tab = self._create_functions_tab()
        self.tabs.addTab(functions_tab, "Funcoes")

        # FAQ tab
        faq_tab = self._create_faq_tab()
        self.tabs.addTab(faq_tab, "FAQ")

        layout.addWidget(self.tabs)

    def _create_html_tab(self, html_content: str) -> QWidget:
        """Create a tab with HTML content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(self._style_html(html_content))
        content.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: none;
                padding: 16px;
            }
        """)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_functions_tab(self) -> QWidget:
        """Create the functions documentation tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tree with function categories
        self.functions_tree = QTreeWidget()
        self.functions_tree.setHeaderLabel("Funcoes")
        self.functions_tree.setMinimumWidth(200)
        self.functions_tree.setMaximumWidth(300)

        for category, data in FUNCTIONS_CONTENT.items():
            cat_item = QTreeWidgetItem([category])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, ("category", category))
            self.functions_tree.addTopLevelItem(cat_item)

            for func_name in data["items"].keys():
                func_item = QTreeWidgetItem([func_name])
                func_item.setData(0, Qt.ItemDataRole.UserRole, ("function", category, func_name))
                cat_item.addChild(func_item)

        self.functions_tree.expandAll()
        self.functions_tree.currentItemChanged.connect(self._on_function_selected)
        splitter.addWidget(self.functions_tree)

        # Content area
        self.function_content = QTextEdit()
        self.function_content.setReadOnly(True)
        self.function_content.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: none;
                padding: 16px;
            }
        """)
        self.function_content.setHtml(self._style_html(
            "<p><i>Selecione uma funcao na lista a esquerda para ver sua descricao.</i></p>"
        ))
        splitter.addWidget(self.function_content)

        splitter.setSizes([250, 550])
        layout.addWidget(splitter)

        return widget

    def _on_function_selected(self, current, previous):
        """Handle function selection in tree."""
        if not current:
            return

        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == "category":
            category = data[1]
            cat_data = FUNCTIONS_CONTENT[category]
            html = f"<h2>{category}</h2>"
            html += f"<p>{cat_data['desc']}</p>"
            html += "<h3>Elementos:</h3><ul>"
            for name, desc in cat_data["items"].items():
                html += f"<li><b>{name}:</b> {desc}</li>"
            html += "</ul>"
            self.function_content.setHtml(self._style_html(html))

        elif data[0] == "function":
            category = data[1]
            func_name = data[2]
            desc = FUNCTIONS_CONTENT[category]["items"][func_name]
            html = f"<h2>{func_name}</h2>"
            html += f"<p><b>Categoria:</b> {category}</p>"
            html += f"<p>{desc}</p>"
            self.function_content.setHtml(self._style_html(html))

    def _create_faq_tab(self) -> QWidget:
        """Create the FAQ tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        for i, faq in enumerate(FAQ_CONTENT):
            group = QGroupBox(f"{i+1}. {faq['q']}")
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: 600;
                    color: #1e293b;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 16px;
                    background-color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 8px;
                }
            """)
            group_layout = QVBoxLayout(group)

            answer = QTextEdit()
            answer.setReadOnly(True)
            answer.setHtml(self._style_html(faq['a']))
            answer.setMaximumHeight(200)
            answer.setStyleSheet("""
                QTextEdit {
                    background-color: transparent;
                    border: none;
                }
            """)
            group_layout.addWidget(answer)

            content_layout.addWidget(group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _style_html(self, html: str) -> str:
        """Add base styling to HTML content."""
        return f"""
        <style>
            body {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                color: #1e293b;
                line-height: 1.6;
            }}
            h2 {{
                color: #1e293b;
                font-size: 18px;
                margin-top: 16px;
                margin-bottom: 12px;
            }}
            h3 {{
                color: #475569;
                font-size: 14px;
                margin-top: 12px;
                margin-bottom: 8px;
            }}
            p {{
                margin: 8px 0;
            }}
            ul, ol {{
                margin: 8px 0;
                padding-left: 24px;
            }}
            li {{
                margin: 4px 0;
            }}
            pre {{
                background-color: #f1f5f9;
                padding: 12px;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                overflow-x: auto;
            }}
            code {{
                background-color: #f1f5f9;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }}
            b {{
                color: #1e293b;
            }}
        </style>
        {html}
        """
