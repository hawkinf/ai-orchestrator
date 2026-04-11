"""Reviewer client for code review model."""

import json
import os
from typing import Optional

from .models import ReviewResponse, ReviewStatus
from .utils import parse_json_from_text


class ReviewerClient:
    """
    Client for the reviewer model (ChatGPT/Codex).

    Reviews execution results and decides next steps.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._api_key = os.getenv("OPENAI_API_KEY")

    def review(self, prompt: str) -> tuple[ReviewResponse, str]:
        """
        Review execution and provide feedback.

        Args:
            prompt: Complete reviewer prompt

        Returns:
            Tuple of (ReviewResponse, raw_response)
        """
        # Check for manual response
        manual_response = self._check_manual_response()
        if manual_response:
            return self._parse_response(manual_response)

        # Return placeholder for manual workflow
        placeholder = ReviewResponse(
            status=ReviewStatus.NEEDS_FOLLOWUP,
            findings=["[PENDING: Copy reviewer response here]"],
            regression_risks=[],
            next_prompt=None,
            commit_allowed=False,
            human_review_required=True,
            suggestions=[],
        )

        return placeholder, prompt

    def _check_manual_response(self) -> Optional[str]:
        """Check for manual response."""
        return None

    def _parse_response(self, response: str) -> tuple[ReviewResponse, str]:
        """
        Parse reviewer response into structured format.

        Args:
            response: Raw response text

        Returns:
            Tuple of (ReviewResponse, raw_response)
        """
        parsed = parse_json_from_text(response)

        if parsed:
            try:
                # Handle status field
                if "status" in parsed:
                    status_str = parsed["status"].lower()
                    if status_str == "approved":
                        parsed["status"] = ReviewStatus.APPROVED
                    elif status_str == "blocked":
                        parsed["status"] = ReviewStatus.BLOCKED
                    else:
                        parsed["status"] = ReviewStatus.NEEDS_FOLLOWUP

                review = ReviewResponse.model_validate(parsed)
                return review, response
            except Exception:
                pass

        # Fallback if parsing fails
        return ReviewResponse(
            status=ReviewStatus.NEEDS_FOLLOWUP,
            findings=["[PARSE ERROR: Could not parse reviewer response]"],
            regression_risks=["Manual review required"],
            next_prompt=None,
            commit_allowed=False,
            human_review_required=True,
            suggestions=[],
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

        required = ["status", "commit_allowed"]
        return all(k in parsed for k in required)


class ManualReviewerClient(ReviewerClient):
    """
    Reviewer client for manual workflow.

    Reads review response from file.
    """

    def __init__(
        self,
        response_file: str = "workspace/prompts/reviewer_response.json",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.response_file = response_file

    def review(self, prompt: str) -> tuple[ReviewResponse, str]:
        """Review, checking for manual response file."""
        import os

        if os.path.exists(self.response_file):
            with open(self.response_file, "r", encoding="utf-8") as f:
                response = f.read()

            # Clear after reading
            os.remove(self.response_file)

            return self._parse_response(response)

        return super().review(prompt)

    def get_prompt_for_manual_use(self, prompt: str) -> str:
        """Format prompt for manual copy/paste."""
        return f"""
═══════════════════════════════════════════════════════════════
MANUAL REVIEWER WORKFLOW
═══════════════════════════════════════════════════════════════

1. Copy the prompt below
2. Paste into ChatGPT (or your reviewer model)
3. Copy the JSON response
4. Save to: {self.response_file}
5. Run: python -m orchestrator.main resume --run-id <id>

═══════════════════════════════════════════════════════════════
PROMPT TO COPY:
═══════════════════════════════════════════════════════════════

{prompt}

═══════════════════════════════════════════════════════════════
"""
