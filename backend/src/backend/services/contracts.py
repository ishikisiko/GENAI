from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SyncResponse(BaseModel):
    outcome: Literal["completed"] = "completed"


class AsyncSubmissionResponse(BaseModel):
    outcome: Literal["accepted"] = "accepted"
    job_id: str
    job_type: str
    job_status: str
    should_poll: bool = True
    job_status_path: str = "/api/jobs/{job_id}"
    status_path: str | None = None


class AsyncStatusResponse(BaseModel):
    outcome: Literal["status"] = "status"
    job_id: str
    job_type: str
    status: str
    should_poll: bool
    job_status_path: str = "/api/jobs/{job_id}"
    status_path: str | None = None
    last_error: str | None = None
    last_error_code: str | None = None
