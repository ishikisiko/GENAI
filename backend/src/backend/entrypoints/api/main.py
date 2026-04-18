from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.db import Database
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.job_repository import JobRepository
from backend.repository.simulation_repository import SimulationRepository
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode
from backend.shared.logging import configure_logging, correlation_context, get_logger
from backend.shared.request_context import build_request_context
from backend.services.extraction_contracts import GraphExtractionSubmissionRequest
from backend.services.extraction_service import ExtractionService
from backend.services.llm_client import LlmJsonClient
from backend.services.agent_generation_contracts import AgentGenerationRequest
from backend.services.agent_generation_service import AgentGenerationService
from backend.services.simulation_contracts import SimulationSubmissionRequest
from backend.services.simulation_service import SimulationService


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
    await app.state.database.dispose()


def create_app(
    config: BackendConfig,
    database: Database,
    repository: JobRepository | None = None,
    simulation_service: SimulationService | None = None,
    extraction_service: ExtractionService | None = None,
    agent_generation_service: AgentGenerationService | None = None,
) -> FastAPI:
    configure_logging(config.app_name, config.log_level)
    logger = get_logger("backend.api")
    repository = repository or JobRepository(database)
    llm_client = LlmJsonClient(config)
    simulation_service = simulation_service or SimulationService(
        config=config,
        simulation_repository=SimulationRepository(database),
        job_repository=repository,
        llm_client=llm_client,
    )
    extraction_service = extraction_service or ExtractionService(
        extraction_repository=ExtractionRepository(database),
        job_repository=repository,
        llm_client=llm_client,
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

    @app.get("/health/ready")
    async def readiness():
        try:
            await app.state.database.ping()
        except Exception as exc:
            raise DependencyError(dependency="database", details={"reason": str(exc)}) from exc
        return {"status": "ready", "service": config.app_name}

    @app.get("/ops")
    async def operations():
        try:
            counts = await app.state.repository.get_status_counts()
        except Exception as exc:
            raise DependencyError(dependency="database", details={"reason": str(exc)}) from exc

        safe_counts = {str(status): count for status, count in counts.items()}
        return {
            "service": config.app_name,
            "jobs": safe_counts,
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

    return app
