"""Feedback persistence helpers for end-user reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from orchestrator.observability import get_observability
from orchestrator.paths import OrchestratorPaths
from orchestrator.version import VersionInfo


VALID_FEEDBACK_TYPES = {"bug", "sugestão", "dúvida"}


@dataclass(frozen=True)
class FeedbackEntry:
    feedback_type: str
    description: str
    timestamp: str
    app_version: str
    diagnostic_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tipo": self.feedback_type,
            "descricao": self.description,
            "timestamp": self.timestamp,
            "versao_app": self.app_version,
            "diagnostico": self.diagnostic_path,
        }


class FeedbackStore:
    """Create and persist feedback reports under the workspace."""

    def __init__(self, paths: OrchestratorPaths, version_info: VersionInfo):
        self.paths = paths
        self.version_info = version_info

    def build_feedback(
        self,
        *,
        feedback_type: str,
        description: str,
        timestamp: str,
        diagnostic_path: Optional[Path] = None,
    ) -> FeedbackEntry:
        normalized_type = feedback_type.strip().lower()
        if normalized_type not in VALID_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback type: {feedback_type}")

        text = description.strip()
        if not text:
            raise ValueError("Feedback description is required")

        return FeedbackEntry(
            feedback_type=normalized_type,
            description=text,
            timestamp=timestamp,
            app_version=str(self.version_info.version),
            diagnostic_path=str(diagnostic_path) if diagnostic_path else None,
        )

    def save_feedback(self, entry: FeedbackEntry) -> Path:
        self.paths.feedback_dir.mkdir(parents=True, exist_ok=True)
        safe_timestamp = entry.timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
        output_path = self.paths.feedback_dir / f"feedback_{safe_timestamp}.json"
        output_path.write_text(
            json.dumps(entry.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        get_observability().record_app_event(
            event="feedback_saved",
            message="User feedback saved locally",
            context={"feedback_path": str(output_path), "feedback_type": entry.feedback_type},
        )
        return output_path