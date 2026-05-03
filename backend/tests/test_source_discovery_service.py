from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    CandidateReviewStatus,
    EvidencePackRecord,
    EvidencePackSourceRecord,
    GlobalSourceDocumentRecord,
    SourceCandidateRecord,
    SourceDiscoveryJobRecord,
    SourceDiscoveryStatus,
    SourceDocumentRecord,
    SourceTopicAssignmentRecord,
)
from backend.repository.source_library_repository import CandidateLibrarySaveResult
from backend.shared.config import BackendConfig
from backend.services.source_discovery_contracts import (
    SOURCE_DISCOVERY_JOB_TYPE,
    EvidencePackCreateRequest,
    SourceCandidateLibrarySaveRequest,
    SourceCandidateWrite,
    SourceDiscoveryJobPayload,
    SourceDiscoveryPlanningContext,
)
from backend.services.source_discovery_service import (
    BraveSearchProvider,
    FetchedContent,
    HttpContentFetcher,
    MockContentFetcher,
    SearchResult,
    SimpleCandidateScorer,
    SimpleQueryExpander,
    SimpleSourceClassifier,
    SourceDiscoveryService,
    build_source_discovery_content_fetcher,
    build_source_discovery_search_provider,
    brave_freshness_for_time_range,
)
from backend.services.semantic_source_recall import LocalSemanticIndex
from backend.services.source_library_service import SourceLibraryService
from backend.shared.errors import ApplicationError, ConfigurationError


class _FakeJobRepository:
    def __init__(self) -> None:
        self.touched: list[str] = []

    async def touch_heartbeat(self, job_id: str):
        self.touched.append(job_id)


class _FakeExtractionRepository:
    def __init__(self) -> None:
        self.submitted_document_ids: list[str] = []

    async def create_submission(self, case_id: str, document_ids: list[str]) -> Job:
        self.submitted_document_ids = document_ids
        return Job(
            id="job-graph-123",
            job_type="graph.extract",
            status=JobStatus.PENDING,
            payload={"case_id": case_id, "document_ids": document_ids},
        )


class _DuplicateSearchProvider:
    async def search(self, query: str, request: SourceDiscoveryJobPayload) -> list[SearchResult]:
        published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        return [
            SearchResult(
                title=f"Official {request.topic}",
                url="https://example.test/source",
                snippet=f"{request.topic} official regulator claim",
                source_type="official",
                published_at=published_at,
            ),
            SearchResult(
                title=f"Duplicate {request.topic}",
                url="https://example.test/source/",
                snippet=f"{request.topic} duplicated claim",
                source_type="news",
                published_at=published_at,
            ),
            SearchResult(
                title=f"Community {request.topic}",
                url="https://example.test/community",
                snippet=f"{request.topic} consumer and media claim",
                source_type="social",
                published_at=published_at,
            ),
        ]


class _FakeSourceRepository:
    def __init__(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        self.discovery_job = SourceDiscoveryJobRecord(
            id="discovery-123",
            case_id="case-123",
            job_id="job-123",
            status=SourceDiscoveryStatus.PENDING,
            topic="Battery recall",
            description="Battery fire reports",
            region="US",
            language="en",
            time_range="last_30_days",
            source_types=["official", "news", "social"],
            max_sources=5,
            query_plan=[],
            candidate_count=0,
            accepted_count=0,
            rejected_count=0,
            created_at=now,
            updated_at=now,
        )
        self.candidates: list[SourceCandidateRecord] = []
        self.pack_sources: list[EvidencePackSourceRecord] = []

    async def mark_discovery_running(self, discovery_job_id: str, query_plan: list[str]):
        self.discovery_job.status = SourceDiscoveryStatus.RUNNING
        self.discovery_job.query_plan = query_plan
        return self.discovery_job

    async def write_candidates(
        self,
        discovery_job_id: str,
        case_id: str,
        candidates: list[SourceCandidateWrite],
    ) -> list[SourceCandidateRecord]:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        rows: list[SourceCandidateRecord] = []
        for index, candidate in enumerate(candidates):
            rows.append(
                SourceCandidateRecord(
                    id=f"candidate-{index}",
                    discovery_job_id=discovery_job_id,
                    case_id=case_id,
                    title=candidate.title,
                    url=candidate.url,
                    canonical_url=candidate.canonical_url,
                    source_type=candidate.source_type,
                    language=candidate.language,
                    region=candidate.region,
                    published_at=candidate.published_at,
                    provider=candidate.provider,
                    provider_metadata=candidate.provider_metadata,
                    content=candidate.content,
                    excerpt=candidate.excerpt,
                    content_hash=candidate.content_hash,
                    classification=candidate.classification,
                    claim_previews=candidate.claim_previews,
                    stakeholder_previews=candidate.stakeholder_previews,
                    review_status=CandidateReviewStatus.PENDING,
                    relevance=candidate.scores.relevance,
                    authority=candidate.scores.authority,
                    freshness=candidate.scores.freshness,
                    claim_richness=candidate.scores.claim_richness,
                    diversity=candidate.scores.diversity,
                    grounding_value=candidate.scores.grounding_value,
                    total_score=candidate.total_score or candidate.scores.total(),
                    created_at=now,
                    updated_at=now,
                )
            )
        self.candidates = rows
        self.discovery_job.candidate_count = len(rows)
        return rows

    async def mark_discovery_completed(self, discovery_job_id: str):
        self.discovery_job.status = SourceDiscoveryStatus.COMPLETED
        return self.discovery_job

    async def mark_discovery_failed(self, discovery_job_id: str, code: str, message: str):
        self.discovery_job.status = SourceDiscoveryStatus.FAILED
        self.discovery_job.last_error_code = code
        self.discovery_job.last_error = message
        return self.discovery_job

    async def list_candidates(self, case_id=None, discovery_job_id=None, review_status=None):
        candidates = self.candidates
        if review_status:
            candidates = [candidate for candidate in candidates if candidate.review_status == review_status]
        return sorted(candidates, key=lambda candidate: candidate.total_score, reverse=True)

    async def update_candidate_review(self, source_id: str, review_status: str):
        for candidate in self.candidates:
            if str(candidate.id) == source_id:
                candidate.review_status = CandidateReviewStatus(review_status)
                self.discovery_job.accepted_count = len(
                    [item for item in self.candidates if item.review_status == CandidateReviewStatus.ACCEPTED]
                )
                self.discovery_job.rejected_count = len(
                    [item for item in self.candidates if item.review_status == CandidateReviewStatus.REJECTED]
                )
                return candidate
        raise ApplicationError(code="NOT_FOUND", message="not found", status_code=404)

    async def create_evidence_pack(self, request: EvidencePackCreateRequest):
        accepted = [
            candidate
            for candidate in self.candidates
            if candidate.review_status == CandidateReviewStatus.ACCEPTED
            and (not request.candidate_ids or str(candidate.id) in request.candidate_ids)
        ]
        if not accepted:
            raise ApplicationError(code="VALIDATION_ERROR", message="Accept at least one source", status_code=400)
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        self.pack_sources = [
            EvidencePackSourceRecord(
                id=f"pack-source-{index}",
                evidence_pack_id="pack-123",
                candidate_id=str(candidate.id),
                sort_order=index,
                title=candidate.title,
                url=candidate.url,
                source_type=candidate.source_type,
                language=candidate.language,
                region=candidate.region,
                provider=candidate.provider,
                provider_metadata=candidate.provider_metadata,
                content=candidate.content,
                excerpt=candidate.excerpt,
                score_dimensions={
                    "relevance": candidate.relevance,
                    "authority": candidate.authority,
                    "freshness": candidate.freshness,
                    "claim_richness": candidate.claim_richness,
                    "diversity": candidate.diversity,
                    "grounding_value": candidate.grounding_value,
                },
                total_score=candidate.total_score,
                claim_previews=candidate.claim_previews,
                stakeholder_previews=candidate.stakeholder_previews,
                created_at=now,
            )
            for index, candidate in enumerate(accepted)
        ]
        return EvidencePackRecord(
            id="pack-123",
            case_id=request.case_id,
            discovery_job_id=request.discovery_job_id,
            title=request.title or "Pack",
            source_count=len(accepted),
            created_at=now,
            updated_at=now,
        )

    async def get_evidence_pack(self, evidence_pack_id: str):
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        pack = EvidencePackRecord(
            id=evidence_pack_id,
            case_id="case-123",
            discovery_job_id="discovery-123",
            title="Pack",
            source_count=len(self.pack_sources),
            created_at=now,
            updated_at=now,
        )
        return pack, self.pack_sources

    async def materialize_evidence_pack_sources(self, evidence_pack_id: str):
        return [
            SourceDocumentRecord(
                id="doc-1",
                case_id="case-123",
                evidence_pack_id=evidence_pack_id,
                evidence_pack_source_id="pack-source-0",
                source_origin="evidence_pack",
                title="Official Battery recall",
                content="grounding content",
                doc_type="statement",
                source_metadata={
                    "candidate_id": "candidate-0",
                    "evidence_pack_id": evidence_pack_id,
                    "total_score": 0.9,
                },
            )
        ]


class _FakeSourceLibraryRepository:
    def __init__(self, duplicate_reused: bool = False, with_assignment: bool = True) -> None:
        self.duplicate_reused = duplicate_reused
        self.with_assignment = with_assignment
        self.saved_requests: list[tuple[str, SourceCandidateLibrarySaveRequest]] = []

    async def save_candidate_to_library(self, candidate_id: str, request: SourceCandidateLibrarySaveRequest):
        self.saved_requests.append((candidate_id, request))
        source = GlobalSourceDocumentRecord(
            id="global-source-123",
            title="Official Battery recall",
            content="official content",
            doc_type="statement",
            content_hash="hash",
            source_kind="official",
            authority_level="high",
            freshness_status="current",
            source_status="active",
            source_metadata={},
            created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
        assignment = None
        if self.with_assignment and request.topic_id:
            assignment = SourceTopicAssignmentRecord(
                id="assignment-123",
                global_source_id="global-source-123",
                topic_id=request.topic_id,
                relevance_score=0.9,
                reason=request.reason,
                assigned_by=request.assigned_by,
                source_candidate_id=candidate_id,
                discovery_job_id="discovery-123",
                assignment_metadata={"provider": "mock"},
                status="active",
                created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
                updated_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            )
        return CandidateLibrarySaveResult(
            source=source,
            assignment=assignment,
            duplicate_reused=self.duplicate_reused,
        )


def _build_job() -> Job:
    payload = {
        "source_discovery_job_id": "discovery-123",
        "case_id": "case-123",
        "topic": "Battery recall",
        "description": "Battery fire reports",
        "region": "US",
        "language": "en",
        "time_range": "last_30_days",
        "source_types": ["official", "news", "social"],
        "max_sources": 5,
    }
    return Job(id="job-123", job_type=SOURCE_DISCOVERY_JOB_TYPE, status=JobStatus.RUNNING, payload=payload)


def _build_payload() -> SourceDiscoveryJobPayload:
    return SourceDiscoveryJobPayload.from_job_payload("job-123", dict(_build_job().payload))


def test_brave_provider_maps_web_results_and_sends_subscription_header():
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Official Battery recall update",
                            "url": "https://example.test/recall",
                            "description": "Regulator update with consumer claim details",
                            "age": "1 day ago",
                            "language": "en",
                            "family_friendly": True,
                            "profile": {"name": "Example"},
                        }
                    ]
                }
            },
        )

    provider = BraveSearchProvider(
        api_key="test-key",
        count=3,
        country="us",
        search_lang="en",
        rate_limit_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    results = asyncio.run(provider.search("Battery recall US", _build_payload()))

    assert len(results) == 1
    assert results[0].provider == "brave"
    assert results[0].title == "Official Battery recall update"
    assert results[0].metadata["rank"] == 1
    assert results[0].metadata["age"] == "1 day ago"
    assert seen_requests[0].headers["X-Subscription-Token"] == "test-key"
    assert seen_requests[0].url.params["q"] == "Battery recall US"
    assert seen_requests[0].url.params["count"] == "3"
    assert seen_requests[0].url.params["freshness"] == "pm"


def test_brave_freshness_supports_presets_and_custom_ranges():
    def fixed_now() -> datetime:
        return datetime(2026, 4, 30, tzinfo=timezone.utc)

    assert brave_freshness_for_time_range("last_24_hours", now=fixed_now) == "pd"
    assert brave_freshness_for_time_range("last_7_days", now=fixed_now) == "pw"
    assert brave_freshness_for_time_range("last_30_days", now=fixed_now) == "pm"
    assert brave_freshness_for_time_range("last_365_days", now=fixed_now) == "py"
    assert brave_freshness_for_time_range("last_90_days", now=fixed_now) == "2026-01-30to2026-04-30"
    assert brave_freshness_for_time_range("2026-04-01to2026-04-30", now=fixed_now) == "2026-04-01to2026-04-30"
    assert brave_freshness_for_time_range("anytime", now=fixed_now) is None


def test_brave_provider_throttles_to_one_request_per_second():
    now = 100.0
    sleeps: list[float] = []

    def clock() -> float:
        return now

    async def sleep(delay: float) -> None:
        nonlocal now
        sleeps.append(delay)
        now += delay

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"web": {"results": []}})

    provider = BraveSearchProvider(
        api_key="test-key",
        rate_limit_seconds=1.0,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleep=sleep,
    )

    async def run_searches() -> None:
        await provider.search("first", _build_payload())
        await provider.search("second", _build_payload())

    asyncio.run(run_searches())

    assert sleeps == [1.0]


def test_brave_provider_retries_rate_limit_response():
    now = 100.0
    sleeps: list[float] = []
    calls = 0

    def clock() -> float:
        return now

    async def sleep(delay: float) -> None:
        nonlocal now
        sleeps.append(delay)
        now += delay

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"retry-after": "2"},
                json={"error": {"detail": "Request rate limit exceeded for plan"}},
            )
        return httpx.Response(200, json={"web": {"results": []}})

    provider = BraveSearchProvider(
        api_key="test-key",
        rate_limit_seconds=1.0,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleep=sleep,
    )

    results = asyncio.run(provider.search("Battery recall US", _build_payload()))

    assert results == []
    assert calls == 2
    assert sleeps == [2.0]


def test_search_provider_factory_selects_brave_and_requires_key():
    config = BackendConfig(
        database_url="postgresql+asyncpg://localhost/db",
        source_discovery_search_provider="brave",
        brave_search_api_key="test-key",
    )

    assert isinstance(build_source_discovery_search_provider(config), BraveSearchProvider)

    with pytest.raises(ConfigurationError):
        build_source_discovery_search_provider(
            BackendConfig(
                database_url="postgresql+asyncpg://localhost/db",
                source_discovery_search_provider="brave",
                brave_search_api_key="",
            )
        )


def test_content_fetcher_factory_selects_http_by_default():
    config = BackendConfig(
        database_url="postgresql+asyncpg://localhost/db",
        source_discovery_search_provider="brave",
        brave_search_api_key="test-key",
    )

    assert isinstance(build_source_discovery_content_fetcher(config), HttpContentFetcher)


def test_http_content_fetcher_extracts_page_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><head><script>ignore()</script></head><body><article><h1>Recall update</h1><p>Regulator confirmed the recall timeline.</p></article></body></html>",
        )

    fetcher = HttpContentFetcher(timeout_seconds=1, transport=httpx.MockTransport(handler))

    content = asyncio.run(
        fetcher.fetch(
            SearchResult(
                title="Recall update",
                url="https://example.test/recall",
                snippet="Fallback snippet",
                source_type="official",
                provider="brave",
            )
        )
    )

    assert content.metadata["fetch_status"] == "fetched"
    assert "Regulator confirmed the recall timeline." in content.content
    assert "ignore()" not in content.content


def test_worker_pipeline_writes_deduped_candidates_with_scores_sorted():
    source_repository = _FakeSourceRepository()
    service = SourceDiscoveryService(
        source_repository=source_repository,
        job_repository=_FakeJobRepository(),
        extraction_repository=_FakeExtractionRepository(),
        search_provider=_DuplicateSearchProvider(),
    )

    result = asyncio.run(service.handle_job(_build_job()))
    listed = asyncio.run(service.list_candidates(discovery_job_id="discovery-123"))

    assert result["candidate_count"] == 2
    assert source_repository.discovery_job.status == SourceDiscoveryStatus.COMPLETED
    assert len(listed.candidates) == 2
    assert listed.candidates[0].total_score >= listed.candidates[1].total_score
    assert listed.candidates[0].scores.relevance > 0
    assert listed.candidates[0].claim_previews


def test_candidate_relevance_downranks_generic_term_matches():
    scorer = SimpleCandidateScorer()
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="Xibei pre-made dish incident social media",
        description="Gather posts from Chinese social sites.",
        region="China",
        language="en",
        time_range="last_30_days",
        source_types=["social"],
        max_sources=10,
    )
    result = SearchResult(
        title="Xiao Zhan incident - Wikipedia",
        url="https://en.wikipedia.org/wiki/Xiao_Zhan_boycott_incident",
        snippet="A social media boycott incident involving a celebrity fandom.",
        source_type="social",
        provider="brave",
    )

    score = scorer.score(
        request,
        result,
        content=FetchedContent(
            content=(
                "Xiao Zhan incident social media discussion. "
                "The article covers a celebrity boycott and online fandom conflict."
            ),
            excerpt="",
            metadata={},
        ),
        classification="official",
        duplicate_index=0,
    )

    assert score.relevance <= 0.35
    assert score.total() <= 0.45


def test_candidate_relevance_rewards_specific_topic_matches():
    scorer = SimpleCandidateScorer()
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="Xibei pre-made dish incident social media",
        description="Gather posts from Chinese social sites.",
        region="China",
        language="en",
        time_range="last_30_days",
        source_types=["social"],
        max_sources=10,
    )
    result = SearchResult(
        title="Xibei pre-made dish incident trends across social media",
        url="https://example.test/xibei",
        snippet="Xibei customers discuss the pre-made dish controversy on social media.",
        source_type="social",
        provider="brave",
    )

    score = scorer.score(
        request,
        result,
        content=FetchedContent(
            content=(
                "Xibei pre-made dish incident social media posts discuss restaurant responses, "
                "consumer claims, and the evolving timeline."
            ),
            excerpt="",
            metadata={},
        ),
        classification="social",
        duplicate_index=0,
    )

    assert score.relevance >= 0.8


def test_candidate_relevance_uses_bounded_semantic_support_for_core_matches():
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="Battery recall fire reports",
        description="battery overheating safety recall",
        region="US",
        language="en",
        time_range="last_30_days",
        source_types=["news"],
        max_sources=10,
    )
    result = SearchResult(
        title="Battery recall expands after overheating reports",
        url="https://example.test/battery",
        snippet="Regulators cite fire risk in recalled battery packs.",
        source_type="news",
    )
    content = FetchedContent(
        content="Battery recall documents describe overheating, fire reports, and consumer safety claims.",
        excerpt="",
        metadata={},
    )

    lexical_score = SimpleCandidateScorer().score(request, result, content, "news", 0)
    semantic_score = SimpleCandidateScorer(LocalSemanticIndex()).score(request, result, content, "news", 0)

    assert semantic_score.relevance >= lexical_score.relevance
    assert semantic_score.relevance <= 1.0


def test_semantic_support_does_not_bypass_core_relevance_gate():
    scorer = SimpleCandidateScorer(LocalSemanticIndex())
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="Xibei pre-made dish incident social media",
        description="Gather posts from Chinese social sites.",
        region="China",
        language="en",
        time_range="last_30_days",
        source_types=["social"],
        max_sources=10,
    )
    result = SearchResult(
        title="Xiao Zhan incident - Wikipedia",
        url="https://en.wikipedia.org/wiki/Xiao_Zhan_boycott_incident",
        snippet="A social media incident involving a celebrity fandom.",
        source_type="social",
        provider="brave",
    )
    content = FetchedContent(
        content=(
            "China social media incident discussion with timeline details. "
            "The article covers a celebrity boycott and online fandom conflict."
        ),
        excerpt="",
        metadata={},
    )

    score = scorer.score(request, result, content, "official", 0)

    assert score.relevance <= 0.35
    assert score.total() <= 0.45


def test_candidate_relevance_matches_chinese_event_variants():
    scorer = SimpleCandidateScorer()
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="西贝预制菜事件",
        description="关注罗永浩、西贝官方回应和预制菜争议。",
        region="中国",
        language="zh",
        time_range="last_30_days",
        source_types=["news"],
        max_sources=10,
        planning_context=SourceDiscoveryPlanningContext(
            core_entities=["西贝", "预制菜"],
            actor_names=["罗永浩", "贾国龙"],
            event_aliases=["西贝预制菜风波", "预制菜之争", "罗永浩吐槽西贝事件"],
        ),
    )
    result = SearchResult(
        title="西贝预制菜之争：民众和餐饮专家在关心什么？",
        url="https://www.bbc.com/zhongwen/articles/example",
        snippet="罗永浩发文后，西贝回应预制菜争议。",
        source_type="news",
        provider="brave",
    )
    score = scorer.score(
        request,
        result,
        FetchedContent(content="西贝预制菜风波持续发酵，罗永浩与贾国龙先后回应。", excerpt="", metadata={}),
        "news",
        0,
    )

    assert score.relevance >= 0.8


def test_candidate_relevance_downranks_chinese_generic_social_background():
    scorer = SimpleCandidateScorer()
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="西贝预制菜事件",
        description="",
        region="中国",
        language="zh",
        time_range="last_30_days",
        source_types=["social"],
        max_sources=10,
    )
    result = SearchResult(
        title="中国社交媒体平台完整指南",
        url="https://example.org/chinese-social-media-platforms",
        snippet="介绍微博、微信、抖音和小红书等平台。",
        source_type="social",
        provider="brave",
    )
    score = scorer.score(
        request,
        result,
        FetchedContent(content="这是一篇关于社交媒体平台和营销渠道的背景介绍。", excerpt="", metadata={}),
        "social",
        0,
    )

    assert score.relevance <= 0.25
    assert score.grounding_value <= 0.35


def test_query_expander_generates_evidence_bucketed_chinese_queries():
    request = SourceDiscoveryJobPayload(
        source_discovery_job_id="discovery-123",
        job_id="job-123",
        case_id="case-123",
        topic="西贝预制菜事件",
        description="",
        region="中国",
        language="zh",
        time_range="last_30_days",
        source_types=["news", "official", "social"],
        max_sources=10,
        planning_context=SourceDiscoveryPlanningContext(
            core_entities=["西贝", "预制菜"],
            actor_names=["罗永浩"],
            event_aliases=["预制菜之争"],
        ),
    )

    queries = SimpleQueryExpander().expand(request)

    assert len(queries) <= 6
    assert any(query.startswith("timeline:") for query in queries)
    assert any(query.startswith("official_response:") for query in queries)
    assert any(query.startswith("regulatory_context:") for query in queries)
    assert any(query.startswith("social_evidence:") for query in queries)
    assert any("西贝" in query and "罗永浩" in query for query in queries)


def test_classifier_keeps_media_article_with_official_quotes_as_news():
    classifier = SimpleSourceClassifier()
    result = SearchResult(
        title="Restaurant chain apologizes after official statement",
        url="https://www.bbc.com/news/example",
        snippet="The article quotes regulators and official statements.",
        source_type="official",
        provider="brave",
    )

    classification = classifier.classify(
        result,
        FetchedContent(content="Regulators said the company issued an official statement.", excerpt="", metadata={}),
    )

    assert classification == "news"


def test_classifier_uses_source_identity_for_official_and_social_sources():
    classifier = SimpleSourceClassifier()

    official = classifier.classify(
        SearchResult(
            title="市场监管总局公告",
            url="https://www.samr.gov.cn/notice",
            snippet="监管公告",
            source_type="news",
            provider="brave",
        ),
        FetchedContent(content="官方公告", excerpt="", metadata={}),
    )
    social = classifier.classify(
        SearchResult(
            title="罗永浩微博原文",
            url="https://weibo.com/example",
            snippet="用户发帖",
            source_type="news",
            provider="brave",
        ),
        FetchedContent(content="微博用户评论", excerpt="", metadata={}),
    )

    assert official == "official"
    assert social == "social"


def test_real_provider_discovery_filters_mock_or_test_candidates():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Mock test result",
                            "url": "https://mock.search/test",
                            "description": "西贝预制菜事件",
                        }
                    ]
                }
            },
        )

    source_repository = _FakeSourceRepository()
    service = SourceDiscoveryService(
        source_repository=source_repository,
        job_repository=_FakeJobRepository(),
        extraction_repository=_FakeExtractionRepository(),
        search_provider=BraveSearchProvider(
            api_key="token",
            rate_limit_seconds=0,
            transport=httpx.MockTransport(handler),
        ),
        content_fetcher=MockContentFetcher(),
    )
    job = Job(
        id="job-123",
        job_type=SOURCE_DISCOVERY_JOB_TYPE,
        status=JobStatus.PENDING,
        payload={
            "source_discovery_job_id": "discovery-123",
            "case_id": "case-123",
            "topic": "西贝预制菜事件",
            "description": "",
            "region": "中国",
            "language": "zh",
            "time_range": "last_30_days",
            "source_types": ["news"],
            "max_sources": 5,
        },
    )

    outcome = asyncio.run(service.handle_job(job))

    assert outcome["candidate_count"] == 0
    assert source_repository.candidates == []


def test_evidence_pack_requires_accepted_candidates_and_then_creates_pack():
    source_repository = _FakeSourceRepository()
    service = SourceDiscoveryService(
        source_repository=source_repository,
        job_repository=_FakeJobRepository(),
        extraction_repository=_FakeExtractionRepository(),
    )
    source_repository.candidates = [
        SourceCandidateRecord(
            id="candidate-0",
            discovery_job_id="discovery-123",
            case_id="case-123",
            title="Official Battery recall",
            source_type="official",
            language="en",
            region="US",
            provider="mock",
            provider_metadata={},
            content="official content",
            excerpt="official content",
            content_hash="hash",
            classification="official",
            claim_previews=[],
            stakeholder_previews=[],
            review_status=CandidateReviewStatus.PENDING,
            relevance=0.9,
            authority=0.95,
            freshness=0.8,
            claim_richness=0.7,
            diversity=1.0,
            grounding_value=0.9,
            total_score=0.875,
            created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
    ]

    with pytest.raises(ApplicationError):
        asyncio.run(
            service.create_evidence_pack(
                EvidencePackCreateRequest(
                    case_id="case-123",
                    discovery_job_id="discovery-123",
                    candidate_ids=["candidate-0"],
                )
            )
        )

    asyncio.run(service.update_candidate_review("candidate-0", request=type("Req", (), {"review_status": "accepted"})()))
    response = asyncio.run(
        service.create_evidence_pack(
            EvidencePackCreateRequest(
                case_id="case-123",
                discovery_job_id="discovery-123",
                candidate_ids=["candidate-0"],
            )
        )
    )

    assert response.evidence_pack_id == "pack-123"
    assert response.source_count == 1
    assert response.evidence_pack.sources[0].score_dimensions.authority == 0.95


def test_accepting_candidate_does_not_promote_to_source_registry():
    source_repository = _FakeSourceRepository()
    service = SourceDiscoveryService(
        source_repository=source_repository,
        job_repository=_FakeJobRepository(),
        extraction_repository=_FakeExtractionRepository(),
        search_provider=_DuplicateSearchProvider(),
    )

    asyncio.run(service.handle_job(_build_job()))
    asyncio.run(service.update_candidate_review("candidate-0", request=type("Req", (), {"review_status": "accepted"})()))

    assert source_repository.discovery_job.accepted_count == 1


def test_explicit_candidate_save_to_topic_returns_assignment_metadata():
    repository = _FakeSourceLibraryRepository(duplicate_reused=False, with_assignment=True)
    service = SourceLibraryService(repository=repository)

    response = asyncio.run(
        service.save_candidate_to_library(
            "candidate-0",
            SourceCandidateLibrarySaveRequest(topic_id="topic-123", reason="Relevant official source"),
        )
    )

    assert response.global_source_id == "global-source-123"
    assert response.topic_id == "topic-123"
    assert response.topic_assignment_id == "assignment-123"
    assert response.duplicate_reused is False
    assert repository.saved_requests[0][0] == "candidate-0"


def test_explicit_candidate_save_as_unassigned_can_reuse_duplicate_source():
    repository = _FakeSourceLibraryRepository(duplicate_reused=True, with_assignment=False)
    service = SourceLibraryService(repository=repository)

    response = asyncio.run(
        service.save_candidate_to_library(
            "candidate-0",
            SourceCandidateLibrarySaveRequest(topic_id=None, reason="Hold for later classification"),
        )
    )

    assert response.global_source_id == "global-source-123"
    assert response.topic_id is None
    assert response.topic_assignment_id is None
    assert response.duplicate_reused is True


def test_start_grounding_materializes_documents_and_submits_graph_job():
    source_repository = _FakeSourceRepository()
    extraction_repository = _FakeExtractionRepository()
    service = SourceDiscoveryService(
        source_repository=source_repository,
        job_repository=_FakeJobRepository(),
        extraction_repository=extraction_repository,
    )

    response = asyncio.run(service.start_grounding("pack-123"))

    assert response.job_type == "graph.extract"
    assert response.materialized_document_count == 1
    assert extraction_repository.submitted_document_ids == ["doc-1"]
