from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.domain.simulation_records import (
    CandidateReviewStatus,
    GlobalSourceDocumentRecord,
    SourceCandidateRecord,
    SourceFragmentRecord,
)
from backend.repository.source_library_repository import (
    SourceFragmentMatch,
    SourceLibraryRepository,
    SourceSemanticRecallResult,
    SourceSemanticRecommendationEntry,
)
from backend.services.semantic_source_recall import (
    LocalSemanticIndex,
    aggregate_semantic_support,
    chunk_source_text,
)
from backend.services.source_library_service import SourceLibraryService


def _now() -> datetime:
    return datetime(2026, 4, 27, tzinfo=timezone.utc)


def _global_source(source_id: str, source_kind: str = "official") -> GlobalSourceDocumentRecord:
    return GlobalSourceDocumentRecord(
        id=source_id,
        title=f"{source_kind} source",
        content="Battery recall regulator evidence fragment.",
        doc_type="statement" if source_kind == "official" else "news",
        canonical_url=f"https://example.test/{source_id}",
        content_hash=f"hash-{source_id}",
        source_kind=source_kind,
        authority_level="high" if source_kind == "official" else "medium",
        freshness_status="current",
        source_status="active",
        source_metadata={},
        created_at=_now(),
        updated_at=_now(),
    )


def _candidate(candidate_id: str = "10000000-0000-0000-0000-000000000010") -> SourceCandidateRecord:
    return SourceCandidateRecord(
        id=candidate_id,
        discovery_job_id="10000000-0000-0000-0000-000000000020",
        case_id="10000000-0000-0000-0000-000000000030",
        title="Community battery reports",
        url="https://example.test/community",
        canonical_url="https://example.test/community",
        source_type="social",
        language="en",
        region="US",
        provider="mock",
        provider_metadata={},
        content="Consumers report battery recall symptoms and timeline.",
        excerpt="Consumers report battery recall symptoms.",
        content_hash="candidate-hash",
        classification="social",
        claim_previews=[],
        stakeholder_previews=[],
        review_status=CandidateReviewStatus.PENDING,
        relevance=0.8,
        authority=0.45,
        freshness=0.9,
        claim_richness=0.7,
        diversity=1.0,
        grounding_value=0.75,
        total_score=0.76,
        created_at=_now(),
        updated_at=_now(),
    )


def _fragment(
    fragment_id: str,
    source_scope: str,
    source_id: str,
    text: str = "Battery recall regulator evidence fragment.",
) -> SourceFragmentRecord:
    return SourceFragmentRecord(
        id=fragment_id,
        source_scope=source_scope,
        global_source_id=source_id if source_scope == "global" else None,
        source_candidate_id=source_id if source_scope == "candidate" else None,
        fragment_index=0,
        fragment_text=text,
        content_hash=f"hash-{fragment_id}",
        embedding_model="local-token-hash",
        embedding_version="v1",
        embedding_vector=LocalSemanticIndex().embed(text),
        vector_index_id=f"{source_scope}:{source_id}:0",
        index_status="indexed",
        last_indexed_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )


def test_chunking_and_local_embedding_are_deterministic():
    fragments = chunk_source_text("Battery recall evidence. Regulator warning issued.")
    index = LocalSemanticIndex()

    assert [fragment.index for fragment in fragments] == [0]
    assert fragments[0].text == "Battery recall evidence. Regulator warning issued."
    assert index.embed(fragments[0].text) == index.embed(fragments[0].text)
    assert index.similarity(index.embed("battery recall"), index.embed(fragments[0].text)) > 0


def test_bounded_aggregation_does_not_sum_repeated_fragments():
    repeated_scores = [0.9, 0.9, 0.9, 0.9, 0.9]

    assert aggregate_semantic_support(repeated_scores, top_n=3) == 0.9
    assert aggregate_semantic_support([0.9, 0.6, 0.3], top_n=2) == 0.75


def test_diversity_rerank_preserves_strongest_match_and_mixed_coverage():
    repository = SourceLibraryRepository(database=object())  # type: ignore[arg-type]
    official_a = _global_source("10000000-0000-0000-0000-000000000001", "official")
    official_b = _global_source("10000000-0000-0000-0000-000000000002", "official")
    social = _global_source("10000000-0000-0000-0000-000000000003", "social")
    entries = [
        SourceSemanticRecommendationEntry(
            source_scope="global",
            source=official_a,
            candidate=None,
            assignments=[],
            usage_count=0,
            duplicate_candidate=False,
            already_in_case=False,
            semantic_support=0.99,
            final_score=0.9,
            matched_fragments=[],
            ranking_reasons=[],
        ),
        SourceSemanticRecommendationEntry(
            source_scope="global",
            source=official_b,
            candidate=None,
            assignments=[],
            usage_count=0,
            duplicate_candidate=False,
            already_in_case=False,
            semantic_support=0.86,
            final_score=0.88,
            matched_fragments=[],
            ranking_reasons=[],
        ),
        SourceSemanticRecommendationEntry(
            source_scope="global",
            source=social,
            candidate=None,
            assignments=[],
            usage_count=0,
            duplicate_candidate=False,
            already_in_case=False,
            semantic_support=0.84,
            final_score=0.85,
            matched_fragments=[],
            ranking_reasons=[],
        ),
    ]

    ranked = repository._diversity_rerank(entries)

    assert ranked[0].source is official_a
    assert ranked[1].source is social


class _FallbackRepository:
    async def list_case_topics(self, case_id: str):
        return []

    async def semantic_recommendations(self, case_id: str, query: str | None = None, limit: int = 12):
        return SourceSemanticRecallResult(
            applied=False,
            reason="no_indexed_fragments",
            query=query,
            indexed_fragment_count=0,
            matched_fragment_count=0,
            entries=[],
        )

    async def related_topic_ids(self, topic_ids: list[str]):
        return []

    async def list_registry(self, **kwargs):
        return []


def test_case_selection_returns_semantic_fallback_metadata():
    service = SourceLibraryService(repository=_FallbackRepository())  # type: ignore[arg-type]

    response = asyncio.run(service.get_case_selection("case-123", query="battery recall"))

    assert response.semantic_recall.applied is False
    assert response.semantic_recall.reason == "no_indexed_fragments"
    assert [section.key for section in response.sections] == [
        "recommended",
        "semantic_matches",
        "same_topic",
        "related",
        "global_search",
        "manual_upload",
    ]


def test_candidate_semantic_recommendation_preserves_review_status_and_scope():
    candidate = _candidate()
    fragment = _fragment(
        "10000000-0000-0000-0000-000000000040",
        "candidate",
        str(candidate.id),
        text=candidate.content,
    )
    entry = SourceSemanticRecommendationEntry(
        source_scope="candidate",
        source=None,
        candidate=candidate,
        assignments=[],
        usage_count=0,
        duplicate_candidate=False,
        already_in_case=False,
        semantic_support=0.82,
        final_score=0.77,
        matched_fragments=[
            SourceFragmentMatch(
                fragment=fragment,
                source_scope="candidate",
                source_id=str(candidate.id),
                similarity=0.82,
            )
        ],
        ranking_reasons=[],
    )

    response = SourceLibraryService._semantic_source_response(entry)

    assert response.source_scope == "candidate"
    assert response.candidate_id == str(candidate.id)
    assert response.candidate_review_status == "pending"
    assert response.already_in_case is False
    assert response.matched_fragments[0].source_scope == "candidate"
