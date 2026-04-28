from __future__ import annotations

from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, Iterable

from backend.domain.models import Job
from backend.repository.job_repository import JobRepository
from backend.shared.errors import ApplicationError
from backend.shared.logging import correlation_context, get_logger


class WorkerRuntime:
    """Simple polling runtime for claiming and executing jobs."""

    def __init__(
        self,
        repository: JobRepository,
        worker_id: str,
        handlers: Dict[str, Callable[[Job], Awaitable[dict[str, object] | None]]] | None = None,
        maintenance_tasks: Iterable[Callable[[], Awaitable[int | None]]] | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self._repository = repository
        self._worker_id = worker_id
        self._handlers = handlers or {}
        self._maintenance_tasks = list(maintenance_tasks or [])
        self._poll_interval_seconds = poll_interval_seconds
        self._logger = get_logger("backend.worker")
        self._running = True

    def stop(self) -> None:
        self._running = False

    async def loop_once(self) -> bool:
        """Run at most one polling/execution cycle."""
        for task in self._maintenance_tasks:
            try:
                recovered = await task()
            except Exception:  # pragma: no cover - keeps optional maintenance from stopping workers.
                self._logger.exception("worker_maintenance_task_failed")
                continue
            if recovered:
                self._logger.info("worker_maintenance_task_completed", extra={"count": recovered})

        job = await self._repository.claim_next_pending_job(self._worker_id)
        if job is None:
            return False

        with correlation_context(job_id=job.id, worker_id=self._worker_id):
            self._logger.info("job_claimed", extra={"job_type": job.job_type})
            try:
                handler = self._handlers.get(job.job_type)
                if handler is None:
                    await self._repository.mark_running_failed(
                        job.id,
                        code="UNHANDLED_JOB_TYPE",
                        message=f"No handler registered for {job.job_type}",
                    )
                    self._logger.error("job_failed_unhandled", extra={"job_id": job.id, "job_type": job.job_type})
                    return True

                result = await handler(job)
                completion_result = dict(result or {})
                completion_result.setdefault("completed_at", datetime.now(timezone.utc).isoformat())
                await self._repository.mark_running_complete(
                    job.id,
                    result=completion_result,
                )
                self._logger.info("job_completed", extra={"job_id": job.id})
            except ApplicationError as exc:
                await self._repository.mark_running_failed(job.id, code=exc.code.value, message=exc.message)
                self._logger.error("job_failed", extra={"job_id": job.id, "error": exc.message})
            except Exception as exc:  # pragma: no cover - catches worker runtime failures.
                await self._repository.mark_running_failed(
                    job.id,
                    code="WORKER_ERROR",
                    message=str(exc),
                )
                self._logger.exception("job_failed_unexpected", extra={"job_id": job.id})
        return True

    async def run(self) -> None:
        import asyncio

        self._running = True
        while self._running:
            had_work = await self.loop_once()
            if not had_work:
                await asyncio.sleep(self._poll_interval_seconds)
