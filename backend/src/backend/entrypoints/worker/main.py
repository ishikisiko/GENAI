from __future__ import annotations

from backend.services.extraction_contracts import GRAPH_EXTRACTION_JOB_TYPE
from backend.services.extraction_service import ExtractionService
from backend.repository.job_repository import JobRepository
from backend.services.simulation_service import SimulationService
from backend.services.source_discovery_contracts import SOURCE_DISCOVERY_JOB_TYPE
from backend.services.source_discovery_service import SourceDiscoveryService
from backend.services.worker import WorkerRuntime


def build_worker(
    runtime_id: str,
    repository: JobRepository,
    simulation_service: SimulationService,
    extraction_service: ExtractionService,
    source_discovery_service: SourceDiscoveryService,
    poll_interval_seconds: float,
):
    return WorkerRuntime(
        repository=repository,
        worker_id=runtime_id,
        handlers={
            "simulation.run": simulation_service.handle_job,
            GRAPH_EXTRACTION_JOB_TYPE: extraction_service.handle_job,
            SOURCE_DISCOVERY_JOB_TYPE: source_discovery_service.handle_job,
        },
        maintenance_tasks=[simulation_service.recover_stale_jobs],
        poll_interval_seconds=poll_interval_seconds,
    )
