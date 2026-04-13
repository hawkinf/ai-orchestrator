# AI Orchestrator

Local orchestration system for AI-assisted development, coordinating planning, execution, and review across different AI models.

## Overview

AI Orchestrator is a desktop application and CLI that manages the development workflow between:

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

### Option A: GUI Mode (Recommended)

Launch the desktop application:

```bash
# Start the GUI
python -m gui.app
```

The GUI provides:

- **Nova Tarefa**: Create and submit tasks with full configuration
- **Execucoes**: View run history, details, and artifacts
- **Diagnostico**: Pre-flight system checks (see Diagnostics Panel below)
- **Logs / Relatorios**: Browse logs and reports
- **Configuracoes**: Edit settings visually, test API connection
- Checkpoint approval dialogs
- Real-time progress updates during pipeline execution
- Resume interrupted runs
- Open run artifacts directly from the UI

### Option B: CLI Integrated Mode

Fully automated execution using OpenAI API and Claude Code CLI:

```bash
# Set your OpenAI API key
set OPENAI_API_KEY=sk-your-key  # Windows
export OPENAI_API_KEY=sk-your-key  # macOS/Linux

# Run a task (fully automated)
python -m orchestrator.main run "Fix the login validation bug"

# With a specific profile
python -m orchestrator.main run "Add logout button" --profile flutter

# Test mode (no real Claude calls)
python -m orchestrator.main run "Test task" --mock
```

The integrated mode will:

1. Plan the task with OpenAI (GPT-4o)
2. Execute with Claude Code CLI
3. Review changes with OpenAI
4. Run validation commands
5. Commit and push (if configured)

### Option C: CLI Manual Mode

For copy-paste workflow between AI models:

```bash
python -m orchestrator.main start --task "Fix the login validation bug"
```

Then follow the manual workflow:

1. Copy the planner prompt from `workspace/prompts/planner_<run_id>.txt`
2. Paste into ChatGPT and get the JSON response
3. Save the response to `workspace/prompts/planner_response.json`
4. Resume: `python -m orchestrator.main resume --run-id <run_id>`

### Monitor and Control

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
| `run "task" [--profile P] [--mock]` | Run fully automated (OpenAI + Claude) |
| `start --task "..."` | Start manual mode run |
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

### GUI Pipeline Execution

The GUI provides real-time progress updates during pipeline execution:

1. **Submit Task**: Fill in the task description and click "Executar"
2. **Real-time Updates**: Watch progress in the status bar as each phase completes:
   - Initializing → Planning → Executing → Reviewing → Validating → Committing → Finalizing
3. **Checkpoint Handling**: If a checkpoint is triggered, a dialog appears for approval
4. **View Results**: Navigate to "Execucoes" to see run details, logs, and artifacts
5. **Resume Runs**: Click ">>" on any incomplete run to resume execution

**Status Bar Shows:**

- Current run ID
- Execution phase
- Current iteration (e.g., "2/3")
- Last update timestamp

**Artifacts Tab:**

- View all generated files (JSON, logs, reports, patches)
- Double-click to open with default application

## Diagnostics Panel

The Diagnostics Panel provides a pre-flight check system to verify all components are operational before running tasks. Access it via **Diagnostico** in the sidebar.

### Available Checks

| Check | Description | Critical |
|-------|-------------|----------|
| **OpenAI API** | Verifies API key and connectivity | Yes |
| **Claude Executor** | Checks Claude Code CLI availability | Yes |
| **Configuration** | Validates config.yaml structure | No |
| **Workspace** | Checks workspace directories and permissions | Yes |
| **Project Directory** | Validates project structure for profile | No |
| **Git** | Checks Git availability and repository status | Yes |
| **Validation Commands** | Verifies configured commands exist | No |
| **Environment & .env** | Checks environment variables | No |
| **Core Modules** | Verifies orchestrator modules can be imported | Yes |

### Status Indicators

| Status | Meaning |
|--------|---------|
| **NOT_TESTED** (gray) | Check not yet executed |
| **RUNNING** (blue) | Check currently executing |
| **OK** (green) | Check passed |
| **WARNING** (yellow) | Check passed with warnings |
| **FAILED** (red) | Check failed |
| **CRITICAL** (dark red) | Critical failure - blocks execution |

### Features

- **Run All Checks**: Execute complete diagnostic suite
- **Run Single Check**: Re-run individual checks
- **Expandable Details**: Click any check to see detailed information
- **Recommendations**: Failed checks provide actionable suggestions
- **Export Reports**: Save diagnostics as JSON or Markdown
- **Copy to Clipboard**: Copy full report for sharing
- **Open Logs/Config**: Quick access to workspace folders

### Usage

1. Navigate to **Diagnostico** in the sidebar
2. Click **Executar Diagnostico** to run all checks
3. Review results - expand any check for details
4. Fix issues using the provided recommendations
5. Re-run individual checks as needed
6. Export report if needed for documentation

### Architecture

```
orchestrator/diagnostics.py   - Core diagnostic logic (all checks)
gui/diagnostics_panel.py      - Visual panel (PySide6 widgets)
gui/diagnostics_worker.py     - Background execution (QRunnable)
gui/diagnostics_models.py     - UI state models
```

All checks run in background threads to avoid blocking the UI.

## Project Structure

```
ai-orchestrator/
├── orchestrator/              # Core orchestration engine
│   ├── __init__.py
│   ├── main.py                # CLI entry point
│   ├── cli.py                 # CLI commands
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   ├── paths.py               # Path management
│   ├── state_store.py         # State persistence
│   ├── task_engine.py         # Manual orchestration engine
│   ├── integrated_engine.py   # Automated orchestration engine
│   ├── openai_client.py       # OpenAI API client
│   ├── claude_executor.py     # Claude Code CLI executor
│   ├── prompt_builder.py      # Prompt generation
│   ├── report_parser.py       # Execution report parser
│   ├── artifact_writer.py     # Artifact/report writer
│   ├── checkpoint.py          # Checkpoint management
│   ├── validation.py          # Validation runner
│   ├── git_ops.py             # Git operations
│   ├── diagnostics.py         # System diagnostics
│   └── logger.py              # Logging utilities
├── gui/                       # Desktop GUI (PySide6)
│   ├── __init__.py
│   ├── app.py                 # GUI entry point
│   ├── main_window.py         # Main application window
│   ├── task_panel.py          # Task creation panel
│   ├── run_panel.py           # Run history/details panel
│   ├── config_panel.py        # Settings panel
│   ├── log_viewer.py          # Log viewer panel
│   ├── checkpoint_dialog.py   # Checkpoint approval dialog
│   ├── diagnostics_panel.py   # Diagnostics panel UI
│   ├── diagnostics_worker.py  # Diagnostics background workers
│   ├── diagnostics_models.py  # Diagnostics UI state models
│   ├── worker.py              # Background workers
│   ├── settings_store.py      # UI preferences persistence
│   ├── ui_models.py           # UI data models
│   └── styles.py              # Styling and themes
├── prompts/
│   ├── planner_system.txt     # Planner system prompt
│   └── reviewer_system.txt    # Reviewer system prompt
├── workspace/
│   ├── runs/                  # Run artifacts
│   ├── state/                 # Persisted state
│   └── logs/                  # Log files
├── tests/
│   ├── test_state_store.py
│   ├── test_prompt_builder.py
│   ├── test_report_parser.py
│   ├── test_checkpoint.py
│   ├── test_git_ops.py
│   ├── test_gui_smoke.py      # GUI smoke tests
│   └── test_diagnostics.py    # Diagnostics tests
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

## Running Tests

```bash
# Run all tests (221 tests)
python -m pytest tests/

# Run core tests
python -m pytest tests/test_state_store.py tests/test_checkpoint.py -v

# Run GUI tests
python -m pytest tests/test_gui_smoke.py tests/test_run_executor.py -v

# Run with coverage
python -m pytest tests/ --cov=orchestrator --cov=gui
```

## Limitations

### Current Limitations

1. **Single Project**: Designed for one project at a time
2. **No Parallel Runs**: One active run per project recommended
3. **Windows Primary**: Tested primarily on Windows (macOS support pending)
4. **Claude Code Required**: Integrated mode requires Claude Code CLI installed

### Planned Improvements

1. Web UI for monitoring
2. Multi-project support
3. macOS/Linux testing
4. Webhook notifications
5. Additional executor backends

## Configuring OpenAI API Key

The orchestrator requires an OpenAI API key for the Planner and Reviewer components. There are several ways to configure it:

### Option 1: Environment Variable (Windows)

**Temporary (current session only):**

```powershell
# PowerShell
$env:OPENAI_API_KEY = "sk-your-key-here"

# CMD
set OPENAI_API_KEY=sk-your-key-here
```

**Permanent (user level):**

```powershell
# PowerShell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")
```

Or via Windows Settings:
1. Open Settings > System > About
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Variable name: `OPENAI_API_KEY`
6. Variable value: `sk-your-key-here`

**Important:** After setting environment variables, you must restart VS Code/terminal.

### Option 2: .env File

Create a file named `.env` in the project root:

```bash
OPENAI_API_KEY=sk-your-key-here
```

The application automatically loads this file on startup using python-dotenv.

### Option 3: macOS/Linux

```bash
# Temporary
export OPENAI_API_KEY=sk-your-key-here

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export OPENAI_API_KEY=sk-your-key-here' >> ~/.bashrc
source ~/.bashrc
```

### Verifying Configuration (GUI)

1. Open the GUI: `python -m gui.app`
2. Go to **Configuracoes** > **Ambiente** tab
3. Check the API Key status:
   - **OK** (green): Key is configured correctly
   - **NAO ENCONTRADA** (red): Key not found
   - **VAZIA** (yellow): Key exists but is empty

### Connection Test Button

The **Ambiente** tab includes two test buttons:

| Button | Description |
|--------|-------------|
| **Testar Conexao** | Full test: key resolution + client initialization + network connectivity |
| **Teste Rapido** | Quick test: key resolution + client initialization only (no network call) |

**What the test validates:**

1. **Key Resolution** - Checks if `OPENAI_API_KEY` is found (environment variable or .env file)
2. **Client Initialization** - Verifies the OpenAI client can be created with the key
3. **Network Connectivity** - Calls the `models.list()` endpoint to validate authentication and network access

**Test results:**

| Status | Meaning |
|--------|---------|
| **SUCESSO** (green) | All stages passed |
| **FALHA** (red) | Test failed at some stage |
| **TESTANDO** (blue) | Test in progress |
| **NAO TESTADO** (gray) | No test executed yet |

**Limitations:**

- The network test uses `models.list()` which is lightweight but still makes an API call
- If you want to avoid API calls, use "Teste Rapido"
- The test validates key format and connectivity but doesn't test actual completion requests
- Rate limits may temporarily block the test

**Security notes:**

- The API key is never displayed in full (masked as `sk-abc1...`)
- The key is never logged in full
- Error messages are sanitized to remove potential secrets

### Verifying Configuration (CLI)

```bash
# Check if key is set
echo %OPENAI_API_KEY%  # Windows CMD
echo $env:OPENAI_API_KEY  # PowerShell
echo $OPENAI_API_KEY  # macOS/Linux

# Test with a run (mock mode)
python -m orchestrator.main run "Test task" --mock
```

### Common Issues

| Issue | Cause | Solution |
| ----- | ----- | -------- |
| "OPENAI_API_KEY not found" | Variable not set | Set via environment or .env |
| Key set but not working | Terminal not restarted | Close and reopen VS Code/terminal |
| .env not loading | File not in project root | Move .env to same folder as config.yaml |

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
