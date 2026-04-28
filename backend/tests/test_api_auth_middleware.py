from __future__ import annotations

import asyncio

import httpx

from backend.entrypoints.api.main import create_app
from backend.shared.config import BackendConfig


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
        raise AssertionError("graph extraction submit should not be called")

    async def get_status(self, job_id: str):
        raise AssertionError("graph extraction status should not be called")


class _FakeAgentGenerationService:
    async def generate(self, request):
        raise AssertionError("agent generation should not be called")


def _build_config(**overrides: object) -> BackendConfig:
    defaults: dict[str, object] = {
        "app_name": "backend-test",
        "app_env": "test",
        "database_url": "postgresql+asyncpg://localhost/db",
        "host": "127.0.0.1",
        "port": 9000,
        "cors_origins": "https://frontend.example",
        "product_auth_mode": "require_bearer",
        "source_discovery_search_provider": "mock",
        "semantic_embedding_provider": "local",
    }
    defaults.update(overrides)
    return BackendConfig(**defaults)


def _build_app(**config_overrides: object):
    return create_app(
        _build_config(**config_overrides),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
    )


async def _send_request(app, method: str, path: str, headers: dict[str, str] | None = None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, headers=headers)


def test_preflight_options_bypasses_bearer_enforcement_for_api_routes():
    app = _build_app()
    response = asyncio.run(
        _send_request(
            app,
            "OPTIONS",
            "/api/simulations",
            headers={
                "Origin": "https://frontend.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,x-request-id",
            },
        )
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"
    assert response.headers["x-request-id"]


def test_api_routes_still_require_bearer_when_auth_mode_is_enforced():
    app = _build_app()
    response = asyncio.run(_send_request(app, "POST", "/api/simulations"))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Authorization header is required for product API requests."
