from __future__ import annotations

import asyncio
from uuid import uuid4

from backend.db import Database
from backend.entrypoints.worker.main import build_worker
from backend.repository.job_repository import JobRepository
from backend.shared.config import load_config


async def _run() -> None:
    config = load_config()
    database = Database(config.database_url)
    repository = JobRepository(database)
    worker = build_worker(
        runtime_id=f"worker-{uuid4()}",
        repository=repository,
        poll_interval_seconds=config.worker_poll_interval_seconds,
    )
    await worker.run()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
