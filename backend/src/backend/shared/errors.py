from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    EXTERNAL_DEPENDENCY_ERROR = "EXTERNAL_DEPENDENCY_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApplicationError(Exception):
    """Base application error with a stable API-safe payload."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_payload(self, request_id: str | None = None, route: str | None = None) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "request_id": request_id,
                "route": route,
            }
        }


class ConfigurationError(ApplicationError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.CONFIGURATION_ERROR,
            message=message,
            status_code=500,
            details=details,
        )


class TransitionError(ApplicationError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            code=ErrorCode.INVALID_TRANSITION,
            message=f"Invalid job status transition: {current} -> {target}",
            status_code=409,
            details={"current": current, "target": target},
        )


class DependencyError(ApplicationError):
    def __init__(self, dependency: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.EXTERNAL_DEPENDENCY_ERROR,
            message=f"Dependency unavailable: {dependency}",
            status_code=503,
            details={"dependency": dependency, **(details or {})},
        )
