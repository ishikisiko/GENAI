from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.db import Database
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.job_repository import JobRepository
from backend.repository.simulation_repository import SimulationRepository
from backend.repository.source_discovery_repository import SourceDiscoveryRepository
from backend.repository.source_library_repository import SourceLibraryRepository
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode
from backend.shared.logging import configure_logging, correlation_context, get_logger
from backend.shared.rate_limit import RedisRateLimiter
from backend.shared.redis_client import RedisClient, RedisUnavailableError, build_redis_client
from backend.shared.request_context import build_request_context
from backend.services.extraction_contracts import GraphExtractionSubmissionRequest
from backend.services.extraction_service import ExtractionService
from backend.services.job_dispatcher import RedisJobDispatcher
from backend.services.llm_client import LlmJsonClient
from backend.services.agent_generation_contracts import AgentGenerationRequest
from backend.services.agent_generation_service import AgentGenerationService
from backend.services.semantic_source_recall import build_semantic_index
from backend.services.simulation_contracts import SimulationSubmissionRequest
from backend.services.simulation_service import SimulationService
from backend.services.source_discovery_contracts import (
    EvidencePackCreateRequest,
    SourceDiscoveryAssistantRequest,
    SourceCandidateLibrarySaveRequest,
    SourceCandidateReviewRequest,
    SourceDiscoveryJobCreateRequest,
)
from backend.services.source_discovery_assistant_service import SourceDiscoveryAssistantService
from backend.services.source_discovery_service import (
    SourceDiscoveryService,
    build_source_discovery_content_fetcher,
    build_source_discovery_search_provider,
)
from backend.services.source_library_contracts import (
    AttachGlobalSourceRequest,
    CaseSourceTopicCreateRequest,
    SourceTopicAssignmentCreateRequest,
    SourceTopicCreateRequest,
    SourceTopicUpdateRequest,
)
from backend.services.source_library_service import SourceLibraryService


def _apply_cors_headers(request: Request, response: Response, config: BackendConfig) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return

    allowed_origins = config.allowed_cors_origins()
    if "*" in allowed_origins:
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        return

    if origin in allowed_origins:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Vary", "Origin")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    await app.state.redis_client.close()
    await app.state.database.dispose()


def create_app(
    config: BackendConfig,
    database: Database,
    repository: JobRepository | None = None,
    simulation_service: SimulationService | None = None,
    extraction_service: ExtractionService | None = None,
    agent_generation_service: AgentGenerationService | None = None,
    source_discovery_service: SourceDiscoveryService | None = None,
    source_discovery_assistant_service: SourceDiscoveryAssistantService | None = None,
    source_library_service: SourceLibraryService | None = None,
    redis_client: RedisClient | None = None,
    rate_limiter: RedisRateLimiter | None = None,
) -> FastAPI:
    configure_logging(config.app_name, config.log_level)
    logger = get_logger("backend.api")
    redis_client = redis_client or build_redis_client(config)
    rate_limiter = rate_limiter or RedisRateLimiter(config, redis_client)
    repository = repository or JobRepository(database)
    job_dispatcher = RedisJobDispatcher(config, redis_client)
    llm_client = LlmJsonClient(config, redis_client=redis_client)
    simulation_service = simulation_service or SimulationService(
        config=config,
        simulation_repository=SimulationRepository(database),
        job_repository=repository,
        llm_client=llm_client,
        job_dispatcher=job_dispatcher,
    )
    extraction_service = extraction_service or ExtractionService(
        extraction_repository=ExtractionRepository(database),
        job_repository=repository,
        llm_client=llm_client,
        job_dispatcher=job_dispatcher,
    )
    source_discovery_search_provider = None
    source_discovery_content_fetcher = None
    if source_discovery_service is None or source_discovery_assistant_service is None:
        source_discovery_search_provider = build_source_discovery_search_provider(config, redis_client=redis_client)
        source_discovery_content_fetcher = build_source_discovery_content_fetcher(config, redis_client=redis_client)
    source_discovery_service = source_discovery_service or SourceDiscoveryService(
        source_repository=SourceDiscoveryRepository(database),
        job_repository=repository,
        extraction_repository=ExtractionRepository(database),
        search_provider=source_discovery_search_provider,
        content_fetcher=source_discovery_content_fetcher,
        job_dispatcher=job_dispatcher,
    )
    source_discovery_assistant_service = source_discovery_assistant_service or SourceDiscoveryAssistantService(
        source_repository=SourceDiscoveryRepository(database),
        llm_client=llm_client,
        search_provider=source_discovery_search_provider,
        content_fetcher=source_discovery_content_fetcher,
    )
    source_library_service = source_library_service or SourceLibraryService(
        repository=SourceLibraryRepository(database, semantic_index=build_semantic_index(config)),
    )
    agent_generation_service = agent_generation_service or AgentGenerationService(
        simulation_repository=SimulationRepository(database),
        llm_client=llm_client,
    )

    app = FastAPI(title=config.app_name, lifespan=_lifespan)
    app.state.config = config
    app.state.database = database
    app.state.repository = repository
    app.state.simulation_service = simulation_service
    app.state.extraction_service = extraction_service
    app.state.agent_generation_service = agent_generation_service
    app.state.source_discovery_service = source_discovery_service
    app.state.source_discovery_assistant_service = source_discovery_assistant_service
    app.state.source_library_service = source_library_service
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        if request.method == "OPTIONS" and request.url.path.startswith("/api/"):
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            _apply_cors_headers(request, response, config)
            return response
        try:
            request_context = build_request_context(request, config, request_id)
        except ApplicationError as exc:
            payload = exc.to_payload(request_id=request_id, route=request.url.path)
            response = JSONResponse(status_code=exc.status_code, content=payload)
            response.headers["x-request-id"] = request_id
            _apply_cors_headers(request, response, config)
            return response

        request.state.request_context = request_context
        try:
            rate_limit_result = await rate_limiter.check(request, request_context)
        except ApplicationError as exc:
            payload = exc.to_payload(request_id=request_id, route=request.url.path)
            response = JSONResponse(status_code=exc.status_code, content=payload)
            response.headers["x-request-id"] = request_id
            _apply_cors_headers(request, response, config)
            return response
        if rate_limit_result is not None and not rate_limit_result.allowed:
            exc = rate_limiter.to_error(rate_limit_result)
            payload = exc.to_payload(request_id=request_id, route=request.url.path)
            response = JSONResponse(status_code=exc.status_code, content=payload)
            response.headers["x-request-id"] = request_id
            response.headers["Retry-After"] = str(rate_limit_result.retry_after_seconds)
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.remaining)
            _apply_cors_headers(request, response, config)
            return response
        response: Response
        with correlation_context(
            request_id=request_id,
            route=request.url.path,
            method=request.method,
            boundary=request_context.boundary,
            auth_mode=request_context.auth_mode,
            authenticated=request_context.authenticated,
            auth_subject=request_context.auth_subject,
        ):
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("unhandled_error", extra={"path": str(request.url)})
                payload = ApplicationError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Unexpected server error",
                    status_code=500,
                    details={"route": request.url.path},
                ).to_payload(request_id=request_id, route=request.url.path)
                response = JSONResponse(status_code=500, content=payload)

            response.headers["x-request-id"] = request_id
            _apply_cors_headers(request, response, config)
        return response

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError):
        logger.error("request_error", extra={"path": str(request.url), "code": exc.code.value})
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(
                request_id=getattr(request.state, "request_id", None),
                route=request.url.path,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        logger.error("request_validation_error", extra={"path": str(request.url), "error": str(exc)})
        payload = ApplicationError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid request payload",
            status_code=422,
            details={"errors": jsonable_encoder(exc.errors())},
        ).to_payload(
            request_id=getattr(request.state, "request_id", None),
            route=request.url.path,
        )
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", extra={"path": str(request.url), "error": str(exc)})
        payload = ApplicationError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Unexpected server error",
            status_code=500,
            details={"route": request.url.path},
        ).to_payload(
            request_id=getattr(request.state, "request_id", None),
            route=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content=payload,
        )

    @app.get("/health/live")
    async def liveness():
        return {"status": "ok", "service": config.app_name}

    @app.get("/")
    async def root():
        return {
            "service": config.app_name,
            "status": "ok",
            "health": "/health/ready",
            "frontend": "http://127.0.0.1:4173",
        }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/health/ready")
    async def readiness():
        try:
            await app.state.database.ping()
        except Exception as exc:
            raise DependencyError(dependency="database", details={"reason": str(exc)}) from exc
        if config.redis_enabled and config.redis_requirement_mode == "required":
            try:
                await app.state.redis_client.ping()
            except Exception as exc:
                raise DependencyError(
                    dependency="redis",
                    details={"reason": str(exc), "mode": config.redis_requirement_mode},
                ) from exc
        return {"status": "ready", "service": config.app_name}

    @app.get("/ops")
    async def operations():
        try:
            counts = await app.state.repository.get_status_counts()
        except Exception as exc:
            raise DependencyError(dependency="database", details={"reason": str(exc)}) from exc

        safe_counts = {str(status): count for status, count in counts.items()}
        redis_status = "disabled"
        if config.redis_enabled:
            try:
                redis_status = "available" if await app.state.redis_client.ping() else "degraded"
            except RedisUnavailableError:
                redis_status = "degraded"
            except Exception:
                redis_status = "degraded"
        return {
            "service": config.app_name,
            "jobs": safe_counts,
            "redis": {
                "enabled": config.redis_enabled,
                "requirement_mode": config.redis_requirement_mode,
                "status": redis_status,
                "features": {
                    "rate_limit": config.redis_rate_limit_enabled,
                    "cache": config.redis_cache_enabled,
                    "stream_dispatch": config.redis_stream_dispatch_enabled,
                },
            },
        }

    @app.post("/api/simulations")
    async def submit_simulation(request: SimulationSubmissionRequest):
        return (await app.state.simulation_service.submit(request)).model_dump()

    @app.get("/api/jobs/{job_id}")
    async def get_job_status(job_id: str):
        return (await app.state.simulation_service.get_job_status(job_id)).model_dump()

    @app.get("/api/simulation-runs/{run_id}")
    async def get_simulation_run_status(run_id: str):
        return (await app.state.simulation_service.get_run_status(run_id)).model_dump(mode="json")

    @app.post("/api/graph-extractions")
    async def submit_graph_extraction(request: GraphExtractionSubmissionRequest):
        return (await app.state.extraction_service.submit(request)).model_dump()

    @app.get("/api/graph-extractions/{job_id}")
    async def get_graph_extraction_status(job_id: str):
        return (await app.state.extraction_service.get_status(job_id)).model_dump()

    @app.post("/api/agent-generation")
    async def generate_agents(request: AgentGenerationRequest):
        return (await app.state.agent_generation_service.generate(request)).model_dump()

    @app.post("/api/source-discovery/jobs")
    async def create_source_discovery_job(request: SourceDiscoveryJobCreateRequest):
        return (await app.state.source_discovery_service.submit(request)).model_dump()

    @app.get("/api/source-discovery/jobs/{job_id}")
    async def get_source_discovery_job(job_id: str):
        return (await app.state.source_discovery_service.get_status(job_id)).model_dump()

    @app.get("/api/source-candidates")
    async def list_source_candidates(
        case_id: str | None = None,
        discovery_job_id: str | None = None,
        review_status: str | None = None,
    ):
        return (
            await app.state.source_discovery_service.list_candidates(
                case_id=case_id,
                discovery_job_id=discovery_job_id,
                review_status=review_status,
            )
        ).model_dump()

    @app.patch("/api/source-candidates/{source_id}")
    async def update_source_candidate(source_id: str, request: SourceCandidateReviewRequest):
        return (await app.state.source_discovery_service.update_candidate_review(source_id, request)).model_dump()

    @app.post("/api/source-discovery/assistant")
    async def source_discovery_assistant(request: SourceDiscoveryAssistantRequest):
        return (await app.state.source_discovery_assistant_service.answer(request)).model_dump()

    @app.post("/api/source-candidates/{source_id}/save-to-library")
    async def save_source_candidate_to_library(source_id: str, request: SourceCandidateLibrarySaveRequest):
        return (await app.state.source_library_service.save_candidate_to_library(source_id, request)).model_dump()

    @app.post("/api/evidence-packs")
    async def create_evidence_pack(request: EvidencePackCreateRequest):
        return (await app.state.source_discovery_service.create_evidence_pack(request)).model_dump()

    @app.get("/api/evidence-packs/{evidence_pack_id}")
    async def get_evidence_pack(evidence_pack_id: str):
        return (await app.state.source_discovery_service.get_evidence_pack(evidence_pack_id)).model_dump()

    @app.post("/api/evidence-packs/{evidence_pack_id}/start-grounding")
    async def start_evidence_pack_grounding(evidence_pack_id: str):
        return (await app.state.source_discovery_service.start_grounding(evidence_pack_id)).model_dump()

    @app.get("/api/source-topics")
    async def list_source_topics():
        return (await app.state.source_library_service.list_topics()).model_dump()

    @app.post("/api/source-topics")
    async def create_source_topic(request: SourceTopicCreateRequest):
        return (await app.state.source_library_service.create_topic(request)).model_dump()

    @app.get("/api/source-topics/{topic_id}")
    async def get_source_topic(topic_id: str):
        return (await app.state.source_library_service.get_topic(topic_id)).model_dump()

    @app.patch("/api/source-topics/{topic_id}")
    async def update_source_topic(topic_id: str, request: SourceTopicUpdateRequest):
        return (await app.state.source_library_service.update_topic(topic_id, request)).model_dump()

    @app.post("/api/case-source-topics")
    async def create_case_source_topic(request: CaseSourceTopicCreateRequest):
        return (await app.state.source_library_service.create_case_topic(request)).model_dump()

    @app.post("/api/source-topic-assignments")
    async def create_source_topic_assignment(request: SourceTopicAssignmentCreateRequest):
        return (await app.state.source_library_service.create_assignment(request)).model_dump()

    @app.delete("/api/source-topic-assignments/{assignment_id}")
    async def remove_source_topic_assignment(assignment_id: str):
        return (await app.state.source_library_service.remove_assignment(assignment_id)).model_dump()

    @app.get("/api/source-registry")
    async def list_source_registry(
        topic_id: str | None = None,
        smart_view: str | None = None,
        query: str | None = None,
        source_kind: str | None = None,
        authority_level: str | None = None,
        freshness_status: str | None = None,
        source_status: str | None = None,
        case_id: str | None = None,
    ):
        return (
            await app.state.source_library_service.list_registry(
                topic_id=topic_id,
                smart_view=smart_view,
                query=query,
                source_kind=source_kind,
                authority_level=authority_level,
                freshness_status=freshness_status,
                source_status=source_status,
                case_id=case_id,
            )
        ).model_dump()

    @app.get("/api/source-registry/{global_source_id}/usage")
    async def get_source_usage(global_source_id: str):
        return (await app.state.source_library_service.get_usage(global_source_id)).model_dump()

    @app.get("/api/cases/{case_id}/source-selection")
    async def get_case_source_selection(case_id: str, query: str | None = None):
        return (await app.state.source_library_service.get_case_selection(case_id, query)).model_dump()

    @app.post("/api/cases/{case_id}/source-documents/from-library")
    async def attach_global_source_to_case(case_id: str, request: AttachGlobalSourceRequest):
        if request.case_id != case_id:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Path case_id must match request case_id.",
                status_code=400,
            )
        return (await app.state.source_library_service.attach_global_source(request)).model_dump()

    return app
