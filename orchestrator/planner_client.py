"""Planner client for interacting with planning model."""

import json
import os
from typing import Optional

from .models import PlanResponse
from .utils import parse_json_from_text


class PlannerClient:
    """
    Client for the planner model (ChatGPT/Codex).

    This is a placeholder implementation that can be extended
    with actual API integration when ready.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._api_key = os.getenv("OPENAI_API_KEY")

    def plan(self, prompt: str) -> tuple[PlanResponse, str]:
        """
        Generate a plan from the given prompt.

        For now, this returns a placeholder that should be filled
        by copying the planner output manually.

        Args:
            prompt: Complete planner prompt

        Returns:
            Tuple of (PlanResponse, raw_response)
        """
        # In production, this would call the OpenAI API
        # For now, we create a manual workflow placeholder

        # Check if there's a manual response file
        manual_response = self._check_manual_response()
        if manual_response:
            return self._parse_response(manual_response)

        # Return placeholder indicating manual input needed
        placeholder = PlanResponse(
            objective="[PENDING: Copy planner response here]",
            scope="[PENDING]",
            constraints=[],
            files_likely_affected=[],
            risks=[],
            validation_steps=[],
            checkpoints=[],
            execution_prompt="[PENDING: Paste planner execution prompt here]",
        )

        return placeholder, prompt

    def _check_manual_response(self) -> Optional[str]:
        """Check for manual response in clipboard or file."""
        # Could be extended to read from a staging file
        return None

    def _parse_response(self, response: str) -> tuple[PlanResponse, str]:
        """
        Parse planner response into structured format.

        Args:
            response: Raw response text

        Returns:
            Tuple of (PlanResponse, raw_response)
        """
        parsed = parse_json_from_text(response)

        if parsed:
            try:
                plan = PlanResponse.model_validate(parsed)
                return plan, response
            except Exception:
                pass

        # If parsing fails, create a fallback
        return PlanResponse(
            objective="[PARSE ERROR: Could not parse planner response]",
            scope=response[:500],
            constraints=[],
            files_likely_affected=[],
            risks=["Parse error - manual review required"],
            validation_steps=[],
            checkpoints=["manual_review_required"],
            execution_prompt=response,
        ), response

    def validate_response(self, response: str) -> bool:
        """
        Validate that a response is properly formatted.

        Args:
            response: Response to validate

        Returns:
            True if valid JSON with required fields
        """
        parsed = parse_json_from_text(response)
        if not parsed:
            return False

        required = ["objective", "scope", "execution_prompt"]
        return all(k in parsed for k in required)


class ManualPlannerClient(PlannerClient):
    """
    Planner client that reads from a file for manual workflow.

    This allows the user to:
    1. Copy the generated prompt
    2. Paste into ChatGPT
    3. Copy the response
    4. Paste into a response file
    5. Continue the workflow
    """

    def __init__(
        self,
        response_file: str = "workspace/prompts/planner_response.json",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.response_file = response_file

    def plan(self, prompt: str) -> tuple[PlanResponse, str]:
        """Generate plan, checking for manual response file."""
        import os

        if os.path.exists(self.response_file):
            with open(self.response_file, "r", encoding="utf-8") as f:
                response = f.read()

            # Clear the file after reading
            os.remove(self.response_file)

            return self._parse_response(response)

        # No response file, return placeholder
        return super().plan(prompt)

    def get_prompt_for_manual_use(self, prompt: str) -> str:
        """
        Get prompt formatted for manual copy/paste to ChatGPT.

        Args:
            prompt: Generated prompt

        Returns:
            Formatted prompt with instructions
        """
        instructions = f"""
═══════════════════════════════════════════════════════════════
MANUAL PLANNER WORKFLOW
═══════════════════════════════════════════════════════════════

1. Copy the prompt below
2. Paste into ChatGPT (or your planner model)
3. Copy the JSON response
4. Save to: {self.response_file}
5. Run: python -m orchestrator.main resume --run-id <id>

═══════════════════════════════════════════════════════════════
PROMPT TO COPY:
═══════════════════════════════════════════════════════════════

{prompt}

═══════════════════════════════════════════════════════════════
"""
        return instructions
