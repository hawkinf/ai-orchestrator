#!/usr/bin/env python3
"""
AI Orchestrator - MVP Manual Assistido
Ferramenta local para organizar fluxo de trabalho com Claude.

Uso:
    python orchestrator.py start --task "sua tarefa aqui"
    python orchestrator.py report --run-id <id> --file resposta.txt
    python orchestrator.py next --run-id <id>
    python orchestrator.py status --run-id <id>
    python orchestrator.py list
"""

import argparse
import json
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from uuid import uuid4


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

WORKSPACE_DIR = Path(__file__).parent / "workspace"
RUNS_DIR = WORKSPACE_DIR / "runs"


# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

def ensure_dirs():
    """Garante que os diretórios de trabalho existem."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def generate_run_id() -> str:
    """Gera um ID único para a rodada."""
    now = datetime.now()
    short_uuid = uuid4().hex[:6]
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{short_uuid}"


def get_run_dir(run_id: str) -> Path:
    """Retorna o diretório de uma rodada."""
    return RUNS_DIR / run_id


def load_state(run_id: str) -> dict:
    """Carrega o estado de uma rodada."""
    state_file = get_run_dir(run_id) / "state.json"
    if not state_file.exists():
        print(f"ERRO: Rodada não encontrada: {run_id}")
        sys.exit(1)
    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(run_id: str, state: dict):
    """Salva o estado de uma rodada."""
    state_file = get_run_dir(run_id) / "state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def write_file(path: Path, content: str):
    """Escreve conteúdo em arquivo com UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(path: Path) -> str:
    """Lê conteúdo de arquivo com UTF-8."""
    if not path.exists():
        print(f"ERRO: Arquivo não encontrado: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ==============================================================================
# GERAÇÃO DE PROMPTS
# ==============================================================================

def build_initial_prompt(task: str, run_id: str) -> str:
    """
    Gera o prompt inicial para Claude.

    Args:
        task: Descrição da tarefa
        run_id: ID da rodada

    Returns:
        Prompt formatado para Claude
    """
    prompt = f"""# TAREFA DE DESENVOLVIMENTO

## Contexto
Run ID: {run_id}
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Objetivo
{task}

## Regras Obrigatórias

1. **Execução direta**: Não pare para pedir confirmação. Decida detalhes pequenos e siga em frente.

2. **Alterações**: Faça as modificações necessárias nos arquivos do projeto.

3. **Validações**: Execute as validações cabíveis para o projeto:
   - Flutter: `flutter analyze` e `flutter test`
   - Python: `pytest` e linters
   - Outros: comandos de build/test apropriados

4. **Evidências**: Sempre mostre evidências reais do que foi feito (trechos de código, saídas de comandos).

5. **Bloqueios**: Se houver algo que impeça a conclusão, declare claramente o bloqueio.

6. **Conclusão**: Ao concluir a tarefa com sucesso:
   - Faça commit com mensagem descritiva
   - Faça sync com GitHub (git push)

7. **Resposta estruturada**: Sua resposta DEVE seguir EXATAMENTE o formato abaixo.

## Formato Obrigatório de Resposta

Responda usando EXATAMENTE estas 8 seções, nesta ordem:

```
## 1. RESUMO
[Resumo em 2-3 frases do que foi feito]

## 2. ARQUIVOS ALTERADOS
- arquivo1.ext - descrição da alteração
- arquivo2.ext - descrição da alteração
[Se nenhum: "Nenhum arquivo alterado"]

## 3. O QUE FOI FEITO
- Passo 1: descrição
- Passo 2: descrição
[Lista detalhada das ações executadas]

## 4. VALIDAÇÕES EXECUTADAS
- Comando 1: resultado
- Comando 2: resultado
[Se nenhuma: "Nenhuma validação executada"]

## 5. RESULTADO DAS VALIDAÇÕES
[PASSOU / FALHOU / PARCIAL - com detalhes]

## 6. PENDÊNCIAS
- Pendência 1
- Pendência 2
[Se nenhuma: "Nenhuma pendência"]

## 7. RISCOS REMANESCENTES
- Risco 1
- Risco 2
[Se nenhum: "Nenhum risco identificado"]

## 8. PRÓXIMO PASSO RECOMENDADO
[Descreva o próximo passo específico, ou "Tarefa concluída - nenhum próximo passo necessário"]
```

## Proibições
- NÃO responda de forma vaga ou genérica
- NÃO pule seções do formato obrigatório
- NÃO deixe de mostrar evidências
- NÃO assuma sucesso sem validar

Comece a executar a tarefa agora.
"""
    return prompt


def build_continuation_prompt(
    task: str,
    run_id: str,
    iteration: int,
    previous_report: str,
) -> str:
    """
    Gera o prompt de continuação para Claude.

    Args:
        task: Descrição da tarefa original
        run_id: ID da rodada
        iteration: Número da iteração atual
        previous_report: Relatório anterior do Claude

    Returns:
        Prompt formatado para continuação
    """
    # Extrair seções relevantes do relatório anterior
    pendencias = extract_section(previous_report, "PENDÊNCIAS", "Não identificadas")
    riscos = extract_section(previous_report, "RISCOS REMANESCENTES", "Não identificados")
    proximo = extract_section(previous_report, "PRÓXIMO PASSO RECOMENDADO", "Continuar a tarefa")
    resumo = extract_section(previous_report, "RESUMO", "Não disponível")

    prompt = f"""# CONTINUAÇÃO DE TAREFA

## Contexto
Run ID: {run_id}
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Iteração: {iteration}

## Tarefa Original
{task}

## Resumo do Trabalho Anterior
{resumo}

## Pendências Identificadas
{pendencias}

## Riscos Remanescentes
{riscos}

## Próximo Passo Indicado
{proximo}

## Objetivo desta Iteração
Continue o trabalho a partir do ponto onde parou. Foque em:
1. Resolver as pendências identificadas
2. Mitigar os riscos remanescentes
3. Executar o próximo passo recomendado

## Regras Obrigatórias

1. **Não repita trabalho**: O que já foi feito está feito. Continue de onde parou.

2. **Execução direta**: Não pare para pedir confirmação. Decida e execute.

3. **Validações**: Execute as validações cabíveis após suas alterações.

4. **Evidências**: Mostre evidências reais do que foi feito.

5. **Bloqueios**: Se houver algo que impeça a conclusão, declare claramente.

6. **Conclusão**: Ao concluir a tarefa com sucesso:
   - Faça commit com mensagem descritiva
   - Faça sync com GitHub (git push)

## Formato Obrigatório de Resposta

Responda usando EXATAMENTE estas 8 seções, nesta ordem:

```
## 1. RESUMO
[Resumo em 2-3 frases do que foi feito NESTA ITERAÇÃO]

## 2. ARQUIVOS ALTERADOS
- arquivo1.ext - descrição da alteração
- arquivo2.ext - descrição da alteração
[Se nenhum: "Nenhum arquivo alterado"]

## 3. O QUE FOI FEITO
- Passo 1: descrição
- Passo 2: descrição
[Lista detalhada das ações executadas NESTA ITERAÇÃO]

## 4. VALIDAÇÕES EXECUTADAS
- Comando 1: resultado
- Comando 2: resultado
[Se nenhuma: "Nenhuma validação executada"]

## 5. RESULTADO DAS VALIDAÇÕES
[PASSOU / FALHOU / PARCIAL - com detalhes]

## 6. PENDÊNCIAS
- Pendência 1
- Pendência 2
[Se nenhuma: "Nenhuma pendência"]

## 7. RISCOS REMANESCENTES
- Risco 1
- Risco 2
[Se nenhum: "Nenhum risco identificado"]

## 8. PRÓXIMO PASSO RECOMENDADO
[Descreva o próximo passo específico, ou "Tarefa concluída - nenhum próximo passo necessário"]
```

## Proibições
- NÃO repita trabalho já feito
- NÃO responda de forma vaga ou genérica
- NÃO pule seções do formato obrigatório
- NÃO deixe de mostrar evidências

Continue a execução agora.
"""
    return prompt


def extract_section(text: str, section_name: str, default: str = "") -> str:
    """
    Extrai uma seção específica do relatório do Claude.

    Args:
        text: Texto completo do relatório
        section_name: Nome da seção a extrair
        default: Valor padrão se não encontrar

    Returns:
        Conteúdo da seção
    """
    import re

    # Padrões para encontrar a seção
    patterns = [
        rf"##\s*\d*\.?\s*{section_name}\s*\n(.*?)(?=\n##|\Z)",
        rf"{section_name}\s*\n(.*?)(?=\n##|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content:
                return content

    return default


# ==============================================================================
# COMANDOS
# ==============================================================================

def cmd_start(args):
    """Inicia uma nova rodada de tarefa."""
    ensure_dirs()

    task = args.task
    if not task:
        print("ERRO: Tarefa não especificada. Use --task 'descrição'")
        sys.exit(1)

    # Gerar ID e criar diretório
    run_id = generate_run_id()
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Salvar tarefa original
    task_file = run_dir / "task.txt"
    write_file(task_file, task)

    # Gerar prompt inicial
    prompt = build_initial_prompt(task, run_id)
    prompt_file = run_dir / "claude_prompt_1.txt"
    write_file(prompt_file, prompt)

    # Criar estado inicial
    state = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "original_task": task,
        "current_iteration": 1,
        "status": "awaiting_claude",
        "last_prompt_file": "claude_prompt_1.txt",
        "last_report_file": None,
        "history": [
            {
                "iteration": 1,
                "prompt_file": "claude_prompt_1.txt",
                "report_file": None,
            }
        ],
    }
    save_state(run_id, state)

    # Mostrar resultado
    print()
    print("=" * 60)
    print("  NOVA RODADA INICIADA")
    print("=" * 60)
    print()
    print(f"  Run ID:    {run_id}")
    print(f"  Tarefa:    {task[:50]}{'...' if len(task) > 50 else ''}")
    print(f"  Status:    aguardando Claude")
    print()
    print(f"  Pasta:     {run_dir}")
    print(f"  Prompt:    {prompt_file}")
    print()
    print("  PRÓXIMOS PASSOS:")
    print("  1. Abra o arquivo claude_prompt_1.txt")
    print("  2. Copie o conteúdo e cole no Claude (VSCode)")
    print("  3. Salve a resposta do Claude em um arquivo")
    print("  4. Execute:")
    print(f"     python orchestrator.py report --run-id {run_id} --file resposta.txt")
    print()
    print("=" * 60)


def cmd_report(args):
    """Registra o relatório/resposta do Claude."""
    run_id = args.run_id
    report_file_arg = args.file

    if not run_id:
        print("ERRO: Run ID não especificado. Use --run-id <id>")
        sys.exit(1)

    if not report_file_arg:
        print("ERRO: Arquivo de relatório não especificado. Use --file <caminho>")
        sys.exit(1)

    # Carregar estado
    state = load_state(run_id)
    run_dir = get_run_dir(run_id)

    # Verificar status
    if state["status"] != "awaiting_claude":
        print(f"AVISO: Status atual é '{state['status']}', não 'awaiting_claude'")
        print("Continuando mesmo assim...")

    # Ler arquivo de relatório
    source_path = Path(report_file_arg)
    report_content = read_file(source_path)

    # Salvar cópia no diretório da rodada
    iteration = state["current_iteration"]
    report_filename = f"claude_report_{iteration}.txt"
    report_path = run_dir / report_filename
    write_file(report_path, report_content)

    # Atualizar estado
    state["status"] = "report_received"
    state["last_report_file"] = report_filename

    # Atualizar histórico
    for entry in state["history"]:
        if entry["iteration"] == iteration:
            entry["report_file"] = report_filename
            break

    save_state(run_id, state)

    # Mostrar resultado
    print()
    print("=" * 60)
    print("  RELATÓRIO REGISTRADO")
    print("=" * 60)
    print()
    print(f"  Run ID:    {run_id}")
    print(f"  Iteração:  {iteration}")
    print(f"  Arquivo:   {report_path}")
    print(f"  Status:    relatório recebido")
    print()
    print("  PRÓXIMOS PASSOS:")
    print("  - Se a tarefa foi concluída: pronto!")
    print("  - Se precisar continuar, execute:")
    print(f"    python orchestrator.py next --run-id {run_id}")
    print()
    print("=" * 60)


def cmd_next(args):
    """Gera o próximo prompt de continuação."""
    run_id = args.run_id

    if not run_id:
        print("ERRO: Run ID não especificado. Use --run-id <id>")
        sys.exit(1)

    # Carregar estado
    state = load_state(run_id)
    run_dir = get_run_dir(run_id)

    # Verificar se há relatório
    if state["status"] != "report_received":
        print(f"ERRO: Status atual é '{state['status']}'")
        print("Execute 'report' primeiro para registrar a resposta do Claude.")
        sys.exit(1)

    # Ler tarefa original e último relatório
    task = state["original_task"]
    last_report_file = state["last_report_file"]

    if not last_report_file:
        print("ERRO: Nenhum relatório anterior encontrado.")
        sys.exit(1)

    report_path = run_dir / last_report_file
    previous_report = read_file(report_path)

    # Incrementar iteração
    new_iteration = state["current_iteration"] + 1

    # Gerar próximo prompt
    prompt = build_continuation_prompt(task, run_id, new_iteration, previous_report)
    prompt_filename = f"next_prompt_{new_iteration}.txt"
    prompt_path = run_dir / prompt_filename
    write_file(prompt_path, prompt)

    # Atualizar estado
    state["current_iteration"] = new_iteration
    state["status"] = "awaiting_claude"
    state["last_prompt_file"] = prompt_filename
    state["last_report_file"] = None
    state["history"].append({
        "iteration": new_iteration,
        "prompt_file": prompt_filename,
        "report_file": None,
    })

    save_state(run_id, state)

    # Mostrar resultado
    print()
    print("=" * 60)
    print("  PRÓXIMO PROMPT GERADO")
    print("=" * 60)
    print()
    print(f"  Run ID:    {run_id}")
    print(f"  Iteração:  {new_iteration}")
    print(f"  Prompt:    {prompt_path}")
    print(f"  Status:    aguardando Claude")
    print()
    print("  PRÓXIMOS PASSOS:")
    print(f"  1. Abra o arquivo {prompt_filename}")
    print("  2. Copie o conteúdo e cole no Claude (VSCode)")
    print("  3. Salve a resposta do Claude em um arquivo")
    print("  4. Execute:")
    print(f"     python orchestrator.py report --run-id {run_id} --file resposta.txt")
    print()
    print("=" * 60)


def cmd_status(args):
    """Mostra o status de uma rodada."""
    run_id = args.run_id

    if not run_id:
        print("ERRO: Run ID não especificado. Use --run-id <id>")
        sys.exit(1)

    # Carregar estado
    state = load_state(run_id)
    run_dir = get_run_dir(run_id)

    # Mapear status para texto amigável
    status_map = {
        "awaiting_claude": "[AGUARDANDO] Resposta do Claude",
        "report_received": "[RECEBIDO] Relatorio registrado",
    }
    status_text = status_map.get(state["status"], state["status"])

    # Mostrar informações
    print()
    print("=" * 60)
    print("  STATUS DA RODADA")
    print("=" * 60)
    print()
    print(f"  Run ID:         {state['run_id']}")
    print(f"  Criado em:      {state['created_at']}")
    print(f"  Iteração:       {state['current_iteration']}")
    print(f"  Status:         {status_text}")
    print()
    print(f"  Tarefa:")
    # Quebrar tarefa em múltiplas linhas se necessário
    task_lines = textwrap.wrap(state['original_task'], width=50)
    for i, line in enumerate(task_lines):
        prefix = "    " if i > 0 else "    "
        print(f"{prefix}{line}")
    print()
    print(f"  Último prompt:  {state['last_prompt_file']}")
    print(f"  Último report:  {state['last_report_file'] or '(nenhum)'}")
    print()
    print(f"  Pasta:          {run_dir}")
    print()
    print("  HISTORICO:")
    for entry in state["history"]:
        report = entry['report_file'] or '(pendente)'
        print(f"    Iteracao {entry['iteration']}: {entry['prompt_file']} -> {report}")
    print()
    print("=" * 60)


def cmd_list(args):
    """Lista todas as rodadas."""
    ensure_dirs()

    runs = sorted(RUNS_DIR.iterdir(), reverse=True) if RUNS_DIR.exists() else []

    if not runs:
        print()
        print("Nenhuma rodada encontrada.")
        print(f"Use: python orchestrator.py start --task 'sua tarefa'")
        print()
        return

    print()
    print("=" * 70)
    print("  RODADAS")
    print("=" * 70)
    print()
    print(f"  {'RUN ID':<28} {'STATUS':<20} {'ITERAÇÃO':<10}")
    print(f"  {'-'*28} {'-'*20} {'-'*10}")

    for run_path in runs[:20]:  # Limitar a 20 mais recentes
        if not run_path.is_dir():
            continue

        state_file = run_path / "state.json"
        if not state_file.exists():
            continue

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            status_short = {
                "awaiting_claude": "aguardando",
                "report_received": "recebido",
            }.get(state["status"], state["status"])

            print(f"  {state['run_id']:<28} {status_short:<20} {state['current_iteration']:<10}")
        except (json.JSONDecodeError, KeyError):
            print(f"  {run_path.name:<28} {'(erro)':<20} {'-':<10}")

    print()
    print("=" * 70)
    print()
    print("  Para ver detalhes: python orchestrator.py status --run-id <id>")
    print()


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Ponto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="AI Orchestrator - MVP Manual Assistido",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos:
              python orchestrator.py start --task "corrigir login e testar"
              python orchestrator.py report --run-id 20260411-143000-abc123 --file resposta.txt
              python orchestrator.py next --run-id 20260411-143000-abc123
              python orchestrator.py status --run-id 20260411-143000-abc123
              python orchestrator.py list
        """),
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: start
    start_parser = subparsers.add_parser("start", help="Iniciar nova tarefa")
    start_parser.add_argument("--task", "-t", required=True, help="Descrição da tarefa")

    # Comando: report
    report_parser = subparsers.add_parser("report", help="Registrar relatório do Claude")
    report_parser.add_argument("--run-id", "-r", required=True, help="ID da rodada")
    report_parser.add_argument("--file", "-f", required=True, help="Arquivo com a resposta do Claude")

    # Comando: next
    next_parser = subparsers.add_parser("next", help="Gerar próximo prompt")
    next_parser.add_argument("--run-id", "-r", required=True, help="ID da rodada")

    # Comando: status
    status_parser = subparsers.add_parser("status", help="Mostrar status da rodada")
    status_parser.add_argument("--run-id", "-r", required=True, help="ID da rodada")

    # Comando: list
    list_parser = subparsers.add_parser("list", help="Listar rodadas")

    # Parse e executar
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "start": cmd_start,
        "report": cmd_report,
        "next": cmd_next,
        "status": cmd_status,
        "list": cmd_list,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
