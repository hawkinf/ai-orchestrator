"""Policy engine for checkpoint auto-approval evaluation.

Evaluates checkpoints against policy rules to determine actions.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple
from uuid import uuid4

from .policy_models import (
    CheckpointContext,
    ConditionOperator,
    PolicyAction,
    PolicyCondition,
    PolicyDecision,
    PolicyRule,
)
from .policy_store import PolicyStore

logger = logging.getLogger("ai_orchestrator.policy_engine")


class PolicyEngine:
    """
    Evaluates checkpoints against policy rules.

    Usage:
        engine = PolicyEngine(workspace_path)
        decision = engine.evaluate(checkpoint_context)

        if decision.decision == PolicyAction.APPROVE:
            # Auto-approve the checkpoint
        elif decision.decision == PolicyAction.REJECT:
            # Auto-reject the checkpoint
        else:
            # Require human approval
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.store = PolicyStore(workspace_path)

    def evaluate(self, context: CheckpointContext) -> PolicyDecision:
        """
        Evaluate a checkpoint context against all enabled rules.

        Rules are evaluated in priority order (lower = higher priority).
        First matching rule determines the decision.
        If no rule matches, defaults to REQUIRE_HUMAN.

        Args:
            context: The checkpoint context to evaluate

        Returns:
            PolicyDecision with the action to take
        """
        rules = self.store.get_enabled_rules()
        logger.debug(f"Evaluating checkpoint {context.checkpoint_id} against {len(rules)} rules")

        for rule in rules:
            matched, reason = self._evaluate_rule(rule, context)
            if matched:
                decision = PolicyDecision(
                    decision_id=str(uuid4()),
                    checkpoint_id=context.checkpoint_id,
                    run_id=context.run_id,
                    decision=rule.action,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    confidence=1.0,
                    reason=reason,
                    timestamp=datetime.now(),
                )

                # Save decision to history
                self.store.save_decision(decision)

                logger.info(
                    f"Checkpoint {context.checkpoint_id} matched rule '{rule.name}': "
                    f"{rule.action.value}"
                )
                return decision

        # No rule matched - default to require human
        decision = PolicyDecision(
            decision_id=str(uuid4()),
            checkpoint_id=context.checkpoint_id,
            run_id=context.run_id,
            decision=PolicyAction.REQUIRE_HUMAN,
            rule_id=None,
            rule_name=None,
            confidence=1.0,
            reason="No policy rule matched - requiring human approval",
            timestamp=datetime.now(),
        )

        self.store.save_decision(decision)
        logger.info(f"Checkpoint {context.checkpoint_id}: no rule matched, requiring human")
        return decision

    def _evaluate_rule(
        self, rule: PolicyRule, context: CheckpointContext
    ) -> Tuple[bool, str]:
        """
        Evaluate a single rule against the context.

        All conditions must match for the rule to apply.

        Returns:
            Tuple of (matched: bool, reason: str)
        """
        if not rule.conditions:
            # Rule with no conditions never matches
            return False, ""

        matched_conditions = []
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False, ""
            matched_conditions.append(
                f"{condition.field} {condition.operator.value} {condition.value}"
            )

        reason = f"Rule '{rule.name}': {'; '.join(matched_conditions)}"
        return True, reason

    def _evaluate_condition(
        self, condition: PolicyCondition, context: CheckpointContext
    ) -> bool:
        """Evaluate a single condition against the context."""
        field_value = context.get_field(condition.field)
        expected = condition.value
        op = condition.operator

        try:
            if op == ConditionOperator.EQUALS:
                return self._compare_equals(field_value, expected)

            elif op == ConditionOperator.NOT_EQUALS:
                return not self._compare_equals(field_value, expected)

            elif op == ConditionOperator.CONTAINS:
                return self._contains(field_value, expected)

            elif op == ConditionOperator.NOT_CONTAINS:
                return not self._contains(field_value, expected)

            elif op == ConditionOperator.IN:
                return self._in_list(field_value, expected)

            elif op == ConditionOperator.NOT_IN:
                return not self._in_list(field_value, expected)

            elif op == ConditionOperator.GREATER_THAN:
                return self._compare_numeric(field_value, expected, ">")

            elif op == ConditionOperator.LESS_THAN:
                return self._compare_numeric(field_value, expected, "<")

            elif op == ConditionOperator.GREATER_EQUAL:
                return self._compare_numeric(field_value, expected, ">=")

            elif op == ConditionOperator.LESS_EQUAL:
                return self._compare_numeric(field_value, expected, "<=")

            elif op == ConditionOperator.IS_TRUE:
                return bool(field_value) is True

            elif op == ConditionOperator.IS_FALSE:
                return bool(field_value) is False

            elif op == ConditionOperator.EXISTS:
                return field_value is not None

            elif op == ConditionOperator.NOT_EXISTS:
                return field_value is None

            elif op == ConditionOperator.MATCHES_REGEX:
                return self._matches_regex(field_value, expected)

            else:
                logger.warning(f"Unknown operator: {op}")
                return False

        except Exception as e:
            logger.warning(f"Error evaluating condition {condition.field}: {e}")
            return False

    def _compare_equals(self, actual: Any, expected: Any) -> bool:
        """Compare for equality with type coercion."""
        if actual is None:
            return expected is None

        # String comparison (case-insensitive)
        if isinstance(actual, str) and isinstance(expected, str):
            return actual.lower() == expected.lower()

        return actual == expected

    def _contains(self, actual: Any, expected: Any) -> bool:
        """Check if actual contains expected."""
        if actual is None:
            return False

        if isinstance(actual, str):
            return str(expected).lower() in actual.lower()

        if isinstance(actual, (list, tuple)):
            return expected in actual

        return False

    def _in_list(self, actual: Any, expected: Any) -> bool:
        """Check if actual is in expected list."""
        if not isinstance(expected, (list, tuple)):
            return False
        return actual in expected

    def _compare_numeric(self, actual: Any, expected: Any, op: str) -> bool:
        """Compare numeric values."""
        try:
            actual_num = float(actual) if actual is not None else 0
            expected_num = float(expected) if expected is not None else 0

            if op == ">":
                return actual_num > expected_num
            elif op == "<":
                return actual_num < expected_num
            elif op == ">=":
                return actual_num >= expected_num
            elif op == "<=":
                return actual_num <= expected_num
            return False
        except (ValueError, TypeError):
            return False

    def _matches_regex(self, actual: Any, pattern: Any) -> bool:
        """Check if actual matches regex pattern."""
        if actual is None or pattern is None:
            return False
        try:
            return bool(re.search(str(pattern), str(actual), re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False

    # =========================================================================
    # Context Extraction
    # =========================================================================

    @staticmethod
    def extract_context_from_checkpoint(
        checkpoint_data: dict,
        run_id: str,
    ) -> CheckpointContext:
        """
        Extract a CheckpointContext from raw checkpoint data.

        This is the main entry point for converting checkpoint data
        from the orchestrator into a policy-evaluable context.

        Args:
            checkpoint_data: Raw checkpoint dict from state file
            run_id: The run ID this checkpoint belongs to

        Returns:
            CheckpointContext ready for policy evaluation
        """
        # Basic fields
        checkpoint_id = checkpoint_data.get("checkpoint_id", str(uuid4()))
        checkpoint_type = checkpoint_data.get("reason", "unknown")
        severity = checkpoint_data.get("severity", "warning")
        description = checkpoint_data.get("description", "")

        # Extract risk indicators
        has_delete = PolicyEngine._detect_delete(checkpoint_data)
        has_migration = PolicyEngine._detect_migration(checkpoint_data)
        has_force_push = PolicyEngine._detect_force_push(checkpoint_data)
        has_destructive_git = PolicyEngine._detect_destructive_git(checkpoint_data)

        # File analysis
        affected_files = checkpoint_data.get("affected_files", [])
        if isinstance(affected_files, str):
            affected_files = [affected_files]
        affected_files_count = len(affected_files)

        # Git analysis
        git_diff_size = checkpoint_data.get("git_diff_lines", 0)
        if not git_diff_size:
            # Try to calculate from diff
            diff = checkpoint_data.get("git_diff", "")
            if diff:
                git_diff_size = len(diff.split("\n"))

        # Command analysis
        command_name = checkpoint_data.get("command", "")
        if not command_name:
            # Try to extract from description
            if "command" in description.lower():
                parts = description.split(":")
                if len(parts) > 1:
                    command_name = parts[1].strip().split()[0] if parts[1].strip() else ""

        # Project type
        project_type = checkpoint_data.get("project_type", "generic")

        # Iteration and failure tracking
        iteration = checkpoint_data.get("iteration", 0)
        failure_count = checkpoint_data.get("failure_count", 0)

        # Extra context
        extra = {}
        for key in ["tool", "model", "tokens_used", "cost_estimate", "api_calls"]:
            if key in checkpoint_data:
                extra[key] = checkpoint_data[key]

        return CheckpointContext(
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            checkpoint_type=checkpoint_type,
            severity=severity,
            description=description,
            has_delete=has_delete,
            has_migration=has_migration,
            has_force_push=has_force_push,
            has_destructive_git=has_destructive_git,
            affected_files_count=affected_files_count,
            affected_files=affected_files,
            git_diff_size=git_diff_size,
            command_name=command_name,
            project_type=project_type,
            iteration=iteration,
            failure_count=failure_count,
            extra=extra,
        )

    @staticmethod
    def _detect_delete(checkpoint_data: dict) -> bool:
        """Detect if checkpoint involves delete operations."""
        # Check description
        description = checkpoint_data.get("description", "").lower()
        if any(word in description for word in ["delete", "remove", "rm ", "unlink", "drop"]):
            return True

        # Check affected files for deletion markers
        affected = checkpoint_data.get("affected_files", [])
        if isinstance(affected, dict):
            if affected.get("deleted"):
                return True

        # Check git diff for deletions
        diff = checkpoint_data.get("git_diff", "")
        if diff:
            deleted_lines = sum(1 for line in diff.split("\n") if line.startswith("-") and not line.startswith("---"))
            added_lines = sum(1 for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++"))
            # Significant deletion if more than 50% of changes are deletions
            if deleted_lines > added_lines * 2 and deleted_lines > 10:
                return True

        # Check command
        command = checkpoint_data.get("command", "").lower()
        if any(word in command for word in ["rm ", "del ", "delete", "drop"]):
            return True

        return False

    @staticmethod
    def _detect_migration(checkpoint_data: dict) -> bool:
        """Detect if checkpoint involves database migration."""
        description = checkpoint_data.get("description", "").lower()
        if "migration" in description or "migrate" in description:
            return True

        # Check affected files for migration patterns
        affected = checkpoint_data.get("affected_files", [])
        if isinstance(affected, list):
            for f in affected:
                if isinstance(f, str):
                    if "migration" in f.lower() or "/migrations/" in f.lower():
                        return True

        # Check command
        command = checkpoint_data.get("command", "").lower()
        if "migrate" in command or "migration" in command:
            return True

        return False

    @staticmethod
    def _detect_force_push(checkpoint_data: dict) -> bool:
        """Detect if checkpoint involves git force push."""
        description = checkpoint_data.get("description", "").lower()
        if "force push" in description or "force-push" in description:
            return True

        command = checkpoint_data.get("command", "").lower()
        if "push" in command and ("--force" in command or "-f" in command):
            return True

        return False

    @staticmethod
    def _detect_destructive_git(checkpoint_data: dict) -> bool:
        """Detect destructive git operations."""
        # Check checkpoint type
        if checkpoint_data.get("reason") == "git_destructive":
            return True

        command = checkpoint_data.get("command", "").lower()
        destructive_patterns = [
            "git reset --hard",
            "git clean -f",
            "git checkout .",
            "git restore .",
            "git push --force",
            "git push -f",
            "git branch -D",
            "git rebase",
        ]
        for pattern in destructive_patterns:
            if pattern in command:
                return True

        description = checkpoint_data.get("description", "").lower()
        if "destructive" in description and "git" in description:
            return True

        return False

    # =========================================================================
    # Override Support
    # =========================================================================

    def record_override(
        self,
        decision_id: str,
        override_decision: PolicyAction,
        reason: str = "",
    ) -> Optional[PolicyDecision]:
        """
        Record a human override of a policy decision.

        Args:
            decision_id: The original decision ID
            override_decision: The new decision
            reason: Reason for the override

        Returns:
            Updated PolicyDecision or None if not found
        """
        return self.store.record_override(decision_id, override_decision, reason)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self):
        """Get policy statistics."""
        return self.store.get_stats()

    def get_decisions(
        self,
        limit: int = 100,
        run_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> List[PolicyDecision]:
        """Get decision history."""
        return self.store.get_decisions(limit=limit, run_id=run_id, rule_id=rule_id)

    # =========================================================================
    # Rule Management (delegated to store)
    # =========================================================================

    def get_rules(self) -> List[PolicyRule]:
        """Get all rules."""
        return self.store.get_all_rules()

    def get_enabled_rules(self) -> List[PolicyRule]:
        """Get enabled rules."""
        return self.store.get_enabled_rules()

    def create_rule(self, rule: PolicyRule) -> PolicyRule:
        """Create a new rule."""
        return self.store.create_rule(rule)

    def update_rule(self, rule: PolicyRule) -> PolicyRule:
        """Update a rule."""
        return self.store.update_rule(rule)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        return self.store.delete_rule(rule_id)

    def enable_rule(self, rule_id: str, enabled: bool = True) -> Optional[PolicyRule]:
        """Enable or disable a rule."""
        return self.store.enable_rule(rule_id, enabled)


def get_policy_engine(workspace_path: Path) -> PolicyEngine:
    """Factory function to create a PolicyEngine."""
    return PolicyEngine(workspace_path)
