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


class SimpleQueryExpander:
    def expand(self, request: SourceDiscoveryJobPayload) -> list[str]:
        base = " ".join(part for part in [request.topic, request.region, request.description] if part).strip()
        source_type_terms = " OR ".join(request.source_types[:4])
        queries = [base or request.topic]
        if request.region:
            queries.append(f"{request.topic} {request.region} crisis sources")
        if source_type_terms:
            queries.append(f"{request.topic} ({source_type_terms}) evidence")
        if request.time_range:
            queries.append(f"{request.topic} {request.time_range} latest")
        deduped: list[str] = []
        for query in queries:
            normalized = " ".join(query.split())
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped[:4]


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
                    metadata={"query": query, "rank": index + 1, "mock": True},
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
                        "age": item.get("age"),
                        "language": item.get("language"),
                        "family_friendly": item.get("family_friendly"),
                        "profile": item.get("profile"),
                        "subtype": item.get("subtype"),
                    },
                )
            )
        return results

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
        lowered = f"{result.source_type} {result.title} {content.content}".lower()
        if "official" in lowered or "statement" in lowered or "regulator" in lowered:
            return "official"
        if "social" in lowered or "complaint" in lowered or "community" in lowered:
            return "social"
        if "research" in lowered or "academic" in lowered:
            return "research"
        return "news"


class SimpleCandidateScorer:
    def score(
        self,
        request: SourceDiscoveryJobPayload,
        result: SearchResult,
        content: FetchedContent,
        classification: str,
        duplicate_index: int,
    ) -> SourceScoreDimensions:
        topic_tokens = {token for token in request.topic.lower().split() if len(token) > 2}
        haystack = f"{result.title} {result.snippet} {content.content}".lower()
        matched = sum(1 for token in topic_tokens if token in haystack)
        relevance = min(1.0, 0.45 + (matched / max(len(topic_tokens), 1)) * 0.55)

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

        return SourceScoreDimensions(
            relevance=round(relevance, 4),
            authority=round(authority, 4),
            freshness=round(freshness, 4),
            claim_richness=round(claim_richness, 4),
            diversity=round(diversity, 4),
            grounding_value=grounding_value,
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
            results = await self._search_provider.search(query, payload)
            for result in results:
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
