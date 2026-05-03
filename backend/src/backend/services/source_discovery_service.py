from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from hashlib import sha256
import re
import time
from typing import Any, Awaitable, Callable, Protocol
from urllib.parse import urlparse, urlunparse

import httpx

from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    EvidencePackRecord,
    EvidencePackSourceRecord,
    SourceCandidateRecord,
    SourceDiscoveryJobRecord,
)
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.job_repository import JobRepository
from backend.repository.source_discovery_repository import SourceDiscoveryRepository
from backend.services.source_discovery_contracts import (
    SOURCE_DISCOVERY_JOB_TYPE,
    EvidencePackCreateRequest,
    EvidencePackCreateResponse,
    EvidencePackGroundingResponse,
    EvidencePackResponse,
    EvidencePackSourceResponse,
    SourceCandidateListResponse,
    SourceCandidateResponse,
    SourceCandidateReviewRequest,
    SourceCandidateWrite,
    SourceDiscoveryJobCreateRequest,
    SourceDiscoveryJobPayload,
    SourceDiscoveryJobResponse,
    SourceDiscoverySubmissionResponse,
    SourceScoreDimensions,
)
from backend.services.semantic_source_recall import LocalSemanticIndex
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, ConfigurationError, DependencyError, ErrorCode
from backend.shared.logging import get_logger


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source_type: str
    provider: str = "mock"
    published_at: datetime | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class FetchedContent:
    content: str
    excerpt: str
    metadata: dict[str, object]


class QueryExpander(Protocol):
    def expand(self, request: SourceDiscoveryJobPayload) -> list[str]:
        ...


class SearchProvider(Protocol):
    async def search(self, query: str, request: SourceDiscoveryJobPayload) -> list[SearchResult]:
        ...


class ContentFetcher(Protocol):
    async def fetch(self, result: SearchResult) -> FetchedContent:
        ...


class SourceClassifier(Protocol):
    def classify(self, result: SearchResult, content: FetchedContent) -> str:
        ...


class CandidateScorer(Protocol):
    def score(
        self,
        request: SourceDiscoveryJobPayload,
        result: SearchResult,
        content: FetchedContent,
        classification: str,
        duplicate_index: int,
    ) -> SourceScoreDimensions:
        ...


class PreviewExtractor(Protocol):
    def extract_claims(self, content: str) -> list[dict[str, object]]:
        ...

    def extract_stakeholders(self, content: str) -> list[dict[str, object]]:
        ...


_CUSTOM_DATE_RANGE_RE = re.compile(
    r"^(?P<start>\d{4}-\d{2}-\d{2})\s*(?:to|\.{2}|/)\s*(?P<end>\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)
_RELATIVE_DAYS_RE = re.compile(r"^(?:last|past)[_\s-]*(?P<days>\d+)[_\s-]*days?$", re.IGNORECASE)
_TOPIC_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_GENERIC_RELEVANCE_TOKENS = {
    "about",
    "after",
    "before",
    "case",
    "china",
    "chinese",
    "crisis",
    "dish",
    "event",
    "evidence",
    "incident",
    "latest",
    "made",
    "media",
    "official",
    "pre",
    "report",
    "reports",
    "social",
    "source",
    "sources",
    "statement",
    "timeline",
    "update",
    "事件",
    "风波",
    "爭議",
    "争议",
    "之争",
    "新聞",
    "新闻",
    "媒體",
    "媒体",
    "社交",
    "社交媒体",
    "平台",
    "時間線",
    "时间线",
    "來源",
    "来源",
    "官方",
    "回应",
    "回應",
    "监管",
    "監管",
    "标准",
    "標準",
    "报道",
    "報道",
}
_EVIDENCE_BUCKET_QUERIES = {
    "timeline": ["时间线", "始末", "9月10日", "timeline"],
    "official_response": ["官方回应", "道歉信", "声明", "贾国龙"],
    "regulatory_context": ["国家标准", "餐饮", "明示", "监管"],
    "social_evidence": ["微博", "原文", "直播", "罗永浩"],
    "impact": ["关店", "营收", "客流", "影响"],
}
_OFFICIAL_DOMAIN_PARTS = ("gov.", ".gov", "gov.cn", "samr.gov.cn", "xibei.com")
_MEDIA_DOMAIN_PARTS = (
    "bbc.com",
    "thepaper.cn",
    "qq.com",
    "yicaiglobal.com",
    "sixthtone.com",
    "chinadaily.com.cn",
    "globaltimes.cn",
    "thebeijinger.com",
    "kr-asia.com",
    "jiemian.com",
    "21jingji.com",
    "bjnews.com.cn",
    "scol.com.cn",
    "citynewsservice.cn",
    "worldofchinese.com",
)
_SOCIAL_DOMAIN_PARTS = (
    "weibo.com",
    "douyin.com",
    "bilibili.com",
    "xiaohongshu.com",
    "zhihu.com",
    "substack.com",
    "youtube.com",
    "twitter.com",
    "x.com",
)
_RESEARCH_DOMAIN_PARTS = ("edu", "ac.", "research", "scholar", "cnki")
_GENERIC_BACKGROUND_TERMS = (
    "wikipedia",
    "guide to",
    "platforms",
    "social platforms",
    "社交媒体平台",
    "社交平台",
    "百科",
)


def brave_freshness_for_time_range(
    time_range: str,
    now: Callable[[], datetime] | None = None,
) -> str | None:
    raw = time_range.strip()
    if not raw:
        return None

    normalized = re.sub(r"[\s-]+", "_", raw.lower())
    aliases = {
        "anytime": None,
        "any_time": None,
        "all_time": None,
        "no_limit": None,
        "pd": "pd",
        "last_day": "pd",
        "past_day": "pd",
        "last_24_hours": "pd",
        "past_24_hours": "pd",
        "pw": "pw",
        "last_week": "pw",
        "past_week": "pw",
        "last_7_days": "pw",
        "past_7_days": "pw",
        "pm": "pm",
        "last_month": "pm",
        "past_month": "pm",
        "last_30_days": "pm",
        "past_30_days": "pm",
        "last_31_days": "pm",
        "past_31_days": "pm",
        "py": "py",
        "last_year": "py",
        "past_year": "py",
        "last_365_days": "py",
        "past_365_days": "py",
    }
    if normalized in aliases:
        return aliases[normalized]

    date_range_match = _CUSTOM_DATE_RANGE_RE.match(raw)
    if date_range_match:
        try:
            start = datetime.fromisoformat(date_range_match.group("start")).date()
            end = datetime.fromisoformat(date_range_match.group("end")).date()
        except ValueError:
            return None
        if start <= end:
            return f"{start.isoformat()}to{end.isoformat()}"
        return None

    relative_match = _RELATIVE_DAYS_RE.match(raw)
    if not relative_match:
        return None

    days = int(relative_match.group("days"))
    if days <= 0:
        return None
    if days == 1:
        return "pd"
    if days == 7:
        return "pw"
    if days in {30, 31}:
        return "pm"
    if days == 365:
        return "py"

    end = (now or (lambda: datetime.now(timezone.utc)))().astimezone(timezone.utc).date()
    start = end - timedelta(days=days)
    return f"{start.isoformat()}to{end.isoformat()}"


class SimpleQueryExpander:
    def expand(self, request: SourceDiscoveryJobPayload) -> list[str]:
        core_terms = _core_search_terms(request)
        base = " ".join(part for part in [core_terms, request.region] if part).strip() or request.topic
        queries = [f"timeline: {base} {' '.join(_EVIDENCE_BUCKET_QUERIES['timeline'][:3])}"]
        bucket_order = ["official_response", "regulatory_context", "social_evidence", "impact"]
        for bucket in bucket_order:
            terms = _EVIDENCE_BUCKET_QUERIES[bucket]
            queries.append(f"{bucket}: {base} {' '.join(terms[:4])}")
        for bucket in request.planning_context.evidence_buckets if request.planning_context else []:
            for query in bucket.queries:
                label = bucket.key or bucket.label or "assistant"
                queries.append(f"{label}: {query}")
        if request.description and not _has_cjk(request.description):
            queries.append(f"context: {request.topic} {request.description}")
        deduped: list[str] = []
        for query in queries:
            normalized = " ".join(query.split())
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped[:6]


class MockSearchProvider:
    async def search(self, query: str, request: SourceDiscoveryJobPayload) -> list[SearchResult]:
        base_date = datetime(2026, 4, 1, tzinfo=timezone.utc)
        source_types = request.source_types or ["news", "official", "social"]
        results: list[SearchResult] = []
        for index, source_type in enumerate(source_types[:4]):
            slug = "-".join(request.topic.lower().split())[:48] or "crisis"
            region = request.region or "global"
            title_prefix = {
                "official": "Official update",
                "statement": "Official statement",
                "social": "Community reports",
                "complaint": "Consumer complaints",
                "academic": "Research brief",
            }.get(source_type, "News analysis")
            results.append(
                SearchResult(
                    title=f"{title_prefix}: {request.topic}",
                    url=f"https://mock.search/{region}/{source_type}/{slug}-{index}",
                    snippet=(
                        f"{request.topic} in {region}. {request.description or 'Background and source evidence.'} "
                        f"Includes claims, stakeholders, and timeline details from {source_type} sources."
                    ),
                    source_type=source_type,
                    provider="mock",
                    published_at=base_date - timedelta(days=index * 5),
                    metadata={"query": query, "rank": index + 1, "mock": True, "time_range": request.time_range},
                )
            )
        return results


class BraveSearchProvider:
    def __init__(
        self,
        api_key: str | None,
        endpoint: str = "https://api.search.brave.com/res/v1/web/search",
        count: int = 10,
        country: str = "us",
        search_lang: str = "en",
        rate_limit_seconds: float = 1.0,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        current_time: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key:
            raise ConfigurationError("BRAVE_SEARCH_API_KEY is required when Brave source discovery is enabled")
        self._api_key = api_key
        self._endpoint = endpoint
        self._count = max(1, min(count, 20))
        self._country = country
        self._search_lang = search_lang
        self._rate_limit_seconds = max(rate_limit_seconds, 0.0)
        self._timeout_seconds = max(timeout_seconds, 1.0)
        self._transport = transport
        self._clock = clock
        self._current_time = current_time or (lambda: datetime.now(timezone.utc))
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last_request_at: float | None = None

    async def search(self, query: str, request: SourceDiscoveryJobPayload) -> list[SearchResult]:
        for attempt in range(2):
            await self._throttle()
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.get(
                        self._endpoint,
                        headers={
                            "Accept": "application/json",
                            "X-Subscription-Token": self._api_key,
                        },
                        params={
                            "q": query,
                            "count": self._count,
                            "country": self._country,
                            "search_lang": self._search_lang,
                            "spellcheck": "1",
                            **self._freshness_params(request),
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return self._map_results(payload, query, request)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt == 0:
                    await self._sleep(self._retry_delay_seconds(exc.response))
                    continue
                raise DependencyError(
                    "brave_search",
                    details={"status_code": exc.response.status_code, "reason": exc.response.text[:240]},
                ) from exc
            except httpx.HTTPError as exc:
                raise DependencyError("brave_search", details={"reason": str(exc)}) from exc

        raise DependencyError("brave_search", details={"reason": "Search request failed after retry"})

    def _retry_delay_seconds(self, response: httpx.Response) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(float(retry_after), self._rate_limit_seconds, 1.0)
            except ValueError:
                pass
        return max(self._rate_limit_seconds, 1.0)

    async def _throttle(self) -> None:
        async with self._lock:
            now = self._clock()
            if self._last_request_at is not None:
                delay = self._rate_limit_seconds - (now - self._last_request_at)
                if delay > 0:
                    await self._sleep(delay)
            self._last_request_at = self._clock()

    def _map_results(
        self,
        payload: dict[str, Any],
        query: str,
        request: SourceDiscoveryJobPayload,
    ) -> list[SearchResult]:
        web = payload.get("web") if isinstance(payload, dict) else None
        raw_results = web.get("results", []) if isinstance(web, dict) else []
        results: list[SearchResult] = []
        freshness = brave_freshness_for_time_range(request.time_range, now=self._current_time)
        for rank, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("description") or item.get("snippet") or "").strip()
            if not title or not url:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_type=self._source_type_for_result(item, request),
                    provider="brave",
                    metadata={
                        "query": query,
                        "rank": rank,
                        "freshness": freshness,
                        "age": item.get("age"),
                        "language": item.get("language"),
                        "family_friendly": item.get("family_friendly"),
                        "profile": item.get("profile"),
                        "subtype": item.get("subtype"),
                    },
                )
            )
        return results

    def _freshness_params(self, request: SourceDiscoveryJobPayload) -> dict[str, str]:
        freshness = brave_freshness_for_time_range(request.time_range, now=self._current_time)
        return {"freshness": freshness} if freshness else {}

    @staticmethod
    def _source_type_for_result(item: dict[str, Any], request: SourceDiscoveryJobPayload) -> str:
        haystack = " ".join(
            str(value)
            for value in [
                item.get("title"),
                item.get("description"),
                item.get("url"),
                item.get("subtype"),
            ]
            if value
        ).lower()
        for source_type in request.source_types:
            if source_type and source_type.lower() in haystack:
                return source_type
        return request.source_types[0] if request.source_types else "news"


class MockContentFetcher:
    async def fetch(self, result: SearchResult) -> FetchedContent:
        content = (
            f"{result.title}. {result.snippet} "
            "Key stakeholders include regulators, affected consumers, company representatives, and media outlets. "
            "Reported claims include timeline updates, response obligations, public concern, and possible operational causes."
        )
        return FetchedContent(
            content=content,
            excerpt=content[:500],
            metadata={"fetch_status": "mocked", **(result.metadata or {})},
        )


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        if tag in {"p", "br", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth > 0:
            self._ignored_depth -= 1
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        return normalize_whitespace(unescape(" ".join(self._chunks)))


class HttpContentFetcher:
    def __init__(
        self,
        timeout_seconds: float = 5.0,
        max_bytes: int = 1_000_000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = max(timeout_seconds, 1.0)
        self._max_bytes = max(max_bytes, 8192)
        self._transport = transport

    async def fetch(self, result: SearchResult) -> FetchedContent:
        if not result.url.startswith(("http://", "https://")):
            return self._fallback_content(result, "unsupported_url")

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=True,
                transport=self._transport,
                headers={
                    "User-Agent": "GenaiSourceDiscovery/1.0 (+https://example.local/source-discovery)",
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
                },
            ) as client:
                response = await client.get(result.url)
                response.raise_for_status()
                raw_content = response.content[: self._max_bytes]
                content_type = response.headers.get("content-type", "")
                text = self._extract_text(raw_content, content_type, response.encoding)
                if not text:
                    return self._fallback_content(result, "empty_content")
                excerpt = text[:500]
                return FetchedContent(
                    content=text,
                    excerpt=excerpt,
                    metadata={
                        "fetch_status": "fetched",
                        "http_status": response.status_code,
                        "content_type": content_type,
                        "final_url": str(response.url),
                        "fetched_bytes": len(raw_content),
                    },
                )
        except httpx.HTTPStatusError as exc:
            return self._fallback_content(
                result,
                "http_error",
                {"http_status": exc.response.status_code, "reason": exc.response.text[:240]},
            )
        except httpx.HTTPError as exc:
            return self._fallback_content(result, "fetch_error", {"reason": str(exc)})

    @staticmethod
    def _extract_text(raw_content: bytes, content_type: str, encoding: str | None) -> str:
        charset = encoding or "utf-8"
        text = raw_content.decode(charset, errors="replace")
        if "html" not in content_type.lower() and "<html" not in text[:500].lower():
            return normalize_whitespace(text)
        parser = _HtmlTextExtractor()
        parser.feed(text)
        parser.close()
        return parser.text()

    @staticmethod
    def _fallback_content(
        result: SearchResult,
        fetch_status: str,
        metadata: dict[str, object] | None = None,
    ) -> FetchedContent:
        content = normalize_whitespace(f"{result.title}. {result.snippet}")
        return FetchedContent(
            content=content,
            excerpt=content[:500],
            metadata={"fetch_status": fetch_status, **(metadata or {}), **(result.metadata or {})},
        )


class SimpleSourceClassifier:
    def classify(self, result: SearchResult, content: FetchedContent) -> str:
        domain = _domain_for_url(result.url)
        lowered = f"{result.source_type} {result.title} {content.content[:1200]} {domain}".lower()
        if _domain_matches(domain, _MEDIA_DOMAIN_PARTS):
            return "news"
        if _domain_matches(domain, _SOCIAL_DOMAIN_PARTS):
            return "social"
        if _domain_matches(domain, _RESEARCH_DOMAIN_PARTS) or any(term in lowered for term in ("research", "academic")):
            return "research"
        if _domain_matches(domain, _OFFICIAL_DOMAIN_PARTS):
            return "official"
        if result.source_type == "official" and not _domain_matches(domain, _MEDIA_DOMAIN_PARTS + _SOCIAL_DOMAIN_PARTS):
            official_source_signals = ("official update", "official statement", "press release", "公告", "声明")
            if any(signal in lowered for signal in official_source_signals):
                return "official"
        if result.source_type in {"social", "complaint"} or any(
            term in lowered for term in ("community", "forum", "weibo", "微博", "评论", "用户")
        ):
            return "social"
        return "news"


class SimpleCandidateScorer:
    def __init__(self, semantic_index: LocalSemanticIndex | None = None) -> None:
        self._semantic_index = semantic_index

    def score(
        self,
        request: SourceDiscoveryJobPayload,
        result: SearchResult,
        content: FetchedContent,
        classification: str,
        duplicate_index: int,
    ) -> SourceScoreDimensions:
        topic_tokens = _relevance_tokens(request.topic, request)
        specific_tokens = [token for token in topic_tokens if token not in _GENERIC_RELEVANCE_TOKENS]
        generic_tokens = [token for token in topic_tokens if token in _GENERIC_RELEVANCE_TOKENS]
        haystack = f"{result.title} {result.snippet} {content.content}".lower()
        matched_specific = sum(1 for token in specific_tokens if token in haystack)
        matched_generic = sum(1 for token in generic_tokens if token in haystack)
        specific_denominator = max(min(len(specific_tokens), 4), 1)
        specific_ratio = min(1.0, matched_specific / specific_denominator)
        generic_ratio = matched_generic / max(len(generic_tokens), 1)
        phrase_match = any(phrase in haystack for phrase in _relevance_phrases(request))
        semantic_support = self._semantic_support(request, result, content)
        relevance = 0.15 + (specific_ratio * 0.65) + (generic_ratio * 0.15)
        if phrase_match:
            relevance += 0.15
        if semantic_support and (matched_specific > 0 or not specific_tokens):
            relevance += semantic_support * 0.1
        if specific_tokens and matched_specific == 0:
            relevance = min(relevance, 0.35)
        if _is_generic_background_source(result, content) and matched_specific == 0:
            relevance = min(relevance, 0.25)
        relevance = min(1.0, relevance)

        authority_by_type = {
            "official": 0.95,
            "research": 0.85,
            "news": 0.75,
            "social": 0.45,
        }
        authority = authority_by_type.get(classification, 0.6)

        freshness = 0.7
        if result.published_at:
            age_days = max((datetime.now(timezone.utc) - result.published_at).days, 0)
            freshness = max(0.2, 1.0 - min(age_days, 365) / 365)

        claim_richness = min(1.0, 0.35 + content.content.lower().count("claim") * 0.15 + len(content.content) / 1600)
        diversity = max(0.35, 1.0 - duplicate_index * 0.12)
        grounding_value = round((relevance * 0.4) + (authority * 0.25) + (claim_richness * 0.25) + (diversity * 0.1), 4)
        if _is_generic_background_source(result, content) and matched_specific == 0:
            grounding_value = min(grounding_value, 0.35)

        return SourceScoreDimensions(
            relevance=round(relevance, 4),
            authority=round(authority, 4),
            freshness=round(freshness, 4),
            claim_richness=round(claim_richness, 4),
            diversity=round(diversity, 4),
            grounding_value=grounding_value,
        )

    def _semantic_support(
        self,
        request: SourceDiscoveryJobPayload,
        result: SearchResult,
        content: FetchedContent,
    ) -> float:
        if self._semantic_index is None:
            return 0.0
        query_text = normalize_whitespace(" ".join([request.topic, request.description, request.region]))
        candidate_text = normalize_whitespace(" ".join([result.title, result.snippet, content.content[:4000]]))
        if not query_text or not candidate_text:
            return 0.0
        return self._semantic_index.similarity(
            self._semantic_index.embed(query_text),
            self._semantic_index.embed(candidate_text),
        )


def _relevance_tokens(value: str, request: SourceDiscoveryJobPayload | None = None) -> list[str]:
    tokens: list[str] = []
    raw_values = [value]
    if request is not None:
        if _has_cjk(request.description):
            raw_values.append(request.description)
        if request.planning_context:
            raw_values.extend(request.planning_context.core_entities)
            raw_values.extend(request.planning_context.actor_names)
            raw_values.extend(request.planning_context.event_aliases)
            raw_values.extend(request.planning_context.language_variants)
    for raw_value in raw_values:
        for token in _TOPIC_TOKEN_RE.findall(raw_value.lower()):
            if len(token) <= 2 and not re.search(r"[\u4e00-\u9fff]", token):
                continue
            for expanded in _expand_relevance_token(token):
                if expanded not in tokens:
                    tokens.append(expanded)
    return tokens


def _expand_relevance_token(token: str) -> list[str]:
    if not _has_cjk(token):
        return [token]
    candidates: list[str] = []
    for cjk_value in _CJK_RE.findall(token):
        _append_unique(candidates, cjk_value)
        for suffix in ("事件", "風波", "风波", "爭議", "争议", "之争", "危机", "危機"):
            if cjk_value.endswith(suffix) and len(cjk_value) > len(suffix) + 1:
                _append_unique(candidates, cjk_value[: -len(suffix)])
        for size in (2, 3, 4, 5):
            for index in range(0, max(len(cjk_value) - size + 1, 0)):
                piece = cjk_value[index : index + size]
                if piece not in _GENERIC_RELEVANCE_TOKENS:
                    _append_unique(candidates, piece)
    return candidates or [token]


def _relevance_phrases(request: SourceDiscoveryJobPayload) -> list[str]:
    phrases = [normalize_whitespace(request.topic).lower()]
    if request.planning_context:
        phrases.extend(value.lower() for value in request.planning_context.event_aliases)
        phrases.extend(value.lower() for value in request.planning_context.core_entities)
    return [phrase for phrase in phrases if phrase]


def _core_search_terms(request: SourceDiscoveryJobPayload) -> str:
    terms: list[str] = []
    if request.planning_context:
        for value in [
            *request.planning_context.core_entities,
            *request.planning_context.actor_names,
            *request.planning_context.event_aliases,
            *request.planning_context.language_variants,
        ]:
            _append_unique(terms, value)
    if not terms:
        for token in _relevance_tokens(request.topic, request):
            if token not in _GENERIC_RELEVANCE_TOKENS:
                _append_unique(terms, token)
            if len(terms) >= 4:
                break
    if not terms:
        _append_unique(terms, request.topic)
    return " ".join(terms[:6])


def _is_generic_background_source(result: SearchResult, content: FetchedContent) -> bool:
    haystack = f"{result.title} {result.url} {result.snippet} {content.excerpt}".lower()
    return any(term in haystack for term in _GENERIC_BACKGROUND_TERMS)


def _domain_for_url(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.")


def _domain_matches(domain: str, parts: tuple[str, ...]) -> bool:
    return bool(domain) and any(part in domain for part in parts)


def _has_cjk(value: str) -> bool:
    return bool(_CJK_RE.search(value))


def _append_unique(values: list[str], value: str) -> None:
    normalized = normalize_whitespace(value).lower()
    if normalized and normalized not in values:
        values.append(normalized)


def _query_text(query: str) -> str:
    label, separator, value = query.partition(":")
    if separator and re.fullmatch(r"[a-zA-Z0-9_-]{3,32}", label.strip()):
        return value.strip()
    return query


def _is_mock_or_test_result(result: SearchResult) -> bool:
    domain = _domain_for_url(result.url)
    metadata = result.metadata or {}
    return (
        result.provider == "mock"
        or domain == "mock.search"
        or bool(metadata.get("mock"))
        or domain.endswith(".test")
        or "example.test" in domain
    )


class SimplePreviewExtractor:
    def extract_claims(self, content: str) -> list[dict[str, object]]:
        sentences = [sentence.strip() for sentence in content.replace("\n", " ").split(".") if sentence.strip()]
        previews = []
        for sentence in sentences[:3]:
            previews.append({"text": sentence[:240], "type": "preview"})
        return previews

    def extract_stakeholders(self, content: str) -> list[dict[str, object]]:
        known = ["regulators", "consumers", "company", "media", "community", "officials"]
        lowered = content.lower()
        return [{"name": name.title(), "role": "mentioned"} for name in known if name in lowered][:5]


def build_source_discovery_search_provider(config: BackendConfig) -> SearchProvider:
    if config.source_discovery_search_provider == "mock":
        return MockSearchProvider()
    if config.source_discovery_search_provider == "brave":
        return BraveSearchProvider(
            api_key=config.brave_search_api_key,
            endpoint=config.brave_search_endpoint,
            count=config.brave_search_count,
            country=config.brave_search_country,
            search_lang=config.brave_search_lang,
            rate_limit_seconds=config.brave_search_rate_limit_seconds,
            timeout_seconds=config.request_timeout_seconds,
        )
    raise ConfigurationError(
        f"Unsupported SOURCE_DISCOVERY_SEARCH_PROVIDER: {config.source_discovery_search_provider}"
    )


def build_source_discovery_content_fetcher(config: BackendConfig) -> ContentFetcher:
    if config.source_discovery_content_fetcher == "mock":
        return MockContentFetcher()
    if config.source_discovery_content_fetcher == "http":
        return HttpContentFetcher(timeout_seconds=config.request_timeout_seconds)
    raise ConfigurationError(
        f"Unsupported SOURCE_DISCOVERY_CONTENT_FETCHER: {config.source_discovery_content_fetcher}"
    )


class SourceDiscoveryService:
    def __init__(
        self,
        source_repository: SourceDiscoveryRepository,
        job_repository: JobRepository,
        extraction_repository: ExtractionRepository,
        query_expander: QueryExpander | None = None,
        search_provider: SearchProvider | None = None,
        content_fetcher: ContentFetcher | None = None,
        classifier: SourceClassifier | None = None,
        scorer: CandidateScorer | None = None,
        preview_extractor: PreviewExtractor | None = None,
    ) -> None:
        self._source_repository = source_repository
        self._job_repository = job_repository
        self._extraction_repository = extraction_repository
        self._query_expander = query_expander or SimpleQueryExpander()
        self._search_provider = search_provider or MockSearchProvider()
        self._content_fetcher = content_fetcher or MockContentFetcher()
        self._classifier = classifier or SimpleSourceClassifier()
        self._scorer = scorer or SimpleCandidateScorer()
        self._preview_extractor = preview_extractor or SimplePreviewExtractor()
        self._allow_mock_results = not isinstance(self._search_provider, BraveSearchProvider)
        self._logger = get_logger("backend.source_discovery")

    async def submit(self, request: SourceDiscoveryJobCreateRequest) -> SourceDiscoverySubmissionResponse:
        discovery_job, job = await self._source_repository.create_discovery_submission(request)
        return self._discovery_response(discovery_job, job, outcome="accepted")

    async def get_status(self, discovery_job_id: str) -> SourceDiscoveryJobResponse:
        discovery_job, job = await self._source_repository.get_discovery_job(discovery_job_id)
        return self._discovery_response(discovery_job, job)

    async def list_candidates(
        self,
        case_id: str | None = None,
        discovery_job_id: str | None = None,
        review_status: str | None = None,
    ) -> SourceCandidateListResponse:
        candidates = await self._source_repository.list_candidates(case_id, discovery_job_id, review_status)
        return SourceCandidateListResponse(candidates=[self._candidate_response(candidate) for candidate in candidates])

    async def update_candidate_review(
        self,
        source_id: str,
        request: SourceCandidateReviewRequest,
    ) -> SourceCandidateResponse:
        candidate = await self._source_repository.update_candidate_review(source_id, request.review_status)
        return self._candidate_response(candidate)

    async def create_evidence_pack(self, request: EvidencePackCreateRequest) -> EvidencePackCreateResponse:
        pack = await self._source_repository.create_evidence_pack(request)
        pack_response = await self.get_evidence_pack(str(pack.id))
        return EvidencePackCreateResponse(
            evidence_pack_id=str(pack.id),
            case_id=str(pack.case_id),
            source_count=pack.source_count,
            evidence_pack=pack_response,
        )

    async def get_evidence_pack(self, evidence_pack_id: str) -> EvidencePackResponse:
        pack, sources = await self._source_repository.get_evidence_pack(evidence_pack_id)
        return self._evidence_pack_response(pack, sources)

    async def start_grounding(self, evidence_pack_id: str) -> EvidencePackGroundingResponse:
        documents = await self._source_repository.materialize_evidence_pack_sources(evidence_pack_id)
        if not documents:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Evidence pack has no materialized documents.",
                status_code=400,
            )
        case_id = str(documents[0].case_id)
        job = await self._extraction_repository.create_submission(
            case_id=case_id,
            document_ids=[str(document.id) for document in documents],
        )
        return EvidencePackGroundingResponse(
            evidence_pack_id=evidence_pack_id,
            case_id=case_id,
            job_id=str(job.id),
            job_status=_status_value(job.status),
            job_status_path=f"/api/jobs/{job.id}",
            status_path=f"/api/graph-extractions/{job.id}",
            document_count=len(documents),
            materialized_document_count=len(documents),
        )

    async def handle_job(self, job: Job) -> dict[str, object]:
        if job.job_type != SOURCE_DISCOVERY_JOB_TYPE:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unsupported job type: {job.job_type}",
                status_code=400,
            )
        payload = SourceDiscoveryJobPayload.from_job_payload(str(job.id), dict(job.payload))
        try:
            return await self._execute(payload)
        except ApplicationError as exc:
            details = ", ".join(
                f"{key}={value}"
                for key, value in exc.details.items()
                if key != "dependency" and value not in (None, "")
            )
            await self._source_repository.mark_discovery_failed(
                payload.source_discovery_job_id,
                code=exc.code.value,
                message=f"{exc.message}: {details}" if details else exc.message,
            )
            raise
        except Exception as exc:
            await self._source_repository.mark_discovery_failed(
                payload.source_discovery_job_id,
                code="SOURCE_DISCOVERY_ERROR",
                message=str(exc),
            )
            raise

    async def _execute(self, payload: SourceDiscoveryJobPayload) -> dict[str, object]:
        queries = self._query_expander.expand(payload)
        await self._source_repository.mark_discovery_running(payload.source_discovery_job_id, queries)
        await self._job_repository.touch_heartbeat(payload.job_id)

        seen: set[str] = set()
        candidates: list[SourceCandidateWrite] = []
        duplicate_index = 0
        for query in queries:
            search_query = _query_text(query)
            results = await self._search_provider.search(search_query, payload)
            for result in results:
                if _is_mock_or_test_result(result) and not self._allow_mock_results:
                    continue
                canonical_url = canonicalize_url(result.url)
                content = await self._content_fetcher.fetch(result)
                content_hash = hash_content(content.content or result.snippet)
                dedupe_key = canonical_url or content_hash
                if dedupe_key in seen:
                    duplicate_index += 1
                    continue
                seen.add(dedupe_key)

                classification = self._classifier.classify(result, content)
                scores = self._scorer.score(payload, result, content, classification, duplicate_index)
                provider_metadata = dict(content.metadata)
                provider_metadata.update(result.metadata or {})
                provider_metadata.setdefault("query", search_query)
                provider_metadata.setdefault("query_bucket", query.partition(":")[0] if ":" in query else "general")
                candidates.append(
                    SourceCandidateWrite(
                        title=result.title,
                        url=result.url,
                        canonical_url=canonical_url,
                        source_type=result.source_type,
                        language=payload.language,
                        region=payload.region,
                        published_at=result.published_at,
                        provider=result.provider,
                        provider_metadata=provider_metadata,
                        content=content.content,
                        excerpt=content.excerpt or result.snippet,
                        content_hash=content_hash,
                        classification=classification,
                        claim_previews=self._preview_extractor.extract_claims(content.content),
                        stakeholder_previews=self._preview_extractor.extract_stakeholders(content.content),
                        scores=scores,
                        total_score=scores.total(),
                    )
                )
                if len(candidates) >= payload.max_sources:
                    break
            await self._job_repository.touch_heartbeat(payload.job_id)
            if len(candidates) >= payload.max_sources:
                break

        written = await self._source_repository.write_candidates(
            payload.source_discovery_job_id,
            payload.case_id,
            sorted(candidates, key=lambda candidate: candidate.total_score or 0, reverse=True),
        )
        await self._source_repository.mark_discovery_completed(payload.source_discovery_job_id)
        await self._job_repository.touch_heartbeat(payload.job_id)
        self._logger.info(
            "source_discovery_completed",
            extra={"case_id": payload.case_id, "candidate_count": len(written)},
        )
        return {"source_discovery_job_id": payload.source_discovery_job_id, "candidate_count": len(written)}

    @staticmethod
    def _discovery_response(
        discovery_job: SourceDiscoveryJobRecord,
        job: Job,
        outcome: str = "status",
    ):
        response_cls = SourceDiscoverySubmissionResponse if outcome == "accepted" else SourceDiscoveryJobResponse
        return response_cls(
            job_id=str(job.id),
            source_discovery_job_id=str(discovery_job.id),
            case_id=str(discovery_job.case_id),
            job_type=job.job_type,
            status=_status_value(discovery_job.status),
            job_status=_status_value(job.status),
            should_poll=_status_value(job.status) in {JobStatus.PENDING.value, JobStatus.RUNNING.value},
            job_status_path=f"/api/jobs/{job.id}",
            status_path=f"/api/source-discovery/jobs/{discovery_job.id}",
            topic=discovery_job.topic,
            description=discovery_job.description,
            region=discovery_job.region,
            language=discovery_job.language,
            time_range=discovery_job.time_range,
            source_types=list(discovery_job.source_types or []),
            max_sources=discovery_job.max_sources,
            query_plan=list(discovery_job.query_plan or []),
            candidate_count=discovery_job.candidate_count,
            accepted_count=discovery_job.accepted_count,
            rejected_count=discovery_job.rejected_count,
            last_error=discovery_job.last_error or job.last_error,
            last_error_code=discovery_job.last_error_code or job.last_error_code,
            created_at=format_dt(discovery_job.created_at),
            updated_at=format_dt(discovery_job.updated_at),
            completed_at=format_dt(discovery_job.completed_at),
        )

    @staticmethod
    def _candidate_response(candidate: SourceCandidateRecord) -> SourceCandidateResponse:
        return SourceCandidateResponse(
            id=str(candidate.id),
            discovery_job_id=str(candidate.discovery_job_id),
            case_id=str(candidate.case_id),
            title=candidate.title,
            url=candidate.url,
            canonical_url=candidate.canonical_url,
            source_type=candidate.source_type,
            language=candidate.language,
            region=candidate.region,
            published_at=format_dt(candidate.published_at),
            provider=candidate.provider,
            provider_metadata=candidate.provider_metadata or {},
            content=candidate.content,
            excerpt=candidate.excerpt,
            content_hash=candidate.content_hash,
            classification=candidate.classification,
            claim_previews=list(candidate.claim_previews or []),
            stakeholder_previews=list(candidate.stakeholder_previews or []),
            review_status=_status_value(candidate.review_status),
            scores=SourceScoreDimensions(
                relevance=candidate.relevance,
                authority=candidate.authority,
                freshness=candidate.freshness,
                claim_richness=candidate.claim_richness,
                diversity=candidate.diversity,
                grounding_value=candidate.grounding_value,
            ),
            total_score=candidate.total_score,
            duplicate_of=str(candidate.duplicate_of) if candidate.duplicate_of else None,
            created_at=format_dt(candidate.created_at) or "",
            updated_at=format_dt(candidate.updated_at) or "",
        )

    @staticmethod
    def _evidence_pack_response(
        pack: EvidencePackRecord,
        sources: list[EvidencePackSourceRecord],
    ) -> EvidencePackResponse:
        return EvidencePackResponse(
            id=str(pack.id),
            case_id=str(pack.case_id),
            discovery_job_id=str(pack.discovery_job_id) if pack.discovery_job_id else None,
            title=pack.title,
            status=_status_value(pack.status),
            source_count=pack.source_count,
            sources=[SourceDiscoveryService._evidence_pack_source_response(source) for source in sources],
            created_at=format_dt(pack.created_at) or "",
            updated_at=format_dt(pack.updated_at) or "",
            grounded_at=format_dt(pack.grounded_at),
        )

    @staticmethod
    def _evidence_pack_source_response(source: EvidencePackSourceRecord) -> EvidencePackSourceResponse:
        score_dimensions = source.score_dimensions or {}
        return EvidencePackSourceResponse(
            id=str(source.id),
            evidence_pack_id=str(source.evidence_pack_id),
            candidate_id=str(source.candidate_id),
            source_document_id=str(source.source_document_id) if source.source_document_id else None,
            sort_order=source.sort_order,
            title=source.title,
            url=source.url,
            source_type=source.source_type,
            language=source.language,
            region=source.region,
            published_at=format_dt(source.published_at),
            provider=source.provider,
            provider_metadata=source.provider_metadata or {},
            content=source.content,
            excerpt=source.excerpt,
            score_dimensions=SourceScoreDimensions(
                relevance=float(score_dimensions.get("relevance", 0)),
                authority=float(score_dimensions.get("authority", 0)),
                freshness=float(score_dimensions.get("freshness", 0)),
                claim_richness=float(score_dimensions.get("claim_richness", 0)),
                diversity=float(score_dimensions.get("diversity", 0)),
                grounding_value=float(score_dimensions.get("grounding_value", 0)),
            ),
            total_score=source.total_score,
            claim_previews=list(source.claim_previews or []),
            stakeholder_previews=list(source.stakeholder_previews or []),
            created_at=format_dt(source.created_at) or "",
        )


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if not parsed.netloc:
        return url.strip()
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def hash_content(content: str) -> str:
    return sha256(" ".join(content.split()).lower().encode("utf-8")).hexdigest()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
