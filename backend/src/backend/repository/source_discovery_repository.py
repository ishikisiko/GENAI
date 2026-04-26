from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select

from backend.db import Database
from backend.domain.models import Job, JobStatus
from backend.domain.simulation_records import (
    CandidateReviewStatus,
    CrisisCaseRecord,
    EvidencePackRecord,
    EvidencePackSourceRecord,
    EvidencePackStatus,
    SourceCandidateRecord,
    SourceDiscoveryJobRecord,
    SourceDiscoveryStatus,
    SourceDocumentRecord,
)
from backend.services.source_discovery_contracts import (
    SOURCE_DISCOVERY_JOB_TYPE,
    EvidencePackCreateRequest,
    SourceCandidateWrite,
    SourceDiscoveryJobCreateRequest,
)
from backend.shared.errors import ApplicationError, ErrorCode


class SourceDiscoveryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_case(self, case_id: str) -> CrisisCaseRecord | None:
        async with self._database.session() as session:
            return await session.get(CrisisCaseRecord, case_id)

    async def create_discovery_submission(
        self,
        request: SourceDiscoveryJobCreateRequest,
        max_attempts: int = 1,
    ) -> tuple[SourceDiscoveryJobRecord, Job]:
        now = datetime.now(timezone.utc)
        discovery_id = str(uuid4())
        job_id = str(uuid4())
        payload = {
            "source_discovery_job_id": discovery_id,
            "case_id": request.case_id,
            "topic": request.topic,
            "description": request.description,
            "region": request.region,
            "language": request.language,
            "time_range": request.time_range,
            "source_types": request.source_types,
            "max_sources": request.max_sources,
        }

        async with self._database.session() as session:
            crisis_case = await session.get(CrisisCaseRecord, request.case_id)
            if crisis_case is None:
                raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

            job = Job(
                id=job_id,
                job_type=SOURCE_DISCOVERY_JOB_TYPE,
                status=JobStatus.PENDING,
                payload=payload,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            discovery_job = SourceDiscoveryJobRecord(
                id=discovery_id,
                case_id=request.case_id,
                job_id=job_id,
                status=SourceDiscoveryStatus.PENDING,
                topic=request.topic,
                description=request.description,
                region=request.region,
                language=request.language,
                time_range=request.time_range,
                source_types=request.source_types,
                max_sources=request.max_sources,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            session.add(discovery_job)
            await session.flush()
            await session.refresh(job)
            await session.refresh(discovery_job)
            return discovery_job, job

    async def get_discovery_job(self, discovery_job_id: str) -> tuple[SourceDiscoveryJobRecord, Job]:
        async with self._database.session() as session:
            discovery_job = await session.get(SourceDiscoveryJobRecord, discovery_job_id)
            if discovery_job is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source discovery job not found: {discovery_job_id}",
                    status_code=404,
                )
            job = await session.get(Job, discovery_job.job_id)
            if job is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Backing job not found: {discovery_job.job_id}",
                    status_code=404,
                )
            return discovery_job, job

    async def get_discovery_job_by_job_id(self, job_id: str) -> SourceDiscoveryJobRecord:
        async with self._database.session() as session:
            rows = await session.execute(select(SourceDiscoveryJobRecord).where(SourceDiscoveryJobRecord.job_id == job_id))
            discovery_job = rows.scalar_one_or_none()
            if discovery_job is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source discovery job not found for job: {job_id}",
                    status_code=404,
                )
            return discovery_job

    async def mark_discovery_running(self, discovery_job_id: str, query_plan: list[str]) -> SourceDiscoveryJobRecord:
        async with self._database.session() as session:
            discovery_job = await self._get_discovery_job_with_lock(session, discovery_job_id)
            now = datetime.now(timezone.utc)
            discovery_job.status = SourceDiscoveryStatus.RUNNING
            discovery_job.query_plan = query_plan
            discovery_job.last_error = None
            discovery_job.last_error_code = None
            discovery_job.updated_at = now
            return discovery_job

    async def write_candidates(
        self,
        discovery_job_id: str,
        case_id: str,
        candidates: list[SourceCandidateWrite],
    ) -> list[SourceCandidateRecord]:
        now = datetime.now(timezone.utc)
        rows: list[SourceCandidateRecord] = []
        async with self._database.session() as session:
            discovery_job = await self._get_discovery_job_with_lock(session, discovery_job_id)
            if str(discovery_job.case_id) != case_id:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Discovery job does not belong to the requested case.",
                    status_code=400,
                )
            for candidate in candidates:
                scores = candidate.scores
                total_score = candidate.total_score if candidate.total_score is not None else scores.total()
                rows.append(
                    SourceCandidateRecord(
                        discovery_job_id=discovery_job_id,
                        case_id=case_id,
                        title=candidate.title,
                        url=candidate.url,
                        canonical_url=candidate.canonical_url,
                        source_type=candidate.source_type,
                        language=candidate.language,
                        region=candidate.region,
                        published_at=candidate.published_at,
                        provider=candidate.provider,
                        provider_metadata=candidate.provider_metadata,
                        content=candidate.content,
                        excerpt=candidate.excerpt,
                        content_hash=candidate.content_hash,
                        classification=candidate.classification,
                        claim_previews=candidate.claim_previews,
                        stakeholder_previews=candidate.stakeholder_previews,
                        relevance=scores.relevance,
                        authority=scores.authority,
                        freshness=scores.freshness,
                        claim_richness=scores.claim_richness,
                        diversity=scores.diversity,
                        grounding_value=scores.grounding_value,
                        total_score=total_score,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if rows:
                session.add_all(rows)
                await session.flush()
                for row in rows:
                    await session.refresh(row)
            await self._refresh_discovery_counts(session, discovery_job_id)
            return rows

    async def mark_discovery_completed(self, discovery_job_id: str) -> SourceDiscoveryJobRecord:
        async with self._database.session() as session:
            discovery_job = await self._get_discovery_job_with_lock(session, discovery_job_id)
            now = datetime.now(timezone.utc)
            await self._refresh_discovery_counts(session, discovery_job_id)
            discovery_job.status = SourceDiscoveryStatus.COMPLETED
            discovery_job.updated_at = now
            discovery_job.completed_at = now
            discovery_job.last_error = None
            discovery_job.last_error_code = None
            return discovery_job

    async def mark_discovery_failed(self, discovery_job_id: str, code: str, message: str) -> SourceDiscoveryJobRecord:
        async with self._database.session() as session:
            discovery_job = await self._get_discovery_job_with_lock(session, discovery_job_id)
            now = datetime.now(timezone.utc)
            discovery_job.status = SourceDiscoveryStatus.FAILED
            discovery_job.updated_at = now
            discovery_job.completed_at = now
            discovery_job.last_error = message
            discovery_job.last_error_code = code
            return discovery_job

    async def list_candidates(
        self,
        case_id: str | None = None,
        discovery_job_id: str | None = None,
        review_status: str | None = None,
    ) -> list[SourceCandidateRecord]:
        async with self._database.session() as session:
            query = select(SourceCandidateRecord)
            if case_id is not None:
                query = query.where(SourceCandidateRecord.case_id == case_id)
            if discovery_job_id is not None:
                query = query.where(SourceCandidateRecord.discovery_job_id == discovery_job_id)
            if review_status is not None:
                query = query.where(SourceCandidateRecord.review_status == review_status)
            query = query.order_by(SourceCandidateRecord.total_score.desc(), SourceCandidateRecord.created_at.desc())
            rows = await session.execute(query)
            return list(rows.scalars().all())

    async def update_candidate_review(self, source_id: str, review_status: str) -> SourceCandidateRecord:
        async with self._database.session() as session:
            candidate = await session.get(SourceCandidateRecord, source_id)
            if candidate is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source candidate not found: {source_id}",
                    status_code=404,
                )
            candidate.review_status = CandidateReviewStatus(review_status)
            candidate.updated_at = datetime.now(timezone.utc)
            await session.flush()
            await self._refresh_discovery_counts(session, str(candidate.discovery_job_id))
            await session.refresh(candidate)
            return candidate

    async def create_evidence_pack(self, request: EvidencePackCreateRequest) -> EvidencePackRecord:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            crisis_case = await session.get(CrisisCaseRecord, request.case_id)
            if crisis_case is None:
                raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

            candidate_query = select(SourceCandidateRecord).where(
                SourceCandidateRecord.case_id == request.case_id,
                SourceCandidateRecord.review_status == CandidateReviewStatus.ACCEPTED,
            )
            if request.discovery_job_id:
                discovery_job = await session.get(SourceDiscoveryJobRecord, request.discovery_job_id)
                if discovery_job is None or str(discovery_job.case_id) != request.case_id:
                    raise ApplicationError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Discovery job does not belong to the requested case.",
                        status_code=400,
                    )
                candidate_query = candidate_query.where(SourceCandidateRecord.discovery_job_id == request.discovery_job_id)
            if request.candidate_ids:
                candidate_query = candidate_query.where(SourceCandidateRecord.id.in_(request.candidate_ids))
            rows = await session.execute(
                candidate_query.order_by(SourceCandidateRecord.total_score.desc(), SourceCandidateRecord.created_at.desc())
            )
            candidates = list(rows.scalars().all())
            if not candidates:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Accept at least one source candidate before creating an evidence pack.",
                    status_code=400,
                )
            if request.candidate_ids and len({str(candidate.id) for candidate in candidates}) != len(set(request.candidate_ids)):
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="All selected candidates must belong to the case and be accepted.",
                    status_code=400,
                )

            pack = EvidencePackRecord(
                case_id=request.case_id,
                discovery_job_id=request.discovery_job_id or str(candidates[0].discovery_job_id),
                title=request.title or f"Evidence pack: {candidates[0].title}",
                status=EvidencePackStatus.DRAFT,
                source_count=len(candidates),
                created_at=now,
                updated_at=now,
            )
            session.add(pack)
            await session.flush()

            pack_sources = [
                self._build_pack_source(str(pack.id), index, candidate, now)
                for index, candidate in enumerate(candidates)
            ]
            session.add_all(pack_sources)
            await session.flush()
            await session.refresh(pack)
            return pack

    async def get_evidence_pack(self, evidence_pack_id: str) -> tuple[EvidencePackRecord, list[EvidencePackSourceRecord]]:
        async with self._database.session() as session:
            pack = await session.get(EvidencePackRecord, evidence_pack_id)
            if pack is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Evidence pack not found: {evidence_pack_id}",
                    status_code=404,
                )
            rows = await session.execute(
                select(EvidencePackSourceRecord)
                .where(EvidencePackSourceRecord.evidence_pack_id == evidence_pack_id)
                .order_by(EvidencePackSourceRecord.sort_order.asc(), EvidencePackSourceRecord.created_at.asc())
            )
            return pack, list(rows.scalars().all())

    async def materialize_evidence_pack_sources(self, evidence_pack_id: str) -> list[SourceDocumentRecord]:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            pack = await session.get(EvidencePackRecord, evidence_pack_id)
            if pack is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Evidence pack not found: {evidence_pack_id}",
                    status_code=404,
                )
            rows = await session.execute(
                select(EvidencePackSourceRecord)
                .where(EvidencePackSourceRecord.evidence_pack_id == evidence_pack_id)
                .order_by(EvidencePackSourceRecord.sort_order.asc())
                .with_for_update()
            )
            pack_sources = list(rows.scalars().all())
            if not pack_sources:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Evidence pack has no sources to ground.",
                    status_code=400,
                )

            documents: list[SourceDocumentRecord] = []
            for pack_source in pack_sources:
                if pack_source.source_document_id:
                    document = await session.get(SourceDocumentRecord, pack_source.source_document_id)
                    if document is not None:
                        documents.append(document)
                        continue

                document = SourceDocumentRecord(
                    case_id=str(pack.case_id),
                    evidence_pack_id=evidence_pack_id,
                    evidence_pack_source_id=str(pack_source.id),
                    source_origin="evidence_pack",
                    title=pack_source.title,
                    content=pack_source.content or pack_source.excerpt,
                    doc_type=self._doc_type_for_source_type(pack_source.source_type),
                    source_metadata={
                        "evidence_pack_id": evidence_pack_id,
                        "evidence_pack_source_id": str(pack_source.id),
                        "candidate_id": str(pack_source.candidate_id),
                        "url": pack_source.url,
                        "provider": pack_source.provider,
                        "published_at": pack_source.published_at.isoformat() if pack_source.published_at else None,
                        "score_dimensions": pack_source.score_dimensions,
                        "total_score": pack_source.total_score,
                    },
                    created_at=now,
                )
                session.add(document)
                await session.flush()
                pack_source.source_document_id = str(document.id)
                documents.append(document)

            pack.status = EvidencePackStatus.GROUNDING_STARTED
            pack.grounded_at = now
            pack.updated_at = now
            await session.flush()
            for document in documents:
                await session.refresh(document)
            return documents

    async def _get_discovery_job_with_lock(self, session, discovery_job_id: str) -> SourceDiscoveryJobRecord:
        row = await session.get(SourceDiscoveryJobRecord, discovery_job_id, with_for_update=True)
        if row is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message=f"Source discovery job not found: {discovery_job_id}",
                status_code=404,
            )
        return row

    async def _refresh_discovery_counts(self, session, discovery_job_id: str) -> None:
        discovery_job = await session.get(SourceDiscoveryJobRecord, discovery_job_id)
        if discovery_job is None:
            return
        total = await session.execute(
            select(func.count(SourceCandidateRecord.id)).where(
                SourceCandidateRecord.discovery_job_id == discovery_job_id
            )
        )
        accepted = await session.execute(
            select(func.count(SourceCandidateRecord.id)).where(
                SourceCandidateRecord.discovery_job_id == discovery_job_id,
                SourceCandidateRecord.review_status == CandidateReviewStatus.ACCEPTED,
            )
        )
        rejected = await session.execute(
            select(func.count(SourceCandidateRecord.id)).where(
                SourceCandidateRecord.discovery_job_id == discovery_job_id,
                SourceCandidateRecord.review_status == CandidateReviewStatus.REJECTED,
            )
        )
        discovery_job.candidate_count = int(total.scalar_one() or 0)
        discovery_job.accepted_count = int(accepted.scalar_one() or 0)
        discovery_job.rejected_count = int(rejected.scalar_one() or 0)
        discovery_job.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _build_pack_source(
        evidence_pack_id: str,
        index: int,
        candidate: SourceCandidateRecord,
        now: datetime,
    ) -> EvidencePackSourceRecord:
        return EvidencePackSourceRecord(
            evidence_pack_id=evidence_pack_id,
            candidate_id=str(candidate.id),
            sort_order=index,
            title=candidate.title,
            url=candidate.url,
            source_type=candidate.source_type,
            language=candidate.language,
            region=candidate.region,
            published_at=candidate.published_at,
            provider=candidate.provider,
            provider_metadata=candidate.provider_metadata,
            content=candidate.content,
            excerpt=candidate.excerpt,
            score_dimensions={
                "relevance": candidate.relevance,
                "authority": candidate.authority,
                "freshness": candidate.freshness,
                "claim_richness": candidate.claim_richness,
                "diversity": candidate.diversity,
                "grounding_value": candidate.grounding_value,
            },
            total_score=candidate.total_score,
            claim_previews=candidate.claim_previews,
            stakeholder_previews=candidate.stakeholder_previews,
            created_at=now,
        )

    @staticmethod
    def _doc_type_for_source_type(source_type: str) -> str:
        normalized = source_type.lower()
        if normalized in {"official", "statement", "regulator", "company"}:
            return "statement"
        if normalized in {"social", "complaint", "community"}:
            return "complaint"
        return "news"
