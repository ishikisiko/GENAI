from __future__ import annotations

import asyncio

import pytest

from backend.entrypoints.api.main import create_app
from backend.services.source_discovery_contracts import (
    EvidencePackCreateRequest,
    SourceCandidateLibrarySaveRequest,
    SourceCandidateReviewRequest,
    SourceDiscoveryJobCreateRequest,
)
from backend.services.source_library_contracts import (
    AttachGlobalSourceRequest,
    SourceTopicAssignmentCreateRequest,
    SourceTopicCreateRequest,
)
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, ErrorCode


class _FakeDb:
    async def ping(self) -> None:
        return None

    async def dispose(self) -> None:
        return None


class _FakeRepo:
    async def get_status_counts(self) -> dict:
        return {"pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}


class _FakeSimulationService:
    async def submit(self, request):
        raise AssertionError("simulation submit should not be called")

    async def get_job_status(self, job_id: str):
        raise AssertionError("simulation job status should not be called")

    async def get_run_status(self, run_id: str):
        raise AssertionError("simulation run status should not be called")


class _FakeSourceDiscoveryService:
    async def submit(self, request):
        if request.case_id == "missing":
            raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

        class _Response:
            def model_dump(self):
                return {
                    "outcome": "accepted",
                    "source_discovery_job_id": "discovery-123",
                    "case_id": request.case_id,
                    "job_id": "job-123",
                    "job_type": "source_discovery.run",
                    "status": "pending",
                    "job_status": "pending",
                    "job_status_path": "/api/jobs/job-123",
                    "status_path": "/api/source-discovery/jobs/discovery-123",
                    "should_poll": True,
                    "topic": request.topic,
                    "description": request.description,
                    "region": request.region,
                    "language": request.language,
                    "time_range": request.time_range,
                    "source_types": request.source_types,
                    "max_sources": request.max_sources,
                    "query_plan": [],
                    "candidate_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "last_error": None,
                    "last_error_code": None,
                    "created_at": None,
                    "updated_at": None,
                    "completed_at": None,
                }

        return _Response()

    async def get_status(self, job_id: str):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "status",
                    "source_discovery_job_id": job_id,
                    "case_id": "case-123",
                    "job_id": "job-123",
                    "job_type": "source_discovery.run",
                    "status": "completed",
                    "job_status": "completed",
                    "job_status_path": "/api/jobs/job-123",
                    "status_path": f"/api/source-discovery/jobs/{job_id}",
                    "should_poll": False,
                    "topic": "Recall",
                    "description": "",
                    "region": "US",
                    "language": "en",
                    "time_range": "last_30_days",
                    "source_types": ["news"],
                    "max_sources": 5,
                    "query_plan": ["Recall US"],
                    "candidate_count": 1,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "last_error": None,
                    "last_error_code": None,
                    "created_at": None,
                    "updated_at": None,
                    "completed_at": None,
                }

        return _Response()

    async def list_candidates(self, case_id=None, discovery_job_id=None, review_status=None):
        class _Response:
            def model_dump(self):
                return {"outcome": "completed", "candidates": [{"id": "candidate-1", "total_score": 0.9}]}

        return _Response()

    async def update_candidate_review(self, source_id: str, request):
        class _Response:
            def model_dump(self):
                return {"id": source_id, "review_status": request.review_status}

        return _Response()

    async def create_evidence_pack(self, request):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "created",
                    "evidence_pack_id": "pack-123",
                    "case_id": request.case_id,
                    "source_count": 1,
                    "evidence_pack": {"id": "pack-123", "sources": []},
                }

        return _Response()

    async def get_evidence_pack(self, evidence_pack_id: str):
        class _Response:
            def model_dump(self):
                return {"id": evidence_pack_id, "case_id": "case-123", "sources": []}

        return _Response()

    async def start_grounding(self, evidence_pack_id: str):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "accepted",
                    "evidence_pack_id": evidence_pack_id,
                    "case_id": "case-123",
                    "job_id": "job-graph-123",
                    "job_type": "graph.extract",
                    "job_status": "pending",
                    "job_status_path": "/api/jobs/job-graph-123",
                    "status_path": "/api/graph-extractions/job-graph-123",
                    "document_count": 1,
                    "materialized_document_count": 1,
                    "should_poll": True,
                }

        return _Response()


class _FakeSourceLibraryService:
    async def list_topics(self):
        class _Response:
            def model_dump(self):
                return {"outcome": "completed", "topics": [{"id": "topic-1", "name": "Recalls"}]}

        return _Response()

    async def create_topic(self, request):
        class _Response:
            def model_dump(self):
                return {
                    "id": "topic-1",
                    "name": request.name,
                    "description": request.description,
                    "parent_topic_id": request.parent_topic_id,
                    "topic_type": request.topic_type,
                    "status": "active",
                    "created_at": "2026-04-26T00:00:00+00:00",
                    "updated_at": "2026-04-26T00:00:00+00:00",
                }

        return _Response()

    async def get_topic(self, topic_id: str):
        class _Response:
            def model_dump(self):
                return {"id": topic_id, "name": "Recalls", "status": "active"}

        return _Response()

    async def update_topic(self, topic_id: str, request):
        class _Response:
            def model_dump(self):
                return {"id": topic_id, "name": request.name or "Recalls", "status": request.status or "active"}

        return _Response()

    async def create_case_topic(self, request):
        class _Response:
            def model_dump(self):
                return {"id": "case-topic-1", "case_id": request.case_id, "topic_id": request.topic_id}

        return _Response()

    async def create_assignment(self, request):
        class _Response:
            def model_dump(self):
                return {
                    "id": "assignment-1",
                    "global_source_id": request.global_source_id,
                    "topic_id": request.topic_id,
                    "relevance_score": request.relevance_score,
                    "status": "active",
                }

        return _Response()

    async def remove_assignment(self, assignment_id: str):
        class _Response:
            def model_dump(self):
                return {"id": assignment_id, "status": "inactive"}

        return _Response()

    async def list_registry(self, **kwargs):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "completed",
                    "topic_id": kwargs.get("topic_id"),
                    "smart_view": kwargs.get("smart_view"),
                    "sources": [{"id": "source-1", "title": "Official source", "already_in_case": False}],
                }

        return _Response()

    async def get_usage(self, global_source_id: str):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "completed",
                    "global_source_id": global_source_id,
                    "topic_assignments": [],
                    "cases": [],
                    "usage_count": 0,
                }

        return _Response()

    async def get_case_selection(self, case_id: str, query: str | None = None):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "completed",
                    "case_id": case_id,
                    "case_topics": [],
                    "semantic_recall": {
                        "applied": True,
                        "reason": None,
                        "query": query or "Recall case",
                        "indexed_fragment_count": 3,
                        "matched_fragment_count": 1,
                    },
                    "sections": [
                        {
                            "key": "recommended",
                            "sources": [
                                {
                                    "id": "source-1",
                                    "source_scope": "global",
                                    "global_source_id": "source-1",
                                    "candidate_id": None,
                                    "candidate_review_status": None,
                                    "title": "Official source",
                                    "semantic_support": 0.82,
                                    "matched_fragments": [
                                        {
                                            "id": "fragment-1",
                                            "source_scope": "global",
                                            "source_id": "source-1",
                                            "fragment_index": 0,
                                            "text": "Recall evidence",
                                            "similarity": 0.82,
                                            "content_hash": "hash",
                                        }
                                    ],
                                    "ranking_reasons": [
                                        {
                                            "key": "semantic_support",
                                            "label": "Semantic support",
                                            "value": "82 match",
                                            "score": 0.82,
                                        }
                                    ],
                                    "already_in_case": False,
                                }
                            ],
                        }
                    ],
                }

        return _Response()

    async def attach_global_source(self, request):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "created",
                    "id": "doc-1",
                    "case_id": request.case_id,
                    "global_source_id": request.global_source_id,
                }

        return _Response()

    async def save_candidate_to_library(self, source_id: str, request):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "saved",
                    "candidate_id": source_id,
                    "global_source_id": "global-1",
                    "topic_id": request.topic_id,
                    "topic_assignment_id": "assignment-1" if request.topic_id else None,
                    "duplicate_reused": False,
                }

        return _Response()


def _build_config():
    return BackendConfig(
        app_name="backend-test",
        app_env="test",
        database_url="postgresql+asyncpg://localhost/db",
        host="127.0.0.1",
        port=9000,
        source_discovery_search_provider="mock",
        semantic_embedding_provider="local",
    )


def _get_endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


def _build_app():
    return create_app(
        _build_config(),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        source_discovery_service=_FakeSourceDiscoveryService(),
        source_library_service=_FakeSourceLibraryService(),
    )


def test_create_source_discovery_job_endpoint_returns_status_paths():
    endpoint = _get_endpoint(_build_app(), "/api/source-discovery/jobs", "POST")

    response = asyncio.run(
        endpoint(
            SourceDiscoveryJobCreateRequest(
                case_id="case-123",
                topic="Product recall",
                description="Battery fire reports",
                region="US",
                language="en",
                time_range="last_30_days",
                source_types=["news", "official"],
                max_sources=8,
            )
        )
    )

    assert response["source_discovery_job_id"] == "discovery-123"
    assert response["job_id"] == "job-123"
    assert response["status_path"] == "/api/source-discovery/jobs/discovery-123"


def test_create_source_discovery_job_rejects_missing_case():
    endpoint = _get_endpoint(_build_app(), "/api/source-discovery/jobs", "POST")

    with pytest.raises(ApplicationError):
        asyncio.run(endpoint(SourceDiscoveryJobCreateRequest(case_id="missing", topic="Product recall")))


def test_candidate_and_evidence_pack_endpoints_are_wired():
    app = _build_app()
    list_endpoint = _get_endpoint(app, "/api/source-candidates", "GET")
    patch_endpoint = _get_endpoint(app, "/api/source-candidates/{source_id}", "PATCH")
    pack_endpoint = _get_endpoint(app, "/api/evidence-packs", "POST")
    grounding_endpoint = _get_endpoint(app, "/api/evidence-packs/{evidence_pack_id}/start-grounding", "POST")

    candidates = asyncio.run(list_endpoint(case_id="case-123", discovery_job_id="discovery-123", review_status=None))
    updated = asyncio.run(patch_endpoint("candidate-1", SourceCandidateReviewRequest(review_status="accepted")))
    pack = asyncio.run(
        pack_endpoint(
            EvidencePackCreateRequest(
                case_id="case-123",
                discovery_job_id="discovery-123",
                candidate_ids=["candidate-1"],
            )
        )
    )
    grounding = asyncio.run(grounding_endpoint("pack-123"))

    assert candidates["candidates"][0]["id"] == "candidate-1"
    assert updated["review_status"] == "accepted"
    assert pack["evidence_pack_id"] == "pack-123"
    assert grounding["job_type"] == "graph.extract"


def test_source_library_topic_and_registry_endpoints_are_wired():
    app = _build_app()
    create_topic_endpoint = _get_endpoint(app, "/api/source-topics", "POST")
    list_registry_endpoint = _get_endpoint(app, "/api/source-registry", "GET")
    assignment_endpoint = _get_endpoint(app, "/api/source-topic-assignments", "POST")
    selection_endpoint = _get_endpoint(app, "/api/cases/{case_id}/source-selection", "GET")
    attach_endpoint = _get_endpoint(app, "/api/cases/{case_id}/source-documents/from-library", "POST")

    topic = asyncio.run(create_topic_endpoint(SourceTopicCreateRequest(name="Recalls", topic_type="crisis")))
    registry = asyncio.run(list_registry_endpoint(topic_id="topic-1", smart_view=None))
    assignment = asyncio.run(
        assignment_endpoint(SourceTopicAssignmentCreateRequest(global_source_id="source-1", topic_id="topic-1"))
    )
    selection = asyncio.run(selection_endpoint("case-123", query=None))
    attached = asyncio.run(
        attach_endpoint(
            "case-123",
            AttachGlobalSourceRequest(case_id="case-123", global_source_id="source-1", topic_id="topic-1"),
        )
    )

    assert topic["id"] == "topic-1"
    assert registry["sources"][0]["id"] == "source-1"
    assert assignment["topic_id"] == "topic-1"
    assert selection["sections"][0]["key"] == "recommended"
    assert attached["global_source_id"] == "source-1"


def test_source_selection_endpoint_returns_semantic_recommendation_contract():
    selection_endpoint = _get_endpoint(_build_app(), "/api/cases/{case_id}/source-selection", "GET")

    selection = asyncio.run(selection_endpoint("case-123", query="battery recall"))
    source = selection["sections"][0]["sources"][0]

    assert selection["semantic_recall"]["applied"] is True
    assert source["source_scope"] == "global"
    assert source["semantic_support"] == 0.82
    assert source["matched_fragments"][0]["text"] == "Recall evidence"
    assert source["ranking_reasons"][0]["key"] == "semantic_support"


def test_source_candidate_save_to_library_endpoint_is_explicit():
    endpoint = _get_endpoint(_build_app(), "/api/source-candidates/{source_id}/save-to-library", "POST")

    response = asyncio.run(
        endpoint("candidate-1", SourceCandidateLibrarySaveRequest(topic_id="topic-1", reason="Relevant source"))
    )

    assert response["candidate_id"] == "candidate-1"
    assert response["topic_assignment_id"] == "assignment-1"
