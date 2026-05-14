"""AI Orchestrator - Local development assistant orchestration system."""

__version__ = "0.1.0"
__author__ = "Hawk Informatica"

from .config import OrchestratorConfig, load_config
from .models import TaskStatus, RunState, TaskRequest
from .paths import OrchestratorPaths
from .task_engine import TaskEngine
from .integrated_engine import IntegratedTaskEngine
from .openai_client import PlannerClient, ReviewerClient
from .claude_executor import ClaudeExecutor, MockClaudeExecutor
from .validation import ValidationRunner
from .checkpoint_index import CheckpointIndex, CheckpointSummary, CheckpointFilter
from .policy_engine import PolicyEngine, get_policy_engine
from .policy_models import (
    PolicyAction,
    PolicyRule,
    PolicyDecision,
    PolicyCondition,
    CheckpointContext,
)
from .policy_store import PolicyStore
from .replay_engine import ReplayEngine, get_replay_engine
from .replay_models import (
    ReplayMode,
    ReplayStage,
    ReplayStatus,
    ReplayConfig,
    ReplayResult,
    ReplayComparison,
    ComparisonResult,
)
from .version import (
    Version,
    VersionInfo,
    VersionManager,
    ReleaseChannel,
    get_version_manager,
    get_version,
    get_version_info,
)
from .updater import (
    Updater,
    UpdateConfig,
    UpdateStatus,
    UpdateResult,
    ReleaseInfo,
    get_updater,
    check_for_updates,
)
from .claude_detector import (
    ClaudeExecutorDetector,
    ClaudeDetectionResult,
    ClaudeStatus,
)
from .env_config_service import (
    EnvConfigService,
    EnvWriteResult,
    OpenAIKeyState,
    OpenAIKeyStatus,
)
from .ai_connection_service import AIConnectionService, OpenAIConnectionTester

__all__ = [
    "OrchestratorConfig",
    "load_config",
    "TaskStatus",
    "RunState",
    "TaskRequest",
    "OrchestratorPaths",
    "TaskEngine",
    "IntegratedTaskEngine",
    "PlannerClient",
    "ReviewerClient",
    "ClaudeExecutor",
    "MockClaudeExecutor",
    "ValidationRunner",
    "CheckpointIndex",
    "CheckpointSummary",
    "CheckpointFilter",
    "PolicyEngine",
    "get_policy_engine",
    "PolicyAction",
    "PolicyRule",
    "PolicyDecision",
    "PolicyCondition",
    "CheckpointContext",
    "PolicyStore",
    "ReplayEngine",
    "get_replay_engine",
    "ReplayMode",
    "ReplayStage",
    "ReplayStatus",
    "ReplayConfig",
    "ReplayResult",
    "ReplayComparison",
    "ComparisonResult",
    "ClaudeExecutorDetector",
    "ClaudeDetectionResult",
    "ClaudeStatus",
    "EnvConfigService",
    "EnvWriteResult",
    "OpenAIKeyState",
    "OpenAIKeyStatus",
    "AIConnectionService",
    "OpenAIConnectionTester",
    "Version",
    "VersionInfo",
    "VersionManager",
    "ReleaseChannel",
    "get_version_manager",
    "get_version",
    "get_version_info",
    "Updater",
    "UpdateConfig",
    "UpdateStatus",
    "UpdateResult",
    "ReleaseInfo",
    "get_updater",
    "check_for_updates",
]
