from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.services.contracts import AsyncStatusResponse, AsyncSubmissionResponse
from backend.services.extraction_contracts import GraphExtractionSubmissionResponse


SOURCE_DISCOVERY_JOB_TYPE = "source_discovery.run"


class SourceDiscoveryEvidenceBucketHint(BaseModel):
    key: str
    label: str = ""
    queries: list[str] = Field(default_factory=list)


class SourceDiscoveryPlanningContext(BaseModel):
    core_entities: list[str] = Field(default_factory=list)
    actor_names: list[str] = Field(default_factory=list)
    event_aliases: list[str] = Field(default_factory=list)
    language_variants: list[str] = Field(default_factory=list)
    evidence_buckets: list[SourceDiscoveryEvidenceBucketHint] = Field(default_factory=list)

    @field_validator("core_entities", "actor_names", "event_aliases", "language_variants", mode="before")
    @classmethod
    def normalize_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        raw_values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        for item in raw_values:
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized


class SourceDiscoveryJobCreateRequest(BaseModel):
    case_id: str
    topic: str
    description: str = ""
    region: str = ""
    language: str = "en"
    time_range: str = ""
    source_types: list[str] = Field(default_factory=lambda: ["news", "official", "social"])
    max_sources: int = Field(default=10, ge=1, le=50)
    planning_context: SourceDiscoveryPlanningContext | None = None

    @field_validator("topic")
    @classmethod
    def topic_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic is required")
        return value

    @field_validator("source_types")
    @classmethod
    def normalize_source_types(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().lower() for item in value if item.strip()]
        return normalized or ["news"]

    @field_validator("time_range")
    @classmethod
    def normalize_time_range(cls, value: str) -> str:
        return value.strip()


class SourceDiscoveryJobPayload(SourceDiscoveryJobCreateRequest):
    source_discovery_job_id: str
    job_id: str

    @classmethod
    def from_job_payload(cls, job_id: str, payload: dict[str, Any]) -> "SourceDiscoveryJobPayload":
        return cls.model_validate({"job_id": job_id, **payload})


class SourceScoreDimensions(BaseModel):
    relevance: float = 0.0
    authority: float = 0.0
    freshness: float = 0.0
    claim_richness: float = 0.0
    diversity: float = 0.0
    grounding_value: float = 0.0

    def total(self) -> float:
        quality_average = sum([
            self.relevance,
            self.authority,
            self.freshness,
            self.claim_richness,
            self.diversity,
            self.grounding_value,
        ]) / 6

        if self.relevance < 0.35:
            quality_average = min(quality_average, 0.45)
        elif self.relevance < 0.5:
            quality_average = min(quality_average, 0.65)

        return round(quality_average, 4)


class SourceCandidateWrite(BaseModel):
    title: str
    url: str | None = None
    canonical_url: str | None = None
    source_type: str = "news"
    language: str = "en"
    region: str = ""
    published_at: datetime | None = None
    provider: str = "mock"
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    content: str = ""
    excerpt: str = ""
    content_hash: str = ""
    classification: str = "news"
    claim_previews: list[dict[str, Any]] = Field(default_factory=list)
    stakeholder_previews: list[dict[str, Any]] = Field(default_factory=list)
    scores: SourceScoreDimensions = Field(default_factory=SourceScoreDimensions)
    total_score: float | None = None


class SourceCandidateResponse(BaseModel):
    id: str
    discovery_job_id: str
    case_id: str
    title: str
    url: str | None
    canonical_url: str | None
    source_type: str
    language: str
    region: str
    published_at: str | None
    provider: str
    provider_metadata: dict[str, Any]
    content: str
    excerpt: str
    content_hash: str
    classification: str
    claim_previews: list[dict[str, Any]]
    stakeholder_previews: list[dict[str, Any]]
    review_status: str
    scores: SourceScoreDimensions
    total_score: float
    duplicate_of: str | None
    created_at: str
    updated_at: str


class SourceCandidateListResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    candidates: list[SourceCandidateResponse]


class SourceCandidateReviewRequest(BaseModel):
    review_status: Literal["pending", "accepted", "rejected"]


class SourceCandidateLibrarySaveRequest(BaseModel):
    topic_id: str | None = None
    reason: str = ""
    assigned_by: str = "user"


class SourceCandidateLibrarySaveResponse(BaseModel):
    outcome: Literal["saved"] = "saved"
    candidate_id: str
    global_source_id: str
    topic_id: str | None
    topic_assignment_id: str | None
    duplicate_reused: bool


class SourceDiscoveryJobResponse(AsyncStatusResponse):
    source_discovery_job_id: str
    case_id: str
    status: str
    job_status: str
    job_type: str = SOURCE_DISCOVERY_JOB_TYPE
    status_path: str = "/api/source-discovery/jobs/{source_discovery_job_id}"
    topic: str
    description: str
    region: str
    language: str
    time_range: str
    source_types: list[str]
    max_sources: int
    query_plan: list[str]
    candidate_count: int
    accepted_count: int
    rejected_count: int
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None


class SourceDiscoverySubmissionResponse(SourceDiscoveryJobResponse, AsyncSubmissionResponse):
    outcome: Literal["accepted"] = "accepted"


class EvidencePackCreateRequest(BaseModel):
    case_id: str
    discovery_job_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)
    title: str | None = None


class EvidencePackSourceResponse(BaseModel):
    id: str
    evidence_pack_id: str
    candidate_id: str
    source_document_id: str | None
    sort_order: int
    title: str
    url: str | None
    source_type: str
    language: str
    region: str
    published_at: str | None
    provider: str
    provider_metadata: dict[str, Any]
    content: str
    excerpt: str
    score_dimensions: SourceScoreDimensions
    total_score: float
    claim_previews: list[dict[str, Any]]
    stakeholder_previews: list[dict[str, Any]]
    created_at: str


class EvidencePackResponse(BaseModel):
    id: str
    case_id: str
    discovery_job_id: str | None
    title: str
    status: str
    source_count: int
    sources: list[EvidencePackSourceResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str
    grounded_at: str | None


class EvidencePackCreateResponse(BaseModel):
    outcome: Literal["created"] = "created"
    evidence_pack_id: str
    case_id: str
    source_count: int
    evidence_pack: EvidencePackResponse


class EvidencePackGroundingResponse(GraphExtractionSubmissionResponse):
    evidence_pack_id: str
    materialized_document_count: int


class SourceDiscoveryAssistantRequest(BaseModel):
    mode: str
    question: str = ""
    case_id: str | None = None
    discovery_job_id: str | None = None
    topic: str = ""
    description: str = ""
    region: str = ""
    language: str = "en"
    time_range: str = ""
    source_types: list[str] = Field(default_factory=list)
    max_sources: int | None = Field(default=None, ge=1, le=50)

    @field_validator("time_range")
    @classmethod
    def normalize_time_range(cls, value: str) -> str:
        return value.strip()


class SourceDiscoveryAssistantCitation(BaseModel):
    candidate_id: str | None = None
    title: str
    url: str | None = None
    published_at: str | None = None
    quote: str = ""


class SourceDiscoveryAssistantPlanningSuggestion(BaseModel):
    label: str
    rationale: str = ""
    topic: str | None = None
    description: str | None = None
    region: str | None = None
    language: str | None = None
    time_range: str | None = None
    source_types: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    core_entities: list[str] = Field(default_factory=list)
    actor_names: list[str] = Field(default_factory=list)
    event_aliases: list[str] = Field(default_factory=list)
    language_variants: list[str] = Field(default_factory=list)
    evidence_buckets: list[SourceDiscoveryEvidenceBucketHint] = Field(default_factory=list)


class SourceDiscoveryAssistantRecommendedSettings(BaseModel):
    topic: str | None = None
    description: str | None = None
    region: str | None = None
    language: str | None = None
    time_range: str | None = None
    source_types: list[str] = Field(default_factory=list)
    max_sources: int | None = Field(default=None, ge=1, le=50)
    queries: list[str] = Field(default_factory=list)
    core_entities: list[str] = Field(default_factory=list)
    actor_names: list[str] = Field(default_factory=list)
    event_aliases: list[str] = Field(default_factory=list)
    language_variants: list[str] = Field(default_factory=list)
    evidence_buckets: list[SourceDiscoveryEvidenceBucketHint] = Field(default_factory=list)


class SourceDiscoveryAssistantSourceSummary(BaseModel):
    title: str
    url: str | None = None
    source_type: str = "news"
    provider: str = ""
    published_at: str | None = None
    summary: str = ""
    citation: SourceDiscoveryAssistantCitation | None = None


class SourceDiscoveryAssistantBriefingLimit(BaseModel):
    max_queries: int
    max_results_per_query: int
    max_total_sources: int
    max_content_chars_per_source: int


class SourceDiscoveryAssistantTimelineItem(BaseModel):
    event_date: str | None = None
    reporting_date: str | None = None
    title: str
    summary: str
    citations: list[SourceDiscoveryAssistantCitation] = Field(default_factory=list)


class SourceDiscoveryAssistantEventStage(BaseModel):
    name: str
    summary: str
    confidence: Literal["low", "medium", "high"] = "low"
    citations: list[SourceDiscoveryAssistantCitation] = Field(default_factory=list)


class SourceDiscoveryAssistantSourceConflict(BaseModel):
    summary: str
    sides: list[str] = Field(default_factory=list)
    citations: list[SourceDiscoveryAssistantCitation] = Field(default_factory=list)


class SourceDiscoveryAssistantEvidenceGap(BaseModel):
    summary: str
    follow_up_searches: list[str] = Field(default_factory=list)


class SourceDiscoveryAssistantResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    mode: Literal["search_planning", "source_interpretation", "search_backed_briefing"]
    answer: str
    insufficient_evidence: bool = False
    planning_suggestions: list[SourceDiscoveryAssistantPlanningSuggestion] = Field(default_factory=list)
    recommended_settings: SourceDiscoveryAssistantRecommendedSettings | None = None
    source_summaries: list[SourceDiscoveryAssistantSourceSummary] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    controversy_focus: list[str] = Field(default_factory=list)
    briefing_limits: SourceDiscoveryAssistantBriefingLimit | None = None
    timeline: list[SourceDiscoveryAssistantTimelineItem] = Field(default_factory=list)
    event_stages: list[SourceDiscoveryAssistantEventStage] = Field(default_factory=list)
    citations: list[SourceDiscoveryAssistantCitation] = Field(default_factory=list)
    conflicts: list[SourceDiscoveryAssistantSourceConflict] = Field(default_factory=list)
    evidence_gaps: list[SourceDiscoveryAssistantEvidenceGap] = Field(default_factory=list)
    follow_up_searches: list[str] = Field(default_factory=list)
