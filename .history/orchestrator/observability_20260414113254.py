"""Structured observability helpers for desktop runtime support."""

from __future__ import annotations

import json
import logging
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from .paths import OrchestratorPaths


class StructuredJsonlHandler(logging.Handler):
    """Mirror standard logging records into structured JSONL files."""

    def __init__(self, service: "AppObservability"):
        super().__init__(level=logging.DEBUG)
        self._service = service

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno == logging.DEBUG and not self._service.debug_mode:
                return

            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "category": "python_log",
                "logger": record.name,
                "level": record.levelname.lower(),
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
            }
            if record.exc_info:
                payload["traceback"] = "".join(traceback.format_exception(*record.exc_info))

            self._service._write_jsonl(self._service.app_log_path, payload)
            if record.levelno >= logging.ERROR:
                error_payload = dict(payload)
                error_payload["error_type"] = (
                    record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else "logged_error"
                )
                self._service._write_jsonl(self._service.error_log_path, error_payload)
                self._service._register_failure(
                    error_type=error_payload["error_type"],
                    message=payload["message"],
                    context={"logger": record.name, "module": record.module},
                )
        except Exception:
            pass


class NullObservability:
    """No-op implementation used before workspace initialization."""

    debug_mode = False

    def set_debug_mode(self, enabled: bool) -> None:
        self.debug_mode = enabled

    def attach_logging_handler(self) -> None:
        return None

    def detach_logging_handler(self) -> None:
        return None

    def record_app_event(self, *args, **kwargs) -> None:
        return None

    def record_run_event(self, *args, **kwargs) -> None:
        return None

    def record_user_action(self, *args, **kwargs) -> None:
        return None

    def record_error(self, *args, **kwargs) -> str:
        return datetime.utcnow().strftime("err_%Y%m%d%H%M%S")

    def get_failure_summary(self) -> dict[str, Any]:
        return {"by_type": {}, "recent_errors": [], "last_updated": None}

    def create_diagnostic_package(self, *args, **kwargs) -> Path:
        raise RuntimeError("Observability is not configured")


class AppObservability:
    """Centralized structured logging and diagnostic packaging."""

    MAX_RECENT_ERRORS = 25

    def __init__(self, workspace_root: Path, debug_mode: bool = False):
        self.paths = OrchestratorPaths(workspace_root)
        self.debug_mode = debug_mode
        self._lock = threading.RLock()
        self._logging_handler: Optional[StructuredJsonlHandler] = None
        self._failure_stats_path = self.paths.state_dir / "failure_stats.json"
        self._failure_stats = self._load_failure_stats()
        self._ensure_log_files()

    @property
    def app_log_path(self) -> Path:
        return self.paths.logs_dir / "app.log"

    @property
    def runs_log_path(self) -> Path:
        return self.paths.logs_dir / "runs.log"

    @property
    def error_log_path(self) -> Path:
        return self.paths.logs_dir / "errors.log"

    @property
    def user_actions_log_path(self) -> Path:
        return self.paths.logs_dir / "user_actions.log"

    def _ensure_log_files(self) -> None:
        for path in [
            self.app_log_path,
            self.runs_log_path,
            self.error_log_path,
            self.user_actions_log_path,
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

    def _load_failure_stats(self) -> dict[str, Any]:
        if self._failure_stats_path.exists():
            try:
                return json.loads(self._failure_stats_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"by_type": {}, "recent_errors": [], "last_updated": None}

    def _save_failure_stats(self) -> None:
        self._failure_stats_path.write_text(
            json.dumps(self._failure_stats, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _write_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _register_failure(self, error_type: str, message: str, context: Optional[dict[str, Any]] = None) -> None:
        with self._lock:
            by_type = self._failure_stats.setdefault("by_type", {})
            by_type[error_type] = int(by_type.get(error_type, 0)) + 1

            recent = self._failure_stats.setdefault("recent_errors", [])
            recent.insert(0, {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error_type": error_type,
                "message": message,
                "context": context or {},
            })
            del recent[self.MAX_RECENT_ERRORS:]
            self._failure_stats["last_updated"] = datetime.utcnow().isoformat() + "Z"
            self._save_failure_stats()

    def set_debug_mode(self, enabled: bool) -> None:
        self.debug_mode = enabled
        self.record_app_event(
            event="debug_mode_changed",
            message=f"Debug mode {'enabled' if enabled else 'disabled'}",
            context={"debug_mode": enabled},
            level="info",
        )

    def attach_logging_handler(self) -> None:
        if self._logging_handler is not None:
            return
        handler = StructuredJsonlHandler(self)
        logging.getLogger().addHandler(handler)
        self._logging_handler = handler

    def detach_logging_handler(self) -> None:
        if self._logging_handler is None:
            return
        root_logger = logging.getLogger()
        root_logger.removeHandler(self._logging_handler)
        self._logging_handler = None

    def record_app_event(
        self,
        event: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
        level: str = "info",
        debug_only: bool = False,
    ) -> None:
        if debug_only and not self.debug_mode:
            return
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": "app_event",
            "level": level,
            "event": event,
            "message": message,
            "context": context or {},
            "debug_mode": self.debug_mode,
        }
        self._write_jsonl(self.app_log_path, payload)

    def record_run_event(
        self,
        run_id: str,
        event: str,
        message: str,
        iteration: Optional[int] = None,
        phase: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        level: str = "info",
        debug_only: bool = False,
    ) -> None:
        if debug_only and not self.debug_mode:
            return
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": "run_event",
            "level": level,
            "run_id": run_id,
            "event": event,
            "phase": phase,
            "iteration": iteration,
            "message": message,
            "context": context or {},
        }
        self._write_jsonl(self.runs_log_path, payload)

    def record_user_action(
        self,
        action: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": "user_action",
            "action": action,
            "context": context or {},
        }
        self._write_jsonl(self.user_actions_log_path, payload)

    def record_error(
        self,
        error_type: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
        traceback_text: Optional[str] = None,
        run_id: Optional[str] = None,
        phase: Optional[str] = None,
        fatal: bool = False,
    ) -> str:
        error_id = datetime.utcnow().strftime("err_%Y%m%d%H%M%S%f")
        if traceback_text is None and exception is not None:
            traceback_text = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )

        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": "error_event",
            "error_id": error_id,
            "error_type": error_type,
            "message": message,
            "run_id": run_id,
            "phase": phase,
            "fatal": fatal,
            "context": context or {},
            "traceback": traceback_text,
        }
        self._write_jsonl(self.error_log_path, payload)
        self._write_jsonl(self.app_log_path, payload)
        self._register_failure(error_type=error_type, message=message, context=context)
        return error_id

    def get_failure_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "by_type": dict(self._failure_stats.get("by_type", {})),
                "recent_errors": list(self._failure_stats.get("recent_errors", [])),
                "last_updated": self._failure_stats.get("last_updated"),
            }

    def create_diagnostic_package(
        self,
        report: Optional[Any] = None,
        config_path: Optional[Path] = None,
        preferences_path: Optional[Path] = None,
        version_path: Optional[Path] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Path:
        self.paths.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.paths.diagnostics_dir / f"diagnostic_{timestamp}.zip"

        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "workspace_root": str(self.paths.workspace_root),
            "debug_mode": self.debug_mode,
            "failure_summary": self.get_failure_summary(),
            "metadata": metadata or {},
        }

        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(
                "diagnostic_summary.json",
                json.dumps(summary, indent=2, ensure_ascii=False),
            )

            if report is not None:
                archive.writestr(
                    "diagnostics/report.json",
                    json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                )
                archive.writestr("diagnostics/report.md", report.to_markdown())

            for file_path in [
                self.app_log_path,
                self.runs_log_path,
                self.error_log_path,
                self.user_actions_log_path,
                self._failure_stats_path,
            ]:
                if file_path.exists():
                    archive.write(file_path, f"logs/{file_path.name}")

            for extra_path, arc_prefix in [
                (config_path, "config/config.yaml"),
                (preferences_path, "config/gui_preferences.json"),
                (version_path, "config/version.json"),
            ]:
                if extra_path and extra_path.exists():
                    archive.write(extra_path, arc_prefix)

            if self.paths.state_dir.exists():
                for state_file in sorted(self.paths.state_dir.glob("*.json")):
                    archive.write(state_file, f"state/{state_file.name}")

            if self.paths.runs_dir.exists():
                run_dirs = sorted(
                    [path for path in self.paths.runs_dir.iterdir() if path.is_dir()],
                    key=lambda item: item.stat().st_mtime,
                    reverse=True,
                )[:2]
                for run_dir in run_dirs:
                    for file_path in run_dir.rglob("*.json"):
                        archive.write(file_path, f"runs/{run_dir.name}/{file_path.relative_to(run_dir)}")
                    for file_path in run_dir.rglob("*.md"):
                        archive.write(file_path, f"runs/{run_dir.name}/{file_path.relative_to(run_dir)}")

        self.record_app_event(
            event="diagnostic_package_created",
            message="Diagnostic package exported",
            context={"archive_path": str(archive_path)},
            level="info",
        )
        return archive_path


_observability: AppObservability | NullObservability = NullObservability()


def configure_observability(workspace_root: Path, debug_mode: bool = False) -> AppObservability:
    """Configure the process-wide observability service."""
    global _observability
    if isinstance(_observability, AppObservability):
        if _observability.paths.workspace_root == Path(workspace_root).resolve():
            _observability.set_debug_mode(debug_mode)
            _observability.attach_logging_handler()
            return _observability
        _observability.detach_logging_handler()

    service = AppObservability(Path(workspace_root), debug_mode=debug_mode)
    service.attach_logging_handler()
    _observability = service
    return service


def get_observability() -> AppObservability | NullObservability:
    """Return the process-wide observability service."""
    return _observability