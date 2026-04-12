# AI Orchestrator - MVP Manual Assistido

Ferramenta simples para organizar o fluxo de trabalho com Claude no VSCode.

## O que é

Um script Python único que:
- Cria uma pasta por tarefa
- Gera prompts estruturados para Claude
- Armazena as respostas organizadamente
- Gera próximos prompts baseados nas respostas anteriores

## Por que usar

- **Organização**: Cada tarefa fica em sua pasta com histórico completo
- **Padronização**: Prompts e respostas seguem formato consistente
- **Rastreabilidade**: Estado salvo em JSON, fácil de retomar
- **Zero dependências**: Apenas Python padrão

## Instalação

Nenhuma instalação necessária. Apenas copie `orchestrator.py` para seu projeto.

```bash
# Estrutura criada automaticamente:
workspace/
  runs/
    <run_id>/
      task.txt
      claude_prompt_1.txt
      claude_report_1.txt
      next_prompt_2.txt
      state.json
```

## Como Usar

### 1. Iniciar uma Tarefa

```bash
python orchestrator.py start --task "corrigir login e rodar flutter analyze/test"
```

Saída:
```
============================================================
  NOVA RODADA INICIADA
============================================================

  Run ID:    20260411-161500-a1b2c3
  Tarefa:    corrigir login e rodar flutter analyze/test
  Status:    aguardando Claude

  Pasta:     workspace/runs/20260411-161500-a1b2c3
  Prompt:    workspace/runs/20260411-161500-a1b2c3/claude_prompt_1.txt

  PRÓXIMOS PASSOS:
  1. Abra o arquivo claude_prompt_1.txt
  2. Copie o conteúdo e cole no Claude (VSCode)
  3. Salve a resposta do Claude em um arquivo
  4. Execute:
     python orchestrator.py report --run-id 20260411-161500-a1b2c3 --file resposta.txt
```

### 2. Registrar Resposta do Claude

Após Claude responder, salve a resposta em um arquivo e registre:

```bash
python orchestrator.py report --run-id 20260411-161500-a1b2c3 --file resposta.txt
```

### 3. Gerar Próximo Prompt (se necessário)

Se a tarefa não foi concluída:

```bash
python orchestrator.py next --run-id 20260411-161500-a1b2c3
```

Isso gera `next_prompt_2.txt` com:
- Resumo da tarefa original
- O que Claude já fez
- Pendências e riscos identificados
- Instruções para continuar

### 4. Ver Status

```bash
python orchestrator.py status --run-id 20260411-161500-a1b2c3
```

### 5. Listar Rodadas

```bash
python orchestrator.py list
```

## Formato da Resposta do Claude

O prompt gerado pede que Claude responda neste formato:

```
## 1. RESUMO
[Resumo em 2-3 frases]

## 2. ARQUIVOS ALTERADOS
- arquivo1.ext - descrição

## 3. O QUE FOI FEITO
- Passo 1: descrição

## 4. VALIDAÇÕES EXECUTADAS
- flutter analyze: resultado

## 5. RESULTADO DAS VALIDAÇÕES
PASSOU / FALHOU / PARCIAL

## 6. PENDÊNCIAS
- Pendência 1

## 7. RISCOS REMANESCENTES
- Risco 1

## 8. PRÓXIMO PASSO RECOMENDADO
[Próximo passo ou "Tarefa concluída"]
```

## Estrutura de Arquivos

```
workspace/runs/20260411-161500-a1b2c3/
├── task.txt              # Tarefa original
├── claude_prompt_1.txt   # Primeiro prompt para Claude
├── claude_report_1.txt   # Resposta do Claude (iteração 1)
├── next_prompt_2.txt     # Prompt de continuação (iteração 2)
├── claude_report_2.txt   # Resposta do Claude (iteração 2)
└── state.json            # Estado da rodada
```

## state.json

```json
{
  "run_id": "20260411-161500-a1b2c3",
  "created_at": "2026-04-11T16:15:00",
  "original_task": "corrigir login e rodar flutter analyze/test",
  "current_iteration": 2,
  "status": "report_received",
  "last_prompt_file": "next_prompt_2.txt",
  "last_report_file": "claude_report_2.txt",
  "history": [
    {"iteration": 1, "prompt_file": "claude_prompt_1.txt", "report_file": "claude_report_1.txt"},
    {"iteration": 2, "prompt_file": "next_prompt_2.txt", "report_file": "claude_report_2.txt"}
  ]
}
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `start --task "..."` | Iniciar nova tarefa |
| `report --run-id <id> --file <arq>` | Registrar resposta do Claude |
| `next --run-id <id>` | Gerar próximo prompt |
| `status --run-id <id>` | Ver status da rodada |
| `list` | Listar rodadas |

## Exemplo Completo

```bash
# 1. Iniciar
python orchestrator.py start --task "adicionar botão de logout na tela principal"

# 2. Copiar claude_prompt_1.txt e colar no Claude VSCode
# 3. Salvar resposta em resposta1.txt

# 4. Registrar
python orchestrator.py report --run-id 20260411-161500-a1b2c3 --file resposta1.txt

# 5. Se precisar continuar
python orchestrator.py next --run-id 20260411-161500-a1b2c3

# 6. Copiar next_prompt_2.txt e colar no Claude
# 7. Salvar resposta em resposta2.txt

# 8. Registrar
python orchestrator.py report --run-id 20260411-161500-a1b2c3 --file resposta2.txt

# 9. Verificar status
python orchestrator.py status --run-id 20260411-161500-a1b2c3
```

## Limitações

- **Manual**: Você copia/cola entre o script e o Claude
- **Local**: Não se conecta a APIs
- **Simples**: Sem validações automáticas

## Próximos Passos (Versão Futura)

- Integração direta com Claude CLI
- Execução automática de validações
- Commit/push automáticos
- API para planner/reviewer
