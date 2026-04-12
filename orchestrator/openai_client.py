"""OpenAI client for planner and reviewer."""

import json
import os
import re
from typing import Optional

from openai import OpenAI

from .models import PlanResponse, ReviewResponse, ReviewStatus
from .utils import parse_json_from_text
from .env_validator import EnvironmentValidator, get_openai_key_or_raise


class OpenAIClient:
    """
    Client for OpenAI API calls.

    Handles planner and reviewer interactions with structured outputs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        # Use provided key or get from environment with better diagnostics
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = get_openai_key_or_raise()

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make API call to OpenAI.

        Args:
            system_prompt: System message
            user_prompt: User message

        Returns:
            Raw response content
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content or ""

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from response, handling various formats."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*({\s*[\s\S]*?\s*})\s*```',
            r'(\{[\s\S]*\})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        return None

    def plan(self, system_prompt: str, user_prompt: str) -> tuple[PlanResponse, str, str]:
        """
        Call planner to create execution plan.

        Args:
            system_prompt: Planner system prompt
            user_prompt: Task and context

        Returns:
            Tuple of (PlanResponse, raw_response, error_message)
        """
        try:
            raw_response = self._call_api(system_prompt, user_prompt)
        except Exception as e:
            error_msg = f"OpenAI API error: {str(e)}"
            return self._default_plan(error_msg), "", error_msg

        # Parse response
        parsed = self._extract_json(raw_response)

        if parsed:
            try:
                # Handle execution_prompt field name variations
                if "execution_prompt_for_claude" in parsed:
                    parsed["execution_prompt"] = parsed.pop("execution_prompt_for_claude")

                plan = PlanResponse.model_validate(parsed)
                return plan, raw_response, ""
            except Exception as e:
                error_msg = f"Plan validation error: {str(e)}"
                return self._default_plan(error_msg, raw_response), raw_response, error_msg

        error_msg = "Could not parse JSON from planner response"
        return self._default_plan(error_msg, raw_response), raw_response, error_msg

    def _default_plan(self, error_msg: str, raw: str = "") -> PlanResponse:
        """Create default plan when parsing fails."""
        return PlanResponse(
            objective=f"[PARSE ERROR] {error_msg}",
            scope=raw[:500] if raw else "Unable to generate plan",
            constraints=[],
            files_likely_affected=[],
            risks=["Plan parsing failed - manual review required"],
            validation_steps=[],
            checkpoints=["manual_review_required"],
            execution_prompt=raw or error_msg,
        )

    def review(self, system_prompt: str, user_prompt: str) -> tuple[ReviewResponse, str, str]:
        """
        Call reviewer to evaluate execution.

        Args:
            system_prompt: Reviewer system prompt
            user_prompt: Execution report and context

        Returns:
            Tuple of (ReviewResponse, raw_response, error_message)
        """
        try:
            raw_response = self._call_api(system_prompt, user_prompt)
        except Exception as e:
            error_msg = f"OpenAI API error: {str(e)}"
            return self._default_review(error_msg), "", error_msg

        # Parse response
        parsed = self._extract_json(raw_response)

        if parsed:
            try:
                # Handle status field
                if "status" in parsed:
                    status_str = str(parsed["status"]).lower()
                    if status_str == "approved":
                        parsed["status"] = ReviewStatus.APPROVED
                    elif status_str == "blocked":
                        parsed["status"] = ReviewStatus.BLOCKED
                    else:
                        parsed["status"] = ReviewStatus.NEEDS_FOLLOWUP

                # Handle field name variations
                if "whether_commit_is_allowed" in parsed:
                    parsed["commit_allowed"] = parsed.pop("whether_commit_is_allowed")
                if "whether_human_review_is_required" in parsed:
                    parsed["human_review_required"] = parsed.pop("whether_human_review_is_required")
                if "regressions_risk" in parsed:
                    parsed["regression_risks"] = parsed.pop("regressions_risk")
                if "next_prompt_for_executor" in parsed:
                    parsed["next_prompt"] = parsed.pop("next_prompt_for_executor")

                review = ReviewResponse.model_validate(parsed)
                return review, raw_response, ""
            except Exception as e:
                error_msg = f"Review validation error: {str(e)}"
                return self._default_review(error_msg), raw_response, error_msg

        error_msg = "Could not parse JSON from reviewer response"
        return self._default_review(error_msg), raw_response, error_msg

    def _default_review(self, error_msg: str) -> ReviewResponse:
        """Create default review when parsing fails."""
        return ReviewResponse(
            status=ReviewStatus.NEEDS_FOLLOWUP,
            findings=[f"[PARSE ERROR] {error_msg}"],
            regression_risks=["Review parsing failed"],
            next_prompt=None,
            commit_allowed=False,
            human_review_required=True,
            suggestions=[],
        )


class PlannerClient:
    """Specialized client for planning."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        self.openai = OpenAIClient(
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def plan(self, system_prompt: str, user_prompt: str) -> tuple[PlanResponse, str, str]:
        """Generate execution plan."""
        return self.openai.plan(system_prompt, user_prompt)


class ReviewerClient:
    """Specialized client for reviewing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        self.openai = OpenAIClient(
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def review(self, system_prompt: str, user_prompt: str) -> tuple[ReviewResponse, str, str]:
        """Review execution results."""
        return self.openai.review(system_prompt, user_prompt)
