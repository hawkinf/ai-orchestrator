"""Policy store for persisting rules and decision history.

Manages storage of policy rules and decision history in the workspace.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from .policy_models import (
    PolicyAction,
    PolicyDecision,
    PolicyRule,
    PolicyStats,
    DEFAULT_RULES,
)

logger = logging.getLogger("ai_orchestrator.policy_store")


class PolicyStore:
    """
    Persistent storage for policy rules and decisions.

    Storage structure:
        workspace/policies/
            rules.json          - Policy rules
            history.json        - Decision history
            stats.json          - Aggregated statistics
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.policies_dir = workspace_path / "policies"
        self._rules_cache: Dict[str, PolicyRule] = {}
        self._ensure_dirs()
        self._load_rules()

    def _ensure_dirs(self):
        """Ensure policy directories exist."""
        self.policies_dir.mkdir(parents=True, exist_ok=True)

    def _rules_file(self) -> Path:
        """Get path to rules file."""
        return self.policies_dir / "rules.json"

    def _history_file(self) -> Path:
        """Get path to history file."""
        return self.policies_dir / "history.json"

    def _stats_file(self) -> Path:
        """Get path to stats file."""
        return self.policies_dir / "stats.json"

    # =========================================================================
    # Rules Management
    # =========================================================================

    def _load_rules(self):
        """Load rules from file or create defaults."""
        rules_file = self._rules_file()

        if rules_file.exists():
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for rule_data in data.get("rules", []):
                    rule = PolicyRule.from_dict(rule_data)
                    self._rules_cache[rule.id] = rule

                logger.info(f"Loaded {len(self._rules_cache)} policy rules")

            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error loading rules, using defaults: {e}")
                self._init_default_rules()
        else:
            self._init_default_rules()

    def _init_default_rules(self):
        """Initialize with default builtin rules."""
        self._rules_cache.clear()
        for rule_data in DEFAULT_RULES:
            rule = PolicyRule.from_dict(rule_data)
            self._rules_cache[rule.id] = rule
        self._save_rules()
        logger.info(f"Initialized {len(self._rules_cache)} default policy rules")

    def _save_rules(self):
        """Save rules to file."""
        rules_file = self._rules_file()
        data = {
            "updated_at": datetime.now().isoformat(),
            "rules": [rule.to_dict() for rule in self._rules_cache.values()],
        }
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_rules(self) -> List[PolicyRule]:
        """Get all policy rules sorted by priority."""
        rules = list(self._rules_cache.values())
        rules.sort(key=lambda r: r.priority)
        return rules

    def get_enabled_rules(self) -> List[PolicyRule]:
        """Get only enabled rules sorted by priority."""
        rules = [r for r in self._rules_cache.values() if r.enabled]
        rules.sort(key=lambda r: r.priority)
        return rules

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a specific rule by ID."""
        return self._rules_cache.get(rule_id)

    def create_rule(self, rule: PolicyRule) -> PolicyRule:
        """Create a new rule."""
        if rule.id in self._rules_cache:
            raise ValueError(f"Rule with ID '{rule.id}' already exists")

        rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        self._rules_cache[rule.id] = rule
        self._save_rules()
        logger.info(f"Created policy rule: {rule.id}")
        return rule

    def update_rule(self, rule: PolicyRule) -> PolicyRule:
        """Update an existing rule."""
        if rule.id not in self._rules_cache:
            raise ValueError(f"Rule with ID '{rule.id}' not found")

        existing = self._rules_cache[rule.id]
        if existing.builtin and not rule.builtin:
            # Preserve builtin flag
            rule.builtin = True

        rule.updated_at = datetime.now()
        self._rules_cache[rule.id] = rule
        self._save_rules()
        logger.info(f"Updated policy rule: {rule.id}")
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule (cannot delete builtin rules)."""
        rule = self._rules_cache.get(rule_id)
        if not rule:
            return False

        if rule.builtin:
            raise ValueError(f"Cannot delete builtin rule: {rule_id}")

        del self._rules_cache[rule_id]
        self._save_rules()
        logger.info(f"Deleted policy rule: {rule_id}")
        return True

    def enable_rule(self, rule_id: str, enabled: bool = True) -> Optional[PolicyRule]:
        """Enable or disable a rule."""
        rule = self._rules_cache.get(rule_id)
        if not rule:
            return None

        rule.enabled = enabled
        rule.updated_at = datetime.now()
        self._save_rules()
        logger.info(f"{'Enabled' if enabled else 'Disabled'} policy rule: {rule_id}")
        return rule

    def update_priority(self, rule_id: str, priority: int) -> Optional[PolicyRule]:
        """Update rule priority."""
        rule = self._rules_cache.get(rule_id)
        if not rule:
            return None

        rule.priority = priority
        rule.updated_at = datetime.now()
        self._save_rules()
        logger.info(f"Updated priority for rule {rule_id}: {priority}")
        return rule

    def reset_to_defaults(self):
        """Reset rules to defaults (keeps custom rules disabled)."""
        # Mark all custom rules as disabled instead of deleting
        for rule in self._rules_cache.values():
            if not rule.builtin:
                rule.enabled = False

        # Restore default builtin rules
        for rule_data in DEFAULT_RULES:
            default_rule = PolicyRule.from_dict(rule_data)
            if default_rule.id in self._rules_cache:
                existing = self._rules_cache[default_rule.id]
                existing.enabled = default_rule.enabled
                existing.priority = default_rule.priority
            else:
                self._rules_cache[default_rule.id] = default_rule

        self._save_rules()
        logger.info("Reset policy rules to defaults")

    # =========================================================================
    # Decision History
    # =========================================================================

    def save_decision(self, decision: PolicyDecision):
        """Save a policy decision to history."""
        history_file = self._history_file()
        history: List[dict] = []

        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                history = data.get("decisions", [])
            except (json.JSONDecodeError, Exception):
                pass

        # Add new decision
        history.append(decision.to_dict())

        # Keep only last 1000 decisions
        if len(history) > 1000:
            history = history[-1000:]

        data = {
            "updated_at": datetime.now().isoformat(),
            "decisions": history,
        }

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Update stats
        self._update_stats(decision)

        logger.debug(f"Saved policy decision: {decision.decision_id}")

    def get_decisions(
        self,
        limit: int = 100,
        run_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> List[PolicyDecision]:
        """Get decision history."""
        history_file = self._history_file()
        if not history_file.exists():
            return []

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            decisions = []
            for decision_data in data.get("decisions", []):
                decision = PolicyDecision.from_dict(decision_data)

                # Apply filters
                if run_id and decision.run_id != run_id:
                    continue
                if rule_id and decision.rule_id != rule_id:
                    continue

                decisions.append(decision)

            # Return most recent first
            decisions.reverse()
            return decisions[:limit]

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error loading decision history: {e}")
            return []

    def record_override(
        self,
        decision_id: str,
        override_decision: PolicyAction,
        reason: str = "",
    ) -> Optional[PolicyDecision]:
        """Record a human override of a policy decision."""
        history_file = self._history_file()
        if not history_file.exists():
            return None

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            decisions = data.get("decisions", [])
            updated_decision = None

            for i, decision_data in enumerate(decisions):
                if decision_data.get("decision_id") == decision_id:
                    decisions[i]["was_overridden"] = True
                    decisions[i]["override_decision"] = override_decision.value
                    decisions[i]["override_reason"] = reason
                    decisions[i]["override_timestamp"] = datetime.now().isoformat()
                    updated_decision = PolicyDecision.from_dict(decisions[i])
                    break

            if updated_decision:
                data["decisions"] = decisions
                data["updated_at"] = datetime.now().isoformat()

                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Update stats
                self._increment_overrides()

                logger.info(f"Recorded override for decision: {decision_id}")

            return updated_decision

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error recording override: {e}")
            return None

    # =========================================================================
    # Statistics
    # =========================================================================

    def _update_stats(self, decision: PolicyDecision):
        """Update statistics with a new decision."""
        stats = self.get_stats()

        stats.total_decisions += 1
        stats.last_decision_at = decision.timestamp

        if decision.decision == PolicyAction.APPROVE:
            stats.auto_approved += 1
        elif decision.decision == PolicyAction.REJECT:
            stats.auto_rejected += 1
        elif decision.decision == PolicyAction.REQUIRE_HUMAN:
            stats.required_human += 1

        if decision.rule_id:
            stats.decisions_by_rule[decision.rule_id] = (
                stats.decisions_by_rule.get(decision.rule_id, 0) + 1
            )

        # Calculate override rate
        if stats.total_decisions > 0:
            stats.override_rate = (stats.human_overrides / stats.total_decisions) * 100

        self._save_stats(stats)

    def _increment_overrides(self):
        """Increment override count in stats."""
        stats = self.get_stats()
        stats.human_overrides += 1

        if stats.total_decisions > 0:
            stats.override_rate = (stats.human_overrides / stats.total_decisions) * 100

        self._save_stats(stats)

    def get_stats(self) -> PolicyStats:
        """Get policy statistics."""
        stats_file = self._stats_file()
        if not stats_file.exists():
            return PolicyStats()

        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PolicyStats.from_dict(data)
        except (json.JSONDecodeError, Exception):
            return PolicyStats()

    def _save_stats(self, stats: PolicyStats):
        """Save statistics to file."""
        stats_file = self._stats_file()
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, indent=2, ensure_ascii=False)

    def reset_stats(self):
        """Reset statistics."""
        self._save_stats(PolicyStats())
        logger.info("Reset policy statistics")

    # =========================================================================
    # Import/Export
    # =========================================================================

    def export_rules(self, output_path: Path) -> Path:
        """Export rules to a JSON file."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "rules": [rule.to_dict() for rule in self.get_all_rules() if not rule.builtin],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(data['rules'])} rules to: {output_path}")
        return output_path

    def import_rules(self, input_path: Path) -> int:
        """Import rules from a JSON file."""
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported = 0
        for rule_data in data.get("rules", []):
            rule = PolicyRule.from_dict(rule_data)
            rule.builtin = False  # Imported rules are never builtin

            # Generate new ID if exists
            if rule.id in self._rules_cache:
                rule.id = f"{rule.id}_{uuid4().hex[:8]}"

            self._rules_cache[rule.id] = rule
            imported += 1

        self._save_rules()
        logger.info(f"Imported {imported} rules from: {input_path}")
        return imported


def get_policy_store(workspace_path: Path) -> PolicyStore:
    """Factory function to create a PolicyStore."""
    return PolicyStore(workspace_path)
