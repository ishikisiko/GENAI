from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from backend.shared.config import BackendConfig
from backend.shared.errors import ConfigurationError, DependencyError
from backend.shared.cache_keys import hash_value, stable_cache_key
from backend.shared.logging import get_logger
from backend.shared.redis_client import RedisClient, RedisUnavailableError


def _trim_trailing_slash(value: str) -> str:
    return value.rstrip("/")


def _extract_json_candidates(content: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        trimmed = value.strip()
        if not trimmed or trimmed in seen:
            return
        seen.add(trimmed)
        candidates.append(trimmed)

    add(content)

    fenced_match = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", content.strip(), flags=re.IGNORECASE)
    if fenced_match:
        add(fenced_match.group(1))

    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", content, flags=re.IGNORECASE):
        add(match.group(1))

    stack: list[str] = []
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(content):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in "{[":
            if not stack:
                start = index
            stack.append("}" if char == "{" else "]")
            continue
        if stack and char == stack[-1]:
            stack.pop()
            if not stack and start >= 0:
                add(content[start : index + 1])
                start = -1

    return candidates


def _extract_json_string(content: str) -> str:
    for candidate in _extract_json_candidates(content):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    raise DependencyError("llm", details={"reason": "LLM returned non-JSON content"})


class LlmJsonClient:
    def __init__(self, config: BackendConfig, redis_client: RedisClient | None = None) -> None:
        self._config = config
        self._redis = redis_client
        self._logger = get_logger("backend.llm")
        self._api_key = config.llm_api_key or config.anthropic_api_key or config.openai_api_key
        self._base_url = _trim_trailing_slash(
            config.llm_base_url or config.anthropic_base_url or "https://api.openai.com/v1"
        )
        self._provider = config.llm_provider or (
            "anthropic" if "anthropic" in self._base_url.lower() else "openai"
        )
        self._model = config.llm_model or config.anthropic_model or "gpt-4o-mini"
        self._timeout = max(config.llm_request_timeout_ms, 1000) / 1000

    async def chat_json(self, prompt: str, temperature: float = 0.7, max_retries: int = 2) -> dict[str, Any]:
        if not self._api_key:
            raise ConfigurationError("LLM_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY is not configured")

        cache_key = self._cache_key(prompt, temperature)
        if cache_key:
            cached = await self._get_cached(cache_key)
            if isinstance(cached, dict):
                return cached

        attempt = 0
        while True:
            try:
                payload = await self._request_json(prompt=prompt, temperature=temperature)
                if cache_key:
                    await self._set_cached(cache_key, payload)
                return payload
            except (httpx.TimeoutException, httpx.HTTPError, DependencyError) as exc:
                attempt += 1
                retryable = self._is_retryable(exc)
                if attempt > max_retries or not retryable:
                    if isinstance(exc, DependencyError):
                        raise
                    raise DependencyError("llm", details={"reason": str(exc)}) from exc
                await asyncio.sleep(min(2**attempt, 5))

    async def _request_json(self, prompt: str, temperature: float) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if self._provider == "anthropic":
                response = await client.post(
                    self._anthropic_url(),
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "temperature": temperature,
                        "max_tokens": self._config.llm_max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = "".join(
                    part.get("text", "")
                    for part in payload.get("content", [])
                    if isinstance(part, dict) and part.get("type") == "text"
                )
                return json.loads(_extract_json_string(content))

            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "temperature": temperature,
                    "max_tokens": self._config.llm_max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise DependencyError("llm", details={"reason": "Missing response content"})
            return json.loads(_extract_json_string(content))

    def _anthropic_url(self) -> str:
        if self._base_url.endswith("/v1"):
            return f"{self._base_url}/messages"
        return f"{self._base_url}/v1/messages"

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in {429, 500, 502, 503, 504, 529}
        if isinstance(exc, httpx.HTTPError):
            return True
        if isinstance(exc, DependencyError):
            return False
        return False

    def _cache_key(self, prompt: str, temperature: float) -> str | None:
        if (
            not self._config.redis_cache_enabled
            or self._config.redis_cache_llm_ttl_seconds <= 0
            or self._redis is None
            or not self._redis.enabled
        ):
            return None
        return stable_cache_key(
            "llm-json",
            {
                "provider": self._provider,
                "base_url": self._base_url,
                "model": self._model,
                "temperature": temperature,
                "max_tokens": self._config.llm_max_tokens,
                "prompt_hash": hash_value(prompt),
            },
        )

    async def _get_cached(self, key: str) -> Any | None:
        if self._redis is None:
            return None
        try:
            return await self._redis.get_json(key)
        except RedisUnavailableError as exc:
            self._logger.warning("redis_cache_get_degraded", extra={"operation": "llm", "reason": str(exc)})
            if self._config.redis_requirement_mode == "required":
                raise DependencyError("redis", details={"operation": "llm_cache_get", "reason": str(exc)}) from exc
            return None

    async def _set_cached(self, key: str, payload: dict[str, Any]) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set_json(key, payload, self._config.redis_cache_llm_ttl_seconds)
        except RedisUnavailableError as exc:
            self._logger.warning("redis_cache_set_degraded", extra={"operation": "llm", "reason": str(exc)})
            if self._config.redis_requirement_mode == "required":
                raise DependencyError("redis", details={"operation": "llm_cache_set", "reason": str(exc)}) from exc
