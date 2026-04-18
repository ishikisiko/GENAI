from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.services.agent_generation_contracts import (
    AgentGenerationRequest,
    AgentGenerationResponse,
    GeneratedAgent,
)
from backend.services.simulation_repository import SimulationRepository
from backend.services.llm_client import LlmJsonClient
from backend.shared.errors import ApplicationError, ErrorCode
from backend.shared.logging import get_logger


class LlmAgentBundle(BaseModel):
    agents: list[GeneratedAgent]


class AgentGenerationService:
    def __init__(self, simulation_repository: SimulationRepository, llm_client: LlmJsonClient) -> None:
        self._simulation_repository = simulation_repository
        self._llm_client = llm_client
        self._logger = get_logger("backend.agent_generation")

    async def generate(self, request: AgentGenerationRequest) -> AgentGenerationResponse:
        crisis_case = await self._simulation_repository.get_case(request.case_id)
        if crisis_case is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message="Case not found",
                status_code=404,
            )

        entities = await self._simulation_repository.list_entities(request.case_id)
        claims = await self._simulation_repository.list_claims(request.case_id)

        self._logger.info(
            "agent_generation_started",
            extra={"case_id": request.case_id, "entity_count": len(entities), "claim_count": len(claims)},
        )

        graph_summary = f"""
Crisis: {crisis_case.title}
{crisis_case.description}

Key Entities: {", ".join(f"{entity.name} ({entity.entity_type})" for entity in entities)}

Key Claims:
{chr(10).join(f"- [{claim.claim_type}] {claim.content}" for claim in claims[:10])}
""".strip()

        prompt = f"""You are a crisis communication expert. Based on the crisis scenario below, generate 4 stakeholder agent profiles that will participate in a public opinion simulation.

CRISIS CONTEXT:
{graph_summary}

Generate exactly 4 agents with these roles (one each):
1. consumer - An affected consumer/customer
2. supporter - A brand/organization supporter or loyal customer
3. critic - A vocal critic, activist, or skeptical journalist
4. media - A media outlet or journalist reporting on the crisis

For each agent return:
- role: (one of: consumer, supporter, critic, media)
- stance: brief stance description (e.g. "Deeply concerned and disappointed", "Cautiously defending the brand")
- concern: their primary concern in this crisis (1-2 sentences)
- emotional_sensitivity: integer 1-10 (how emotionally reactive they are)
- spread_tendency: integer 1-10 (how likely they are to spread information)
- persona_description: 2-3 sentence vivid description of who this person is
- initial_beliefs: array of 3-5 belief strings grounded in the crisis facts

Return ONLY a valid JSON object with key "agents" containing the array."""

        extracted = await self._llm_client.chat_json(prompt=prompt, temperature=0.7, max_retries=3)
        payload = LlmAgentBundle.model_validate(extracted)

        if len(payload.agents) != 4:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="LLM response must include exactly 4 agents",
                status_code=422,
            )

        expected_roles = {"consumer", "supporter", "critic", "media"}
        if {agent.role for agent in payload.agents} != expected_roles:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="LLM response must include exactly roles: consumer, supporter, critic, media",
                status_code=422,
            )

        generated_rows = [
            {
                "role": agent.role,
                "stance": agent.stance,
                "concern": agent.concern,
                "emotional_sensitivity": int(agent.emotional_sensitivity),
                "spread_tendency": int(agent.spread_tendency),
                "persona_description": agent.persona_description,
                "initial_beliefs": list(agent.initial_beliefs),
            }
            for agent in payload.agents
        ]

        await self._simulation_repository.replace_agents(request.case_id, generated_rows)

        self._logger.info(
            "agent_generation_completed",
            extra={"case_id": request.case_id, "agent_count": len(payload.agents), "at": datetime.utcnow().isoformat()},
        )

        return AgentGenerationResponse(
            case_id=request.case_id,
            case_status="agents_ready",
            agents=payload.agents,
        )
