from __future__ import annotations

from datetime import timezone

from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import SourceDocumentRecord
from backend.repository.extraction_repository import ExtractionRepository
from backend.repository.job_repository import JobRepository
from backend.services.extraction_contracts import (
    GRAPH_EXTRACTION_JOB_TYPE,
    DocumentGraphFragment,
    ExtractedClaim,
    ExtractedDocumentGraph,
    ExtractedEntity,
    ExtractedRelation,
    GraphExtractionJobPayload,
    GraphExtractionResultSummary,
    GraphExtractionStatusResponse,
    GraphExtractionSubmissionRequest,
    GraphExtractionSubmissionResponse,
    MergedGraphResult,
)
from backend.services.llm_client import LlmJsonClient
from backend.shared.errors import ApplicationError, ErrorCode
from backend.shared.logging import get_logger


def normalize_name(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)


def normalize_document_graph(source_doc_id: str, raw_graph: ExtractedDocumentGraph) -> DocumentGraphFragment:
    entity_map: dict[str, ExtractedEntity] = {}
    relation_map: dict[str, ExtractedRelation] = {}
    claim_map: dict[str, ExtractedClaim] = {}

    for entity in raw_graph.entities:
        name = entity.name.strip()
        if not name:
            continue
        key = normalize_name(name)
        if key not in entity_map:
            entity_map[key] = ExtractedEntity(
                name=name,
                entity_type=(entity.entity_type or "organization").strip() or "organization",
                description=entity.description.strip(),
            )

    for relation in raw_graph.relations:
        source_entity_name = relation.source_entity_name.strip()
        target_entity_name = relation.target_entity_name.strip()
        relation_type = relation.relation_type.strip()
        if not source_entity_name or not target_entity_name or not relation_type:
            continue
        key = "|".join(
            [
                normalize_name(source_entity_name),
                relation_type.lower(),
                normalize_name(target_entity_name),
            ]
        )
        if key not in relation_map:
            relation_map[key] = ExtractedRelation(
                source_entity_name=source_entity_name,
                target_entity_name=target_entity_name,
                relation_type=relation_type,
                description=relation.description.strip(),
            )

    for claim in raw_graph.claims:
        content = claim.content.strip()
        if not content:
            continue
        claim_type = (claim.claim_type or "fact").strip() or "fact"
        credibility = (claim.credibility or "medium").strip() or "medium"
        key = f"{claim_type.lower()}|{normalize_text(content)}"
        if key not in claim_map:
            claim_map[key] = ExtractedClaim(
                content=content,
                claim_type=claim_type,
                credibility=credibility,
                source_doc_id=source_doc_id,
            )

    return DocumentGraphFragment(
        source_doc_id=source_doc_id,
        entities=list(entity_map.values()),
        relations=list(relation_map.values()),
        claims=list(claim_map.values()),
    )


def merge_document_graphs(partials: list[DocumentGraphFragment]) -> MergedGraphResult:
    entity_map: dict[str, ExtractedEntity] = {}
    relation_map: dict[str, ExtractedRelation] = {}
    claim_map: dict[str, ExtractedClaim] = {}

    for partial in partials:
        for entity in partial.entities:
            key = normalize_name(entity.name)
            if key not in entity_map:
                entity_map[key] = entity

        for relation in partial.relations:
            key = "|".join(
                [
                    normalize_name(relation.source_entity_name),
                    relation.relation_type.strip().lower(),
                    normalize_name(relation.target_entity_name),
                ]
            )
            if key not in relation_map:
                relation_map[key] = relation

        for claim in partial.claims:
            key = f"{claim.claim_type.strip().lower()}|{normalize_text(claim.content)}"
            if key not in claim_map:
                claim_map[key] = claim

    return MergedGraphResult(
        entities=list(entity_map.values()),
        relations=list(relation_map.values()),
        claims=list(claim_map.values()),
    )


class ExtractionService:
    def __init__(
        self,
        extraction_repository: ExtractionRepository,
        job_repository: JobRepository,
        llm_client: LlmJsonClient,
    ) -> None:
        self._extraction_repository = extraction_repository
        self._job_repository = job_repository
        self._llm_client = llm_client
        self._logger = get_logger("backend.graph_extraction")

    async def submit(self, request: GraphExtractionSubmissionRequest) -> GraphExtractionSubmissionResponse:
        crisis_case = await self._extraction_repository.get_case(request.case_id)
        if crisis_case is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message="Case not found",
                status_code=404,
            )

        documents = await self._extraction_repository.list_source_documents(request.case_id)
        if not documents:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Add at least one source document before extracting the graph.",
                status_code=400,
            )

        job = await self._extraction_repository.create_submission(
            case_id=request.case_id,
            document_ids=[str(document.id) for document in documents],
        )
        self._logger.info(
            "graph_extraction_submitted",
            extra={"case_id": request.case_id, "job_id": str(job.id), "document_count": len(documents)},
        )
        return GraphExtractionSubmissionResponse(
            case_id=request.case_id,
            job_id=str(job.id),
            job_status=_status_value(job.status),
            job_status_path=f"/api/jobs/{job.id}",
            status_path=f"/api/graph-extractions/{job.id}",
            document_count=len(documents),
        )

    async def get_status(self, job_id: str) -> GraphExtractionStatusResponse:
        job = await self._job_repository.get_job(job_id)
        if job.job_type != GRAPH_EXTRACTION_JOB_TYPE:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unsupported job type: {job.job_type}",
                status_code=400,
            )

        payload = GraphExtractionJobPayload.from_job_payload(str(job.id), dict(job.payload))
        counts = await self._extraction_repository.count_graph_records(payload.case_id)
        latest_attempt = await self._job_repository.get_latest_attempt(job_id)
        result_summary = self._extract_result_summary(payload.case_id, len(payload.document_ids), latest_attempt)

        return GraphExtractionStatusResponse(
            job_id=str(job.id),
            case_id=payload.case_id,
            job_type=job.job_type,
            status=_status_value(job.status),
            job_status_path=f"/api/jobs/{job.id}",
            status_path=f"/api/graph-extractions/{job.id}",
            document_count=result_summary.document_count,
            processed_documents=result_summary.processed_documents,
            failed_documents=result_summary.failed_documents,
            entities_count=counts["entities_count"],
            relations_count=counts["relations_count"],
            claims_count=counts["claims_count"],
            last_error=job.last_error,
            last_error_code=job.last_error_code,
            created_at=job.created_at.astimezone(timezone.utc).isoformat() if job.created_at else None,
            updated_at=job.updated_at.astimezone(timezone.utc).isoformat() if job.updated_at else None,
            should_poll=_status_value(job.status) in {JobStatus.PENDING.value, JobStatus.RUNNING.value},
        )

    async def handle_job(self, job: Job) -> dict[str, object]:
        if job.job_type != GRAPH_EXTRACTION_JOB_TYPE:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unsupported job type: {job.job_type}",
                status_code=400,
            )

        payload = GraphExtractionJobPayload.from_job_payload(str(job.id), dict(job.payload))
        return await self._execute(payload)

    async def _execute(self, payload: GraphExtractionJobPayload) -> dict[str, object]:
        documents = await self._extraction_repository.list_source_documents(payload.case_id, payload.document_ids)
        if not documents:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No source documents were available for this extraction job.",
                status_code=400,
            )

        missing_documents = max(len(payload.document_ids) - len(documents), 0)
        partials: list[DocumentGraphFragment] = []
        failed_documents = missing_documents

        await self._job_repository.touch_heartbeat(payload.job_id)
        for document in documents:
            await self._job_repository.touch_heartbeat(payload.job_id)
            partial = await self._extract_document_graph(document)
            if partial is None:
                failed_documents += 1
                continue
            partials.append(partial)

        if not partials:
            raise ApplicationError(
                code=ErrorCode.EXTERNAL_DEPENDENCY_ERROR,
                message="All document extraction attempts failed.",
                status_code=503,
                details={"dependency": "llm"},
            )

        merged = merge_document_graphs(partials)
        counts = await self._extraction_repository.replace_case_graph(payload.case_id, merged)
        await self._job_repository.touch_heartbeat(payload.job_id)

        return GraphExtractionResultSummary(
            case_id=payload.case_id,
            document_count=len(payload.document_ids),
            processed_documents=len(partials),
            failed_documents=failed_documents,
            entities_count=counts["entities_count"],
            relations_count=counts["relations_count"],
            claims_count=counts["claims_count"],
        ).model_dump(mode="json")

    async def _extract_document_graph(self, document: SourceDocumentRecord) -> DocumentGraphFragment | None:
        prompt = f"""You are a knowledge graph extraction expert. Analyze the following single crisis-related document and extract structured information.

DOCUMENT:
[{document.doc_type.upper()}] {document.title}
{document.content}

Extract and return a JSON object with:
1. "entities": array of {{name, entity_type (person/organization/product/event/location), description}}
2. "relations": array of {{source_entity_name, target_entity_name, relation_type, description}}
3. "claims": array of {{content, claim_type (allegation/fact/statement/event), credibility (high/medium/low)}}

Rules:
- Extract 2-8 entities, up to 5 relations, and 2-8 claims from this document only
- Focus on crisis-relevant entities, events, allegations, and official statements
- Do not invent facts that are not grounded in this document
- Use concise but specific descriptions

Return ONLY valid JSON, no markdown or explanation."""

        try:
            payload = await self._llm_client.chat_json(prompt=prompt, temperature=0.2, max_retries=3)
            return normalize_document_graph(
                source_doc_id=str(document.id),
                raw_graph=ExtractedDocumentGraph.model_validate(payload),
            )
        except Exception:
            return None

    @staticmethod
    def _extract_result_summary(
        case_id: str,
        document_count: int,
        latest_attempt,
    ) -> GraphExtractionResultSummary:
        if latest_attempt is not None and isinstance(latest_attempt.payload_snapshot, dict):
            result_payload = latest_attempt.payload_snapshot.get("result")
            if isinstance(result_payload, dict):
                return GraphExtractionResultSummary.model_validate(result_payload)

        return GraphExtractionResultSummary(
            case_id=case_id,
            document_count=document_count,
            processed_documents=0,
            failed_documents=0,
            entities_count=0,
            relations_count=0,
            claims_count=0,
        )
