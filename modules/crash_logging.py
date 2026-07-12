"""Centralized crash logging for the Streamlit app.

The logging stack is intentionally best-effort: failures in Sentry or an
external log sink must never create a second application failure.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import re
import sys
import traceback
import urllib.request
from contextlib import contextmanager, nullcontext
from typing import Any


_STREAM_HANDLER_CONFIGURED = False
_SENTRY_CONFIGURED = False
_BETTER_STACK_CONFIGURED = False
_DEFAULT_SENTRY_DSN = "https://8770fa479f91862ab0af5ab615f0c933@o4511610392346624.ingest.us.sentry.io/4511610397065216"

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd|authorization|credential)"
    r"\s*[:=]\s*([^\s,;]+)"
)
_SENSITIVE_KEY_PARTS = {
    "address",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "email",
    "gmail_app_password",
    "password",
    "passwd",
    "phone",
    "pwd",
    "secret",
    "street",
    "token",
}
_FILE_KEY_PARTS = {"upload_file", "upload_files", "uploaded_file", "uploaded_files"}


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


def _redact_string(value: str) -> str:
    value = _EMAIL_RE.sub("[Filtered email]", str(value))
    value = _PHONE_RE.sub("[Filtered phone]", value)
    return _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[Filtered secret]", value)


def _is_sensitive_key(key: str) -> bool:
    key = str(key or "").strip().lower()
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def _is_file_key(key: str) -> bool:
    key = str(key or "").strip().lower()
    return any(part in key for part in _FILE_KEY_PARTS)


def _scrub_sentry_value(value: Any, *, key: str = "", depth: int = 0) -> Any:
    if depth > 10:
        return _redact_string(str(value))[:1000]
    if key and _is_sensitive_key(key):
        return "[Filtered]"
    if key and _is_file_key(key):
        return "[Filtered file]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _redact_string(value)[:5000]
    if isinstance(value, dict):
        clean = {}
        for item_key, item_value in list(value.items())[:100]:
            clean_key = str(item_key)[:120]
            clean[clean_key] = _scrub_sentry_value(item_value, key=clean_key, depth=depth + 1)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [_scrub_sentry_value(item, key=key, depth=depth + 1) for item in list(value)[:100]]
    return _redact_string(str(value))[:2000]


def _scrub_sentry_event(event: dict[str, Any], hint: Any = None) -> dict[str, Any] | None:
    del hint
    try:
        return _scrub_sentry_value(event)
    except Exception:
        return event


def _scrub_sentry_log(log: dict[str, Any], hint: Any = None) -> dict[str, Any] | None:
    del hint
    try:
        if "body" in log:
            log["body"] = _scrub_sentry_value(log["body"])
        if "attributes" in log:
            log["attributes"] = _scrub_sentry_value(log["attributes"])
        return log
    except Exception:
        return log


def sentry_breadcrumb(
    message: str,
    *,
    category: str = "workflow",
    level: str = "info",
    **data: Any,
) -> None:
    """Add a Sentry breadcrumb with sanitized, non-sensitive workflow metadata."""
    if not _SENTRY_CONFIGURED:
        return

    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category=str(category or "workflow"),
            message=str(message or ""),
            level=str(level or "info"),
            data=_scrub_sentry_value(_sanitize(data or {})),
        )
    except Exception:
        return


def sentry_metric(kind: str, name: str, value: float, unit: str | None = None, **attributes: Any) -> None:
    """Capture a Sentry metric when Sentry is enabled."""
    if not _SENTRY_CONFIGURED:
        return

    try:
        import sentry_sdk

        metric_func = getattr(sentry_sdk.metrics, str(kind or "").lower(), None)
        if metric_func is None:
            return
        metric_func(
            str(name),
            float(value),
            unit=unit,
            attributes=_scrub_sentry_value(_sanitize(attributes or {})),
        )
    except Exception:
        return


def sentry_set_user_context(*, session_id: str = "", email: str = "", user_id: str = "") -> None:
    """Set a non-PII Sentry user context from session/user identifiers."""
    if not _SENTRY_CONFIGURED:
        return

    try:
        import sentry_sdk

        clean_session = str(session_id or "").strip()[:120]
        clean_user_id = str(user_id or "").strip()[:120]
        clean_email = str(email or "").strip().lower()
        hashed_email = hashlib.sha256(clean_email.encode("utf-8")).hexdigest() if clean_email else ""
        sentry_user = {
            key: value
            for key, value in {
                "id": clean_user_id or hashed_email or clean_session,
                "email_hash": hashed_email,
                "session_id": clean_session,
            }.items()
            if value
        }
        if sentry_user:
            sentry_sdk.set_user(sentry_user)
    except Exception:
        return


def sentry_cron_checkin(
    monitor_slug: str,
    status: str,
    *,
    check_in_id: str = "",
    duration: float | None = None,
) -> str:
    """Send a Sentry cron check-in when a monitor slug is configured."""
    if not _SENTRY_CONFIGURED or not str(monitor_slug or "").strip():
        return ""

    try:
        from sentry_sdk.crons import capture_checkin

        return capture_checkin(
            monitor_slug=str(monitor_slug).strip(),
            check_in_id=str(check_in_id or "") or None,
            status=str(status or ""),
            duration=duration,
        )
    except Exception:
        return ""


def _normalize_better_stack_host(host: str) -> str:
    host = str(host or "").strip().rstrip("/")
    if host and not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host


@contextmanager
def sentry_span(op: str, description: str = "", **data: Any):
    """Create a Sentry performance transaction when Sentry is enabled."""
    if not _SENTRY_CONFIGURED:
        yield
        return

    try:
        import sentry_sdk

        span_context = sentry_sdk.start_transaction(
            op=str(op or "task"),
            name=str(description or op or "task"),
        )
    except Exception:
        span_context = nullcontext()

    with span_context as span:
        if span is not None:
            for key, value in _sanitize(data or {}).items():
                try:
                    span.set_data(str(key), value)
                except Exception:
                    pass
        yield span


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

    dsn = _safe_get_config("SENTRY_DSN", secrets, _DEFAULT_SENTRY_DSN)
    if dsn and not _SENTRY_CONFIGURED:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            profiles_sample_rate = _as_float(
                _safe_get_config("SENTRY_PROFILES_SAMPLE_RATE", secrets, ""),
                0.0,
            )
            profile_session_sample_rate = _as_float(
                _safe_get_config("SENTRY_PROFILE_SESSION_SAMPLE_RATE", secrets, ""),
                0.0,
            )
            integrations = [
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                )
            ]
            try:
                from sentry_sdk.integrations.mcp import MCPIntegration

                integrations.append(MCPIntegration())
            except Exception as mcp_exc:
                logger.warning("Sentry MCP integration could not be enabled: %s", mcp_exc)

            sentry_options = {
                "dsn": dsn,
                "environment": _safe_get_config("SENTRY_ENVIRONMENT", secrets, "production"),
                "release": release or _safe_get_config("SENTRY_RELEASE", secrets, ""),
                "traces_sample_rate": _as_float(
                    _safe_get_config("SENTRY_TRACES_SAMPLE_RATE", secrets, "1.0"),
                    0.0,
                ),
                "send_default_pii": _as_bool(
                    _safe_get_config("SENTRY_SEND_DEFAULT_PII", secrets, "true"),
                    False,
                ),
                "enable_logs": _as_bool(
                    _safe_get_config("SENTRY_ENABLE_LOGS", secrets, "false"),
                    False,
                ),
                "before_send": _scrub_sentry_event,
                "before_send_log": _scrub_sentry_log,
                "integrations": integrations,
            }
            if profiles_sample_rate > 0.0:
                sentry_options["profiles_sample_rate"] = profiles_sample_rate
                sentry_options["profile_lifecycle"] = _safe_get_config(
                    "SENTRY_PROFILE_LIFECYCLE",
                    secrets,
                    "trace",
                )
            if profile_session_sample_rate > 0.0:
                sentry_options["profile_session_sample_rate"] = profile_session_sample_rate
                sentry_options["profile_lifecycle"] = _safe_get_config(
                    "SENTRY_PROFILE_LIFECYCLE",
                    secrets,
                    "trace",
                )

            sentry_sdk.init(
                **sentry_options,
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
