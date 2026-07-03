"""Centralized crash logging for the Streamlit app.

The logging stack is intentionally best-effort: failures in Sentry or an
external log sink must never create a second application failure.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import traceback
import urllib.request
from typing import Any


_STREAM_HANDLER_CONFIGURED = False
_SENTRY_CONFIGURED = False
_BETTER_STACK_CONFIGURED = False


def _safe_get_config(name: str, secrets: Any = None, default: str = "") -> str:
    value = os.environ.get(name)
    if value:
        return str(value).strip()

    if secrets is None:
        return default

    try:
        value = secrets.get(name, default)
    except Exception:
        return default
    if value is None:
        return default
    return str(value).strip()


def _as_bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return str(value)[:1000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:5000]
    if isinstance(value, dict):
        clean = {}
        for key, item in list(value.items())[:60]:
            clean[str(key)[:120]] = _sanitize(item, depth=depth + 1)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item, depth=depth + 1) for item in list(value)[:50]]
    return str(value)[:2000]


def _normalize_better_stack_host(host: str) -> str:
    host = str(host or "").strip().rstrip("/")
    if host and not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host


class BetterStackHandler(logging.Handler):
    """Send error-level records to Better Stack's HTTP ingest endpoint."""

    def __init__(self, source_token: str, ingesting_host: str, timeout: float = 3.0):
        super().__init__(level=logging.ERROR)
        self.source_token = source_token
        self.ingesting_host = _normalize_better_stack_host(ingesting_host)
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "dt": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            for attr in ("source_app", "crash_step", "event_type", "crash_details"):
                if hasattr(record, attr):
                    payload[attr] = _sanitize(getattr(record, attr))
            if record.exc_info:
                payload["exception"] = "".join(traceback.format_exception(*record.exc_info))[:50000]

            data = json.dumps(payload, default=str).encode("utf-8")
            request = urllib.request.Request(
                self.ingesting_host,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.source_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass
        except Exception:
            self.handleError(record)


def configure_crash_logging(
    *,
    source_app: str = "Frankenstein",
    release: str = "",
    secrets: Any = None,
) -> logging.Logger:
    """Configure stdout logging, optional Sentry, and optional Better Stack."""
    global _STREAM_HANDLER_CONFIGURED, _SENTRY_CONFIGURED, _BETTER_STACK_CONFIGURED

    logger = logging.getLogger("brinc")
    logger.setLevel(logging.INFO)
    root = logging.getLogger()
    root.setLevel(min(root.level or logging.INFO, logging.INFO))

    if not _STREAM_HANDLER_CONFIGURED:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        if not any(isinstance(handler, logging.StreamHandler) for handler in root.handlers):
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            stream_handler.setLevel(logging.INFO)
            root.addHandler(stream_handler)
        _STREAM_HANDLER_CONFIGURED = True

    dsn = _safe_get_config("SENTRY_DSN", secrets)
    if dsn and not _SENTRY_CONFIGURED:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_sdk.init(
                dsn=dsn,
                environment=_safe_get_config("SENTRY_ENVIRONMENT", secrets, "production"),
                release=release or _safe_get_config("SENTRY_RELEASE", secrets, ""),
                traces_sample_rate=_as_float(
                    _safe_get_config("SENTRY_TRACES_SAMPLE_RATE", secrets, "0"),
                    0.0,
                ),
                send_default_pii=_as_bool(
                    _safe_get_config("SENTRY_SEND_DEFAULT_PII", secrets, "false"),
                    False,
                ),
                enable_logs=_as_bool(
                    _safe_get_config("SENTRY_ENABLE_LOGS", secrets, "false"),
                    False,
                ),
                integrations=[
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR,
                    )
                ],
            )
            _SENTRY_CONFIGURED = True
            logger.info("Sentry crash logging enabled.", extra={"source_app": source_app})
        except Exception as exc:
            logger.warning("Sentry crash logging could not be enabled: %s", exc)

    source_token = (
        _safe_get_config("BETTER_STACK_SOURCE_TOKEN", secrets)
        or _safe_get_config("LOGTAIL_SOURCE_TOKEN", secrets)
    )
    ingesting_host = (
        _safe_get_config("BETTER_STACK_INGESTING_HOST", secrets)
        or _safe_get_config("LOGTAIL_INGESTING_HOST", secrets)
        or _safe_get_config("LOGTAIL_HOST", secrets)
    )
    if source_token and ingesting_host and not _BETTER_STACK_CONFIGURED:
        try:
            handler = BetterStackHandler(source_token, ingesting_host)
            handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
            root.addHandler(handler)
            _BETTER_STACK_CONFIGURED = True
            logger.info("Better Stack crash logging enabled.", extra={"source_app": source_app})
        except Exception as exc:
            logger.warning("Better Stack crash logging could not be enabled: %s", exc)

    return logger


def log_crash(
    step: str,
    exc: BaseException | None = None,
    traceback_text: str | None = None,
    *,
    details: dict[str, Any] | None = None,
    source_app: str = "Frankenstein",
) -> None:
    """Log a crash to stdout and configured external sinks."""
    logger = logging.getLogger("brinc.crash")
    details = _sanitize(details or {})
    error_text = f"{type(exc).__name__}: {exc}" if exc else "Unknown error"
    if traceback_text:
        details = dict(details)
        details["traceback"] = str(traceback_text)[:50000]

    exc_info = sys.exc_info()
    active_exc_info = exc_info if exc is not None and exc_info[1] is exc else None
    logger.error(
        "Crash at %s: %s",
        step,
        error_text,
        exc_info=active_exc_info,
        extra={
            "source_app": source_app,
            "crash_step": str(step or ""),
            "event_type": "crash",
            "crash_details": details,
        },
    )

    if not _SENTRY_CONFIGURED:
        return

    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("source_app", source_app)
            scope.set_tag("crash_step", str(step or ""))
            scope.set_context("crash_details", details)
            if traceback_text:
                scope.set_extra("traceback", str(traceback_text)[:50000])
            if exc is not None:
                sentry_sdk.capture_exception(exc)
            else:
                sentry_sdk.capture_message(f"Crash at {step}: {error_text}", level="error")
        sentry_sdk.flush(timeout=2)
    except Exception as sentry_exc:
        logger.warning("Sentry crash capture failed: %s", sentry_exc)
