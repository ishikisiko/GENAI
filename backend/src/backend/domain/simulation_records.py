from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Integer, JSON, Uuid

from backend.domain.models import Base


class RunType(StrEnum):
    BASELINE = "baseline"
    INTERVENTION = "intervention"


class StrategyType(StrEnum):
    APOLOGY = "apology"
    CLARIFICATION = "clarification"
    COMPENSATION = "compensation"
    REBUTTAL = "rebuttal"


class SimulationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrisisCaseRecord(Base):
    __tablename__ = "crisis_cases"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SourceDocumentRecord(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    global_source_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("global_source_documents.id"), nullable=True)
    source_origin: Mapped[str] = mapped_column(String(32), nullable=False, default="case_upload")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalSourceDocumentRecord(Base):
    __tablename__ = "global_source_documents"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AgentProfileRecord(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    stance: Mapped[str] = mapped_column(Text, nullable=False)
    concern: Mapped[str] = mapped_column(Text, nullable=False)
    emotional_sensitivity: Mapped[int] = mapped_column(Integer, nullable=False)
    spread_tendency: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_beliefs: Mapped[list[str]] = mapped_column(JSON, default=list)
    persona_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)
    credibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_doc_id: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EntityRecord(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RelationRecord(Base):
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    source_entity_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("entities.id", ondelete="SET NULL"))
    target_entity_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("entities.id", ondelete="SET NULL"))
    relation_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SimulationRunRecord(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    run_type: Mapped[RunType] = mapped_column(String(32), default=RunType.BASELINE, nullable=False)
    strategy_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strategy_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    injection_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_rounds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[SimulationStatus] = mapped_column(String(20), default=SimulationStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RoundStateRecord(Base):
    __tablename__ = "round_states"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[str] = mapped_column(Uuid, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_responses: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    overall_sentiment: Mapped[float] = mapped_column(Float, nullable=False)
    polarization_level: Mapped[float] = mapped_column(Float, nullable=False)
    narrative_state: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_applied: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MetricSnapshotRecord(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[str] = mapped_column(Uuid, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    polarization_score: Mapped[float] = mapped_column(Float, nullable=False)
    negative_claim_spread: Mapped[float] = mapped_column(Float, nullable=False)
    stabilization_indicator: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
