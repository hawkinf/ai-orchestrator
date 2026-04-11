"""Prompt building for planner, executor, and reviewer."""

from pathlib import Path
from typing import Optional

from .models import ExecutionReport, PlanResponse, RunState
from .config import OrchestratorConfig


class PromptBuilder:
    """
    Builds structured prompts for each stage of the pipeline.

    Prompts are loaded from template files when available,
    with fallback to embedded templates.
    """

    def __init__(self, config: OrchestratorConfig, prompts_dir: Optional[Path] = None):
        self.config = config
        self.prompts_dir = prompts_dir or Path("prompts")

    def _load_template(self, name: str, fallback: str) -> str:
        """Load template from file or use fallback."""
        template_path = self.prompts_dir / f"{name}.txt"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return fallback

    def build_planner_prompt(
        self,
        task_description: str,
        project_context: Optional[str] = None,
        constraints: Optional[list[str]] = None,
    ) -> str:
        """
        Build prompt for the planner.

        Args:
            task_description: User's task description
            project_context: Optional project context
            constraints: Optional additional constraints

        Returns:
            Complete planner prompt
        """
        system_template = self._load_template("planner_system", PLANNER_SYSTEM_DEFAULT)

        constraint_text = ""
        if constraints:
            constraint_text = "\n".join(f"- {c}" for c in constraints)

        context_text = project_context or "No additional context provided."

        prompt = f"""{system_template}

## TASK
{task_description}

## PROJECT CONTEXT
{context_text}

## ADDITIONAL CONSTRAINTS
{constraint_text or "None specified."}

## PROFILE
Active profile: {self.config.active_profile}
Validation commands: {', '.join(self.config.get_validation_commands()) or 'None'}

Please analyze this task and provide your response in the required JSON format.
"""
        return prompt

    def build_executor_prompt(
        self,
        plan: PlanResponse,
        iteration: int = 1,
        previous_feedback: Optional[str] = None,
    ) -> str:
        """
        Build prompt for the executor (Claude Code).

        Args:
            plan: Plan from planner
            iteration: Current iteration number
            previous_feedback: Feedback from previous iteration

        Returns:
            Complete executor prompt
        """
        wrapper_template = self._load_template("executor_wrapper", EXECUTOR_WRAPPER_DEFAULT)

        feedback_section = ""
        if previous_feedback:
            feedback_section = f"""
## FEEDBACK FROM PREVIOUS ITERATION
{previous_feedback}

Please address the above feedback in this iteration.
"""

        prompt = f"""{wrapper_template}

## ITERATION
This is iteration {iteration}.

## OBJECTIVE
{plan.objective}

## SCOPE
{plan.scope}

## EXECUTION INSTRUCTIONS
{plan.execution_prompt}

## FILES LIKELY AFFECTED
{chr(10).join('- ' + f for f in plan.files_likely_affected) or 'Not specified'}

## CONSTRAINTS
{chr(10).join('- ' + c for c in plan.constraints) or 'None'}

## RISKS TO AVOID
{chr(10).join('- ' + r for r in plan.risks) or 'None identified'}

## VALIDATION STEPS
{chr(10).join('- ' + v for v in plan.validation_steps) or 'Standard validation'}
{feedback_section}
After completing your work, provide a structured report of what was done.
"""
        return prompt

    def build_reviewer_prompt(
        self,
        state: RunState,
        execution_report: ExecutionReport,
        git_diff: str,
    ) -> str:
        """
        Build prompt for the reviewer.

        Args:
            state: Current run state
            execution_report: Report from executor
            git_diff: Git diff of changes

        Returns:
            Complete reviewer prompt
        """
        system_template = self._load_template("reviewer_system", REVIEWER_SYSTEM_DEFAULT)

        prompt = f"""{system_template}

## ORIGINAL TASK
{state.task.description}

## PLAN OBJECTIVE
{state.plan.objective if state.plan else 'No plan available'}

## PLAN SCOPE
{state.plan.scope if state.plan else 'No plan available'}

## EXECUTION REPORT
### Summary
{execution_report.summary}

### Files Changed
{chr(10).join('- ' + f for f in execution_report.files_changed) or 'None'}

### Commands Executed
{chr(10).join('- ' + c for c in execution_report.commands_executed) or 'None'}

### Tests Run
Passed: {execution_report.tests_passed}
Failed: {execution_report.tests_failed}

### Pending Items
{chr(10).join('- ' + p for p in execution_report.pending_items) or 'None'}

### Remaining Risks
{chr(10).join('- ' + r for r in execution_report.remaining_risks) or 'None identified'}

## GIT DIFF
```
{git_diff[:5000]}{'...[truncated]' if len(git_diff) > 5000 else ''}
```

## ITERATION
Current iteration: {state.current_iteration}
Max iterations: {self.config.max_iterations}

Please review this execution and provide your response in the required JSON format.
"""
        return prompt


# ============================================================
# Default Templates (embedded fallbacks)
# ============================================================

PLANNER_SYSTEM_DEFAULT = """You are a senior software architect and planner.

Your role is to analyze tasks and create clear, actionable execution plans.

You MUST respond with a JSON object containing these fields:
- objective: Clear, single-sentence objective
- scope: Description of what will be changed
- constraints: List of constraints to follow
- files_likely_affected: List of files that may need changes
- risks: List of potential risks
- validation_steps: List of steps to validate success
- checkpoints: List of points requiring human review (migrations, deletions, etc.)
- execution_prompt: Detailed instructions for the executor

Keep plans focused and achievable in a single session.
Identify risks early.
Be specific about validation criteria.

RESPOND ONLY WITH VALID JSON. No additional text."""


EXECUTOR_WRAPPER_DEFAULT = """You are executing a planned development task.

IMPORTANT RULES:
1. Follow the plan precisely
2. Make minimal, focused changes
3. Run validation commands after changes
4. Report what you did clearly
5. If blocked, explain why and stop
6. Never skip tests
7. Never leave debug code
8. Always handle errors gracefully

After completing work, provide a structured report:
- Summary of what was done
- Files changed
- Commands executed
- Tests run and results
- Any pending items
- Any remaining risks

Be thorough but concise."""


REVIEWER_SYSTEM_DEFAULT = """You are a senior code reviewer.

Your role is to review execution results and decide next steps.

You MUST respond with a JSON object containing these fields:
- status: One of "approved", "needs_followup", "blocked"
- findings: List of review findings
- regression_risks: List of potential regressions
- next_prompt: Instructions for next iteration (if needs_followup)
- commit_allowed: Boolean - whether changes can be committed
- human_review_required: Boolean - whether human must review
- suggestions: List of improvement suggestions

CRITERIA FOR APPROVAL:
- Task objective is met
- No regressions introduced
- Tests pass
- Code follows project standards
- No obvious bugs or issues

RESPOND ONLY WITH VALID JSON. No additional text."""
