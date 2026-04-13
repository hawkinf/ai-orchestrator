"""Policy engine models for auto-approval of checkpoints.

Defines rules, conditions, and decision models for the policy engine.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger("ai_orchestrator.policy_models")


class PolicyAction(Enum):
    """Actions that can be taken by a policy rule."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUIRE_HUMAN = "require_human"


class ConditionOperator(Enum):
    """Operators for condition evaluation."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MATCHES_REGEX = "matches_regex"


@dataclass
class PolicyCondition:
    """Single condition in a policy rule."""
    field: str  # e.g., "checkpoint.severity", "affected_files_count"
    operator: ConditionOperator
    value: Any = None  # Value to compare against (not needed for IS_TRUE, IS_FALSE)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyCondition":
        """Create from dictionary."""
        return cls(
            field=data["field"],
            operator=ConditionOperator(data["operator"]),
            value=data.get("value"),
        )


@dataclass
class PolicyRule:
    """A policy rule for checkpoint auto-approval."""
    id: str
    name: str
    description: str
    conditions: List[PolicyCondition]
    action: PolicyAction
    priority: int = 100  # Lower = higher priority
    enabled: bool = True
    builtin: bool = False  # Builtin rules cannot be deleted
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "builtin": self.builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyRule":
        """Create from dictionary."""
        conditions = [PolicyCondition.from_dict(c) for c in data.get("conditions", [])]
        created_at = None
        updated_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            conditions=conditions,
            action=PolicyAction(data["action"]),
            priority=data.get("priority", 100),
            enabled=data.get("enabled", True),
            builtin=data.get("builtin", False),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class PolicyDecision:
    """Record of a policy decision on a checkpoint."""
    decision_id: str
    checkpoint_id: str
    run_id: str
    decision: PolicyAction
    rule_id: Optional[str] = None  # None if no rule matched
    rule_name: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0
    reason: str = ""
    timestamp: Optional[datetime] = None
    was_overridden: bool = False
    override_decision: Optional[PolicyAction] = None
    override_reason: str = ""
    override_timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "decision": self.decision.value,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "was_overridden": self.was_overridden,
            "override_decision": self.override_decision.value if self.override_decision else None,
            "override_reason": self.override_reason,
            "override_timestamp": (
                self.override_timestamp.isoformat() if self.override_timestamp else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyDecision":
        """Create from dictionary."""
        timestamp = None
        override_timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
        if data.get("override_timestamp"):
            try:
                override_timestamp = datetime.fromisoformat(data["override_timestamp"])
            except (ValueError, TypeError):
                pass

        return cls(
            decision_id=data["decision_id"],
            checkpoint_id=data["checkpoint_id"],
            run_id=data["run_id"],
            decision=PolicyAction(data["decision"]),
            rule_id=data.get("rule_id"),
            rule_name=data.get("rule_name"),
            confidence=data.get("confidence", 1.0),
            reason=data.get("reason", ""),
            timestamp=timestamp,
            was_overridden=data.get("was_overridden", False),
            override_decision=(
                PolicyAction(data["override_decision"]) if data.get("override_decision") else None
            ),
            override_reason=data.get("override_reason", ""),
            override_timestamp=override_timestamp,
        )


@dataclass
class PolicyStats:
    """Statistics about policy decisions."""
    total_decisions: int = 0
    auto_approved: int = 0
    auto_rejected: int = 0
    required_human: int = 0
    human_overrides: int = 0
    override_rate: float = 0.0  # Percentage of decisions that were overridden
    decisions_by_rule: Dict[str, int] = field(default_factory=dict)
    last_decision_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_decisions": self.total_decisions,
            "auto_approved": self.auto_approved,
            "auto_rejected": self.auto_rejected,
            "required_human": self.required_human,
            "human_overrides": self.human_overrides,
            "override_rate": self.override_rate,
            "decisions_by_rule": self.decisions_by_rule,
            "last_decision_at": (
                self.last_decision_at.isoformat() if self.last_decision_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyStats":
        """Create from dictionary."""
        last_decision_at = None
        if data.get("last_decision_at"):
            try:
                last_decision_at = datetime.fromisoformat(data["last_decision_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            total_decisions=data.get("total_decisions", 0),
            auto_approved=data.get("auto_approved", 0),
            auto_rejected=data.get("auto_rejected", 0),
            required_human=data.get("required_human", 0),
            human_overrides=data.get("human_overrides", 0),
            override_rate=data.get("override_rate", 0.0),
            decisions_by_rule=data.get("decisions_by_rule", {}),
            last_decision_at=last_decision_at,
        )


@dataclass
class CheckpointContext:
    """Context data for evaluating checkpoint against policies."""
    checkpoint_id: str
    run_id: str
    checkpoint_type: str  # reason from CheckpointReason
    severity: str  # from CheckpointSeverity
    description: str

    # Derived/extracted data
    has_delete: bool = False
    has_migration: bool = False
    has_force_push: bool = False
    has_destructive_git: bool = False
    affected_files_count: int = 0
    affected_files: List[str] = field(default_factory=list)
    git_diff_size: int = 0  # Lines changed
    command_name: str = ""
    project_type: str = "generic"
    iteration: int = 0
    failure_count: int = 0

    # Additional context
    extra: Dict[str, Any] = field(default_factory=dict)

    def get_field(self, field_path: str) -> Any:
        """Get a field value by path (e.g., 'checkpoint.severity')."""
        parts = field_path.split(".")

        # Direct field access
        if len(parts) == 1:
            if hasattr(self, field_path):
                return getattr(self, field_path)
            return self.extra.get(field_path)

        # Nested access (e.g., checkpoint.severity)
        if parts[0] == "checkpoint":
            field_name = parts[1]
            field_map = {
                "type": self.checkpoint_type,
                "severity": self.severity,
                "description": self.description,
            }
            return field_map.get(field_name)

        # Extra data access
        if parts[0] == "extra":
            return self.extra.get(parts[1])

        # Default: try direct attribute
        return getattr(self, field_path, None)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "checkpoint_type": self.checkpoint_type,
            "severity": self.severity,
            "description": self.description,
            "has_delete": self.has_delete,
            "has_migration": self.has_migration,
            "has_force_push": self.has_force_push,
            "has_destructive_git": self.has_destructive_git,
            "affected_files_count": self.affected_files_count,
            "affected_files": self.affected_files,
            "git_diff_size": self.git_diff_size,
            "command_name": self.command_name,
            "project_type": self.project_type,
            "iteration": self.iteration,
            "failure_count": self.failure_count,
            "extra": self.extra,
        }


# Default builtin rules
DEFAULT_RULES: List[Dict] = [
    {
        "id": "builtin_require_human_critical",
        "name": "Require Human for Critical",
        "description": "Always require human approval for critical severity checkpoints",
        "conditions": [
            {"field": "checkpoint.severity", "operator": "equals", "value": "critical"},
        ],
        "action": "require_human",
        "priority": 10,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_require_human_delete",
        "name": "Require Human for Delete Operations",
        "description": "Require human approval when delete operations are detected",
        "conditions": [
            {"field": "has_delete", "operator": "is_true"},
        ],
        "action": "require_human",
        "priority": 15,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_require_human_migration",
        "name": "Require Human for Migrations",
        "description": "Require human approval for database migrations",
        "conditions": [
            {"field": "has_migration", "operator": "is_true"},
        ],
        "action": "require_human",
        "priority": 15,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_require_human_destructive_git",
        "name": "Require Human for Destructive Git",
        "description": "Require human approval for destructive git operations",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "git_destructive"},
        ],
        "action": "require_human",
        "priority": 10,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_require_human_infrastructure",
        "name": "Require Human for Infrastructure",
        "description": "Require human approval for infrastructure changes",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "infrastructure_change"},
        ],
        "action": "require_human",
        "priority": 10,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_require_human_architecture",
        "name": "Require Human for Architecture Rewrite",
        "description": "Require human approval for architecture rewrites",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "architecture_rewrite"},
        ],
        "action": "require_human",
        "priority": 10,
        "enabled": True,
        "builtin": True,
    },
    {
        "id": "builtin_reject_repeated_failures",
        "name": "Reject After Many Failures",
        "description": "Auto-reject if checkpoint is due to too many repeated failures",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "repeated_failures"},
            {"field": "failure_count", "operator": "greater_than", "value": 5},
        ],
        "action": "reject",
        "priority": 20,
        "enabled": False,  # Disabled by default - can be dangerous
        "builtin": True,
    },
    {
        "id": "builtin_approve_low_risk_manual",
        "name": "Auto-approve Low Risk Manual Requests",
        "description": "Auto-approve manual checkpoint requests with low risk",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "manual_request"},
            {"field": "checkpoint.severity", "operator": "equals", "value": "info"},
            {"field": "has_delete", "operator": "is_false"},
            {"field": "has_migration", "operator": "is_false"},
        ],
        "action": "approve",
        "priority": 50,
        "enabled": False,  # Disabled by default
        "builtin": True,
    },
    {
        "id": "builtin_approve_command_allowlist_small",
        "name": "Auto-approve Small Safe Commands",
        "description": "Auto-approve command checkpoints with small changes",
        "conditions": [
            {"field": "checkpoint.type", "operator": "equals", "value": "command_not_allowed"},
            {"field": "checkpoint.severity", "operator": "equals", "value": "warning"},
            {"field": "affected_files_count", "operator": "less_than", "value": 5},
            {"field": "has_delete", "operator": "is_false"},
        ],
        "action": "approve",
        "priority": 60,
        "enabled": False,  # Disabled by default
        "builtin": True,
    },
]
