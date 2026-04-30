from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.domain.simulation_records import RunType, StrategyType
from backend.services.simulation_contracts import SimulationJobPayload, SimulationSubmissionRequest, StrategySequenceStep
from backend.services.simulation_service import SimulationService
from backend.shared.config import BackendConfig


def _build_config():
    return BackendConfig(
        app_name="backend-test",
        app_env="test",
        database_url="postgresql+asyncpg://localhost/db",
        host="127.0.0.1",
        port=9000,
        source_discovery_search_provider="mock",
        semantic_embedding_provider="local",
    )


def test_strategy_sequence_request_is_sorted_and_exclusive():
    request = SimulationSubmissionRequest(
        case_id="case-123",
        run_type="intervention",
        total_rounds=4,
        strategy_sequence=[
            {"round_number": 3, "strategy_type": "apology"},
            {"round_number": 1, "strategy_type": "clarification"},
        ],
    )

    assert [step.round_number for step in request.strategy_sequence or []] == [1, 3]

    with pytest.raises(ValidationError):
        SimulationSubmissionRequest(
            case_id="case-123",
            run_type="intervention",
            total_rounds=4,
            strategy_type="apology",
            injection_round=2,
            strategy_sequence=[{"round_number": 1, "strategy_type": "clarification"}],
        )


def test_strategy_sequence_rejects_invalid_baseline_and_duplicate_rounds():
    with pytest.raises(ValidationError):
        SimulationSubmissionRequest(
            case_id="case-123",
            run_type="baseline",
            total_rounds=4,
            strategy_sequence=[{"round_number": 1, "strategy_type": "clarification"}],
        )

    with pytest.raises(ValidationError):
        SimulationSubmissionRequest(
            case_id="case-123",
            run_type="intervention",
            total_rounds=4,
            strategy_sequence=[
                {"round_number": 2, "strategy_type": "clarification"},
                {"round_number": 2, "strategy_type": "apology"},
            ],
        )


class _FakeSimulationRepository:
    def __init__(self) -> None:
        self.recorded_rounds: list[dict[str, object]] = []

    async def get_case(self, case_id: str):
        return SimpleNamespace(id=case_id, title="Test Crisis")

    async def list_agents(self, case_id: str):
        return [
            SimpleNamespace(
                id="agent-consumer",
                role="consumer",
                persona_description="Concerned customer",
                stance="worried",
                concern="safety",
                emotional_sensitivity=7,
                spread_tendency=6,
                initial_beliefs=["The product may be unsafe"],
            )
        ]

    async def list_claims(self, case_id: str):
        return [SimpleNamespace(claim_type="allegation", content="Customers report illness")]

    async def list_entities(self, case_id: str):
        return [SimpleNamespace(name="Brand", entity_type="organization")]

    async def mark_run_running(self, run_id: str):
        return None

    async def update_run_heartbeat(self, run_id: str, status=None):
        return None

    async def record_round(self, **kwargs):
        self.recorded_rounds.append(kwargs)

    async def mark_run_completed(self, run_id: str):
        return None

    async def mark_run_failed(self, run_id: str, message: str):
        raise AssertionError(message)


class _FakeJobRepository:
    async def touch_heartbeat(self, job_id: str):
        return None


class _FakeLlmClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def chat_json(self, *, prompt: str, temperature: float = 0.7, max_retries: int = 2):
        self.prompts.append(prompt)
        return {
            "agent_responses": [
                {
                    "agent_id": "consumer",
                    "response": "I am watching how the company handles this.",
                    "sentiment_delta": 0.05,
                    "amplification": 0.4,
                }
            ],
            "overall_sentiment": -0.1,
            "polarization_level": 0.4,
            "negative_claim_spread": 0.5,
            "stabilization_indicator": 0.3,
            "narrative_state": "The public is still evaluating the response.",
        }


def test_worker_applies_strategy_sequence_per_round():
    simulation_repository = _FakeSimulationRepository()
    llm_client = _FakeLlmClient()
    service = SimulationService(
        _build_config(),
        simulation_repository=simulation_repository,
        job_repository=_FakeJobRepository(),
        llm_client=llm_client,
    )
    payload = SimulationJobPayload(
        job_id="job-123",
        run_id="run-123",
        case_id="case-123",
        run_type=RunType.INTERVENTION,
        total_rounds=3,
        strategy_sequence=[
            StrategySequenceStep(round_number=1, strategy_type=StrategyType.CLARIFICATION),
            StrategySequenceStep(round_number=3, strategy_type=StrategyType.APOLOGY),
        ],
    )

    asyncio.run(service._execute(payload))

    assert [round_data["strategy_applied"] for round_data in simulation_repository.recorded_rounds] == [
        "clarification",
        None,
        "apology",
    ]
    assert "PLANNED CRISIS RESPONSE STRATEGY ISSUED (Round 1)" in llm_client.prompts[0]
    assert "No new official response is issued this round" in llm_client.prompts[1]
    assert "Prior official responses may still shape public reactions" in llm_client.prompts[1]
    assert "PLANNED CRISIS RESPONSE STRATEGY ISSUED (Round 3)" in llm_client.prompts[2]
