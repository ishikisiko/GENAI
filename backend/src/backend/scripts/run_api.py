from __future__ import annotations

import uvicorn

from backend.db import Database
from backend.entrypoints.api.main import create_app
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.simulation_repository import SimulationRepository
from backend.repository.job_repository import JobRepository
from backend.shared.config import load_config
from backend.shared.redis_client import build_redis_client
from backend.services.extraction_service import ExtractionService
from backend.services.agent_generation_service import AgentGenerationService
from backend.services.job_dispatcher import RedisJobDispatcher
from backend.services.llm_client import LlmJsonClient
from backend.services.simulation_service import SimulationService


def main() -> None:
    config = load_config()
    database = Database(config.database_url)
    redis_client = build_redis_client(config)
    job_dispatcher = RedisJobDispatcher(config, redis_client)
    repository = JobRepository(database)
    llm_client = LlmJsonClient(config, redis_client=redis_client)
    simulation_service = SimulationService(
        config=config,
        simulation_repository=SimulationRepository(database),
        job_repository=repository,
        llm_client=llm_client,
        job_dispatcher=job_dispatcher,
    )
    extraction_service = ExtractionService(
        extraction_repository=ExtractionRepository(database),
        job_repository=repository,
        llm_client=llm_client,
        job_dispatcher=job_dispatcher,
    )
    agent_generation_service = AgentGenerationService(
        simulation_repository=SimulationRepository(database),
        llm_client=llm_client,
    )
    app = create_app(
        config,
        database,
        repository=repository,
        simulation_service=simulation_service,
        extraction_service=extraction_service,
        agent_generation_service=agent_generation_service,
        redis_client=redis_client,
    )
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
