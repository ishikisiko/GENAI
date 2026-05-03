from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from backend.shared.config import BackendConfig
from backend.shared.logging import get_logger


class RedisUnavailableError(Exception):
    """Raised when a Redis operation cannot be completed."""


@dataclass(frozen=True)
class RedisStreamMessage:
    id: str
    fields: dict[str, str]


class RedisClient(Protocol):
    enabled: bool

    async def close(self) -> None:
        ...

    async def ping(self) -> bool:
        ...

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int:
        ...

    async def get_json(self, key: str) -> Any | None:
        ...

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        ...

    async def stream_add(self, stream: str, fields: dict[str, str]) -> str:
        ...

    async def stream_group_create(self, stream: str, group: str) -> None:
        ...

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 0,
    ) -> list[RedisStreamMessage]:
        ...

    async def stream_ack(self, stream: str, group: str, message_id: str) -> None:
        ...


class DisabledRedisClient:
    enabled = False

    async def close(self) -> None:
        return None

    async def ping(self) -> bool:
        return False

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int:
        raise RedisUnavailableError("Redis is disabled")

    async def get_json(self, key: str) -> Any | None:
        return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None

    async def stream_add(self, stream: str, fields: dict[str, str]) -> str:
        raise RedisUnavailableError("Redis is disabled")

    async def stream_group_create(self, stream: str, group: str) -> None:
        raise RedisUnavailableError("Redis is disabled")

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 0,
    ) -> list[RedisStreamMessage]:
        return []

    async def stream_ack(self, stream: str, group: str, message_id: str) -> None:
        return None


class InMemoryRedisClient:
    enabled = True

    def __init__(self, fail_operations: bool = False) -> None:
        self.fail_operations = fail_operations
        self._values: dict[str, tuple[Any, float | None]] = {}
        self._streams: dict[str, list[RedisStreamMessage]] = {}
        self._acked: set[tuple[str, str, str]] = set()
        self._groups: set[tuple[str, str]] = set()
        self._sequence = 0

    async def close(self) -> None:
        return None

    async def ping(self) -> bool:
        self._raise_if_failing()
        return True

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int:
        self._raise_if_failing()
        self._expire_key(key)
        current = self._values.get(key, (0, None))[0]
        value = int(current or 0) + 1
        expires_at = time.monotonic() + ttl_seconds
        self._values[key] = (value, expires_at)
        return value

    async def get_json(self, key: str) -> Any | None:
        self._raise_if_failing()
        self._expire_key(key)
        value = self._values.get(key)
        return value[0] if value else None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._raise_if_failing()
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds > 0 else None
        self._values[key] = (value, expires_at)

    async def stream_add(self, stream: str, fields: dict[str, str]) -> str:
        self._raise_if_failing()
        self._sequence += 1
        message_id = f"{int(time.time() * 1000)}-{self._sequence}"
        self._streams.setdefault(stream, []).append(RedisStreamMessage(id=message_id, fields=dict(fields)))
        return message_id

    async def stream_group_create(self, stream: str, group: str) -> None:
        self._raise_if_failing()
        self._groups.add((stream, group))
        self._streams.setdefault(stream, [])

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 0,
    ) -> list[RedisStreamMessage]:
        self._raise_if_failing()
        await self.stream_group_create(stream, group)
        messages = [
            message
            for message in self._streams.get(stream, [])
            if (stream, group, message.id) not in self._acked
        ]
        return messages[:count]

    async def stream_ack(self, stream: str, group: str, message_id: str) -> None:
        self._raise_if_failing()
        self._acked.add((stream, group, message_id))

    def _expire_key(self, key: str) -> None:
        value = self._values.get(key)
        if value is None:
            return
        _stored, expires_at = value
        if expires_at is not None and expires_at <= time.monotonic():
            self._values.pop(key, None)

    def _raise_if_failing(self) -> None:
        if self.fail_operations:
            raise RedisUnavailableError("In-memory Redis failure requested")


class AsyncRedisClient:
    enabled = True

    def __init__(self, url: str, timeout_seconds: float) -> None:
        try:
            from redis.asyncio import Redis
            from redis.exceptions import RedisError
        except ImportError as exc:  # pragma: no cover - exercised only in missing dependency envs.
            raise RedisUnavailableError("redis package is not installed") from exc

        self._redis_error = RedisError
        self._timeout_seconds = timeout_seconds
        self._client = Redis.from_url(
            url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
            decode_responses=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def ping(self) -> bool:
        return bool(await self._run(self._client.ping()))

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int:
        async def operation() -> int:
            async with self._client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, ttl_seconds)
                result = await pipe.execute()
                return int(result[0])

        return await self._run(operation())

    async def get_json(self, key: str) -> Any | None:
        raw = await self._run(self._client.get(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RedisUnavailableError("Redis cache value is not valid JSON") from exc

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._run(self._client.set(key, json.dumps(value, sort_keys=True, default=str), ex=ttl_seconds))

    async def stream_add(self, stream: str, fields: dict[str, str]) -> str:
        return str(await self._run(self._client.xadd(stream, fields)))

    async def stream_group_create(self, stream: str, group: str) -> None:
        try:
            await self._run(self._client.xgroup_create(stream, group, id="0", mkstream=True))
        except RedisUnavailableError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 0,
    ) -> list[RedisStreamMessage]:
        await self.stream_group_create(stream, group)
        rows = await self._run(
            self._client.xreadgroup(
                group,
                consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
        )
        messages: list[RedisStreamMessage] = []
        for _stream_name, stream_messages in rows or []:
            for message_id, fields in stream_messages:
                messages.append(
                    RedisStreamMessage(
                        id=str(message_id),
                        fields={str(key): str(value) for key, value in dict(fields).items()},
                    )
                )
        return messages

    async def stream_ack(self, stream: str, group: str, message_id: str) -> None:
        await self._run(self._client.xack(stream, group, message_id))

    async def _run(self, awaitable):
        try:
            return await asyncio.wait_for(awaitable, timeout=self._timeout_seconds)
        except Exception as exc:
            if isinstance(exc, RedisUnavailableError):
                raise
            raise RedisUnavailableError(str(exc)) from exc


def build_redis_client(config: BackendConfig) -> RedisClient:
    if not config.redis_enabled:
        return DisabledRedisClient()
    logger = get_logger("backend.redis")
    try:
        return AsyncRedisClient(config.redis_url, config.redis_operation_timeout_seconds)
    except RedisUnavailableError:
        logger.exception("redis_client_init_failed")
        if config.redis_requirement_mode == "required":
            raise
        return DisabledRedisClient()
