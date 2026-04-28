from __future__ import annotations

import asyncio

from backend.domain.models import JobStatus
from backend.repository.job_repository import JobRepository


class _Rows:
    def all(self):
        return [(JobStatus.PENDING, 2), ("completed", 1)]


class _CapturingSession:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _Rows()


class _SessionContext:
    def __init__(self, session: _CapturingSession) -> None:
        self.session = session

    async def __aenter__(self) -> _CapturingSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _CapturingDatabase:
    def __init__(self) -> None:
        self.session_obj = _CapturingSession()

    def session(self) -> _SessionContext:
        return _SessionContext(self.session_obj)


def test_get_status_counts_groups_by_job_status_and_fills_missing_statuses():
    database = _CapturingDatabase()
    repository = JobRepository(database)

    counts = asyncio.run(repository.get_status_counts())

    compiled = str(database.session_obj.statement)
    assert "GROUP BY jobs.status" in compiled
    assert counts == {
        "pending": 2,
        "running": 0,
        "completed": 1,
        "failed": 0,
        "cancelled": 0,
    }
