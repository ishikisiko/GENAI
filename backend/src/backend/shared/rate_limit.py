from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode
from backend.shared.logging import get_logger
from backend.shared.redis_client import RedisClient, RedisUnavailableError
from backend.shared.request_context import RequestContext


@dataclass(frozen=True)
class RateLimitRule:
    route: str
    method: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RedisRateLimiter:
    def __init__(self, config: BackendConfig, redis_client: RedisClient) -> None:
        self._config = config
        self._redis = redis_client
        self._logger = get_logger("backend.rate_limit")
        self._rules = self._build_rules(config)

    @property
    def enabled(self) -> bool:
        return self._config.redis_rate_limit_enabled

    async def check(self, request: Request, context: RequestContext) -> RateLimitResult | None:
        rule = self._rules.get((request.method.upper(), request.url.path))
        if rule is None or not self.enabled:
            return None
        if not self._redis.enabled:
            return self._handle_unavailable(rule, "redis_disabled")

        identity = self._identity_for_request(request, context)
        key = f"genai:rate-limit:{rule.method}:{rule.route}:{identity}"
        try:
            count = await self._redis.increment_with_ttl(key, rule.window_seconds)
        except RedisUnavailableError as exc:
            return self._handle_unavailable(rule, str(exc))

        remaining = max(rule.limit - count, 0)
        if count <= rule.limit:
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=remaining,
                retry_after_seconds=0,
            )
        return RateLimitResult(
            allowed=False,
            limit=rule.limit,
            remaining=0,
            retry_after_seconds=rule.window_seconds,
        )

    def to_error(self, result: RateLimitResult) -> ApplicationError:
        return ApplicationError(
            code=ErrorCode.RATE_LIMITED,
            message="Rate limit exceeded. Please retry after the active rate-limit window.",
            status_code=429,
            details={
                "limit": result.limit,
                "remaining": result.remaining,
                "retry_after_seconds": result.retry_after_seconds,
            },
        )

    def _handle_unavailable(self, rule: RateLimitRule, reason: str) -> RateLimitResult:
        self._logger.warning(
            "redis_rate_limit_degraded",
            extra={"route": rule.route, "method": rule.method, "reason": reason},
        )
        if self._config.redis_requirement_mode == "required":
            raise DependencyError("redis", details={"operation": "rate_limit", "reason": reason})
        return RateLimitResult(
            allowed=True,
            limit=rule.limit,
            remaining=rule.limit,
            retry_after_seconds=0,
        )

    @staticmethod
    def _identity_for_request(request: Request, context: RequestContext) -> str:
        if context.auth_subject:
            return f"sub:{context.auth_subject}"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_host = request.client.host if request.client else "anonymous"
        return f"ip:{client_host}"

    @staticmethod
    def _build_rules(config: BackendConfig) -> dict[tuple[str, str], RateLimitRule]:
        window = config.redis_rate_limit_window_seconds
        rules = [
            RateLimitRule(
                method="POST",
                route="/api/simulations",
                limit=config.redis_rate_limit_simulations,
                window_seconds=window,
            ),
            RateLimitRule(
                method="POST",
                route="/api/agent-generation",
                limit=config.redis_rate_limit_agent_generation,
                window_seconds=window,
            ),
            RateLimitRule(
                method="POST",
                route="/api/source-discovery/jobs",
                limit=config.redis_rate_limit_source_discovery_jobs,
                window_seconds=window,
            ),
            RateLimitRule(
                method="POST",
                route="/api/source-discovery/assistant",
                limit=config.redis_rate_limit_source_discovery_assistant,
                window_seconds=window,
            ),
        ]
        return {(rule.method, rule.route): rule for rule in rules}
