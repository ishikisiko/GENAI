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
    evidence_pack_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("evidence_packs.id"), nullable=True)
    evidence_pack_source_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("evidence_pack_sources.id"), nullable=True)
    source_topic_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_topics.id"), nullable=True)
    source_topic_assignment_id: Mapped[str | None] = mapped_column(
        Uuid,
        ForeignKey("source_topic_assignments.id"),
        nullable=True,
    )
    source_origin: Mapped[str] = mapped_column(String(32), nullable=False, default="case_upload")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SourceDiscoveryStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandidateReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EvidencePackStatus(StrEnum):
    DRAFT = "draft"
    GROUNDING_STARTED = "grounding_started"


class SourceDiscoveryJobRecord(Base):
    __tablename__ = "source_discovery_jobs"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[SourceDiscoveryStatus] = mapped_column(
        String(32),
        default=SourceDiscoveryStatus.PENDING,
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    region: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    time_range: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    query_plan: Mapped[list[str]] = mapped_column(JSON, default=list)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceCandidateRecord(Base):
    __tablename__ = "source_candidates"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    discovery_job_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("source_discovery_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="news")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    region: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    classification: Mapped[str] = mapped_column(String(64), nullable=False, default="news")
    claim_previews: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    stakeholder_previews: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    review_status: Mapped[CandidateReviewStatus] = mapped_column(
        String(32),
        default=CandidateReviewStatus.PENDING,
        nullable=False,
    )
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    authority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    claim_richness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    diversity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grounding_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duplicate_of: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_candidates.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EvidencePackRecord(Base):
    __tablename__ = "evidence_packs"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    discovery_job_id: Mapped[str | None] = mapped_column(
        Uuid,
        ForeignKey("source_discovery_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[EvidencePackStatus] = mapped_column(
        String(32),
        default=EvidencePackStatus.DRAFT,
        nullable=False,
    )
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    grounded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidencePackSourceRecord(Base):
    __tablename__ = "evidence_pack_sources"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    evidence_pack_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("evidence_packs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("source_candidates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_document_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_documents.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="news")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    region: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score_dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    claim_previews: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    stakeholder_previews: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalSourceDocumentRecord(Base):
    __tablename__ = "global_source_documents"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="news")
    authority_level: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    freshness_status: Mapped[str] = mapped_column(String(32), nullable=False, default="current")
    source_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SourceTopicRecord(Base):
    __tablename__ = "source_topics"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_topic_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_topics.id"), nullable=True)
    topic_type: Mapped[str] = mapped_column(String(64), nullable=False, default="collection")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CaseSourceTopicRecord(Base):
    __tablename__ = "case_source_topics"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(Uuid, ForeignKey("crisis_cases.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str] = mapped_column(Uuid, ForeignKey("source_topics.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SourceTopicAssignmentRecord(Base):
    __tablename__ = "source_topic_assignments"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    global_source_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("global_source_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[str] = mapped_column(Uuid, ForeignKey("source_topics.id", ondelete="CASCADE"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assigned_by: Mapped[str] = mapped_column(String(64), nullable=False, default="user")
    source_candidate_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_candidates.id"), nullable=True)
    discovery_job_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("source_discovery_jobs.id"), nullable=True)
    assignment_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SourceFragmentRecord(Base):
    __tablename__ = "source_fragments"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    global_source_id: Mapped[str | None] = mapped_column(
        Uuid,
        ForeignKey("global_source_documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_candidate_id: Mapped[str | None] = mapped_column(
        Uuid,
        ForeignKey("source_candidates.id", ondelete="CASCADE"),
        nullable=True,
    )
    fragment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    fragment_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False, default="local-token-hash")
    embedding_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    vector_index_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    index_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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
    strategy_sequence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
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
