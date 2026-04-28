from __future__ import annotations

import asyncio

from backend.entrypoints.worker.main import build_worker


class _FakeJobRepository:
    async def claim_next_pending_job(self, worker_id: str):
        return None


class _FakeSimulationService:
    async def recover_stale_jobs(self):
        return 0

    async def handle_job(self, job):
        return None


class _FakeExtractionService:
    async def handle_job(self, job):
        return None


class _FakeSourceDiscoveryService:
    async def handle_job(self, job):
        return None


class _FakeSourceLibraryRepository:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    async def index_stale_source_fragments(self, limit: int):
        self.batch_sizes.append(limit)
        return 2


def test_worker_runs_semantic_fragment_maintenance_when_configured():
    source_library_repository = _FakeSourceLibraryRepository()
    worker = build_worker(
        runtime_id="worker-test",
        repository=_FakeJobRepository(),
        simulation_service=_FakeSimulationService(),
        extraction_service=_FakeExtractionService(),
        source_discovery_service=_FakeSourceDiscoveryService(),
        poll_interval_seconds=0.01,
        source_library_repository=source_library_repository,
        semantic_fragment_maintenance_batch_size=3,
    )

    had_work = asyncio.run(worker.loop_once())

    assert had_work is False
    assert source_library_repository.batch_sizes == [3]
