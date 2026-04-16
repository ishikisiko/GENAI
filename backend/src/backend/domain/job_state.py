from __future__ import annotations

from backend.domain.models import JobStatus
from backend.shared.errors import TransitionError


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.FAILED: {JobStatus.PENDING},
    JobStatus.COMPLETED: set(),
    JobStatus.CANCELLED: set(),
}


def validate_transition(current: JobStatus, target: JobStatus) -> None:
    allowed = ALLOWED_TRANSITIONS[current]
    if target not in allowed:
        raise TransitionError(current=current.value, target=target.value)
