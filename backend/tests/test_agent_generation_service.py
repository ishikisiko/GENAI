from __future__ import annotations

import asyncio

import pytest

from backend.services.agent_generation_contracts import AgentGenerationRequest
from backend.services.agent_generation_service import AgentGenerationService
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode


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


def test_generate_agents_normalizes_common_llm_shape_drift():
    repository = _FakeRepository()
    llm_client = _FakeLlmClient(
        {
            "agents": [
                {
                    "role": "customer",
                    "stanc": "Worried",
                    "primary_concern": "Safety",
                    "emotional_sensitivity": "8",
                    "spread_tendency": "6",
                    "description": "A concerned customer.",
                    "beliefs": [{"text": "The incident may affect family dining choices."}],
                },
                {
                    "role": "brand_supporter",
                    "position": "Supportive",
                    "concern": "Brand reputation",
                    "emotional_sensitivity": 4,
                    "spread_tendency": 5,
                    "persona": "A loyal customer.",
                    "initial_beliefs": "The brand deserves a chance to respond.",
                },
                {
                    "role": "activist",
                    "attitude": "Critical",
                    "main_concern": "Accountability",
                    "emotional_sensitivity": 7,
                    "spread_tendency": 9,
                    "persona_description": "A consumer advocate.",
                    "initial_beliefs": ["Public pressure is necessary."],
                },
                {
                    "role": "journalist",
                    "stance": "Investigating",
                    "concern": "Verified public facts",
                    "emotional_sensitivity": 5,
                    "spread_tendency": 8,
                    "persona_description": "A beat reporter.",
                    "initial_beliefs": ["The story needs careful sourcing."],
                },
            ]
        }
    )

    service = AgentGenerationService(repository, llm_client)
    response = asyncio.run(service.generate(AgentGenerationRequest(case_id="case-123")))

    assert {agent.role for agent in response.agents} == {"consumer", "supporter", "critic", "media"}
    assert response.agents[0].stance == "Worried"
    assert response.agents[0].initial_beliefs == ["The incident may affect family dining choices."]
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


def test_generate_agents_rejects_unusable_llm_payload_as_dependency_error():
    repository = _FakeRepository()
    llm_client = _FakeLlmClient({"agents": "not an array"})
    service = AgentGenerationService(repository, llm_client)

    with pytest.raises(DependencyError):
        asyncio.run(service.generate(AgentGenerationRequest(case_id="case-123")))

    assert repository.replace_calls == 0
