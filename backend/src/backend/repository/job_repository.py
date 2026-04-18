from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import NoResultFound

from backend.db import Database
from backend.domain.job_state import validate_transition
from backend.domain.models import Job, JobAttempt, JobAttemptStatus, JobStatus
from backend.shared.errors import ApplicationError, ErrorCode


class JobRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create_job(
        self,
        job_type: str,
        payload: dict | None = None,
        max_attempts: int = 5,
        scheduled_at: datetime | None = None,
    ) -> Job:
        now = datetime.now(timezone.utc)
        payload = payload or {}
        async with self._database.session() as session:
            job = Job(
                id=str(uuid4()),
                job_type=job_type,
                status=JobStatus.PENDING,
                payload=payload,
                max_attempts=max_attempts,
                scheduled_at=scheduled_at,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            await session.flush()
            await session.refresh(job)
            return job

    async def claim_next_pending_job(self, worker_id: str) -> Job | None:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            query = (
                select(Job)
                .where(
                    Job.status == JobStatus.PENDING,
                    (Job.scheduled_at.is_(None)) | (Job.scheduled_at <= now),
                )
                .order_by(Job.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(query)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            if row.attempt_count >= row.max_attempts and row.max_attempts > 0:
                row.status = JobStatus.FAILED
                row.updated_at = now
                row.last_error = "Maximum retry attempts reached"
                row.last_error_code = "MAX_RETRIES_EXCEEDED"
                await session.flush()
                return None

            row.status = JobStatus.RUNNING
            row.locked_by = worker_id
            row.locked_at = now
            row.heartbeat_at = now
            row.updated_at = now
            row.attempt_count += 1

            attempt = JobAttempt(
                id=str(uuid4()),
                job_id=row.id,
                attempt_number=row.attempt_count,
                worker_id=worker_id,
                status=JobAttemptStatus.RUNNING,
                payload_snapshot=row.payload,
                started_at=now,
                created_at=now,
            )
            session.add(attempt)
            await session.flush()
            await session.refresh(row)
            return row

    async def mark_running_complete(
        self,
        job_id: str,
        result: dict | None = None,
    ) -> Job:
        async with self._database.session() as session:
            job = await self._get_job_with_lock(session, job_id)
            validate_transition(job.status, JobStatus.COMPLETED)

            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            job.heartbeat_at = None
            job.locked_by = None
            job.locked_at = None
            job.last_error = None
            job.last_error_code = None

            attempt = await self._get_current_attempt(session, job_id)
            if attempt is not None:
                attempt.status = JobAttemptStatus.COMPLETED
                attempt.completed_at = datetime.now(timezone.utc)
                if result is not None:
                    attempt.payload_snapshot = {"result": result}
            return job

    async def mark_running_failed(self, job_id: str, code: str, message: str) -> Job:
        async with self._database.session() as session:
            job = await self._get_job_with_lock(session, job_id)
            validate_transition(job.status, JobStatus.FAILED)
            now = datetime.now(timezone.utc)

            job.status = JobStatus.FAILED
            job.updated_at = now
            job.heartbeat_at = None
            job.locked_by = None
            job.locked_at = None
            job.last_error = message
            job.last_error_code = code
            if job.attempt_count >= job.max_attempts and job.max_attempts > 0:
                # terminal failure; no further retry by default
                pass
            attempt = await self._get_current_attempt(session, job_id)
            if attempt is not None:
                attempt.status = JobAttemptStatus.FAILED
                attempt.completed_at = now
                attempt.error_code = code
                attempt.error_message = message
            return job

    async def retry(self, job_id: str) -> Job:
        async with self._database.session() as session:
            job = await self._get_job_with_lock(session, job_id)
            validate_transition(job.status, JobStatus.PENDING)

            job.status = JobStatus.PENDING
            job.updated_at = datetime.now(timezone.utc)
            job.last_error = None
            job.last_error_code = None
            job.locked_by = None
            job.locked_at = None
            job.heartbeat_at = None
            return job

    async def cancel(self, job_id: str, reason: str) -> Job:
        async with self._database.session() as session:
            job = await self._get_job_with_lock(session, job_id)
            if job.status in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
                return job
            validate_transition(job.status, JobStatus.CANCELLED)
            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now(timezone.utc)
            job.heartbeat_at = None
            job.locked_by = None
            job.locked_at = None
            job.last_error = reason
            job.last_error_code = "CANCELLED"
            attempt = await self._get_current_attempt(session, job_id)
            if attempt is not None and attempt.status == JobAttemptStatus.RUNNING:
                attempt.status = JobAttemptStatus.CANCELLED
                attempt.completed_at = datetime.now(timezone.utc)
                attempt.error_code = "CANCELLED"
                attempt.error_message = reason
            return job

    async def get_status_counts(self) -> dict[str, int]:
        async with self._database.session() as session:
            rows = await session.execute(select(Job.status, func.count(Job.id)))
            return {status: count for status, count in rows.all()}

    async def get_job(self, job_id: str) -> Job:
        async with self._database.session() as session:
            return await self._get_job_with_lock(session, job_id, lock=False)

    async def get_latest_attempt(self, job_id: str) -> JobAttempt | None:
        async with self._database.session() as session:
            return await self._get_current_attempt(session, job_id)

    async def touch_heartbeat(self, job_id: str) -> Job:
        async with self._database.session() as session:
            job = await self._get_job_with_lock(session, job_id)
            if job.status != JobStatus.RUNNING:
                return job
            now = datetime.now(timezone.utc)
            job.heartbeat_at = now
            job.updated_at = now
            return job

    async def find_stale_running_jobs(self, stale_before: datetime, job_type: str | None = None) -> list[Job]:
        async with self._database.session() as session:
            query = select(Job).where(
                Job.status == JobStatus.RUNNING,
                or_(Job.heartbeat_at < stale_before, Job.heartbeat_at.is_(None) & (Job.locked_at < stale_before)),
            )
            if job_type is not None:
                query = query.where(Job.job_type == job_type)
            rows = await session.execute(query.order_by(Job.updated_at.asc()))
            return list(rows.scalars().all())

    async def mark_running_stale(self, job_id: str, message: str) -> Job:
        return await self.mark_running_failed(job_id, code="STALE_TIMEOUT", message=message)

    async def _get_current_attempt(self, session, job_id: str) -> JobAttempt | None:
        query = (
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_number.desc())
            .limit(1)
        )
        row = await session.execute(query)
        return row.scalar_one_or_none()

    async def _get_job_with_lock(self, session, job_id: str, lock: bool = True) -> Job:
        query = select(Job).where(Job.id == job_id)
        if lock:
            query = query.with_for_update(skip_locked=True)
        result = await session.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound as exc:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message=f"Job not found: {job_id}",
                status_code=404,
            ) from exc
