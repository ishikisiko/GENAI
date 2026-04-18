from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from fastapi import Request

from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, ErrorCode


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    boundary: str
    auth_mode: str
    authenticated: bool
    auth_subject: str | None = None


def build_request_context(request: Request, config: BackendConfig, request_id: str) -> RequestContext:
    path = request.url.path
    if not path.startswith("/api/"):
        return RequestContext(
            request_id=request_id,
            boundary="operator",
            auth_mode=config.product_auth_mode,
            authenticated=False,
            auth_subject=None,
        )

    auth_header = request.headers.get("authorization")
    token: str | None = None
    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not value.strip():
            raise ApplicationError(
                code=ErrorCode.UNAUTHORIZED,
                message="Authorization header must use Bearer token format.",
                status_code=401,
            )
        token = value.strip()
    elif config.product_auth_mode == "require_bearer":
        raise ApplicationError(
            code=ErrorCode.UNAUTHORIZED,
            message="Authorization header is required for product API requests.",
            status_code=401,
        )

    return RequestContext(
        request_id=request_id,
        boundary="product",
        auth_mode=config.product_auth_mode,
        authenticated=token is not None,
        auth_subject=_decode_jwt_subject(token) if token else None,
    )


def _decode_jwt_subject(token: str) -> str | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{payload}{padding}".encode("utf-8")).decode("utf-8")
        parsed = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None
    subject = parsed.get("sub")
    return subject if isinstance(subject, str) and subject else None
