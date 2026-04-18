from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.domain.models import Job
from backend.domain.simulation_records import RunType, SimulationStatus
from backend.repository.job_repository import JobRepository
from backend.repository.simulation_repository import SIMULATION_JOB_TYPE, SimulationRepository
from backend.services.llm_client import LlmJsonClient
from backend.services.simulation_contracts import (
    JobStatusResponse,
    SimulationJobPayload,
    SimulationRoundResult,
    SimulationRunStatusResponse,
    SimulationSubmissionRequest,
    SimulationSubmissionResponse,
)
from backend.shared.config import BackendConfig
from backend.shared.errors import ApplicationError, ErrorCode


def get_default_strategy_message(strategy_type: str) -> str:
    defaults = {
        "apology": "We sincerely apologize for the harm caused. We take full responsibility and are committed to making things right.",
        "clarification": "We want to clarify the facts: the situation has been misrepresented. Here is the accurate account of what occurred.",
        "compensation": "We are offering full refunds and compensation to all affected customers. Please contact us directly to resolve this.",
        "rebuttal": "The claims being circulated are inaccurate. We have conducted a thorough investigation and the evidence does not support these allegations.",
    }
    return defaults.get(
        strategy_type,
        "We are aware of the situation and are actively working to address all concerns.",
    )


class SimulationService:
    def __init__(
        self,
        config: BackendConfig,
        simulation_repository: SimulationRepository,
        job_repository: JobRepository,
        llm_client: LlmJsonClient,
    ) -> None:
        self._config = config
        self._simulation_repository = simulation_repository
        self._job_repository = job_repository
        self._llm_client = llm_client

    async def submit(self, request: SimulationSubmissionRequest) -> SimulationSubmissionResponse:
        crisis_case = await self._simulation_repository.get_case(request.case_id)
        if crisis_case is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message="Case not found",
                status_code=404,
            )

        agents = await self._simulation_repository.list_agents(request.case_id)
        if not agents:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No agents found for this case. Generate agents first.",
                status_code=400,
            )

        if await self._simulation_repository.has_active_run(request.case_id):
            raise ApplicationError(
                code=ErrorCode.CONFLICT,
                message="Another simulation is already running for this case. Please wait until it finishes.",
                status_code=409,
            )

        run, job = await self._simulation_repository.create_submission(request)
        return SimulationSubmissionResponse(
            run_id=str(run.id),
            job_id=str(job.id),
            job_status=job.status.value,
            run_status=run.status.value,
        )

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        job = await self._job_repository.get_job(job_id)
        run = await self._simulation_repository.get_run_by_job_id(job_id)
        return JobStatusResponse(
            id=str(job.id),
            job_type=job.job_type,
            status=job.status.value,
            run_id=str(run.id) if run else None,
            last_error=job.last_error,
            last_error_code=job.last_error_code,
            locked_at=job.locked_at.astimezone(timezone.utc).isoformat() if job.locked_at else None,
            heartbeat_at=job.heartbeat_at.astimezone(timezone.utc).isoformat() if job.heartbeat_at else None,
            updated_at=job.updated_at.astimezone(timezone.utc).isoformat() if job.updated_at else None,
            created_at=job.created_at.astimezone(timezone.utc).isoformat() if job.created_at else None,
        )

    async def get_run_status(self, run_id: str) -> SimulationRunStatusResponse:
        status = await self._simulation_repository.get_run_status(run_id)
        run_status = status["status"]
        if isinstance(run_status, str):
            run_status = SimulationStatus(run_status)
        return SimulationRunStatusResponse(
            id=str(status["id"]),
            job_id=status["job_id"],
            status=run_status,
            error_message=status["error_message"],
            total_rounds=int(status["total_rounds"]),
            completed_rounds=int(status["completed_rounds"]),
            last_completed_round=int(status["last_completed_round"]),
            last_heartbeat_at=status["last_heartbeat_at"].astimezone(timezone.utc).isoformat()
            if status["last_heartbeat_at"]
            else None,
            created_at=status["created_at"].astimezone(timezone.utc).isoformat(),
            completed_at=status["completed_at"].astimezone(timezone.utc).isoformat() if status["completed_at"] else None,
            should_poll=run_status in {SimulationStatus.PENDING, SimulationStatus.RUNNING},
        )

    async def handle_job(self, job: Job) -> None:
        if job.job_type != SIMULATION_JOB_TYPE:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unsupported job type: {job.job_type}",
                status_code=400,
            )
        payload = SimulationJobPayload.from_job_payload(str(job.id), dict(job.payload))
        await self._execute(payload)

    async def recover_stale_jobs(self) -> int:
        timeout_seconds = max(self._config.simulation_stale_timeout_seconds, 60)
        stale_before = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        jobs = await self._job_repository.find_stale_running_jobs(
            stale_before=stale_before,
            job_type=SIMULATION_JOB_TYPE,
        )
        recovered = 0
        for job in jobs:
            await self._job_repository.mark_running_stale(
                str(job.id),
                message="Simulation was interrupted or timed out before completion.",
            )
            await self._simulation_repository.mark_run_failed_for_job(
                str(job.id),
                message="Simulation was interrupted or timed out before completion.",
            )
            recovered += 1
        return recovered

    async def _execute(self, payload: SimulationJobPayload) -> None:
        crisis_case = await self._simulation_repository.get_case(payload.case_id)
        if crisis_case is None:
            raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

        agents = await self._simulation_repository.list_agents(payload.case_id)
        claims = await self._simulation_repository.list_claims(payload.case_id)
        entities = await self._simulation_repository.list_entities(payload.case_id)
        if not agents:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No agents found for this case. Generate agents first.",
                status_code=400,
            )

        await self._job_repository.touch_heartbeat(payload.job_id)
        await self._simulation_repository.mark_run_running(payload.run_id)

        previous_narrative = "The crisis has just emerged publicly. Initial reactions are forming."
        previous_sentiment = -0.3

        crisis_context = f"""
Crisis: {crisis_case.title or "Unknown Crisis"}

Key Facts:
{"".join(f"- [{claim.claim_type}] {claim.content}\n" for claim in claims[:8])}

Key Entities: {", ".join(f"{entity.name} ({entity.entity_type})" for entity in entities)}
""".strip()

        agent_summaries = "\n\n".join(
            (
                f"{agent.role.upper()} - {agent.persona_description}\n"
                f"Stance: {agent.stance}\n"
                f"Concern: {agent.concern}\n"
                f"Emotional Sensitivity: {agent.emotional_sensitivity}/10, "
                f"Spread Tendency: {agent.spread_tendency}/10\n"
                f"Beliefs: {'; '.join(agent.initial_beliefs or [])}"
            )
            for agent in agents
        )

        try:
            for round_number in range(1, payload.total_rounds + 1):
                await self._job_repository.touch_heartbeat(payload.job_id)
                await self._simulation_repository.update_run_heartbeat(payload.run_id, status=SimulationStatus.RUNNING)

                is_injection_round = (
                    payload.run_type == RunType.INTERVENTION
                    and payload.injection_round is not None
                    and round_number == payload.injection_round
                )
                strategy_applied = payload.strategy_type.value if is_injection_round and payload.strategy_type else None

                strategy_context = self._build_strategy_context(payload, round_number, is_injection_round)
                prompt = f"""You are simulating a crisis communication scenario. Simulate round {round_number} of {payload.total_rounds}.

CRISIS CONTEXT:
{crisis_context}

AGENTS IN THIS SIMULATION:
{agent_summaries}

CURRENT NARRATIVE STATE (end of round {round_number - 1}):
{previous_narrative}

CURRENT OVERALL SENTIMENT: {previous_sentiment:.2f} (scale: -1.0 very negative to +1.0 very positive)
{strategy_context}

For round {round_number}, generate each agent's realistic reaction/response based on their persona and the current narrative.

Return a JSON object with:
- "agent_responses": array of {{
    "agent_id": the agent's role (consumer/supporter/critic/media),
    "response": 2-3 sentence realistic response/reaction this agent would post or say,
    "sentiment_delta": float from -0.3 to +0.3 showing how this agent's reaction shifts overall sentiment,
    "amplification": float 0-1 showing how much this agent amplifies the crisis
  }}
- "overall_sentiment": float -1.0 to 1.0 for end of this round
- "polarization_level": float 0.0 to 1.0 (how divided public opinion is)
- "negative_claim_spread": float 0.0 to 1.0 (how much negative claims are spreading)
- "stabilization_indicator": float 0.0 to 1.0 (how stable/settled the situation is)
- "narrative_state": 2-3 sentence summary of the overall narrative at end of this round

Ensure values are realistic and evolve logically from round to round.
Return ONLY valid JSON."""
                raw_result = await self._llm_client.chat_json(prompt=prompt, temperature=0.75, max_retries=3)
                round_result = SimulationRoundResult.from_llm_payload(raw_result)

                agent_responses = [
                    {
                        "agent_id": str(agents[index].id) if index < len(agents) else response.agent_id,
                        "role": response.agent_id,
                        "response": response.response,
                        "sentiment_delta": response.sentiment_delta,
                        "amplification": response.amplification,
                    }
                    for index, response in enumerate(round_result.agent_responses)
                ]
                await self._simulation_repository.record_round(
                    run_id=payload.run_id,
                    round_number=round_number,
                    agent_responses=agent_responses,
                    overall_sentiment=round_result.overall_sentiment,
                    polarization_level=round_result.polarization_level,
                    narrative_state=round_result.narrative_state,
                    strategy_applied=strategy_applied,
                    negative_claim_spread=round_result.negative_claim_spread,
                    stabilization_indicator=round_result.stabilization_indicator,
                )
                previous_narrative = round_result.narrative_state
                previous_sentiment = round_result.overall_sentiment

            await self._simulation_repository.mark_run_completed(payload.run_id)
            await self._job_repository.touch_heartbeat(payload.job_id)
        except Exception as exc:
            await self._simulation_repository.mark_run_failed(payload.run_id, str(exc))
            raise

    @staticmethod
    def _build_strategy_context(
        payload: SimulationJobPayload,
        round_number: int,
        is_injection_round: bool,
    ) -> str:
        if not payload.strategy_type:
            return ""
        if is_injection_round:
            return (
                f'\n\nCRISIS RESPONSE STRATEGY INJECTED (Round {round_number}):\n'
                f"Strategy Type: {payload.strategy_type.value.upper()}\n"
                f'Message: "{payload.strategy_message or get_default_strategy_message(payload.strategy_type.value)}"\n'
                "This response has just been made public. All agents are now aware of this official response."
            )
        if payload.injection_round and round_number > payload.injection_round:
            return (
                f"\n\nNote: The {payload.strategy_type.value} response was issued in round "
                f"{payload.injection_round}. Agents are processing its ongoing effects."
            )
        return ""
