from __future__ import annotations

import asyncio

from backend.entrypoints.api.main import create_app
from backend.shared.config import BackendConfig
from backend.services.extraction_contracts import GraphExtractionSubmissionRequest


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


class _FakeExtractionService:
    async def submit(self, request):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "accepted",
                    "case_id": request.case_id,
                    "job_id": "job-graph-123",
                    "job_type": "graph.extract",
                    "job_status": "pending",
                    "job_status_path": "/api/jobs/job-graph-123",
                    "status_path": "/api/graph-extractions/job-graph-123",
                    "should_poll": True,
                    "document_count": 3,
                }

        return _Response()

    async def get_status(self, job_id: str):
        class _Response:
            def model_dump(self):
                return {
                    "outcome": "status",
                    "job_id": job_id,
                    "case_id": "case-123",
                    "job_type": "graph.extract",
                    "status": "running",
                    "job_status_path": f"/api/jobs/{job_id}",
                    "status_path": f"/api/graph-extractions/{job_id}",
                    "document_count": 3,
                    "processed_documents": 1,
                    "failed_documents": 0,
                    "entities_count": 0,
                    "relations_count": 0,
                    "claims_count": 0,
                    "last_error": None,
                    "last_error_code": None,
                    "created_at": "2026-04-18T00:00:00+00:00",
                    "updated_at": "2026-04-18T00:00:05+00:00",
                    "should_poll": True,
                }

        return _Response()


def _get_endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


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


def test_submit_graph_extraction_endpoint_returns_job_metadata():
    app = create_app(
        _build_config(),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
    )
    endpoint = _get_endpoint(app, "/api/graph-extractions", "POST")
    response = asyncio.run(endpoint(GraphExtractionSubmissionRequest(case_id="case-123")))

    assert response["job_id"] == "job-graph-123"
    assert response["document_count"] == 3
    assert response["job_status_path"] == "/api/jobs/job-graph-123"
    assert response["status_path"] == "/api/graph-extractions/job-graph-123"


def test_graph_extraction_status_endpoint_is_poll_friendly():
    app = create_app(
        _build_config(),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
    )
    endpoint = _get_endpoint(app, "/api/graph-extractions/{job_id}", "GET")
    response = asyncio.run(endpoint("job-graph-123"))

    assert response["job_type"] == "graph.extract"
    assert response["should_poll"] is True
