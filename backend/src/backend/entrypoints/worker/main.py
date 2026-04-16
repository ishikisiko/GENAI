from __future__ import annotations

from backend.repository.job_repository import JobRepository
from backend.services.worker import WorkerRuntime


def build_worker(runtime_id: str, repository: JobRepository, poll_interval_seconds: float):
    return WorkerRuntime(
        repository=repository,
        worker_id=runtime_id,
        poll_interval_seconds=poll_interval_seconds,
    )
