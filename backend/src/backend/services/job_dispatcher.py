from __future__ import annotations

from dataclasses import dataclass

from backend.domain.models import Job
from backend.shared.config import BackendConfig
from backend.shared.errors import DependencyError
from backend.shared.logging import get_logger
from backend.shared.redis_client import RedisClient, RedisStreamMessage, RedisUnavailableError


@dataclass(frozen=True)
class JobDispatchMessage:
    message_id: str
    job_id: str
    job_type: str


class RedisJobDispatcher:
    def __init__(self, config: BackendConfig, redis_client: RedisClient) -> None:
        self._config = config
        self._redis = redis_client
        self._logger = get_logger("backend.job_dispatcher")

    @property
    def enabled(self) -> bool:
        return self._config.redis_stream_dispatch_enabled

    async def publish_job(self, job: Job) -> None:
        if not self.enabled:
            return
        if not self._redis.enabled:
            self._handle_unavailable("stream_publish", "redis_disabled")
            return
        try:
            await self._redis.stream_add(
                self._config.redis_stream_name,
                {"job_id": str(job.id), "job_type": str(job.job_type)},
            )
        except RedisUnavailableError as exc:
            self._handle_unavailable("stream_publish", str(exc))

    async def read_job(self, worker_id: str) -> JobDispatchMessage | None:
        if not self.enabled or not self._redis.enabled:
            return None
        try:
            messages = await self._redis.stream_read_group(
                stream=self._config.redis_stream_name,
                group=self._config.redis_stream_group,
                consumer=worker_id,
                count=1,
                block_ms=self._config.redis_stream_read_block_ms,
            )
        except RedisUnavailableError as exc:
            self._handle_unavailable("stream_read", str(exc))
            return None
        for message in messages:
            parsed = self._parse_message(message)
            if parsed is not None:
                return parsed
            await self.ack(message.id)
        return None

    async def ack(self, message_id: str) -> None:
        if not self.enabled or not self._redis.enabled:
            return
        try:
            await self._redis.stream_ack(
                self._config.redis_stream_name,
                self._config.redis_stream_group,
                message_id,
            )
        except RedisUnavailableError as exc:
            self._handle_unavailable("stream_ack", str(exc))

    def _parse_message(self, message: RedisStreamMessage) -> JobDispatchMessage | None:
        job_id = message.fields.get("job_id")
        job_type = message.fields.get("job_type")
        if not job_id or not job_type:
            self._logger.warning(
                "redis_stream_message_invalid",
                extra={"message_id": message.id, "field_names": sorted(message.fields.keys())},
            )
            return None
        return JobDispatchMessage(message_id=message.id, job_id=job_id, job_type=job_type)

    def _handle_unavailable(self, operation: str, reason: str) -> None:
        self._logger.warning("redis_stream_degraded", extra={"operation": operation, "reason": reason})
        if self._config.redis_requirement_mode == "required":
            raise DependencyError("redis", details={"operation": operation, "reason": reason})
