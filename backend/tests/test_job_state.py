from __future__ import annotations

import pytest

from backend.domain.job_state import validate_transition
from backend.domain.models import JobStatus


def test_valid_job_state_transitions():
    validate_transition(JobStatus.PENDING, JobStatus.RUNNING)
    validate_transition(JobStatus.RUNNING, JobStatus.COMPLETED)
    validate_transition(JobStatus.FAILED, JobStatus.PENDING)


def test_invalid_job_state_transition_raises():
    with pytest.raises(Exception):
        validate_transition(JobStatus.PENDING, JobStatus.COMPLETED)
