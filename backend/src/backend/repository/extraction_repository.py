from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from backend.db import Database
from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    ClaimRecord,
    CrisisCaseRecord,
    EntityRecord,
    RelationRecord,
    SourceDocumentRecord,
)
from backend.services.extraction_contracts import (
    GRAPH_EXTRACTION_JOB_TYPE,
    GraphExtractionJobPayload,
    MergedGraphResult,
)


class ExtractionRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_case(self, case_id: str) -> CrisisCaseRecord | None:
        async with self._database.session() as session:
            return await session.get(CrisisCaseRecord, case_id)

    async def list_source_documents(self, case_id: str, document_ids: list[str] | None = None) -> list[SourceDocumentRecord]:
        async with self._database.session() as session:
            query = select(SourceDocumentRecord).where(SourceDocumentRecord.case_id == case_id)
            if document_ids:
                query = query.where(SourceDocumentRecord.id.in_(document_ids))
            rows = await session.execute(query.order_by(SourceDocumentRecord.created_at.asc()))
            documents = list(rows.scalars().all())
            if not document_ids:
                return documents
            order = {document_id: index for index, document_id in enumerate(document_ids)}
            return sorted(documents, key=lambda document: order.get(str(document.id), len(order)))

    async def create_submission(self, case_id: str, document_ids: list[str]) -> Job:
        now = datetime.now(timezone.utc)
        payload = GraphExtractionJobPayload(
            job_id="",
            case_id=case_id,
            document_ids=document_ids,
        ).model_dump(mode="json")
        payload.pop("job_id", None)

        async with self._database.session() as session:
            job = Job(
                job_type=GRAPH_EXTRACTION_JOB_TYPE,
                status=JobStatus.PENDING,
                payload=payload,
                max_attempts=1,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            await session.flush()
            await session.refresh(job)
            return job

    async def count_graph_records(self, case_id: str) -> dict[str, int]:
        async with self._database.session() as session:
            entity_count = await session.execute(select(func.count(EntityRecord.id)).where(EntityRecord.case_id == case_id))
            relation_count = await session.execute(
                select(func.count(RelationRecord.id)).where(RelationRecord.case_id == case_id)
            )
            claim_count = await session.execute(select(func.count(ClaimRecord.id)).where(ClaimRecord.case_id == case_id))
            return {
                "entities_count": int(entity_count.scalar_one() or 0),
                "relations_count": int(relation_count.scalar_one() or 0),
                "claims_count": int(claim_count.scalar_one() or 0),
            }

    async def replace_case_graph(self, case_id: str, graph: MergedGraphResult) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            await session.execute(delete(RelationRecord).where(RelationRecord.case_id == case_id))
            await session.execute(delete(ClaimRecord).where(ClaimRecord.case_id == case_id))
            await session.execute(delete(EntityRecord).where(EntityRecord.case_id == case_id))

            entity_rows = [
                EntityRecord(
                    case_id=case_id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    created_at=now,
                )
                for entity in graph.entities
            ]
            session.add_all(entity_rows)
            await session.flush()

            entity_map = {self.normalize_name(str(entity.name)): str(entity.id) for entity in entity_rows}

            relation_rows = [
                RelationRecord(
                    case_id=case_id,
                    source_entity_id=entity_map.get(self.normalize_name(relation.source_entity_name)),
                    target_entity_id=entity_map.get(self.normalize_name(relation.target_entity_name)),
                    relation_type=relation.relation_type,
                    description=relation.description,
                    created_at=now,
                )
                for relation in graph.relations
                if entity_map.get(self.normalize_name(relation.source_entity_name))
                and entity_map.get(self.normalize_name(relation.target_entity_name))
            ]
            session.add_all(relation_rows)

            claim_rows = [
                ClaimRecord(
                    case_id=case_id,
                    content=claim.content,
                    claim_type=claim.claim_type,
                    credibility=claim.credibility,
                    source_doc_id=claim.source_doc_id,
                    created_at=now,
                )
                for claim in graph.claims
            ]
            session.add_all(claim_rows)

            crisis_case = await session.get(CrisisCaseRecord, case_id)
            if crisis_case is not None:
                crisis_case.status = "grounded"
                crisis_case.updated_at = now

            return {
                "entities_count": len(entity_rows),
                "relations_count": len(relation_rows),
                "claims_count": len(claim_rows),
            }

    @staticmethod
    def normalize_name(value: str) -> str:
        return " ".join(value.strip().split()).lower()
