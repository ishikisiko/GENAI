from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse, urlunparse

from sqlalchemy import func, or_, select

from backend.db import Database
from backend.domain.simulation_records import (
    CandidateReviewStatus,
    CaseSourceTopicRecord,
    CrisisCaseRecord,
    GlobalSourceDocumentRecord,
    SourceCandidateRecord,
    SourceDocumentRecord,
    SourceTopicAssignmentRecord,
    SourceTopicRecord,
)
from backend.services.source_library_contracts import (
    AttachGlobalSourceRequest,
    CaseSourceTopicCreateRequest,
    SourceTopicAssignmentCreateRequest,
    SourceTopicCreateRequest,
    SourceTopicUpdateRequest,
)
from backend.services.source_discovery_contracts import SourceCandidateLibrarySaveRequest
from backend.shared.errors import ApplicationError, ErrorCode


@dataclass(frozen=True)
class SourceRegistryEntry:
    source: GlobalSourceDocumentRecord
    assignments: list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]]
    usage_count: int
    duplicate_candidate: bool
    already_in_case: bool = False


@dataclass(frozen=True)
class SourceUsageEntry:
    document: SourceDocumentRecord
    crisis_case: CrisisCaseRecord


@dataclass(frozen=True)
class CandidateLibrarySaveResult:
    source: GlobalSourceDocumentRecord
    assignment: SourceTopicAssignmentRecord | None
    duplicate_reused: bool


class SourceLibraryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create_topic(self, request: SourceTopicCreateRequest) -> SourceTopicRecord:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            if request.parent_topic_id:
                await self._require_topic(session, request.parent_topic_id)
            topic = SourceTopicRecord(
                name=request.name,
                description=request.description,
                parent_topic_id=request.parent_topic_id,
                topic_type=request.topic_type,
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(topic)
            await session.flush()
            await session.refresh(topic)
            return topic

    async def update_topic(self, topic_id: str, request: SourceTopicUpdateRequest) -> SourceTopicRecord:
        async with self._database.session() as session:
            topic = await self._require_topic(session, topic_id)
            if request.parent_topic_id and request.parent_topic_id == topic_id:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="A source topic cannot be its own parent.",
                    status_code=400,
                )
            if request.parent_topic_id is not None:
                await self._require_topic(session, request.parent_topic_id)
                topic.parent_topic_id = request.parent_topic_id
            if request.name is not None:
                topic.name = request.name
            if request.description is not None:
                topic.description = request.description
            if request.topic_type is not None:
                topic.topic_type = request.topic_type
            if request.status is not None:
                topic.status = request.status
            topic.updated_at = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(topic)
            return topic

    async def get_topic(self, topic_id: str) -> SourceTopicRecord:
        async with self._database.session() as session:
            return await self._require_topic(session, topic_id)

    async def list_topics(self) -> list[SourceTopicRecord]:
        async with self._database.session() as session:
            rows = await session.execute(
                select(SourceTopicRecord).order_by(SourceTopicRecord.name.asc(), SourceTopicRecord.created_at.desc())
            )
            return list(rows.scalars().all())

    async def create_case_topic(self, request: CaseSourceTopicCreateRequest) -> CaseSourceTopicRecord:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            crisis_case = await session.get(CrisisCaseRecord, request.case_id)
            if crisis_case is None:
                raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)
            await self._require_topic(session, request.topic_id)
            rows = await session.execute(
                select(CaseSourceTopicRecord).where(
                    CaseSourceTopicRecord.case_id == request.case_id,
                    CaseSourceTopicRecord.topic_id == request.topic_id,
                )
            )
            existing = rows.scalar_one_or_none()
            if existing is not None:
                existing.relation_type = request.relation_type
                existing.reason = request.reason
                existing.updated_at = now
                await session.flush()
                await session.refresh(existing)
                return existing

            row = CaseSourceTopicRecord(
                case_id=request.case_id,
                topic_id=request.topic_id,
                relation_type=request.relation_type,
                reason=request.reason,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return row

    async def list_case_topics(self, case_id: str) -> list[tuple[CaseSourceTopicRecord, SourceTopicRecord]]:
        async with self._database.session() as session:
            rows = await session.execute(
                select(CaseSourceTopicRecord, SourceTopicRecord)
                .join(SourceTopicRecord, SourceTopicRecord.id == CaseSourceTopicRecord.topic_id)
                .where(CaseSourceTopicRecord.case_id == case_id)
                .order_by(CaseSourceTopicRecord.relation_type.asc(), SourceTopicRecord.name.asc())
            )
            return [(case_topic, topic) for case_topic, topic in rows.all()]

    async def create_assignment(
        self,
        request: SourceTopicAssignmentCreateRequest,
    ) -> SourceTopicAssignmentRecord:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            await self._require_global_source(session, request.global_source_id)
            await self._require_topic(session, request.topic_id)
            rows = await session.execute(
                select(SourceTopicAssignmentRecord).where(
                    SourceTopicAssignmentRecord.global_source_id == request.global_source_id,
                    SourceTopicAssignmentRecord.topic_id == request.topic_id,
                )
            )
            assignment = rows.scalar_one_or_none()
            if assignment is None:
                assignment = SourceTopicAssignmentRecord(
                    global_source_id=request.global_source_id,
                    topic_id=request.topic_id,
                    created_at=now,
                )
                session.add(assignment)
            assignment.relevance_score = request.relevance_score
            assignment.reason = request.reason
            assignment.assigned_by = request.assigned_by
            assignment.source_candidate_id = request.source_candidate_id
            assignment.discovery_job_id = request.discovery_job_id
            assignment.assignment_metadata = request.assignment_metadata
            assignment.status = "active"
            assignment.updated_at = now
            await session.flush()
            await session.refresh(assignment)
            return assignment

    async def remove_assignment(self, assignment_id: str) -> SourceTopicAssignmentRecord:
        async with self._database.session() as session:
            assignment = await session.get(SourceTopicAssignmentRecord, assignment_id)
            if assignment is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source topic assignment not found: {assignment_id}",
                    status_code=404,
                )
            assignment.status = "inactive"
            assignment.updated_at = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(assignment)
            return assignment

    async def list_registry(
        self,
        topic_id: str | None = None,
        smart_view: str | None = None,
        query: str | None = None,
        source_kind: str | None = None,
        authority_level: str | None = None,
        freshness_status: str | None = None,
        source_status: str | None = None,
        case_id: str | None = None,
        limit: int = 100,
    ) -> list[SourceRegistryEntry]:
        async with self._database.session() as session:
            source_query = select(GlobalSourceDocumentRecord)
            if topic_id:
                await self._require_topic(session, topic_id)
                source_query = (
                    source_query.join(
                        SourceTopicAssignmentRecord,
                        SourceTopicAssignmentRecord.global_source_id == GlobalSourceDocumentRecord.id,
                    )
                    .where(SourceTopicAssignmentRecord.topic_id == topic_id)
                    .where(SourceTopicAssignmentRecord.status == "active")
                )
            if query:
                pattern = f"%{query.strip()}%"
                source_query = source_query.where(
                    or_(
                        GlobalSourceDocumentRecord.title.ilike(pattern),
                        GlobalSourceDocumentRecord.content.ilike(pattern),
                        GlobalSourceDocumentRecord.source_kind.ilike(pattern),
                    )
                )
            if source_kind:
                source_query = source_query.where(GlobalSourceDocumentRecord.source_kind == source_kind)
            if authority_level:
                source_query = source_query.where(GlobalSourceDocumentRecord.authority_level == authority_level)
            if freshness_status:
                source_query = source_query.where(GlobalSourceDocumentRecord.freshness_status == freshness_status)
            if source_status:
                source_query = source_query.where(GlobalSourceDocumentRecord.source_status == source_status)
            if smart_view == "high_authority":
                source_query = source_query.where(GlobalSourceDocumentRecord.authority_level == "high")
            if smart_view == "stale":
                source_query = source_query.where(GlobalSourceDocumentRecord.freshness_status == "stale")
            if smart_view == "unassigned":
                assigned = (
                    select(SourceTopicAssignmentRecord.global_source_id)
                    .where(SourceTopicAssignmentRecord.status == "active")
                    .subquery()
                )
                source_query = source_query.where(GlobalSourceDocumentRecord.id.not_in(select(assigned.c.global_source_id)))

            rows = await session.execute(
                source_query.order_by(GlobalSourceDocumentRecord.updated_at.desc()).limit(max(1, min(limit, 250)))
            )
            sources = list(rows.scalars().unique().all())
            if not sources:
                return []

            entries = await self._build_registry_entries(session, sources, case_id)
            if smart_view == "duplicate_candidates":
                entries = [entry for entry in entries if entry.duplicate_candidate]
            if smart_view == "recently_used":
                entries = [entry for entry in entries if entry.usage_count > 0]
                entries.sort(key=lambda entry: entry.usage_count, reverse=True)
            return entries

    async def get_usage(self, global_source_id: str) -> tuple[
        GlobalSourceDocumentRecord,
        list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]],
        list[SourceUsageEntry],
    ]:
        async with self._database.session() as session:
            source = await self._require_global_source(session, global_source_id)
            assignments = await self._assignments_for_sources(session, [global_source_id])
            usage_rows = await session.execute(
                select(SourceDocumentRecord, CrisisCaseRecord)
                .join(CrisisCaseRecord, CrisisCaseRecord.id == SourceDocumentRecord.case_id)
                .where(SourceDocumentRecord.global_source_id == global_source_id)
                .order_by(SourceDocumentRecord.created_at.desc())
            )
            usage = [SourceUsageEntry(document, crisis_case) for document, crisis_case in usage_rows.all()]
            return source, assignments.get(global_source_id, []), usage

    async def related_topic_ids(self, topic_ids: list[str]) -> list[str]:
        if not topic_ids:
            return []
        async with self._database.session() as session:
            rows = await session.execute(
                select(SourceTopicRecord).where(
                    or_(
                        SourceTopicRecord.parent_topic_id.in_(topic_ids),
                        SourceTopicRecord.id.in_(
                            select(SourceTopicRecord.parent_topic_id).where(SourceTopicRecord.id.in_(topic_ids))
                        ),
                    )
                )
            )
            return [str(topic.id) for topic in rows.scalars().all() if str(topic.id) not in set(topic_ids)]

    async def attach_global_source(self, request: AttachGlobalSourceRequest) -> SourceDocumentRecord:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            crisis_case = await session.get(CrisisCaseRecord, request.case_id)
            if crisis_case is None:
                raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)
            source = await self._require_global_source(session, request.global_source_id)
            duplicate = await session.execute(
                select(SourceDocumentRecord).where(
                    SourceDocumentRecord.case_id == request.case_id,
                    SourceDocumentRecord.global_source_id == request.global_source_id,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise ApplicationError(
                    code=ErrorCode.CONFLICT,
                    message="Source is already attached to this case.",
                    status_code=409,
                    details={"case_id": request.case_id, "global_source_id": request.global_source_id},
                )

            assignment = None
            topic_id = request.topic_id
            if request.assignment_id:
                assignment = await session.get(SourceTopicAssignmentRecord, request.assignment_id)
                if assignment is None or str(assignment.global_source_id) != request.global_source_id:
                    raise ApplicationError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Assignment does not belong to the requested source.",
                        status_code=400,
                    )
                topic_id = topic_id or str(assignment.topic_id)
            if topic_id:
                await self._require_topic(session, topic_id)

            document = SourceDocumentRecord(
                case_id=request.case_id,
                global_source_id=request.global_source_id,
                source_topic_id=topic_id,
                source_topic_assignment_id=request.assignment_id,
                source_origin="global_library",
                title=source.title,
                content=source.content,
                doc_type=source.doc_type,
                source_metadata={
                    "selected_topic_id": topic_id,
                    "selected_assignment_id": request.assignment_id,
                    "canonical_url": source.canonical_url,
                    "content_hash": source.content_hash,
                    "source_kind": source.source_kind,
                    "authority_level": source.authority_level,
                    "freshness_status": source.freshness_status,
                    "source_status": source.source_status,
                    "source_metadata": source.source_metadata or {},
                },
                created_at=now,
            )
            session.add(document)
            await session.flush()
            await session.refresh(document)
            return document

    async def save_candidate_to_library(
        self,
        candidate_id: str,
        request: SourceCandidateLibrarySaveRequest,
    ) -> CandidateLibrarySaveResult:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            candidate = await session.get(SourceCandidateRecord, candidate_id)
            if candidate is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source candidate not found: {candidate_id}",
                    status_code=404,
                )
            if candidate.review_status != CandidateReviewStatus.ACCEPTED:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Only accepted source candidates can be saved to the source registry.",
                    status_code=400,
                )

            source, duplicate_reused = await self._find_or_create_source_for_candidate(session, candidate, now)
            assignment = None
            if request.topic_id:
                await self._require_topic(session, request.topic_id)
                assignment = await self._upsert_assignment(
                    session,
                    SourceTopicAssignmentCreateRequest(
                        global_source_id=str(source.id),
                        topic_id=request.topic_id,
                        relevance_score=min(max(float(candidate.total_score or 1.0), 0.0), 1.0),
                        reason=request.reason,
                        assigned_by=request.assigned_by,
                        source_candidate_id=str(candidate.id),
                        discovery_job_id=str(candidate.discovery_job_id),
                        assignment_metadata={
                            "provider": candidate.provider,
                            "candidate_score": candidate.total_score,
                            "classification": candidate.classification,
                        },
                    ),
                    now,
                )
            await session.flush()
            await session.refresh(source)
            if assignment is not None:
                await session.refresh(assignment)
            return CandidateLibrarySaveResult(source=source, assignment=assignment, duplicate_reused=duplicate_reused)

    async def _build_registry_entries(
        self,
        session,
        sources: list[GlobalSourceDocumentRecord],
        case_id: str | None,
    ) -> list[SourceRegistryEntry]:
        source_ids = [str(source.id) for source in sources]
        assignments = await self._assignments_for_sources(session, source_ids)
        usage_counts = await self._usage_counts(session, source_ids)
        attached_ids: set[str] = set()
        if case_id:
            attached_rows = await session.execute(
                select(SourceDocumentRecord.global_source_id).where(
                    SourceDocumentRecord.case_id == case_id,
                    SourceDocumentRecord.global_source_id.in_(source_ids),
                )
            )
            attached_ids = {str(row[0]) for row in attached_rows.all() if row[0]}
        duplicate_hashes = await self._duplicate_values(session, GlobalSourceDocumentRecord.content_hash)
        duplicate_urls = await self._duplicate_values(session, GlobalSourceDocumentRecord.canonical_url)
        return [
            SourceRegistryEntry(
                source=source,
                assignments=assignments.get(str(source.id), []),
                usage_count=usage_counts.get(str(source.id), 0),
                duplicate_candidate=(
                    bool(source.content_hash and source.content_hash in duplicate_hashes)
                    or bool(source.canonical_url and source.canonical_url in duplicate_urls)
                ),
                already_in_case=str(source.id) in attached_ids,
            )
            for source in sources
        ]

    async def _assignments_for_sources(
        self,
        session,
        source_ids: list[str],
    ) -> dict[str, list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]]]:
        rows = await session.execute(
            select(SourceTopicAssignmentRecord, SourceTopicRecord)
            .join(SourceTopicRecord, SourceTopicRecord.id == SourceTopicAssignmentRecord.topic_id)
            .where(SourceTopicAssignmentRecord.global_source_id.in_(source_ids))
            .where(SourceTopicAssignmentRecord.status == "active")
            .order_by(SourceTopicAssignmentRecord.relevance_score.desc(), SourceTopicRecord.name.asc())
        )
        by_source: dict[str, list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]]] = {}
        for assignment, topic in rows.all():
            by_source.setdefault(str(assignment.global_source_id), []).append((assignment, topic))
        return by_source

    async def _usage_counts(self, session, source_ids: list[str]) -> dict[str, int]:
        rows = await session.execute(
            select(SourceDocumentRecord.global_source_id, func.count(SourceDocumentRecord.id))
            .where(SourceDocumentRecord.global_source_id.in_(source_ids))
            .group_by(SourceDocumentRecord.global_source_id)
        )
        return {str(source_id): int(count or 0) for source_id, count in rows.all() if source_id}

    async def _duplicate_values(self, session, column) -> set[str]:
        rows = await session.execute(
            select(column)
            .where(column.is_not(None))
            .group_by(column)
            .having(func.count(GlobalSourceDocumentRecord.id) > 1)
        )
        return {str(value) for value in rows.scalars().all() if value}

    async def _find_or_create_source_for_candidate(
        self,
        session,
        candidate: SourceCandidateRecord,
        now: datetime,
    ) -> tuple[GlobalSourceDocumentRecord, bool]:
        source = None
        if candidate.canonical_url:
            rows = await session.execute(
                select(GlobalSourceDocumentRecord).where(GlobalSourceDocumentRecord.canonical_url == candidate.canonical_url)
            )
            source = rows.scalar_one_or_none()
        if source is None and candidate.content_hash:
            rows = await session.execute(
                select(GlobalSourceDocumentRecord).where(GlobalSourceDocumentRecord.content_hash == candidate.content_hash)
            )
            source = rows.scalar_one_or_none()
        if source is not None:
            return source, True

        source = GlobalSourceDocumentRecord(
            title=candidate.title,
            content=candidate.content or candidate.excerpt,
            doc_type=_doc_type_for_source_kind(candidate.source_type),
            canonical_url=candidate.canonical_url,
            content_hash=candidate.content_hash or hash_content(candidate.content or candidate.excerpt),
            source_kind=candidate.source_type or candidate.classification or "news",
            authority_level=_authority_for_source_kind(candidate.classification or candidate.source_type),
            freshness_status="current",
            source_status="active",
            source_metadata={
                "created_from_candidate_id": str(candidate.id),
                "discovery_job_id": str(candidate.discovery_job_id),
                "provider": candidate.provider,
                "provider_metadata": candidate.provider_metadata or {},
                "url": candidate.url,
                "published_at": candidate.published_at.isoformat() if candidate.published_at else None,
            },
            created_at=now,
            updated_at=now,
        )
        session.add(source)
        await session.flush()
        return source, False

    async def _upsert_assignment(
        self,
        session,
        request: SourceTopicAssignmentCreateRequest,
        now: datetime,
    ) -> SourceTopicAssignmentRecord:
        rows = await session.execute(
            select(SourceTopicAssignmentRecord).where(
                SourceTopicAssignmentRecord.global_source_id == request.global_source_id,
                SourceTopicAssignmentRecord.topic_id == request.topic_id,
            )
        )
        assignment = rows.scalar_one_or_none()
        if assignment is None:
            assignment = SourceTopicAssignmentRecord(
                global_source_id=request.global_source_id,
                topic_id=request.topic_id,
                created_at=now,
            )
            session.add(assignment)
        assignment.relevance_score = request.relevance_score
        assignment.reason = request.reason
        assignment.assigned_by = request.assigned_by
        assignment.source_candidate_id = request.source_candidate_id
        assignment.discovery_job_id = request.discovery_job_id
        assignment.assignment_metadata = request.assignment_metadata
        assignment.status = "active"
        assignment.updated_at = now
        await session.flush()
        return assignment

    async def _require_topic(self, session, topic_id: str) -> SourceTopicRecord:
        topic = await session.get(SourceTopicRecord, topic_id)
        if topic is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message=f"Source topic not found: {topic_id}",
                status_code=404,
            )
        return topic

    async def _require_global_source(self, session, source_id: str) -> GlobalSourceDocumentRecord:
        source = await session.get(GlobalSourceDocumentRecord, source_id)
        if source is None:
            raise ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message=f"Global source not found: {source_id}",
                status_code=404,
            )
        return source


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if not parsed.netloc:
        return url.strip()
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def hash_content(content: str) -> str:
    return sha256(" ".join(content.split()).lower().encode("utf-8")).hexdigest()


def _doc_type_for_source_kind(source_kind: str) -> str:
    normalized = source_kind.lower()
    if normalized in {"official", "statement", "regulator", "company"}:
        return "statement"
    if normalized in {"social", "complaint", "community"}:
        return "complaint"
    return "news"


def _authority_for_source_kind(source_kind: str) -> str:
    normalized = source_kind.lower()
    if normalized in {"official", "statement", "regulator", "research", "academic"}:
        return "high"
    if normalized in {"social", "complaint", "community"}:
        return "medium"
    return "medium"
