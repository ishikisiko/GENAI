from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SourceTopicCreateRequest(BaseModel):
    name: str
    description: str = ""
    parent_topic_id: str | None = None
    topic_type: str = "collection"

    @field_validator("name")
    @classmethod
    def name_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is required")
        return value


class SourceTopicUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_topic_id: str | None = None
    topic_type: str | None = None
    status: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class SourceTopicResponse(BaseModel):
    id: str
    name: str
    description: str
    parent_topic_id: str | None
    topic_type: str
    status: str
    created_at: str
    updated_at: str


class SourceTopicListResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    topics: list[SourceTopicResponse]


class CaseSourceTopicCreateRequest(BaseModel):
    case_id: str
    topic_id: str
    relation_type: str = "primary"
    reason: str = ""


class CaseSourceTopicResponse(BaseModel):
    id: str
    case_id: str
    topic_id: str
    relation_type: str
    reason: str
    created_at: str
    updated_at: str


class SourceTopicAssignmentCreateRequest(BaseModel):
    global_source_id: str
    topic_id: str
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""
    assigned_by: str = "user"
    source_candidate_id: str | None = None
    discovery_job_id: str | None = None
    assignment_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceTopicAssignmentResponse(BaseModel):
    id: str
    global_source_id: str
    topic_id: str
    topic_name: str | None = None
    relevance_score: float
    reason: str
    assigned_by: str
    source_candidate_id: str | None
    discovery_job_id: str | None
    assignment_metadata: dict[str, Any]
    status: str
    created_at: str
    updated_at: str


class SourceTopicAssignmentListResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    assignments: list[SourceTopicAssignmentResponse]


class SourceRegistryAssignmentSummary(BaseModel):
    assignment_id: str
    topic_id: str
    topic_name: str
    relevance_score: float
    reason: str
    assigned_by: str
    status: str


class SourceRegistrySourceResponse(BaseModel):
    id: str
    title: str
    content: str
    doc_type: str
    canonical_url: str | None
    content_hash: str | None
    source_kind: str
    authority_level: str
    freshness_status: str
    source_status: str
    source_metadata: dict[str, Any]
    created_at: str
    updated_at: str
    topic_assignments: list[SourceRegistryAssignmentSummary] = Field(default_factory=list)
    usage_count: int = 0
    duplicate_candidate: bool = False
    already_in_case: bool = False


class SourceRegistryListResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    sources: list[SourceRegistrySourceResponse]
    topic_id: str | None = None
    smart_view: str | None = None


class SourceUsageCaseResponse(BaseModel):
    case_id: str
    case_title: str
    source_document_id: str
    source_origin: str
    source_topic_id: str | None
    created_at: str


class SourceUsageResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    global_source_id: str
    topic_assignments: list[SourceTopicAssignmentResponse]
    cases: list[SourceUsageCaseResponse]
    usage_count: int


class CaseSourceSelectionSection(BaseModel):
    key: str
    title: str
    description: str
    sources: list[SourceRegistrySourceResponse]


class CaseSourceSelectionResponse(BaseModel):
    outcome: Literal["completed"] = "completed"
    case_id: str
    case_topics: list[CaseSourceTopicResponse]
    sections: list[CaseSourceSelectionSection]


class AttachGlobalSourceRequest(BaseModel):
    case_id: str
    global_source_id: str
    topic_id: str | None = None
    assignment_id: str | None = None


class SourceDocumentSnapshotResponse(BaseModel):
    outcome: Literal["created"] = "created"
    id: str
    case_id: str
    global_source_id: str | None
    source_topic_id: str | None
    source_topic_assignment_id: str | None
    source_origin: str
    title: str
    content: str
    doc_type: str
    source_metadata: dict[str, Any]
    created_at: str
