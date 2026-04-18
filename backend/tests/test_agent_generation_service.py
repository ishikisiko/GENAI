from __future__ import annotations

import asyncio

import pytest

from backend.services.agent_generation_contracts import AgentGenerationRequest
from backend.services.agent_generation_service import AgentGenerationService
from backend.shared.errors import ApplicationError, ErrorCode


class _FakeCase:
    title = "Case"
    description = "Description"


class _FakeRepository:
    def __init__(self, *, case_exists: bool = True) -> None:
        self._case_exists = case_exists
        self.replace_calls = 0

    async def get_case(self, case_id: str):
        return _FakeCase() if self._case_exists else None

    async def list_entities(self, case_id: str):
        return []

    async def list_claims(self, case_id: str):
        return []

    async def replace_agents(self, case_id: str, agents: list[dict[str, object]]):
        self.replace_calls += 1
        return agents


class _FakeLlmClient:
    def __init__(self, payload):
        self._payload = payload

    async def chat_json(self, **kwargs):
        return self._payload


def test_generate_agents_persists_profiles_and_returns_sync_payload():
    repository = _FakeRepository()
    llm_client = _FakeLlmClient(
        {
            "agents": [
                {
                    "role": "consumer",
                    "stance": "Concerned",
                    "concern": "Safety",
                    "emotional_sensitivity": 8,
                    "spread_tendency": 6,
                    "persona_description": "Consumer persona",
                    "initial_beliefs": ["Belief 1", "Belief 2"],
                },
                {
                    "role": "supporter",
                    "stance": "Supportive",
                    "concern": "Brand trust",
                    "emotional_sensitivity": 4,
                    "spread_tendency": 5,
                    "persona_description": "Supporter persona",
                    "initial_beliefs": ["Belief 1"],
                },
                {
                    "role": "critic",
                    "stance": "Skeptical",
                    "concern": "Accountability",
                    "emotional_sensitivity": 7,
                    "spread_tendency": 9,
                    "persona_description": "Critic persona",
                    "initial_beliefs": ["Belief 1"],
                },
                {
                    "role": "media",
                    "stance": "Observing",
                    "concern": "Public facts",
                    "emotional_sensitivity": 5,
                    "spread_tendency": 8,
                    "persona_description": "Media persona",
                    "initial_beliefs": ["Belief 1"],
                },
            ]
        }
    )

    service = AgentGenerationService(repository, llm_client)
    response = asyncio.run(service.generate(AgentGenerationRequest(case_id="case-123")))

    assert response.outcome == "completed"
    assert response.case_status == "agents_ready"
    assert len(response.agents) == 4
    assert repository.replace_calls == 1


def test_generate_agents_returns_handled_not_found_error():
    repository = _FakeRepository(case_exists=False)
    llm_client = _FakeLlmClient({"agents": []})
    service = AgentGenerationService(repository, llm_client)

    with pytest.raises(ApplicationError) as exc_info:
        asyncio.run(service.generate(AgentGenerationRequest(case_id="missing-case")))

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert repository.replace_calls == 0


def test_generate_agents_avoids_partial_success_when_llm_roles_are_invalid():
    repository = _FakeRepository()
    llm_client = _FakeLlmClient(
        {
            "agents": [
                {
                    "role": "consumer",
                    "stance": "Concerned",
                    "concern": "Safety",
                    "emotional_sensitivity": 8,
                    "spread_tendency": 6,
                    "persona_description": "Consumer persona",
                    "initial_beliefs": ["Belief 1", "Belief 2"],
                },
                {
                    "role": "supporter",
                    "stance": "Supportive",
                    "concern": "Brand trust",
                    "emotional_sensitivity": 4,
                    "spread_tendency": 5,
                    "persona_description": "Supporter persona",
                    "initial_beliefs": ["Belief 1"],
                },
                {
                    "role": "media",
                    "stance": "Observing",
                    "concern": "Public facts",
                    "emotional_sensitivity": 5,
                    "spread_tendency": 8,
                    "persona_description": "Media persona",
                    "initial_beliefs": ["Belief 1"],
                },
            ]
        }
    )
    service = AgentGenerationService(repository, llm_client)

    with pytest.raises(ApplicationError) as exc_info:
        asyncio.run(service.generate(AgentGenerationRequest(case_id="case-123")))

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert repository.replace_calls == 0
