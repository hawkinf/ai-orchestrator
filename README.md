# AI Orchestrator

Local orchestration system for AI-assisted development, coordinating planning, execution, and review across different AI models.

## Overview

AI Orchestrator is a command-line tool that manages the development workflow between:

- **Planner** (ChatGPT/Codex): Analyzes tasks and creates execution plans
- **Executor** (Claude Code): Implements changes in the codebase
- **Reviewer** (ChatGPT/Codex): Reviews changes and approves commits

The system eliminates manual copy-paste between models by using a file-based pipeline with explicit stages, persistent state, and human checkpoints.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │
│   │  Task   │───▶│  Planner │───▶│ Executor │───▶│Reviewer │  │
│   │  Input  │    │  (GPT)   │    │ (Claude) │    │  (GPT)  │  │
│   └─────────┘    └──────────┘    └──────────┘    └─────────┘  │
│        │              │               │               │        │
│        ▼              ▼               ▼               ▼        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                   STATE PERSISTENCE                      │  │
│   │              (JSON files in workspace/)                  │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │              │               │               │        │
│        ▼              ▼               ▼               ▼        │
│   ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │
│   │Validate │───▶│  Commit  │───▶│   Push   │───▶│ Report  │  │
│   └─────────┘    └──────────┘    └──────────┘    └─────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone or copy the project
cd ai-orchestrator

# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp .env.example .env
cp config.yaml my_project_config.yaml
# Edit .env and config.yaml with your settings
```

## Quick Start

### 1. Start a new task

```bash
python -m orchestrator.main start --task "Fix the login validation bug"
```

### 2. Follow the manual workflow

The orchestrator will generate prompts that you copy to your AI models:

1. Copy the planner prompt from `workspace/prompts/planner_<run_id>.txt`
2. Paste into ChatGPT and get the JSON response
3. Save the response to `workspace/prompts/planner_response.json`
4. Resume: `python -m orchestrator.main resume --run-id <run_id>`

### 3. Monitor and control

```bash
# Check status
python -m orchestrator.main status --run-id <run_id>

# List all runs
python -m orchestrator.main list

# View pending checkpoints
python -m orchestrator.main checkpoints
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `start --task "..."` | Start a new task run |
| `resume --run-id <id>` | Resume an existing run |
| `status [--run-id <id>]` | Show status of run(s) |
| `list [--limit N]` | List recent runs |
| `approve <run_id>` | Approve a pending checkpoint |
| `reject <run_id>` | Reject a pending checkpoint |
| `validate <run_id>` | Run validations |
| `finalize <run_id>` | Force commit and complete |
| `report <run_id>` | Show detailed report |
| `checkpoints` | List pending checkpoints |

## Configuration

### config.yaml

```yaml
# Project settings
project_path: "."
workspace_path: "./workspace"
active_profile: "flutter"

# Execution limits
max_iterations: 3
iteration_timeout_seconds: 300

# Behaviors
allow_auto_commit: false
require_human_on_destructive: true
auto_push_on_complete: false

# Profiles (validation commands by project type)
profiles:
  flutter:
    validation_commands:
      - "flutter analyze"
      - "flutter test"
  python:
    validation_commands:
      - "python -m pytest"
      - "ruff check ."

# Git
git:
  remote: "origin"
  branch: "main"
  protected_branches: ["main", "master"]

# Security
security:
  command_allowlist:
    - "flutter"
    - "dart"
    - "python"
    - "git"

# Checkpoint triggers
checkpoint_triggers:
  - "delete"
  - "migration"
  - "force push"
```

### .env

```bash
OPENAI_API_KEY=sk-your-key
PROJECT_PATH=.
LOG_LEVEL=INFO
```

## Workflow

### Complete Pipeline

```
TASK → PLAN → EXECUTE → REVIEW → VALIDATE → COMMIT → PUSH
```

1. **Task Input**: User provides task description
2. **Planning**: Planner model creates execution plan (JSON)
3. **Execution**: Executor (Claude) implements changes
4. **Review**: Reviewer model evaluates changes
5. **Validation**: Run configured validation commands
6. **Commit**: Git commit with proper message
7. **Push**: Sync with remote repository

### Checkpoints

The system pauses for human approval on:

- Database migrations
- File deletions
- Infrastructure changes
- Git destructive operations
- Repeated failures
- Commands outside allowlist

```bash
# Approve a checkpoint
python -m orchestrator.main approve <run_id> --note "Reviewed and approved"

# Reject a checkpoint
python -m orchestrator.main reject <run_id> --reason "Not safe for production"
```

### Resuming After Interruption

All state is persisted to disk. If the process crashes:

```bash
# See where it stopped
python -m orchestrator.main status --run-id <run_id>

# Resume from that point
python -m orchestrator.main resume --run-id <run_id>
```

## Project Structure

```
ai-orchestrator/
├── orchestrator/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── cli.py               # CLI commands
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic data models
│   ├── paths.py             # Path management
│   ├── state_store.py       # State persistence
│   ├── task_engine.py       # Main orchestration engine
│   ├── prompt_builder.py    # Prompt generation
│   ├── planner_client.py    # Planner model client
│   ├── executor_client.py   # Executor client
│   ├── reviewer_client.py   # Reviewer model client
│   ├── report_parser.py     # Execution report parser
│   ├── artifact_writer.py   # Artifact/report writer
│   ├── checkpoint.py        # Checkpoint management
│   ├── git_ops.py           # Git operations
│   ├── logger.py            # Logging utilities
│   └── utils.py             # Helper functions
├── prompts/
│   ├── planner_system.txt   # Planner system prompt
│   ├── reviewer_system.txt  # Reviewer system prompt
│   └── executor_wrapper.txt # Executor wrapper prompt
├── workspace/
│   ├── tasks/               # Task definitions
│   ├── runs/                # Run artifacts
│   ├── prompts/             # Generated prompts
│   ├── state/               # Persisted state
│   └── logs/                # Log files
├── tests/
│   ├── test_state_store.py
│   ├── test_prompt_builder.py
│   ├── test_report_parser.py
│   ├── test_checkpoint.py
│   └── test_git_ops.py
├── config.yaml
├── requirements.txt
├── .env.example
└── README.md
```

## Run Artifacts

Each run creates artifacts in `workspace/runs/<run_id>/`:

```
workspace/runs/20260411-143022/
├── task.json                    # Original task
├── plan.json                    # Planner response
├── execution/
│   ├── iteration_1_stdout.log   # Executor output
│   ├── iteration_1_stderr.log   # Executor errors
│   └── iteration_1_report.md    # Execution report
├── review/
│   └── iteration_1_review.json  # Review response
├── validation/
│   ├── flutter_analyze.log
│   └── flutter_test.log
├── git/
│   ├── diff.patch              # Changes diff
│   └── git_status.txt          # Git status
└── final/
    ├── final_report.json       # Structured report
    └── final_report.md         # Readable report
```

## Swapping Executor/Models

### Using Different Executor

Modify `config.yaml`:

```yaml
executor:
  command: "claude-code"  # or another CLI tool
  timeout_seconds: 600
```

### Using API-based Models

For direct API integration (requires additional setup):

1. Set `OPENAI_API_KEY` in `.env`
2. Modify `planner_client.py` and `reviewer_client.py` to use API calls
3. Set `manual_mode=False` when creating `TaskEngine`

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_state_store.py -v

# Run with coverage
python -m pytest tests/ --cov=orchestrator
```

## Limitations

### Current Limitations

1. **Manual Model Interaction**: Currently requires copy-paste between models (by design for V1)
2. **Single Project**: Designed for one project at a time
3. **No Parallel Runs**: One active run per project recommended
4. **Windows Primary**: Tested primarily on Windows (macOS support pending)

### Planned Improvements

1. API integration for planner/reviewer
2. Web UI for monitoring
3. Multi-project support
4. macOS/Linux testing
5. Webhook notifications

## Troubleshooting

### "Run not found"

The run ID may be incorrect. List runs with:
```bash
python -m orchestrator.main list
```

### "Executor command not found"

Ensure the executor (e.g., `claude`) is in your PATH:
```bash
where claude  # Windows
which claude  # macOS/Linux
```

### Validation Failures

Check validation logs in `workspace/runs/<run_id>/validation/`

### State Corruption

State files are in `workspace/state/`. If corrupted:
1. Check `workspace/state/<run_id>.json`
2. Delete if necessary and create a new run

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

## License

MIT License - See LICENSE file for details.
