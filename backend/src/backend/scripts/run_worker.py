from __future__ import annotations

import asyncio
from uuid import uuid4

from backend.db import Database
from backend.entrypoints.worker.main import build_worker
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.job_repository import JobRepository
from backend.repository.simulation_repository import SimulationRepository
from backend.repository.source_discovery_repository import SourceDiscoveryRepository
from backend.shared.config import load_config
from backend.services.extraction_service import ExtractionService
from backend.services.llm_client import LlmJsonClient
from backend.services.simulation_service import SimulationService
from backend.services.source_discovery_service import SourceDiscoveryService, build_source_discovery_search_provider


async def _run() -> None:
    config = load_config()
    database = Database(config.database_url)
    repository = JobRepository(database)
    llm_client = LlmJsonClient(config)
    simulation_service = SimulationService(
        config=config,
        simulation_repository=SimulationRepository(database),
        job_repository=repository,
        llm_client=llm_client,
    )
    extraction_service = ExtractionService(
        extraction_repository=ExtractionRepository(database),
        job_repository=repository,
        llm_client=llm_client,
    )
    source_discovery_service = SourceDiscoveryService(
        source_repository=SourceDiscoveryRepository(database),
        job_repository=repository,
        extraction_repository=ExtractionRepository(database),
        search_provider=build_source_discovery_search_provider(config),
    )
    worker = build_worker(
        runtime_id=f"worker-{uuid4()}",
        repository=repository,
        simulation_service=simulation_service,
        extraction_service=extraction_service,
        source_discovery_service=source_discovery_service,
        poll_interval_seconds=config.worker_poll_interval_seconds,
    )
    await worker.run()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
