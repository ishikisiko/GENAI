from __future__ import annotations

import asyncio

from backend.entrypoints.api.main import create_app
from backend.shared.config import BackendConfig
from backend.shared.errors import DependencyError


class _FakeDb:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.ping_called = False

    async def ping(self) -> None:
        self.ping_called = True
        if self.fail:
            raise RuntimeError("database unavailable")

    async def dispose(self) -> None:
        return None


class _FakeRepo:
    async def get_status_counts(self) -> dict:
        return {"pending": 1, "running": 0, "completed": 2, "failed": 0, "cancelled": 0}


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


def test_liveness_and_readiness_success():
    fake_db = _FakeDb()
    app = create_app(_build_config(), database=fake_db, repository=_FakeRepo())
    live_endpoint = _get_endpoint(app, "/health/live", "GET")
    ready_endpoint = _get_endpoint(app, "/health/ready", "GET")

    assert asyncio.run(live_endpoint()) == {"status": "ok", "service": "backend-test"}
    assert asyncio.run(ready_endpoint()) == {"status": "ready", "service": "backend-test"}
    assert fake_db.ping_called is True


def test_readiness_reports_dependency_error():
    app = create_app(_build_config(), database=_FakeDb(fail=True), repository=_FakeRepo())
    ready_endpoint = _get_endpoint(app, "/health/ready", "GET")

    try:
        asyncio.run(ready_endpoint())
    except DependencyError as exc:
        assert exc.status_code == 503
        assert exc.code.value == "EXTERNAL_DEPENDENCY_ERROR"
    else:
        raise AssertionError("Expected readiness endpoint to raise DependencyError")
