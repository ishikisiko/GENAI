from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    CandidateReviewStatus,
    CrisisCaseRecord,
    SourceCandidateRecord,
    SourceDiscoveryJobRecord,
    SourceDiscoveryStatus,
)
from backend.services.source_discovery_assistant_service import SourceDiscoveryAssistantService
from backend.services.source_discovery_service import FetchedContent, SearchResult
from backend.services.source_discovery_contracts import SourceDiscoveryAssistantRequest
from backend.shared.errors import ApplicationError, ConfigurationError, DependencyError, ErrorCode


class _FakeLlmClient:
    def __init__(self, payload=None, error: Exception | None = None) -> None:
        self.payload = payload or {
            "answer": "Use official and news sources for the initial pass.",
            "planning_suggestions": [
                {
                    "label": "Official chronology",
                    "rationale": "Find regulator and company statements first.",
                    "topic": "Battery recall timeline",
                    "description": "Regulator and company recall updates",
                    "region": "US",
                    "language": "en",
                    "time_range": "last_30_days",
                    "source_types": ["official", "news"],
                    "queries": ["battery recall official timeline"],
                }
            ],
            "follow_up_searches": ["battery recall latest official update"],
        }
        self.error = error
        self.prompts: list[str] = []

    async def chat_json(self, **kwargs):
        self.prompts.append(kwargs["prompt"])
        if self.error:
            raise self.error
        return self.payload


class _FakeSourceRepository:
    def __init__(self, *, candidates: list[SourceCandidateRecord] | None = None, case_exists: bool = True) -> None:
        now = datetime(2026, 4, 29, tzinfo=timezone.utc)
        self.case = (
            CrisisCaseRecord(
                id="case-123",
                title="Battery recall",
                description="Reports of battery fires",
                status="draft",
                created_at=now,
                updated_at=now,
            )
            if case_exists
            else None
        )
        self.discovery_job = SourceDiscoveryJobRecord(
            id="discovery-123",
            case_id="case-123",
            job_id="job-123",
            status=SourceDiscoveryStatus.COMPLETED,
            topic="Battery recall",
            description="Reports of battery fires",
            region="US",
            language="en",
            time_range="last_30_days",
            source_types=["official", "news"],
            query_plan=["battery recall timeline"],
            max_sources=5,
            candidate_count=len(candidates or []),
            accepted_count=0,
            rejected_count=0,
            created_at=now,
            updated_at=now,
        )
        self.job = Job(id="job-123", job_type="source_discovery.run", status=JobStatus.COMPLETED, payload={})
        self.candidates = candidates or []
        self.list_candidate_calls: list[str | None] = []
        self.discovery_job_calls: list[str] = []
        self.case_calls: list[str] = []

    async def get_case(self, case_id: str):
        self.case_calls.append(case_id)
        return self.case if case_id == "case-123" else None

    async def get_discovery_job(self, discovery_job_id: str):
        self.discovery_job_calls.append(discovery_job_id)
        if discovery_job_id != "discovery-123":
            raise ApplicationError(code=ErrorCode.NOT_FOUND, message="not found", status_code=404)
        return self.discovery_job, self.job

    async def list_candidates(self, case_id=None, discovery_job_id=None, review_status=None):
        self.list_candidate_calls.append(discovery_job_id)
        return self.candidates


class _FakeBriefingSearchProvider:
    def __init__(self, *, empty: bool = False) -> None:
        self.empty = empty
        self.calls: list[str] = []

    async def search(self, query: str, request) -> list[SearchResult]:
        self.calls.append(query)
        if self.empty:
            return []
        published_at = datetime(2026, 4, 29, tzinfo=timezone.utc)
        return [
            SearchResult(
                title="Official battery recall chronology",
                url="https://example.test/recall",
                snippet="The regulator published an official recall chronology.",
                source_type="official",
                provider="fake",
                published_at=published_at,
                metadata={"query": query, "rank": 1},
            ),
            SearchResult(
                title="Duplicate official battery recall chronology",
                url="https://example.test/recall/",
                snippet="Duplicate coverage of the same chronology.",
                source_type="news",
                provider="fake",
                published_at=published_at,
                metadata={"query": query, "rank": 2},
            ),
        ]


class _FakeBriefingContentFetcher:
    def __init__(self) -> None:
        self.fetched_urls: list[str] = []

    async def fetch(self, result: SearchResult) -> FetchedContent:
        self.fetched_urls.append(result.url)
        return FetchedContent(
            content=f"{result.title}. {result.snippet} Official timeline details.",
            excerpt=result.snippet,
            metadata={"fetch_status": "fake"},
        )


def _candidate() -> SourceCandidateRecord:
    now = datetime(2026, 4, 29, tzinfo=timezone.utc)
    return SourceCandidateRecord(
        id="candidate-1",
        discovery_job_id="discovery-123",
        case_id="case-123",
        title="Official recall timeline",
        url="https://example.test/recall",
        canonical_url="https://example.test/recall",
        source_type="official",
        language="en",
        region="US",
        published_at=now,
        provider="mock",
        provider_metadata={},
        content="The regulator published a recall chronology on April 29.",
        excerpt="Recall chronology on April 29.",
        content_hash="hash",
        classification="official",
        claim_previews=[{"text": "Recall chronology"}],
        stakeholder_previews=[{"name": "Regulator"}],
        review_status=CandidateReviewStatus.PENDING,
        relevance=0.9,
        authority=0.9,
        freshness=0.9,
        claim_richness=0.8,
        diversity=0.7,
        grounding_value=0.9,
        total_score=0.85,
        created_at=now,
        updated_at=now,
    )


def test_search_planning_returns_structured_suggestions() -> None:
    llm_client = _FakeLlmClient()
    service = SourceDiscoveryAssistantService(_FakeSourceRepository(), llm_client)  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="search_planning",
                case_id="case-123",
                topic="Battery recall",
                description="Battery fire reports",
                region="US",
                language="en",
                time_range="last_30_days",
                source_types=["official", "news"],
            )
        )
    )

    assert response.mode == "search_planning"
    assert response.planning_suggestions[0].queries == ["battery recall official timeline"]
    assert response.planning_suggestions[0].time_range == "last_30_days"
    assert "Battery recall" in llm_client.prompts[0]
    assert "Every\nplanning_suggestions item must include time_range" in llm_client.prompts[0]


def test_search_planning_defaults_suggestion_time_range_to_request() -> None:
    llm_client = _FakeLlmClient(
        {
            "answer": "Use official sources.",
            "planning_suggestions": [
                {
                    "label": "Official chronology",
                    "rationale": "Find regulator statements.",
                    "queries": ["battery recall regulator chronology"],
                }
            ],
        }
    )
    service = SourceDiscoveryAssistantService(_FakeSourceRepository(), llm_client)  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="search_planning",
                case_id="case-123",
                topic="Battery recall",
                time_range="last_90_days",
            )
        )
    )

    assert response.planning_suggestions[0].time_range == "last_90_days"


def test_search_planning_requires_case_context() -> None:
    service = SourceDiscoveryAssistantService(_FakeSourceRepository(), _FakeLlmClient())  # type: ignore[arg-type]

    with pytest.raises(ApplicationError) as exc_info:
        asyncio.run(service.answer(SourceDiscoveryAssistantRequest(mode="search_planning", topic="Recall")))

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_source_interpretation_uses_requested_discovery_job_candidates() -> None:
    llm_client = _FakeLlmClient(
        {
            "answer": "The event is in the recall-response stage.",
            "timeline": [
                {
                    "event_date": "2026-04-29",
                    "reporting_date": "2026-04-29T00:00:00+00:00",
                    "title": "Recall chronology published",
                    "summary": "The regulator published a chronology.",
                    "citations": [
                        {
                            "candidate_id": "candidate-1",
                            "title": "Official recall timeline",
                            "url": "https://example.test/recall",
                            "published_at": "2026-04-29T00:00:00+00:00",
                            "quote": "published a recall chronology",
                        }
                    ],
                }
            ],
            "event_stages": [
                {
                    "name": "Recall response",
                    "summary": "Official chronology is available.",
                    "confidence": "medium",
                    "citations": [
                        {
                            "candidate_id": "candidate-1",
                            "title": "Official recall timeline",
                            "url": "https://example.test/recall",
                            "published_at": "2026-04-29T00:00:00+00:00",
                            "quote": "recall chronology",
                        }
                    ],
                }
            ],
            "citations": [
                {
                    "candidate_id": "candidate-1",
                    "title": "Official recall timeline",
                    "url": "https://example.test/recall",
                    "published_at": "2026-04-29T00:00:00+00:00",
                    "quote": "recall chronology",
                }
            ],
        }
    )
    repository = _FakeSourceRepository(candidates=[_candidate()])
    service = SourceDiscoveryAssistantService(repository, llm_client)  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="source_interpretation",
                discovery_job_id="discovery-123",
                question="What stage is this in?",
            )
        )
    )

    assert repository.list_candidate_calls == ["discovery-123"]
    assert response.timeline[0].citations[0].candidate_id == "candidate-1"
    assert "candidate-1" in llm_client.prompts[0]


def test_source_interpretation_returns_insufficient_evidence_without_candidates() -> None:
    llm_client = _FakeLlmClient()
    service = SourceDiscoveryAssistantService(_FakeSourceRepository(candidates=[]), llm_client)  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(SourceDiscoveryAssistantRequest(mode="source_interpretation", discovery_job_id="discovery-123"))
    )

    assert response.insufficient_evidence is True
    assert response.follow_up_searches
    assert llm_client.prompts == []


def test_search_backed_briefing_runs_bounded_search_and_maps_cited_response() -> None:
    llm_client = _FakeLlmClient(
        {
            "answer": "Preliminary sources point to an official recall-response stage.",
            "recommended_settings": {
                "topic": "Battery recall timeline",
                "description": "Official and news chronology of battery fire reports",
                "region": "US",
                "language": "en",
                "time_range": "last_30_days",
                "source_types": ["official", "news"],
                "max_sources": 12,
                "queries": ["battery recall timeline official"],
            },
            "source_summaries": [
                {
                    "title": "Official battery recall chronology",
                    "url": "https://example.test/recall",
                    "source_type": "official",
                    "provider": "fake",
                    "published_at": "2026-04-29T00:00:00+00:00",
                    "summary": "Official chronology describes the recall response.",
                    "citation": {
                        "candidate_id": None,
                        "title": "Official battery recall chronology",
                        "url": "https://example.test/recall",
                        "published_at": "2026-04-29T00:00:00+00:00",
                        "quote": "official recall chronology",
                    },
                }
            ],
            "key_actors": ["Regulator", "Company"],
            "controversy_focus": ["Recall timing"],
            "timeline": [
                {
                    "event_date": "2026-04-29",
                    "reporting_date": "2026-04-29T00:00:00+00:00",
                    "title": "Official chronology published",
                    "summary": "The regulator published an official chronology.",
                    "citations": [
                        {
                            "candidate_id": None,
                            "title": "Official battery recall chronology",
                            "url": "https://example.test/recall",
                            "published_at": "2026-04-29T00:00:00+00:00",
                            "quote": "official recall chronology",
                        }
                    ],
                }
            ],
            "event_stages": [
                {
                    "name": "Recall response",
                    "summary": "Official chronology and news coverage are available.",
                    "confidence": "medium",
                    "citations": [
                        {
                            "candidate_id": None,
                            "title": "Official battery recall chronology",
                            "url": "https://example.test/recall",
                            "published_at": "2026-04-29T00:00:00+00:00",
                            "quote": "official recall chronology",
                        }
                    ],
                }
            ],
            "citations": [
                {
                    "candidate_id": None,
                    "title": "Official battery recall chronology",
                    "url": "https://example.test/recall",
                    "published_at": "2026-04-29T00:00:00+00:00",
                    "quote": "official recall chronology",
                }
            ],
        }
    )
    repository = _FakeSourceRepository()
    search_provider = _FakeBriefingSearchProvider()
    content_fetcher = _FakeBriefingContentFetcher()
    service = SourceDiscoveryAssistantService(
        repository,
        llm_client,
        search_provider=search_provider,
        content_fetcher=content_fetcher,
    )  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="search_backed_briefing",
                case_id="case-123",
                topic="Battery recall",
                region="US",
                language="en",
                source_types=["official", "news"],
            )
        )
    )

    assert response.mode == "search_backed_briefing"
    assert response.recommended_settings is not None
    assert response.recommended_settings.queries == ["battery recall timeline official"]
    assert response.source_summaries[0].citation is not None
    assert response.briefing_limits is not None
    assert response.briefing_limits.max_total_sources == 8
    assert 1 <= len(search_provider.calls) <= 4
    assert repository.discovery_job_calls == []
    assert repository.list_candidate_calls == []
    assert "Duplicate official" not in llm_client.prompts[0]


def test_search_backed_briefing_requires_topic_or_case_context() -> None:
    service = SourceDiscoveryAssistantService(
        _FakeSourceRepository(case_exists=False),
        _FakeLlmClient(),
        search_provider=_FakeBriefingSearchProvider(),
        content_fetcher=_FakeBriefingContentFetcher(),
    )  # type: ignore[arg-type]

    with pytest.raises(ApplicationError) as exc_info:
        asyncio.run(service.answer(SourceDiscoveryAssistantRequest(mode="search_backed_briefing")))

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_search_backed_briefing_returns_insufficient_evidence_without_results() -> None:
    llm_client = _FakeLlmClient()
    service = SourceDiscoveryAssistantService(
        _FakeSourceRepository(),
        llm_client,
        search_provider=_FakeBriefingSearchProvider(empty=True),
        content_fetcher=_FakeBriefingContentFetcher(),
    )  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="search_backed_briefing",
                case_id="case-123",
                topic="Battery recall",
            )
        )
    )

    assert response.insufficient_evidence is True
    assert response.follow_up_searches
    assert response.briefing_limits is not None
    assert llm_client.prompts == []


def test_search_backed_briefing_marks_uncited_llm_output_insufficient() -> None:
    llm_client = _FakeLlmClient({"answer": "This has no citations."})
    service = SourceDiscoveryAssistantService(
        _FakeSourceRepository(),
        llm_client,
        search_provider=_FakeBriefingSearchProvider(),
        content_fetcher=_FakeBriefingContentFetcher(),
    )  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(
            SourceDiscoveryAssistantRequest(
                mode="search_backed_briefing",
                case_id="case-123",
                topic="Battery recall",
            )
        )
    )

    assert response.insufficient_evidence is True
    assert response.evidence_gaps


def test_assistant_normalizes_common_llm_shape_drift() -> None:
    service = SourceDiscoveryAssistantService(
        _FakeSourceRepository(),
        _FakeLlmClient(
            {
                "answer": "Preliminary cited briefing.",
                "recommended_settings": {
                    "topic": "Battery recall timeline",
                    "source_types": "news",
                    "max_sources": "12",
                    "queries": "battery recall official chronology",
                },
                "source_summaries": [
                    {
                        "title": "Official chronology",
                        "url": "https://example.test/recall",
                        "citation": {"url": "https://example.test/recall", "quote": "official chronology"},
                    }
                ],
                "key_actors": "Regulator",
                "controversy_focus": "Recall timing",
                "timeline": [
                    {
                        "summary": "The regulator published a chronology.",
                        "citations": {"url": "https://example.test/recall", "quote": "official chronology"},
                    }
                ],
                "event_stages": [
                    {
                        "stage": "Recall response",
                        "summary": "Official chronology is available.",
                        "confidence": "Medium confidence",
                        "citations": "Official chronology",
                    }
                ],
                "citations": [{"url": "https://example.test/recall", "quote": "official chronology"}],
                "conflicts": [{"summary": "Coverage differs on timing.", "sides": "Company"}],
                "evidence_gaps": "Need primary company statement.",
                "follow_up_searches": "battery recall company statement",
            }
        ),
        search_provider=_FakeBriefingSearchProvider(),
        content_fetcher=_FakeBriefingContentFetcher(),
    )  # type: ignore[arg-type]

    response = asyncio.run(
        service.answer(SourceDiscoveryAssistantRequest(mode="search_backed_briefing", case_id="case-123"))
    )

    assert response.recommended_settings is not None
    assert response.recommended_settings.source_types == ["news"]
    assert response.recommended_settings.max_sources == 12
    assert response.key_actors == ["Regulator"]
    assert response.timeline[0].title == "The regulator published a chronology."
    assert response.timeline[0].citations[0].title == "https://example.test/recall"
    assert response.event_stages[0].confidence == "medium"
    assert response.evidence_gaps[0].summary == "Need primary company statement."


def test_assistant_surfaces_llm_configuration_errors() -> None:
    service = SourceDiscoveryAssistantService(
        _FakeSourceRepository(),
        _FakeLlmClient(error=ConfigurationError("missing key")),
    )  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError):
        asyncio.run(
            service.answer(
                SourceDiscoveryAssistantRequest(mode="search_planning", case_id="case-123", topic="Battery recall")
            )
        )


def test_assistant_rejects_invalid_llm_payload() -> None:
    service = SourceDiscoveryAssistantService(_FakeSourceRepository(), _FakeLlmClient(payload={"answer": 3}))  # type: ignore[arg-type]

    with pytest.raises(DependencyError):
        asyncio.run(
            service.answer(
                SourceDiscoveryAssistantRequest(mode="search_planning", case_id="case-123", topic="Battery recall")
            )
        )
