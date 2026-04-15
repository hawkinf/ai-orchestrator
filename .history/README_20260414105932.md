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

## Desktop Build

Use the PyInstaller spec as the default build target:

```bash
python build.py build
```

This resolves to:

```bash
python -m PyInstaller --noconfirm --clean ai_orchestrator.spec
```

Important build rules:

- When the target is `ai_orchestrator.spec`, do not pass `--onefile` or `--onedir` on the CLI. PyInstaller rejects those flags when a `.spec` file is provided.
- The packaging mode is defined inside `ai_orchestrator.spec`. The current spec is configured as `onefile` because it contains `EXE(...)` without `COLLECT(...)`.
- If you intentionally build from a Python entrypoint instead of the spec, use `python build.py build --target main.py` and then CLI packaging flags are allowed through the build script.
- The Windows build is generated in GUI/windowed mode (`console=False`), so the final executable should open only the application window and not an extra terminal.
- Run the build in a normal terminal session. PyInstaller warns that running as Administrator is unnecessary and not recommended.

## Release Pipeline

The desktop product release flow is now standardized around `build.py` and `dist/` artifacts.

Available commands:

```bash
python build.py build-dev
python build.py build-release
python build.py installer
python build.py release
```

What each command does:

- `build-dev`: produces a development-oriented desktop build.
- `build-release`: refreshes version metadata and generates the release executable.
- `installer`: renders the Inno Setup script and compiles it when `ISCC.exe` is available.
- `release`: runs the release build, attempts the installer step, and writes a release bundle under `dist/releases/v<version>/`.

Build outputs:

- `dist/AIOrchestrator.exe`: portable executable.
- `dist/installer/AI-Orchestrator-Setup-<version>.exe`: Windows installer when Inno Setup is installed.
- `dist/releases/v<version>/`: release bundle for GitHub Releases.
- `dist/build-logs/`: build and installer logs.

Version metadata sources:

- `version.json`: single source of truth for version, channel and build metadata.
- `update_config.json`: default update source, channel and release URL.
- `CHANGELOG.md`: recent changes shown in the desktop UI and copied into release notes.

## Windows Installer

The installer pipeline is Windows-first and based on Inno Setup.

Requirements:

- Inno Setup 6 installed locally if you want the installer executable compiled automatically.
- If Inno Setup is not installed, the project still generates `dist/installer/AIOrchestrator.iss` so the installer can be compiled later.

Default installer behavior:

- installs under `Program Files\AI Orchestrator`
- creates Start Menu shortcut
- optionally creates desktop shortcut
- registers a modern wizard style
- launches the app after installation

## Updates

The desktop app includes a product-facing update flow.

What the user sees:

- `Sobre` dialog with version, build date, release link and recent changes.
- `Atualizações` dialog with current version, latest version, changelog and direct actions.
- buttons labeled `Atualizar`, `Ver changelog` and `Depois`.

Default behavior:

- checks GitHub Releases using `update_config.json`
- prefers the Windows installer artifact when available
- allows turning off update checks on startup
- supports release channels through the persisted UI preferences

## Installation

For local development:

```bash
pip install -r requirements.txt
python -m gui.app
```

For end users on Windows:

1. Download `AI-Orchestrator-Setup-<version>.exe` from the release page.
2. Run the installer.
3. Start AI Orchestrator from the Start Menu or desktop shortcut.

Portable fallback:

1. Download `AIOrchestrator-<version>-win64.exe`.
2. Run the executable directly.

## Troubleshooting Release and Update

- If the installer is not generated, confirm that Inno Setup 6 is installed and `ISCC.exe` is reachable.
- If the app icon does not appear in the packaged executable, verify that `assets/icon.ico` exists before running the build.
- If update checks fail, validate the release endpoint in `update_config.json` and confirm that the GitHub release has a Windows artifact attached.
- If the UI shows outdated build info, rerun `python build.py build-release` so `version.json` and `version_info.txt` are refreshed together.

## Quick Start

### Option A: GUI Mode (Recommended)

Launch the desktop application:

```bash
# Start the GUI
python -m gui.app
```

Behavior notes:

- In development, running `python -m gui.app` from a terminal keeps that terminal open for logs.
- In the packaged Windows build, `AIOrchestrator.exe` runs as a desktop app without an attached console window.
- If the OpenAI API key is missing, the GUI shows a compact guidance dialog and can open `Configuracoes > Ambiente` directly.
- On the first launch, the app can open a guided onboarding wizard to configure project, profile, OpenAI, executor, workspace and Git basics.
- The GUI supports `Modo simples` and `Modo avançado`. Simple mode hides rare options and technical panels; advanced mode exposes full controls.
- The renewed `Ajuda` panel includes an embedded manual with search, practical sections and a copy button for instructions.

The GUI provides:

- **Nova Tarefa**: Create and submit tasks with full configuration
- **Central de Runs**: Dashboard with metrics, filters, and quick actions (see below)
- **Checkpoints**: Centralized checkpoint management with approval/rejection (see Checkpoint Center below)
- **Execucoes**: View run history, details, and artifacts
- **Diagnostico**: Pre-flight system checks (see Diagnostics Panel below)
- **Logs / Relatorios**: Browse logs and reports
- **Configuracoes**: Edit settings visually, test API connection
- Checkpoint approval dialogs
- Real-time progress updates during pipeline execution
- Resume interrupted runs
- Open run artifacts directly from the UI

### GUI Onboarding

Recommended first-run flow:

1. Open the onboarding wizard.
2. Choose the project directory and profile.
3. Configure the OpenAI API key.
4. Confirm the Claude executor command.
5. Validate workspace and Git.
6. Finish and go to `Nova Tarefa` or `Diagnóstico`.

The onboarding can be opened again from `Config`.

### Simple vs Advanced Mode

- `Modo simples`: focuses on the minimum setup, basic task submission and guided explanations.
- `Modo avançado`: exposes replay, policies, extra configuration tabs and the full set of controls.

The selected mode is saved in the GUI preferences.

### Minimum Recommended Setup

The GUI now tracks a minimum recommended setup checklist:

- project path
- profile
- OpenAI configuration
- Claude executor availability
- workspace readiness
- Git readiness as a recommended, non-blocking item

Use `Configurações` to review the checklist or trigger `Concluir configuração`.

### Embedded Manual

The `Ajuda` panel includes:

- Visão Geral
- Primeiros Passos
- Como criar uma tarefa
- Planner / executor / reviewer
- Checkpoints
- Policies
- Replay
- Diagnóstico
- Configuração de OpenAI, Claude e Git
- Modo simples vs avançado
- Como interpretar os Insights do Sistema
- FAQ e solução de problemas

### System Insights

The dashboard now includes a compact `Insights do Sistema` block and a full aggregate view for the recent run history.

It reuses the existing run index, timeline, and per-run insights to detect patterns such as:

- recurring validation failures
- frequent checkpoints
- Git failures
- increasing failure rate
- average duration trend
- success rate by profile

Use the full view to:

- analyze the last 10, 20, 50 or 100 runs
- filter by profile and status
- limit the analysis to a date range
- export the report to `workspace/logs/system_insights_<timestamp>.json`
- export the report to `workspace/logs/system_insights_<timestamp>.md`

### Recommended Actions

Run Insights and System Insights now feed a `Recommended Actions` layer in the GUI.

This layer suggests practical next steps such as:

- open `Configurações > Git`
- open `Configurações > Executor`
- open the `Validação`, `Git` or `Timeline` tab for a specific run
- jump to `Diagnóstico`, `Checkpoints` or `Policies`
- filter the dashboard to recent failed runs
- open `Replay` already pointed at a specific run when possible

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

## Central de Runs (Dashboard)

The Runs Dashboard provides a consolidated operational view of all executions. Access via **Central de Runs** in the sidebar.

### Metrics Summary

The top bar displays real-time metrics:

| Metric | Description |
|--------|-------------|
| **Total** | Total number of runs |
| **Em Execucao** | Currently running |
| **Concluidas** | Successfully completed |
| **Falhas** | Failed runs |
| **Checkpoint** | Awaiting approval |
| **Bloqueadas** | Blocked runs |

### Filters

Filter runs by:

- **Search**: Find by run_id or task description
- **Status**: Running, Completed, Failed, Checkpoint, Blocked
- **Profile**: Filter by project type (flutter, python, etc.)
- **Checkpoint**: Show only runs with pending checkpoints
- **Error**: Show only runs with errors

### Quick Actions

For each run:

- **Retomar**: Resume an incomplete run
- **Pasta**: Open run folder in file explorer
- **Relatorio**: Open final report (JSON or Markdown)
- **Diff**: Open git diff/patch file
- **Diagnostico**: Run pre-flight checks

### Run Detail Preview

Select a run to see:

- Full task description
- Current stage and iteration
- Duration
- Plan objective
- Execution summary
- Review status
- Commit hash
- Errors (if any)
- Checkpoint status
- Identified risks

### Export

- **Export JSON**: Save full dashboard data to `workspace/logs/dashboard_<timestamp>.json`
- **Export Markdown**: Save summary to `workspace/logs/dashboard_<timestamp>.md`
- **Copy Summary**: Copy metrics and recent runs to clipboard

### Auto-Refresh

The dashboard auto-refreshes every 5 seconds by default. Toggle with the **Auto-refresh** checkbox.

### Architecture

```
orchestrator/run_index.py     - Data aggregation from workspace
gui/dashboard_panel.py        - Visual dashboard (PySide6)
gui/dashboard_worker.py       - Background loading (QRunnable)
gui/dashboard_models.py       - UI state models
```

Data is read from existing state files - no duplication of core logic.

## Checkpoint Center

The Checkpoint Center provides centralized management of all checkpoints - critical decision points that require human approval. Access via **Checkpoints** in the sidebar.

### What are Checkpoints?

Checkpoints are safety gates that pause execution when the system detects potentially dangerous or irreversible operations:

| Checkpoint Type | Trigger | Severity |
|-----------------|---------|----------|
| **Git Destructive** | force push, reset --hard, branch -D | Critical |
| **Infrastructure** | terraform, cloudformation, deploy | Critical |
| **Architecture Rewrite** | rewrite, refactor entire, restructure | Critical |
| **Destructive Operation** | delete, rm -rf, drop table, truncate | High Risk |
| **Migration** | database migrations | High Risk |
| **Command Not Allowed** | Commands not in allowlist | Warning |
| **Repeated Failures** | Multiple execution failures | Warning |
| **Manual Request** | User-requested checkpoint | Info |

### Checkpoint List

The main view shows all checkpoints with:

- **Status**: Pending (yellow), Approved (green), Rejected (red)
- **Severity**: Critical, High Risk, Warning, Info
- **Run ID**: Associated run
- **Type**: Checkpoint reason
- **Description**: What triggered the checkpoint
- **Pipeline Stage**: Where in the pipeline
- **Created**: When the checkpoint was created

### Metrics Bar

Real-time metrics showing:

| Metric | Description |
|--------|-------------|
| **Total** | Total checkpoints across all runs |
| **Pendentes** | Awaiting decision |
| **Aprovados** | Approved checkpoints |
| **Rejeitados** | Rejected checkpoints |
| **Criticos** | Critical severity pending |
| **Alto Risco** | High risk severity pending |

### Filters

Filter checkpoints by:

- **Search**: Find by run_id or description
- **Status**: Pending, Approved, Rejected
- **Severity**: Critical, High Risk, Warning, Info
- **Type**: Filter by checkpoint reason

### Checkpoint Detail

Select a checkpoint to see full context:

- Complete description
- Task being executed
- Pipeline stage and iteration
- Risk assessment
- System recommendation
- Files affected
- Diff preview (if available)
- Plan objective and risks

### Actions

For pending checkpoints:

- **Aprovar**: Approve and resume execution
- **Rejeitar**: Reject and cancel the run
- **Observacao**: Add notes to your decision

When you approve a checkpoint:

1. The decision is recorded with timestamp
2. The run automatically resumes
3. The dashboard updates

When you reject a checkpoint:

1. The run is marked as cancelled
2. The decision is recorded for history

### History

View all past decisions:

- Who decided (if applicable)
- When
- Resolution note
- Run outcome after decision

### Export

- **Export JSON**: Full checkpoint data to `workspace/logs/checkpoints_<timestamp>.json`
- **Export Markdown**: Summary to `workspace/logs/checkpoints_<timestamp>.md`
- **Copy Summary**: Copy metrics and pending list to clipboard

### Auto-Refresh

The panel auto-refreshes every 5 seconds. Toggle with the **Auto-refresh** checkbox.

### Architecture

```
orchestrator/checkpoint_index.py  - Checkpoint aggregation from workspace
orchestrator/checkpoint.py        - Core checkpoint logic
gui/checkpoints_panel.py          - Visual panel (PySide6)
gui/checkpoints_worker.py         - Background workers (QRunnable)
gui/checkpoints_models.py         - UI state models
```

Checkpoint Center reads from existing state files and uses the core CheckpointManager for actions - no duplication of business logic.

## Policy Engine

The Policy Engine enables automated decision-making for checkpoints based on configurable rules. Access via **Politicas** in the sidebar.

### Overview

Instead of manually approving every checkpoint, you can define rules that automatically:

- **Approve** low-risk checkpoints
- **Reject** dangerous patterns
- **Require Human** approval for critical operations

### Default Rules

The system includes built-in safety rules (cannot be deleted):

| Rule | Action | Trigger |
|------|--------|---------|
| **Require Human for Critical** | Require Human | Severity = critical |
| **Require Human for Delete** | Require Human | has_delete = true |
| **Require Human for Migrations** | Require Human | has_migration = true |
| **Require Human for Destructive Git** | Require Human | checkpoint.type = git_destructive |
| **Require Human for Infrastructure** | Require Human | checkpoint.type = infrastructure_change |
| **Require Human for Architecture** | Require Human | checkpoint.type = architecture_rewrite |
| **Reject Repeated Failures** | Reject | failure_count > 5 (disabled) |
| **Auto-approve Low Risk Manual** | Approve | type = manual_request, severity = info (disabled) |
| **Auto-approve Small Safe Commands** | Approve | type = command_not_allowed, files < 5 (disabled) |

### Creating Custom Rules

1. Go to **Politicas** > **Rules** tab
2. Click **New Rule**
3. Configure:
   - **ID**: Unique identifier (e.g., `my_approve_tests`)
   - **Name**: Display name
   - **Description**: What the rule does
   - **Action**: Approve, Reject, or Require Human
   - **Priority**: Lower = higher priority (evaluated first)
   - **Conditions**: All must match for rule to apply

### Available Conditions

| Field | Description | Example Values |
|-------|-------------|----------------|
| `checkpoint.type` | Checkpoint reason | manual_request, git_destructive, infrastructure_change |
| `checkpoint.severity` | Severity level | info, warning, high_risk, critical |
| `has_delete` | Delete operation detected | true/false |
| `has_migration` | Migration detected | true/false |
| `has_force_push` | Force push detected | true/false |
| `has_destructive_git` | Destructive git operation | true/false |
| `affected_files_count` | Number of affected files | Any number |
| `git_diff_size` | Lines changed | Any number |
| `failure_count` | Execution failures | Any number |
| `command_name` | Command being executed | Any string |
| `project_type` | Project type | flutter, python, generic |

### Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match (case-insensitive for strings) | severity equals "warning" |
| `not_equals` | Does not match | type not_equals "critical" |
| `contains` | String contains | description contains "test" |
| `in` | Value in list | severity in ["info", "warning"] |
| `greater_than` | Numeric comparison | affected_files_count > 10 |
| `less_than` | Numeric comparison | git_diff_size < 100 |
| `is_true` | Boolean true | has_delete is_true |
| `is_false` | Boolean false | has_migration is_false |
| `exists` | Field exists | command_name exists |
| `matches_regex` | Regex match | description matches_regex "test.*" |

### Decision History

The **Decision History** tab shows all policy decisions:

- Checkpoint ID
- Rule that matched (or "no match")
- Decision (Approve/Reject/Require Human)
- Whether it was overridden
- Timestamp

### Statistics

The top bar shows real-time statistics:

| Metric | Description |
|--------|-------------|
| **Total Decisions** | All policy decisions made |
| **Auto-Approved** | Automatically approved |
| **Auto-Rejected** | Automatically rejected |
| **Required Human** | Required manual approval |
| **Override Rate** | Percentage of decisions overridden |

### Rule Evaluation

Rules are evaluated in priority order (lower number = higher priority):

1. Only enabled rules are considered
2. All conditions in a rule must match
3. First matching rule determines the action
4. If no rule matches, defaults to **Require Human**

### Architecture

```
orchestrator/policy_models.py   - Data models (Rule, Decision, Context)
orchestrator/policy_store.py    - Persistence (rules.json, history.json)
orchestrator/policy_engine.py   - Evaluation engine
gui/policy_panel.py             - Visual panel (PySide6)
```

Policy decisions are stored in `workspace/policies/`:

```
workspace/policies/
├── rules.json      - All policy rules
├── history.json    - Decision history (last 1000)
└── stats.json      - Aggregated statistics
```

## Replay / Simulation

The Replay feature allows you to re-execute runs without side effects for debugging, testing, and comparison. Access via **Replay** in the sidebar.

### Overview

Replay enables:

- **Bug reproduction**: Re-run a failed execution to understand what went wrong
- **Decision simulation**: Test different checkpoint decisions
- **Comparison**: Compare original vs replay outputs
- **Validation**: Verify that changes don't break existing behavior

### Replay Modes

| Mode | Description | Side Effects |
|------|-------------|--------------|
| **Dry Run** | Simulate all stages without real execution | None |
| **Partial** | Execute only specific stages | Minimal |
| **Full** | Complete replay in isolated sandbox | Contained |

### Dry Run Mode

The safest mode - simulates everything without executing real commands:

- No subprocess calls
- No file modifications
- No API calls (uses cached responses)
- Records what would have happened

### Partial Mode

Execute only specific pipeline stages:

- **Planning**: Re-run planner with same input
- **Execution**: Re-run executor (mocked by default)
- **Review**: Re-run reviewer
- **Validation**: Re-run validation commands

### Full Mode (Sandbox)

Complete pipeline execution in isolation:

1. Copies project to temporary directory
2. Executes full pipeline
3. Compares results with original
4. Cleans up sandbox after completion

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| **Mock Executor** | Simulate command execution | Yes |
| **Mock Planner** | Use original plan instead of calling API | No |
| **Mock Reviewer** | Use original review instead of calling API | No |
| **Auto-approve Checkpoints** | Automatically approve all checkpoints | Yes |
| **Use Sandbox** | Run in isolated directory | No (Full mode only) |
| **Timeout** | Maximum execution time | 600s |

### Comparison Report

After replay, view detailed comparison:

**Summary**:
- Overall result (Identical/Different)
- Time comparison (original vs replay)
- Files comparison
- Checkpoints comparison

**Stage Comparisons**:
- Output diff for each stage
- Time difference per stage
- Success/failure status

**Artifacts**:
- `report.json`: Full replay result
- `metrics.json`: Timing and statistics
- `diff.patch`: Unified diff of changes

### History

View all past replays with:

- Replay ID
- Original run
- Mode used
- Status and result
- Duration

### Use Cases

**1. Debugging Failed Runs**
```
1. Select the failed run
2. Choose Dry Run mode
3. Execute replay
4. Compare stage outputs to find the failure point
```

**2. Testing Checkpoint Decisions**
```
1. Select a run with checkpoints
2. Configure custom checkpoint decisions
3. Run replay to see different outcomes
```

**3. Validating Changes**
```
1. Make code changes
2. Replay a successful run
3. Compare outputs to ensure no regressions
```

### Architecture

```
orchestrator/replay_models.py   - Data models (Config, Result, Comparison)
orchestrator/replay_engine.py   - Replay execution engine
gui/replay_panel.py             - Visual panel (PySide6)
```

Replay data is stored in `workspace/replays/`:

```
workspace/replays/
├── index.json                    - List of all replays
└── replay-20260413-120000-abc123/
    ├── report.json               - Full replay result
    ├── metrics.json              - Timing data
    └── diff.patch                - Stage output diffs
```

### Safety

Replay is designed to be safe by default:

- Original runs are never modified
- Dry run mode has zero side effects
- Sandbox mode isolates execution
- All replays are tracked with unique IDs
- Cancel button stops execution immediately

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
│   ├── run_index.py           # Run aggregation for dashboard
│   ├── checkpoint_index.py    # Checkpoint aggregation for center
│   ├── policy_engine.py       # Policy evaluation engine
│   ├── policy_models.py       # Policy data models
│   ├── policy_store.py        # Policy persistence
│   ├── replay_engine.py       # Replay execution engine
│   ├── replay_models.py       # Replay data models
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
│   ├── dashboard_panel.py     # Dashboard panel UI
│   ├── dashboard_worker.py    # Dashboard background workers
│   ├── dashboard_models.py    # Dashboard UI state models
│   ├── checkpoints_panel.py   # Checkpoint center panel UI
│   ├── checkpoints_worker.py  # Checkpoint center background workers
│   ├── checkpoints_models.py  # Checkpoint center UI state models
│   ├── policy_panel.py        # Policy management panel UI
│   ├── replay_panel.py        # Replay panel UI
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
│   ├── test_diagnostics.py    # Diagnostics tests
│   ├── test_run_index.py      # Run index tests
│   ├── test_dashboard.py      # Dashboard tests
│   ├── test_checkpoint_index.py  # Checkpoint index tests
│   ├── test_checkpoints_panel.py # Checkpoint center tests
│   ├── test_policy_engine.py     # Policy engine tests
│   └── test_replay_engine.py     # Replay engine tests
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
## Command Center

O `Command Center` agora é a tela inicial padrão da GUI.

Ele concentra:
- saúde geral do sistema
- próxima ação sugerida
- runs recentes
- alertas e checkpoints
- ações recomendadas prioritárias

No modo `simple`, a tela mostra só o essencial para decidir o próximo passo.
No modo `advanced`, ela expõe mais sinais operacionais e o resumo de saúde detalhado.

Use essa tela para responder rapidamente:
- o sistema está saudável?
- existe algo urgente?
- qual é a melhor próxima ação?
