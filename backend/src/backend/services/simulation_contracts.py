from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.domain.simulation_records import RunType, SimulationStatus, StrategyType
from backend.services.contracts import AsyncStatusResponse, AsyncSubmissionResponse


class SimulationSubmissionRequest(BaseModel):
    case_id: str
    run_type: RunType
    total_rounds: int = Field(default=5, ge=1, le=20)
    strategy_type: StrategyType | None = None
    strategy_message: str | None = None
    injection_round: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_strategy_fields(self) -> "SimulationSubmissionRequest":
        if self.run_type == RunType.BASELINE:
            self.strategy_type = None
            self.strategy_message = None
            self.injection_round = None
            return self

        if self.strategy_type is None:
            raise ValueError("strategy_type is required for intervention runs")
        if self.injection_round is None:
            self.injection_round = 1
        if self.injection_round > self.total_rounds:
            self.injection_round = self.total_rounds
        return self


class SimulationJobPayload(BaseModel):
    job_id: str
    run_id: str
    case_id: str
    run_type: RunType
    total_rounds: int = Field(ge=1, le=20)
    strategy_type: StrategyType | None = None
    strategy_message: str | None = None
    injection_round: int | None = Field(default=None, ge=1)

    @classmethod
    def from_job_payload(cls, job_id: str, payload: dict[str, Any]) -> "SimulationJobPayload":
        return cls.model_validate({"job_id": job_id, **payload})


class SimulationSubmissionResponse(AsyncSubmissionResponse):
    run_id: str
    job_type: str = "simulation.run"
    job_status_path: str = "/api/jobs/{job_id}"
    status_path: str = "/api/simulation-runs/{run_id}"
    run_status: str


class JobStatusResponse(AsyncStatusResponse):
    id: str
    run_id: str | None = None
    locked_at: str | None = None
    heartbeat_at: str | None = None
    updated_at: str | None = None
    created_at: str | None = None



class SimulationRunStatusResponse(AsyncStatusResponse):
    id: str
    job_id: str | None = None
    status: SimulationStatus
    job_type: str = "simulation.run"
    job_status_path: str = "/api/jobs/{job_id}"
    status_path: str = "/api/simulation-runs/{id}"
    error_message: str | None = None
    total_rounds: int
    completed_rounds: int
    last_completed_round: int
    last_heartbeat_at: str | None = None
    created_at: str
    completed_at: str | None = None


class AgentRoundResponse(BaseModel):
    agent_id: str
    response: str
    sentiment_delta: float
    amplification: float


class SimulationRoundResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_responses: list[AgentRoundResponse]
    overall_sentiment: float
    polarization_level: float = 0.5
    negative_claim_spread: float = 0.5
    stabilization_indicator: float = 0.3
    narrative_state: str

    @classmethod
    def from_llm_payload(cls, payload: Any) -> "SimulationRoundResult":
        if isinstance(payload, str):
            payload = json.loads(payload)
        return cls.model_validate(payload)
