from __future__ import annotations

from fastapi.testclient import TestClient

from backend.entrypoints.api.main import create_app
from backend.shared.config import BackendConfig


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
    )


def test_liveness_and_readiness_success():
    app = create_app(_build_config(), database=_FakeDb(), repository=_FakeRepo())
    client = TestClient(app)

    assert client.get("/health/live").status_code == 200
    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 200


def test_readiness_reports_dependency_error():
    app = create_app(_build_config(), database=_FakeDb(fail=True), repository=_FakeRepo())
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EXTERNAL_DEPENDENCY_ERROR"
