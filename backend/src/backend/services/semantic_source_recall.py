from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import re


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
