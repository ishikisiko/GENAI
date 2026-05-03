from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.db import Database
from backend.domain.models import JobAttemptStatus, JobStatus
from backend.repository.job_repository import JobRepository
from backend.scripts.migrate import _run as run_migrations
from backend.services.job_dispatcher import RedisJobDispatcher
from backend.services.worker import WorkerRuntime
from backend.shared.config import BackendConfig
from backend.shared.redis_client import AsyncRedisClient


pytestmark = pytest.mark.integration


def _integration_env() -> tuple[str, str]:
    if os.getenv("RUN_BACKEND_INTEGRATION") != "1":
        pytest.skip("Set RUN_BACKEND_INTEGRATION=1 to run backend integration tests.")
    database_url = os.getenv("BACKEND_INTEGRATION_DATABASE_URL")
    redis_url = os.getenv("BACKEND_INTEGRATION_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip("Set BACKEND_INTEGRATION_DATABASE_URL and BACKEND_INTEGRATION_REDIS_URL.")
    return database_url, redis_url


@pytest.mark.asyncio
async def test_postgres_jobs_and_real_redis_stream_dispatch(tmp_path: Path):
    database_url, redis_url = _integration_env()
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    source_migrations = Path(__file__).resolve().parents[2] / "migrations"
    for migration_name in ("0001_init_jobs_schema.sql", "0002_job_heartbeats.sql"):
        (migrations_dir / migration_name).write_text(
            (source_migrations / migration_name).read_text(),
            encoding="utf-8",
        )
    await run_migrations(database_url, migrations_dir)

    database = Database(database_url)
    redis_client = AsyncRedisClient(redis_url, timeout_seconds=2.0)
    stream_name = "genai:integration:jobs"
    group_name = "genai-integration-workers"
    config = BackendConfig(
        app_name="backend-integration-test",
        app_env="test",
        database_url=database_url,
        redis_enabled=True,
        redis_url=redis_url,
        redis_stream_dispatch_enabled=True,
        redis_stream_name=stream_name,
        redis_stream_group=group_name,
        redis_stream_read_block_ms=100,
        source_discovery_search_provider="mock",
        semantic_embedding_provider="local",
    )
    repository = JobRepository(database)
    dispatcher = RedisJobDispatcher(config, redis_client)
    handled: list[str] = []
    created_job_id: str | None = None

    async def handler(job):
        handled.append(str(job.id))
        return {"integration": True}

    try:
        assert await redis_client.ping() is True
        job = await repository.create_job(
            job_type="integration.job",
            payload={"source": "backend-integration"},
            max_attempts=1,
        )
        created_job_id = str(job.id)
        await dispatcher.publish_job(job)

        worker = WorkerRuntime(
            repository=repository,
            worker_id="worker-integration",
            handlers={"integration.job": handler},
            job_dispatcher=dispatcher,
            poll_interval_seconds=0.01,
        )
        assert await worker.loop_once() is True
        assert await worker.loop_once() is False

        completed_job = await repository.get_job(created_job_id)
        attempt = await repository.get_latest_attempt(created_job_id)
        assert str(completed_job.id) == created_job_id
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.attempt_count == 1
        assert attempt is not None
        assert attempt.status == JobAttemptStatus.COMPLETED
        assert handled == [created_job_id]
    finally:
        if created_job_id is not None:
            async with database.session() as session:
                await session.execute(
                    text("DELETE FROM jobs WHERE id = CAST(:job_id AS uuid)"),
                    {"job_id": created_job_id},
                )
        await redis_client.close()
        await database.dispose()
