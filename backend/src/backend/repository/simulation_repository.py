from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from backend.db import Database
from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    AgentProfileRecord,
    ClaimRecord,
    CrisisCaseRecord,
    EntityRecord,
    MetricSnapshotRecord,
    RoundStateRecord,
    SimulationRunRecord,
    SimulationStatus,
)
from backend.services.simulation_contracts import SimulationJobPayload, SimulationSubmissionRequest
from backend.shared.errors import ApplicationError, ErrorCode


SIMULATION_JOB_TYPE = "simulation.run"


class SimulationRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_case(self, case_id: str) -> CrisisCaseRecord | None:
        async with self._database.session() as session:
            return await session.get(CrisisCaseRecord, case_id)

    async def list_agents(self, case_id: str) -> list[AgentProfileRecord]:
        async with self._database.session() as session:
            rows = await session.execute(
                select(AgentProfileRecord)
                .where(AgentProfileRecord.case_id == case_id)
                .order_by(AgentProfileRecord.created_at.asc())
            )
            return list(rows.scalars().all())

    async def replace_agents(self, case_id: str, agents: list[dict[str, object]]) -> list[AgentProfileRecord]:
        async with self._database.session() as session:
            await session.execute(delete(AgentProfileRecord).where(AgentProfileRecord.case_id == case_id))
            rows: list[AgentProfileRecord] = []
            now = datetime.now(timezone.utc)
            for payload in agents:
                rows.append(
                    AgentProfileRecord(
                        case_id=case_id,
                        role=str(payload["role"]),
                        stance=str(payload["stance"]),
                        concern=str(payload["concern"]),
                        emotional_sensitivity=int(payload["emotional_sensitivity"]),
                        spread_tendency=int(payload["spread_tendency"]),
                        initial_beliefs=list(payload["initial_beliefs"]),
                        persona_description=str(payload["persona_description"]),
                        created_at=now,
                    )
                )
            if rows:
                session.add_all(rows)
                await session.flush()
            crisis_case = await session.get(CrisisCaseRecord, case_id)
            if crisis_case is not None:
                crisis_case.status = "agents_ready"
                crisis_case.updated_at = now
            return rows

    async def list_claims(self, case_id: str) -> list[ClaimRecord]:
        async with self._database.session() as session:
            rows = await session.execute(
                select(ClaimRecord).where(ClaimRecord.case_id == case_id).order_by(ClaimRecord.created_at.asc())
            )
            return list(rows.scalars().all())

    async def list_entities(self, case_id: str) -> list[EntityRecord]:
        async with self._database.session() as session:
            rows = await session.execute(
                select(EntityRecord).where(EntityRecord.case_id == case_id).order_by(EntityRecord.created_at.asc())
            )
            return list(rows.scalars().all())

    async def has_active_run(self, case_id: str) -> bool:
        async with self._database.session() as session:
            rows = await session.execute(
                select(func.count(SimulationRunRecord.id)).where(
                    SimulationRunRecord.case_id == case_id,
                    SimulationRunRecord.status.in_([SimulationStatus.PENDING, SimulationStatus.RUNNING]),
                )
            )
            return (rows.scalar_one() or 0) > 0

    async def create_submission(self, request: SimulationSubmissionRequest) -> tuple[SimulationRunRecord, Job]:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            run = SimulationRunRecord(
                case_id=request.case_id,
                run_type=request.run_type,
                strategy_type=request.strategy_type.value if request.strategy_type else None,
                strategy_message=request.strategy_message,
                injection_round=request.injection_round,
                total_rounds=request.total_rounds,
                status=SimulationStatus.PENDING,
                last_heartbeat_at=now,
                created_at=now,
            )
            session.add(run)
            await session.flush()

            payload = SimulationJobPayload(
                job_id="",
                run_id=str(run.id),
                case_id=request.case_id,
                run_type=request.run_type,
                total_rounds=request.total_rounds,
                strategy_type=request.strategy_type,
                strategy_message=request.strategy_message,
                injection_round=request.injection_round,
            ).model_dump(mode="json")
            payload.pop("job_id", None)

            job = Job(
                job_type=SIMULATION_JOB_TYPE,
                status=JobStatus.PENDING,
                payload=payload,
                max_attempts=1,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            await session.flush()

            run.job_id = str(job.id)
            await session.flush()
            await session.refresh(run)
            await session.refresh(job)
            return run, job

    async def get_run(self, run_id: str) -> SimulationRunRecord:
        async with self._database.session() as session:
            run = await session.get(SimulationRunRecord, run_id)
            if run is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Simulation run not found: {run_id}",
                    status_code=404,
                )
            return run

    async def get_run_by_job_id(self, job_id: str) -> SimulationRunRecord | None:
        async with self._database.session() as session:
            rows = await session.execute(select(SimulationRunRecord).where(SimulationRunRecord.job_id == job_id))
            return rows.scalar_one_or_none()

    async def mark_run_running(self, run_id: str) -> SimulationRunRecord:
        async with self._database.session() as session:
            run = await self._get_run_with_lock(session, run_id)
            now = datetime.now(timezone.utc)
            run.status = SimulationStatus.RUNNING
            run.error_message = None
            run.last_heartbeat_at = now
            return run

    async def update_run_heartbeat(self, run_id: str, status: SimulationStatus | None = None) -> SimulationRunRecord:
        async with self._database.session() as session:
            run = await self._get_run_with_lock(session, run_id)
            run.last_heartbeat_at = datetime.now(timezone.utc)
            if status is not None:
                run.status = status
            return run

    async def record_round(
        self,
        run_id: str,
        round_number: int,
        agent_responses: list[dict],
        overall_sentiment: float,
        polarization_level: float,
        narrative_state: str,
        strategy_applied: str | None,
        negative_claim_spread: float,
        stabilization_indicator: float,
    ) -> None:
        async with self._database.session() as session:
            now = datetime.now(timezone.utc)
            session.add(
                RoundStateRecord(
                    run_id=run_id,
                    round_number=round_number,
                    agent_responses=agent_responses,
                    overall_sentiment=overall_sentiment,
                    polarization_level=polarization_level,
                    narrative_state=narrative_state,
                    strategy_applied=strategy_applied,
                    created_at=now,
                )
            )
            session.add(
                MetricSnapshotRecord(
                    run_id=run_id,
                    round_number=round_number,
                    sentiment_score=overall_sentiment,
                    polarization_score=polarization_level,
                    negative_claim_spread=negative_claim_spread,
                    stabilization_indicator=stabilization_indicator,
                    created_at=now,
                )
            )
            run = await self._get_run_with_lock(session, run_id)
            run.status = SimulationStatus.RUNNING
            run.last_heartbeat_at = now

    async def mark_run_completed(self, run_id: str) -> SimulationRunRecord:
        async with self._database.session() as session:
            run = await self._get_run_with_lock(session, run_id)
            case = await session.get(CrisisCaseRecord, run.case_id)
            now = datetime.now(timezone.utc)
            run.status = SimulationStatus.COMPLETED
            run.error_message = None
            run.completed_at = now
            run.last_heartbeat_at = now
            if case is not None:
                case.status = "simulated"
                case.updated_at = now
            return run

    async def mark_run_failed(self, run_id: str, message: str) -> SimulationRunRecord:
        async with self._database.session() as session:
            run = await self._get_run_with_lock(session, run_id)
            now = datetime.now(timezone.utc)
            run.status = SimulationStatus.FAILED
            run.error_message = message
            run.completed_at = now
            run.last_heartbeat_at = now
            return run

    async def mark_run_failed_for_job(self, job_id: str, message: str) -> SimulationRunRecord | None:
        async with self._database.session() as session:
            rows = await session.execute(
                select(SimulationRunRecord).where(SimulationRunRecord.job_id == job_id).with_for_update()
            )
            run = rows.scalar_one_or_none()
            if run is None:
                return None
            now = datetime.now(timezone.utc)
            run.status = SimulationStatus.FAILED
            run.error_message = message
            run.completed_at = now
            run.last_heartbeat_at = now
            return run

    async def get_run_status(self, run_id: str) -> dict[str, object]:
        async with self._database.session() as session:
            run = await session.get(SimulationRunRecord, run_id)
            if run is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Simulation run not found: {run_id}",
                    status_code=404,
                )
            completed_rounds = await session.execute(
                select(func.count(RoundStateRecord.id)).where(RoundStateRecord.run_id == run_id)
            )
            count = int(completed_rounds.scalar_one() or 0)
            return {
                "id": str(run.id),
                "job_id": str(run.job_id) if run.job_id else None,
                "status": run.status,
                "error_message": run.error_message,
                "total_rounds": run.total_rounds,
                "completed_rounds": count,
                "last_completed_round": count,
                "last_heartbeat_at": run.last_heartbeat_at,
                "created_at": run.created_at,
                "completed_at": run.completed_at,
            }

    async def _get_run_with_lock(self, session, run_id: str) -> SimulationRunRecord:
        rows = await session.execute(
            select(SimulationRunRecord).where(SimulationRunRecord.id == run_id).with_for_update()
        )
        run = rows.scalar_one_or_none()
        if run is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message=f"Simulation run not found: {run_id}",
                status_code=404,
            )
        return run
