from __future__ import annotations

from pydantic import BaseModel


class AsyncSubmissionResponse(BaseModel):
    job_id: str
    job_type: str
    job_status: str
    should_poll: bool = True
    status_path: str | None = None


class AsyncStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    should_poll: bool
    last_error: str | None = None
    last_error_code: str | None = None
