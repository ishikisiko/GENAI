from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import re
from typing import Any, Protocol

import httpx

from backend.shared.config import BackendConfig
from backend.shared.errors import ConfigurationError, DependencyError


EMBEDDING_MODEL = "local-token-hash"
EMBEDDING_VERSION = "v1"
EMBEDDING_DIMENSIONS = 64
DEFAULT_FRAGMENT_CHAR_LIMIT = 900
DEFAULT_FRAGMENT_PREVIEW_LIMIT = 3
DEFAULT_AGGREGATION_TOP_N = 3

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class TextFragment:
    index: int
    text: str
    content_hash: str


class LocalSemanticIndex:
    """Deterministic local embedding abstraction used until an external vector backend is configured."""

    model = EMBEDDING_MODEL
    version = EMBEDDING_VERSION
    dimensions = EMBEDDING_DIMENSIONS

    async def embed_text(self, text: str) -> list[float]:
        return self.embed(text)

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        if not tokens:
            return [0.0] * self.dimensions

        vector = [0.0] * self.dimensions
        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [round(value / magnitude, 6) for value in vector]

    def similarity(self, left: list[float] | None, right: list[float] | None) -> float:
        if not left or not right:
            return 0.0
        width = min(len(left), len(right))
        if width == 0:
            return 0.0
        score = sum(left[index] * right[index] for index in range(width))
        return round(max(0.0, min(score, 1.0)), 6)


class SemanticIndex(Protocol):
    model: str
    version: str

    async def embed_text(self, text: str) -> list[float]:
        ...

    def similarity(self, left: list[float] | None, right: list[float] | None) -> float:
        ...


class OpenAICompatibleSemanticIndex:
    version = "v1"

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError(
                "SEMANTIC_EMBEDDING_API_KEY, LLM_API_KEY, or OPENAI_API_KEY is required for openai_compatible embeddings"
            )
        if not model:
            raise ConfigurationError("SEMANTIC_EMBEDDING_MODEL is required for openai_compatible embeddings")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def embed_text(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                return self._extract_embedding(response.json())
        except httpx.HTTPStatusError as exc:
            raise DependencyError(
                "semantic_embedding",
                details={"status_code": exc.response.status_code, "reason": exc.response.text[:240]},
            ) from exc
        except httpx.HTTPError as exc:
            raise DependencyError("semantic_embedding", details={"reason": str(exc)}) from exc

    def similarity(self, left: list[float] | None, right: list[float] | None) -> float:
        return cosine_similarity(left, right)

    def _extract_embedding(self, payload: dict[str, Any]) -> list[float]:
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                embedding = first.get("embedding")
                if isinstance(embedding, list):
                    return [float(value) for value in embedding]
        embedding = payload.get("embedding")
        if isinstance(embedding, list):
            return [float(value) for value in embedding]
        raise DependencyError("semantic_embedding", details={"reason": "Embedding response did not include a vector"})


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right:
        return 0.0
    width = min(len(left), len(right))
    if width == 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(width))
    left_magnitude = math.sqrt(sum(left[index] * left[index] for index in range(width)))
    right_magnitude = math.sqrt(sum(right[index] * right[index] for index in range(width)))
    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0
    score = dot / (left_magnitude * right_magnitude)
    return round(max(0.0, min(score, 1.0)), 6)


def build_semantic_index(config: BackendConfig) -> SemanticIndex:
    if config.semantic_embedding_provider == "local":
        return LocalSemanticIndex()
    if config.semantic_embedding_provider == "openai_compatible":
        return OpenAICompatibleSemanticIndex(
            api_key=config.semantic_embedding_api_key or config.llm_api_key or config.openai_api_key,
            base_url=config.semantic_embedding_base_url,
            model=config.semantic_embedding_model,
            timeout_seconds=config.semantic_embedding_timeout_seconds,
        )
    raise ConfigurationError(f"Unsupported SEMANTIC_EMBEDDING_PROVIDER: {config.semantic_embedding_provider}")


def tokenize(text: str) -> list[str]:
    return [match.group(0) for match in _TOKEN_RE.finditer(text.lower()) if len(match.group(0)) > 2]


def chunk_source_text(text: str, char_limit: int = DEFAULT_FRAGMENT_CHAR_LIMIT) -> list[TextFragment]:
    normalized = " ".join((text or "").split())
    if not normalized:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= char_limit:
            current = f"{current} {sentence}"
            continue
        chunks.append(current)
        current = sentence

    if current:
        chunks.append(current)

    split_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= char_limit:
            split_chunks.append(chunk)
            continue
        for start in range(0, len(chunk), char_limit):
            split_chunks.append(chunk[start : start + char_limit].strip())

    return [
        TextFragment(index=index, text=chunk, content_hash=hash_fragment_text(chunk))
        for index, chunk in enumerate(split_chunks)
        if chunk
    ]


def hash_fragment_text(text: str) -> str:
    return sha256(" ".join(text.split()).lower().encode("utf-8")).hexdigest()


def aggregate_semantic_support(scores: list[float], top_n: int = DEFAULT_AGGREGATION_TOP_N) -> float:
    if not scores:
        return 0.0
    selected = sorted(scores, reverse=True)[: max(1, top_n)]
    return round(sum(selected) / len(selected), 6)
