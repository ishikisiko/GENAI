from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Generator


_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("backend_log_context", default={})
_LOG_RECORD_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


def _current_context() -> dict[str, Any]:
    return dict(_LOG_CONTEXT.get())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(service_name: str, level: str) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            base: dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": service_name,
                "logger": record.name,
                "message": record.getMessage(),
            }
            base.update(_current_context())
            base.update(
                {
                    key: value
                    for key, value in record.__dict__.items()
                    if key not in _LOG_RECORD_RESERVED and not key.startswith("_")
                }
            )
            if record.exc_info:
                base["error"] = self.formatException(record.exc_info)
            if record.stack_info:
                base["stack"] = record.stack_info
            return json.dumps(base, ensure_ascii=False, default=str)

    level_name = level.upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root.setLevel(level_name)
    root.addHandler(handler)


@contextmanager
def correlation_context(**fields: str | int | float | bool | None) -> Generator[None, None, None]:
    previous = _current_context()
    merged = dict(previous)
    merged.update(fields)
    _LOG_CONTEXT.set(merged)
    try:
        yield None
    finally:
        _LOG_CONTEXT.set(previous)
