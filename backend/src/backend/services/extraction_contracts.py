from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.services.contracts import AsyncStatusResponse, AsyncSubmissionResponse


GRAPH_EXTRACTION_JOB_TYPE = "graph.extract"


class GraphExtractionSubmissionRequest(BaseModel):
    case_id: str


class GraphExtractionJobPayload(BaseModel):
    job_id: str
    case_id: str
    document_ids: list[str] = Field(default_factory=list)

    @classmethod
    def from_job_payload(cls, job_id: str, payload: dict[str, Any]) -> "GraphExtractionJobPayload":
        return cls.model_validate({"job_id": job_id, **payload})


class GraphExtractionSubmissionResponse(AsyncSubmissionResponse):
    case_id: str
    job_type: str = "graph.extract"
    status_path: str = "/api/graph-extractions/{job_id}"
    document_count: int


class GraphExtractionResultSummary(BaseModel):
    case_id: str
    document_count: int
    processed_documents: int
    failed_documents: int
    entities_count: int
    relations_count: int
    claims_count: int


class GraphExtractionStatusResponse(AsyncStatusResponse):
    job_id: str
    case_id: str
    document_count: int
    processed_documents: int
    failed_documents: int
    entities_count: int
    relations_count: int
    claims_count: int
    last_error: str | None = None
    last_error_code: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    should_poll: bool


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    entity_type: str = "organization"
    description: str = ""


class ExtractedRelation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_entity_name: str = ""
    target_entity_name: str = ""
    relation_type: str = ""
    description: str = ""


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str = ""
    claim_type: str = "fact"
    credibility: str = "medium"
    source_doc_id: str | None = None


class ExtractedDocumentGraph(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)


class DocumentGraphFragment(BaseModel):
    source_doc_id: str
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)


class MergedGraphResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)
