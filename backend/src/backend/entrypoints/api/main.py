from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from backend.db import Database
from backend.repository.job_repository import JobRepository
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, DependencyError
from backend.shared.logging import configure_logging, correlation_context, get_logger


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    await app.state.database.dispose()


def create_app(config: BackendConfig, database: Database, repository: JobRepository | None = None) -> FastAPI:
    configure_logging(config.app_name, config.log_level)
    logger = get_logger("backend.api")
    repository = repository or JobRepository(database)

    app = FastAPI(title=config.app_name, lifespan=_lifespan)
    app.state.config = config
    app.state.database = database
    app.state.repository = repository

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        response: Response
        with correlation_context(request_id=request_id, route=request.url.path):
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError):
        logger.error("request_error", extra={"path": str(request.url), "code": exc.code.value})
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", extra={"path": str(request.url), "error": str(exc)})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error",
                }
            },
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

    return app
