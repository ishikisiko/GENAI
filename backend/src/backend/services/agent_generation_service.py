from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.services.agent_generation_contracts import AgentGenerationRequest, AgentGenerationResponse, GeneratedAgent
from backend.services.llm_client import LlmJsonClient
from backend.repository.simulation_repository import SimulationRepository
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode
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
        try:
            payload = LlmAgentBundle.model_validate(self._normalize_llm_payload(extracted))
        except ValidationError as exc:
            raise DependencyError(
                "llm",
                details={
                    "reason": "LLM returned invalid agent payload",
                    "validation_errors": exc.errors(include_url=False),
                },
            ) from exc

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
            extra={
                "case_id": request.case_id,
                "agent_count": len(payload.agents),
                "case_status": "agents_ready",
                "at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return AgentGenerationResponse(
            case_id=request.case_id,
            case_status="agents_ready",
            agents=payload.agents,
        )

    @classmethod
    def _normalize_llm_payload(cls, raw_payload: Any) -> dict[str, Any]:
        if not isinstance(raw_payload, dict):
            raise DependencyError("llm", details={"reason": "LLM returned non-object JSON"})
        agents = raw_payload.get("agents")
        if not isinstance(agents, list):
            raise DependencyError("llm", details={"reason": "LLM response is missing agents array"})
        return {"agents": [cls._normalize_agent(agent) for agent in agents if isinstance(agent, dict)]}

    @classmethod
    def _normalize_agent(cls, agent: dict[str, Any]) -> dict[str, Any]:
        role = cls._normalize_role(agent.get("role") or agent.get("type") or agent.get("stakeholder_type"))
        stance = agent.get("stance") or agent.get("stanc") or agent.get("position") or agent.get("attitude")
        concern = agent.get("concern") or agent.get("primary_concern") or agent.get("main_concern")
        persona = (
            agent.get("persona_description")
            or agent.get("description")
            or agent.get("persona")
            or f"{role or 'Stakeholder'} participant in the crisis conversation."
        )
        return {
            **agent,
            "role": role,
            "stance": str(stance or "Undetermined stance"),
            "concern": str(concern or "Needs more information before reacting."),
            "emotional_sensitivity": cls._normalize_score(agent.get("emotional_sensitivity")),
            "spread_tendency": cls._normalize_score(agent.get("spread_tendency")),
            "persona_description": str(persona),
            "initial_beliefs": cls._normalize_beliefs(agent.get("initial_beliefs") or agent.get("beliefs")),
        }

    @staticmethod
    def _normalize_role(value: Any) -> str:
        normalized = str(value or "").strip().lower().replace(" ", "_")
        aliases = {
            "customer": "consumer",
            "affected_consumer": "consumer",
            "loyalist": "supporter",
            "brand_supporter": "supporter",
            "activist": "critic",
            "skeptic": "critic",
            "skeptical_journalist": "critic",
            "journalist": "media",
            "reporter": "media",
            "news_media": "media",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_score(value: Any) -> int:
        try:
            return min(max(int(float(value)), 1), 10)
        except (TypeError, ValueError):
            return 5

    @classmethod
    def _normalize_beliefs(cls, value: Any) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        beliefs: list[str] = []
        for item in values:
            if isinstance(item, dict):
                item = item.get("belief") or item.get("text") or item.get("content")
            text = str(item or "").strip()
            if text:
                beliefs.append(text)
        return beliefs
