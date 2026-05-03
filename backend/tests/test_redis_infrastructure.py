from __future__ import annotations

import asyncio

import httpx

from backend.domain.models import Job, JobStatus
from backend.entrypoints.api.main import create_app
from backend.services.job_dispatcher import RedisJobDispatcher
from backend.services.llm_client import LlmJsonClient
from backend.services.source_discovery_contracts import SourceDiscoveryJobPayload
from backend.services.source_discovery_service import (
    CachedContentFetcher,
    CachedSearchProvider,
    FetchedContent,
    SearchResult,
)
from backend.services.worker import WorkerRuntime
from backend.shared.cache_keys import stable_cache_key
from backend.shared.config import BackendConfig
from backend.shared.redis_client import InMemoryRedisClient


class _FakeDb:
    async def ping(self) -> None:
        return None

    async def dispose(self) -> None:
        return None


class _FakeRepo:
    async def get_status_counts(self) -> dict:
        return {"pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}


class _FakeSimulationService:
    def __init__(self) -> None:
        self.calls = 0

    async def submit(self, request):
        self.calls += 1

        class _Response:
            def model_dump(self):
                return {
                    "run_id": "run-123",
                    "job_id": "job-123",
                    "job_status": "pending",
                    "run_status": "pending",
                    "job_status_path": "/api/jobs/job-123",
                    "status_path": "/api/simulation-runs/run-123",
                }

        return _Response()

    async def get_job_status(self, job_id: str):
        raise AssertionError("not used")

    async def get_run_status(self, run_id: str):
        raise AssertionError("not used")


class _FakeExtractionService:
    async def submit(self, request):
        raise AssertionError("not used")

    async def get_status(self, job_id: str):
        raise AssertionError("not used")


class _FakeAgentGenerationService:
    async def generate(self, request):
        raise AssertionError("not used")


def _build_config(**overrides: object) -> BackendConfig:
    values: dict[str, object] = {
        "app_name": "backend-test",
        "app_env": "test",
        "database_url": "postgresql+asyncpg://localhost/db",
        "source_discovery_search_provider": "mock",
        "semantic_embedding_provider": "local",
    }
    values.update(overrides)
    return BackendConfig(**values)


async def _send_request(app, method: str, path: str, json: dict | None = None, headers: dict[str, str] | None = None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, json=json, headers=headers)


def test_rate_limited_api_returns_429_and_skips_handler():
    redis_client = InMemoryRedisClient()
    simulation_service = _FakeSimulationService()
    app = create_app(
        _build_config(
            redis_enabled=True,
            redis_rate_limit_enabled=True,
            redis_rate_limit_simulations=1,
            redis_rate_limit_window_seconds=60,
        ),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=simulation_service,
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
        redis_client=redis_client,
    )

    payload = {"case_id": "case-123", "run_type": "baseline", "total_rounds": 3}
    first = asyncio.run(_send_request(app, "POST", "/api/simulations", json=payload))
    second = asyncio.run(_send_request(app, "POST", "/api/simulations", json=payload))

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"
    assert second.headers["retry-after"] == "60"
    assert simulation_service.calls == 1


def test_rate_limiter_uses_authenticated_subject_key_when_available():
    redis_client = InMemoryRedisClient()
    simulation_service = _FakeSimulationService()
    app = create_app(
        _build_config(
            redis_enabled=True,
            redis_rate_limit_enabled=True,
            redis_rate_limit_simulations=1,
            redis_rate_limit_window_seconds=60,
        ),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=simulation_service,
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
        redis_client=redis_client,
    )

    payload = {"case_id": "case-123", "run_type": "baseline", "total_rounds": 3}
    token_a = "header.eyJzdWIiOiAidXNlci1hIn0.signature"
    token_b = "header.eyJzdWIiOiAidXNlci1iIn0.signature"
    first = asyncio.run(_send_request(app, "POST", "/api/simulations", json=payload, headers={"Authorization": f"Bearer {token_a}"}))
    second = asyncio.run(_send_request(app, "POST", "/api/simulations", json=payload, headers={"Authorization": f"Bearer {token_b}"}))

    assert first.status_code == 200
    assert second.status_code == 200
    assert simulation_service.calls == 2


def test_optional_redis_rate_limit_failure_degrades_open():
    redis_client = InMemoryRedisClient(fail_operations=True)
    simulation_service = _FakeSimulationService()
    app = create_app(
        _build_config(
            redis_enabled=True,
            redis_requirement_mode="optional",
            redis_rate_limit_enabled=True,
            redis_rate_limit_simulations=1,
        ),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=simulation_service,
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
        redis_client=redis_client,
    )

    payload = {"case_id": "case-123", "run_type": "baseline", "total_rounds": 3}
    response = asyncio.run(_send_request(app, "POST", "/api/simulations", json=payload))

    assert response.status_code == 200
    assert simulation_service.calls == 1


def test_ops_reports_non_secret_redis_status():
    app = create_app(
        _build_config(
            redis_enabled=True,
            redis_rate_limit_enabled=True,
            redis_cache_enabled=True,
            redis_stream_dispatch_enabled=True,
        ),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
        redis_client=InMemoryRedisClient(),
    )

    response = asyncio.run(_send_request(app, "GET", "/ops"))

    assert response.status_code == 200
    assert response.json()["redis"] == {
        "enabled": True,
        "requirement_mode": "optional",
        "status": "available",
        "features": {"rate_limit": True, "cache": True, "stream_dispatch": True},
    }
    assert "redis://127.0.0.1" not in response.text


def test_required_redis_readiness_reports_dependency_failure_when_unavailable():
    app = create_app(
        _build_config(redis_enabled=True, redis_requirement_mode="required"),
        database=_FakeDb(),
        repository=_FakeRepo(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
        agent_generation_service=_FakeAgentGenerationService(),
        redis_client=InMemoryRedisClient(fail_operations=True),
    )

    response = asyncio.run(_send_request(app, "GET", "/health/ready"))

    assert response.status_code == 503
    assert response.json()["error"]["details"]["dependency"] == "redis"


class _CountingLlmClient(LlmJsonClient):
    def __init__(self, config: BackendConfig, redis_client: InMemoryRedisClient) -> None:
        super().__init__(config, redis_client=redis_client)
        self.calls = 0

    async def _request_json(self, prompt: str, temperature: float):
        self.calls += 1
        return {"answer": prompt, "temperature": temperature}


def test_llm_json_cache_hits_after_first_successful_call():
    redis_client = InMemoryRedisClient()
    client = _CountingLlmClient(
        _build_config(
            redis_enabled=True,
            redis_cache_enabled=True,
            redis_cache_llm_ttl_seconds=60,
            llm_api_key="test-key",
            llm_model="test-model",
        ),
        redis_client,
    )

    first = asyncio.run(client.chat_json("same prompt", temperature=0.1))
    second = asyncio.run(client.chat_json("same prompt", temperature=0.1))

    assert first == second
    assert client.calls == 1


class _CountingSearchProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: str, request: SourceDiscoveryJobPayload) -> list[SearchResult]:
        self.calls += 1
        return [SearchResult(title="Title", url="https://example.test/a", snippet=query, source_type="news")]


class _CountingContentFetcher:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, result: SearchResult) -> FetchedContent:
        self.calls += 1
        return FetchedContent(content=f"{result.title} body", excerpt=result.title, metadata={"status": "ok"})


def test_search_and_content_cache_hit_after_first_call():
    redis_client = InMemoryRedisClient()
    config = _build_config(redis_enabled=True, redis_cache_enabled=True)
    request = SourceDiscoveryJobPayload(
        job_id="job-123",
        source_discovery_job_id="discovery-123",
        case_id="case-123",
        topic="topic",
        description="description",
        region="global",
        language="en",
        time_range="anytime",
        source_types=["news"],
        max_sources=3,
    )
    search = _CountingSearchProvider()
    fetcher = _CountingContentFetcher()
    cached_search = CachedSearchProvider(search, redis_client, 60, "counting", config)
    cached_fetcher = CachedContentFetcher(fetcher, redis_client, 60, "counting", config)

    first_results = asyncio.run(cached_search.search("topic", request))
    second_results = asyncio.run(cached_search.search("topic", request))
    first_content = asyncio.run(cached_fetcher.fetch(first_results[0]))
    second_content = asyncio.run(cached_fetcher.fetch(second_results[0]))

    assert [result.title for result in first_results] == [result.title for result in second_results]
    assert first_content.content == second_content.content
    assert search.calls == 1
    assert fetcher.calls == 1


def test_stable_cache_key_hashes_variable_payloads():
    key = stable_cache_key("llm/json", {"prompt": "secret-ish long prompt", "model": "m"})

    assert key.startswith("genai:llm_json:v1:")
    assert "secret-ish" not in key
    assert len(key.rsplit(":", 1)[-1]) == 64


class _WorkerRepo:
    def __init__(self) -> None:
        self.claimed: list[str] = []
        self.completed: list[str] = []
        self.polled = 0

    async def claim_pending_job(self, job_id: str, worker_id: str):
        self.claimed.append(job_id)
        return Job(id=job_id, job_type="test.job", status=JobStatus.RUNNING, payload={})

    async def claim_next_pending_job(self, worker_id: str):
        self.polled += 1
        return None

    async def mark_running_complete(self, job_id: str, result: dict | None = None):
        self.completed.append(job_id)

    async def mark_running_failed(self, job_id: str, code: str, message: str):
        raise AssertionError("not used")


def test_worker_consumes_redis_stream_job_and_acks_after_completion():
    redis_client = InMemoryRedisClient()
    dispatcher = RedisJobDispatcher(
        _build_config(redis_enabled=True, redis_stream_dispatch_enabled=True),
        redis_client,
    )
    repo = _WorkerRepo()
    handled: list[str] = []

    async def _handler(job: Job):
        handled.append(str(job.id))
        return {"ok": True}

    async def _run():
        await dispatcher.publish_job(Job(id="job-123", job_type="test.job", status=JobStatus.PENDING, payload={}))
        worker = WorkerRuntime(
            repository=repo,
            worker_id="worker-1",
            handlers={"test.job": _handler},
            job_dispatcher=dispatcher,
            poll_interval_seconds=0.01,
        )
        first = await worker.loop_once()
        second = await worker.loop_once()
        return first, second

    first_had_work, second_had_work = asyncio.run(_run())

    assert first_had_work is True
    assert second_had_work is False
    assert repo.claimed == ["job-123"]
    assert repo.completed == ["job-123"]
    assert handled == ["job-123"]


def test_worker_falls_back_to_postgres_polling_when_stream_dispatch_disabled():
    repo = _WorkerRepo()
    worker = WorkerRuntime(
        repository=repo,
        worker_id="worker-1",
        handlers={},
        poll_interval_seconds=0.01,
    )

    had_work = asyncio.run(worker.loop_once())

    assert had_work is False
    assert repo.polled == 1
