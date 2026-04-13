"""Tests for the policy engine module."""

import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from orchestrator.policy_models import (
    PolicyAction,
    PolicyRule,
    PolicyDecision,
    PolicyCondition,
    ConditionOperator,
    PolicyStats,
    CheckpointContext,
    DEFAULT_RULES,
)
from orchestrator.policy_store import PolicyStore
from orchestrator.policy_engine import PolicyEngine


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def policy_store(temp_workspace):
    """Create a policy store with temporary workspace."""
    return PolicyStore(temp_workspace)


@pytest.fixture
def policy_engine(temp_workspace):
    """Create a policy engine with temporary workspace."""
    return PolicyEngine(temp_workspace)


@pytest.fixture
def sample_context():
    """Create a sample checkpoint context."""
    return CheckpointContext(
        checkpoint_id=str(uuid4()),
        run_id=str(uuid4()),
        checkpoint_type="manual_request",
        severity="info",
        description="Test checkpoint",
        has_delete=False,
        has_migration=False,
        has_force_push=False,
        has_destructive_git=False,
        affected_files_count=3,
        affected_files=["file1.py", "file2.py", "file3.py"],
        git_diff_size=50,
    )


@pytest.fixture
def critical_context():
    """Create a critical checkpoint context."""
    return CheckpointContext(
        checkpoint_id=str(uuid4()),
        run_id=str(uuid4()),
        checkpoint_type="git_destructive",
        severity="critical",
        description="Critical checkpoint",
        has_delete=True,
        has_migration=False,
        has_force_push=True,
        has_destructive_git=True,
        affected_files_count=10,
    )


# =============================================================================
# PolicyCondition Tests
# =============================================================================


class TestPolicyCondition:
    def test_to_dict(self):
        condition = PolicyCondition(
            field="checkpoint.severity",
            operator=ConditionOperator.EQUALS,
            value="critical",
        )
        d = condition.to_dict()
        assert d["field"] == "checkpoint.severity"
        assert d["operator"] == "equals"
        assert d["value"] == "critical"

    def test_from_dict(self):
        data = {
            "field": "has_delete",
            "operator": "is_true",
            "value": None,
        }
        condition = PolicyCondition.from_dict(data)
        assert condition.field == "has_delete"
        assert condition.operator == ConditionOperator.IS_TRUE
        assert condition.value is None


# =============================================================================
# PolicyRule Tests
# =============================================================================


class TestPolicyRule:
    def test_to_dict(self):
        rule = PolicyRule(
            id="test_rule",
            name="Test Rule",
            description="Test description",
            conditions=[
                PolicyCondition(
                    field="checkpoint.severity",
                    operator=ConditionOperator.EQUALS,
                    value="critical",
                )
            ],
            action=PolicyAction.REQUIRE_HUMAN,
            priority=10,
            enabled=True,
            builtin=False,
        )
        d = rule.to_dict()
        assert d["id"] == "test_rule"
        assert d["name"] == "Test Rule"
        assert d["action"] == "require_human"
        assert len(d["conditions"]) == 1

    def test_from_dict(self):
        data = {
            "id": "test_rule",
            "name": "Test Rule",
            "description": "Test",
            "conditions": [
                {"field": "has_delete", "operator": "is_true"}
            ],
            "action": "reject",
            "priority": 5,
        }
        rule = PolicyRule.from_dict(data)
        assert rule.id == "test_rule"
        assert rule.action == PolicyAction.REJECT
        assert rule.priority == 5
        assert len(rule.conditions) == 1


# =============================================================================
# CheckpointContext Tests
# =============================================================================


class TestCheckpointContext:
    def test_get_field_direct(self, sample_context):
        assert sample_context.get_field("has_delete") is False
        assert sample_context.get_field("affected_files_count") == 3

    def test_get_field_checkpoint_nested(self, sample_context):
        assert sample_context.get_field("checkpoint.type") == "manual_request"
        assert sample_context.get_field("checkpoint.severity") == "info"

    def test_get_field_extra(self, sample_context):
        sample_context.extra["custom_field"] = "custom_value"
        assert sample_context.get_field("extra.custom_field") == "custom_value"

    def test_to_dict(self, sample_context):
        d = sample_context.to_dict()
        assert d["checkpoint_id"] == sample_context.checkpoint_id
        assert d["has_delete"] is False
        assert d["affected_files_count"] == 3


# =============================================================================
# PolicyStore Tests
# =============================================================================


class TestPolicyStore:
    def test_init_loads_defaults(self, policy_store):
        rules = policy_store.get_all_rules()
        assert len(rules) > 0
        # Check for a known default rule
        rule_ids = [r.id for r in rules]
        assert "builtin_require_human_critical" in rule_ids

    def test_create_rule(self, policy_store):
        rule = PolicyRule(
            id="custom_rule_1",
            name="Custom Rule",
            description="Test",
            conditions=[
                PolicyCondition(
                    field="affected_files_count",
                    operator=ConditionOperator.GREATER_THAN,
                    value=10,
                )
            ],
            action=PolicyAction.REQUIRE_HUMAN,
        )
        created = policy_store.create_rule(rule)
        assert created.id == "custom_rule_1"
        assert policy_store.get_rule("custom_rule_1") is not None

    def test_create_duplicate_rule_fails(self, policy_store):
        rule = PolicyRule(
            id="dup_rule",
            name="Dup Rule",
            description="",
            conditions=[],
            action=PolicyAction.APPROVE,
        )
        policy_store.create_rule(rule)
        with pytest.raises(ValueError):
            policy_store.create_rule(rule)

    def test_update_rule(self, policy_store):
        rule = PolicyRule(
            id="update_rule",
            name="Original Name",
            description="",
            conditions=[],
            action=PolicyAction.APPROVE,
        )
        policy_store.create_rule(rule)

        rule.name = "Updated Name"
        updated = policy_store.update_rule(rule)
        assert updated.name == "Updated Name"

    def test_delete_rule(self, policy_store):
        rule = PolicyRule(
            id="delete_rule",
            name="Delete Me",
            description="",
            conditions=[],
            action=PolicyAction.APPROVE,
        )
        policy_store.create_rule(rule)
        assert policy_store.delete_rule("delete_rule") is True
        assert policy_store.get_rule("delete_rule") is None

    def test_delete_builtin_fails(self, policy_store):
        with pytest.raises(ValueError):
            policy_store.delete_rule("builtin_require_human_critical")

    def test_enable_disable_rule(self, policy_store):
        rule = policy_store.get_rule("builtin_require_human_critical")
        assert rule.enabled is True

        policy_store.enable_rule("builtin_require_human_critical", False)
        rule = policy_store.get_rule("builtin_require_human_critical")
        assert rule.enabled is False

    def test_get_enabled_rules(self, policy_store):
        # Disable one rule
        policy_store.enable_rule("builtin_require_human_critical", False)
        enabled = policy_store.get_enabled_rules()
        rule_ids = [r.id for r in enabled]
        assert "builtin_require_human_critical" not in rule_ids

    def test_save_and_get_decision(self, policy_store, sample_context):
        decision = PolicyDecision(
            decision_id=str(uuid4()),
            checkpoint_id=sample_context.checkpoint_id,
            run_id=sample_context.run_id,
            decision=PolicyAction.APPROVE,
            rule_id="test_rule",
            rule_name="Test Rule",
            reason="Test reason",
        )
        policy_store.save_decision(decision)

        decisions = policy_store.get_decisions(limit=10)
        assert len(decisions) >= 1
        assert decisions[0].decision_id == decision.decision_id

    def test_get_stats(self, policy_store, sample_context):
        # Save some decisions
        for i in range(3):
            decision = PolicyDecision(
                decision_id=str(uuid4()),
                checkpoint_id=str(uuid4()),
                run_id=sample_context.run_id,
                decision=PolicyAction.APPROVE,
            )
            policy_store.save_decision(decision)

        stats = policy_store.get_stats()
        assert stats.total_decisions >= 3
        assert stats.auto_approved >= 3

    def test_record_override(self, policy_store, sample_context):
        decision = PolicyDecision(
            decision_id=str(uuid4()),
            checkpoint_id=sample_context.checkpoint_id,
            run_id=sample_context.run_id,
            decision=PolicyAction.REQUIRE_HUMAN,
        )
        policy_store.save_decision(decision)

        updated = policy_store.record_override(
            decision.decision_id,
            PolicyAction.APPROVE,
            "Override reason",
        )
        assert updated is not None
        assert updated.was_overridden is True
        assert updated.override_decision == PolicyAction.APPROVE


# =============================================================================
# PolicyEngine Tests
# =============================================================================


class TestPolicyEngine:
    def test_evaluate_critical_requires_human(self, policy_engine, critical_context):
        decision = policy_engine.evaluate(critical_context)
        assert decision.decision == PolicyAction.REQUIRE_HUMAN
        assert decision.rule_id is not None

    def test_evaluate_no_match_requires_human(self, policy_engine, sample_context):
        # Disable all rules
        for rule in policy_engine.get_rules():
            policy_engine.enable_rule(rule.id, False)

        decision = policy_engine.evaluate(sample_context)
        assert decision.decision == PolicyAction.REQUIRE_HUMAN
        assert decision.rule_id is None

    def test_evaluate_delete_requires_human(self, policy_engine):
        context = CheckpointContext(
            checkpoint_id=str(uuid4()),
            run_id=str(uuid4()),
            checkpoint_type="file_operation",
            severity="warning",
            description="Delete files",
            has_delete=True,
        )
        decision = policy_engine.evaluate(context)
        assert decision.decision == PolicyAction.REQUIRE_HUMAN

    def test_evaluate_migration_requires_human(self, policy_engine):
        context = CheckpointContext(
            checkpoint_id=str(uuid4()),
            run_id=str(uuid4()),
            checkpoint_type="database_change",
            severity="warning",
            description="Run migration",
            has_migration=True,
        )
        decision = policy_engine.evaluate(context)
        assert decision.decision == PolicyAction.REQUIRE_HUMAN

    def test_custom_rule_approve(self, policy_engine):
        # Create a custom approve rule
        rule = PolicyRule(
            id="custom_approve_test",
            name="Auto-approve test files",
            description="",
            conditions=[
                PolicyCondition(
                    field="affected_files_count",
                    operator=ConditionOperator.LESS_THAN,
                    value=2,
                )
            ],
            action=PolicyAction.APPROVE,
            priority=1,  # High priority
            enabled=True,
        )
        policy_engine.create_rule(rule)

        context = CheckpointContext(
            checkpoint_id=str(uuid4()),
            run_id=str(uuid4()),
            checkpoint_type="file_change",
            severity="info",
            description="Small change",
            affected_files_count=1,
        )
        decision = policy_engine.evaluate(context)
        assert decision.decision == PolicyAction.APPROVE
        assert decision.rule_id == "custom_approve_test"

    def test_priority_ordering(self, policy_engine):
        # Create two rules that could match
        rule1 = PolicyRule(
            id="low_priority",
            name="Low Priority",
            description="",
            conditions=[
                PolicyCondition(
                    field="checkpoint.severity",
                    operator=ConditionOperator.EQUALS,
                    value="info",
                )
            ],
            action=PolicyAction.APPROVE,
            priority=100,
            enabled=True,
        )
        rule2 = PolicyRule(
            id="high_priority",
            name="High Priority",
            description="",
            conditions=[
                PolicyCondition(
                    field="checkpoint.severity",
                    operator=ConditionOperator.EQUALS,
                    value="info",
                )
            ],
            action=PolicyAction.REJECT,
            priority=1,
            enabled=True,
        )
        policy_engine.create_rule(rule1)
        policy_engine.create_rule(rule2)

        context = CheckpointContext(
            checkpoint_id=str(uuid4()),
            run_id=str(uuid4()),
            checkpoint_type="test",
            severity="info",
            description="Test",
        )
        decision = policy_engine.evaluate(context)
        # Higher priority (lower number) should win
        assert decision.rule_id == "high_priority"
        assert decision.decision == PolicyAction.REJECT


# =============================================================================
# Condition Evaluation Tests
# =============================================================================


class TestConditionEvaluation:
    def test_equals_string(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="checkpoint.type",
            operator=ConditionOperator.EQUALS,
            value="manual_request",
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_equals_case_insensitive(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="checkpoint.severity",
            operator=ConditionOperator.EQUALS,
            value="INFO",
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_not_equals(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="checkpoint.severity",
            operator=ConditionOperator.NOT_EQUALS,
            value="critical",
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_contains(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="description",
            operator=ConditionOperator.CONTAINS,
            value="checkpoint",
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_greater_than(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="affected_files_count",
            operator=ConditionOperator.GREATER_THAN,
            value=2,
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_less_than(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="git_diff_size",
            operator=ConditionOperator.LESS_THAN,
            value=100,
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_is_true(self, policy_engine, critical_context):
        condition = PolicyCondition(
            field="has_delete",
            operator=ConditionOperator.IS_TRUE,
        )
        result = policy_engine._evaluate_condition(condition, critical_context)
        assert result is True

    def test_is_false(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="has_delete",
            operator=ConditionOperator.IS_FALSE,
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_exists(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="checkpoint_id",
            operator=ConditionOperator.EXISTS,
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_not_exists(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="nonexistent_field",
            operator=ConditionOperator.NOT_EXISTS,
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_in_list(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="checkpoint.severity",
            operator=ConditionOperator.IN,
            value=["info", "warning"],
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True

    def test_matches_regex(self, policy_engine, sample_context):
        condition = PolicyCondition(
            field="description",
            operator=ConditionOperator.MATCHES_REGEX,
            value="^Test.*",
        )
        result = policy_engine._evaluate_condition(condition, sample_context)
        assert result is True


# =============================================================================
# Context Extraction Tests
# =============================================================================


class TestContextExtraction:
    def test_extract_basic_fields(self):
        checkpoint_data = {
            "checkpoint_id": "cp123",
            "reason": "manual_request",
            "severity": "warning",
            "description": "Test checkpoint",
            "affected_files": ["a.py", "b.py"],
        }
        context = PolicyEngine.extract_context_from_checkpoint(checkpoint_data, "run123")
        assert context.checkpoint_id == "cp123"
        assert context.checkpoint_type == "manual_request"
        assert context.severity == "warning"
        assert context.affected_files_count == 2

    def test_detect_delete(self):
        checkpoint_data = {
            "checkpoint_id": "cp123",
            "description": "Delete unused files",
            "reason": "file_operation",
        }
        context = PolicyEngine.extract_context_from_checkpoint(checkpoint_data, "run123")
        assert context.has_delete is True

    def test_detect_migration(self):
        checkpoint_data = {
            "checkpoint_id": "cp123",
            "description": "Run database migration",
            "reason": "database",
            "affected_files": ["migrations/001_add_table.py"],
        }
        context = PolicyEngine.extract_context_from_checkpoint(checkpoint_data, "run123")
        assert context.has_migration is True

    def test_detect_force_push(self):
        checkpoint_data = {
            "checkpoint_id": "cp123",
            "description": "Push changes",
            "command": "git push --force origin main",
            "reason": "git",
        }
        context = PolicyEngine.extract_context_from_checkpoint(checkpoint_data, "run123")
        assert context.has_force_push is True

    def test_detect_destructive_git(self):
        checkpoint_data = {
            "checkpoint_id": "cp123",
            "reason": "git_destructive",
            "command": "git reset --hard HEAD~1",
        }
        context = PolicyEngine.extract_context_from_checkpoint(checkpoint_data, "run123")
        assert context.has_destructive_git is True


# =============================================================================
# PolicyStats Tests
# =============================================================================


class TestPolicyStats:
    def test_to_dict(self):
        stats = PolicyStats(
            total_decisions=100,
            auto_approved=50,
            auto_rejected=10,
            required_human=40,
            human_overrides=5,
            override_rate=5.0,
        )
        d = stats.to_dict()
        assert d["total_decisions"] == 100
        assert d["auto_approved"] == 50
        assert d["override_rate"] == 5.0

    def test_from_dict(self):
        data = {
            "total_decisions": 200,
            "auto_approved": 100,
            "decisions_by_rule": {"rule1": 50, "rule2": 150},
        }
        stats = PolicyStats.from_dict(data)
        assert stats.total_decisions == 200
        assert stats.decisions_by_rule["rule1"] == 50


# =============================================================================
# Default Rules Tests
# =============================================================================


class TestDefaultRules:
    def test_default_rules_exist(self):
        assert len(DEFAULT_RULES) > 0

    def test_default_rules_have_required_fields(self):
        for rule_data in DEFAULT_RULES:
            assert "id" in rule_data
            assert "name" in rule_data
            assert "action" in rule_data
            assert "conditions" in rule_data

    def test_critical_rule_exists(self):
        rule_ids = [r["id"] for r in DEFAULT_RULES]
        assert "builtin_require_human_critical" in rule_ids

    def test_delete_rule_exists(self):
        rule_ids = [r["id"] for r in DEFAULT_RULES]
        assert "builtin_require_human_delete" in rule_ids

    def test_migration_rule_exists(self):
        rule_ids = [r["id"] for r in DEFAULT_RULES]
        assert "builtin_require_human_migration" in rule_ids
