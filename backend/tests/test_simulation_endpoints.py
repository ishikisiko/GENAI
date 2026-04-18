from __future__ import annotations

import asyncio

from backend.entrypoints.api.main import create_app
from backend.shared.config import BackendConfig
from backend.services.simulation_contracts import SimulationSubmissionRequest


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
        class _Response:
            def model_dump(self):
                return {
                    "run_id": "run-123",
                    "job_id": "job-123",
                    "job_status": "pending",
                    "run_status": "pending",
                }

        return _Response()

    async def get_job_status(self, job_id: str):
        class _Response:
            def model_dump(self):
                return {
                    "id": job_id,
                    "job_type": "simulation.run",
                    "status": "running",
                    "run_id": "run-123",
                    "last_error": None,
                    "last_error_code": None,
                    "locked_at": None,
                    "heartbeat_at": None,
                    "updated_at": None,
                    "created_at": None,
                }

        return _Response()

    async def get_run_status(self, run_id: str):
        class _Response:
            def model_dump(self, mode: str = "python"):
                return {
                    "id": run_id,
                    "job_id": "job-123",
                    "status": "running",
                    "error_message": None,
                    "total_rounds": 5,
                    "completed_rounds": 2,
                    "last_completed_round": 2,
                    "last_heartbeat_at": None,
                    "created_at": "2026-04-17T00:00:00+00:00",
                    "completed_at": None,
                    "should_poll": True,
                }

        return _Response()


def _build_config():
    return BackendConfig(
        app_name="backend-test",
        app_env="test",
        database_url="postgresql+asyncpg://localhost/db",
        host="127.0.0.1",
        port=9000,
    )


def _get_endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


def test_submit_simulation_endpoint_returns_ids():
    app = create_app(
        _build_config(),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
    )
    endpoint = _get_endpoint(app, "/api/simulations", "POST")

    response = asyncio.run(
        endpoint(
            SimulationSubmissionRequest(
                case_id="case-123",
                run_type="baseline",
                total_rounds=5,
            )
        )
    )
    assert response["job_id"] == "job-123"
    assert response["run_id"] == "run-123"


def test_job_and_run_status_endpoints_are_poll_friendly():
    app = create_app(
        _build_config(),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
    )
    job_endpoint = _get_endpoint(app, "/api/jobs/{job_id}", "GET")
    run_endpoint = _get_endpoint(app, "/api/simulation-runs/{run_id}", "GET")

    job_response = asyncio.run(job_endpoint("job-123"))
    run_response = asyncio.run(run_endpoint("run-123"))

    assert job_response["run_id"] == "run-123"
    assert run_response["completed_rounds"] == 2
    assert run_response["should_poll"] is True
