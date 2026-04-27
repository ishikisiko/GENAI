from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse, urlunparse

from sqlalchemy import delete, func, or_, select, update

from backend.db import Database
from backend.domain.simulation_records import (
    CandidateReviewStatus,
    CaseSourceTopicRecord,
    CrisisCaseRecord,
    GlobalSourceDocumentRecord,
    SourceCandidateRecord,
    SourceDocumentRecord,
    SourceFragmentRecord,
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
from backend.services.semantic_source_recall import (
    DEFAULT_FRAGMENT_PREVIEW_LIMIT,
    EMBEDDING_MODEL,
    EMBEDDING_VERSION,
    LocalSemanticIndex,
    aggregate_semantic_support,
    chunk_source_text,
)
from backend.shared.errors import ApplicationError, ErrorCode


@dataclass(frozen=True)
class SourceRegistryEntry:
    source: GlobalSourceDocumentRecord
    assignments: list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]]
    usage_count: int
    duplicate_candidate: bool
    already_in_case: bool = False


@dataclass(frozen=True)
class SourceFragmentMatch:
    fragment: SourceFragmentRecord
    source_scope: str
    source_id: str
    similarity: float


@dataclass(frozen=True)
class SourceRankingReason:
    key: str
    label: str
    value: str
    score: float | None = None


@dataclass(frozen=True)
class SourceSemanticRecommendationEntry:
    source_scope: str
    source: GlobalSourceDocumentRecord | None
    candidate: SourceCandidateRecord | None
    assignments: list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]]
    usage_count: int
    duplicate_candidate: bool
    already_in_case: bool
    semantic_support: float
    final_score: float
    matched_fragments: list[SourceFragmentMatch]
    ranking_reasons: list[SourceRankingReason]


@dataclass(frozen=True)
class SourceSemanticRecallResult:
    applied: bool
    reason: str | None
    query: str | None
    indexed_fragment_count: int
    matched_fragment_count: int
    entries: list[SourceSemanticRecommendationEntry]


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
        self._semantic_index = LocalSemanticIndex()

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

    async def refresh_global_source_fragments(self, global_source_id: str) -> list[SourceFragmentRecord]:
        async with self._database.session() as session:
            source = await self._require_global_source(session, global_source_id)
            return await self._refresh_global_source_fragments(session, source)

    async def refresh_candidate_source_fragments(self, candidate_id: str) -> list[SourceFragmentRecord]:
        async with self._database.session() as session:
            candidate = await session.get(SourceCandidateRecord, candidate_id)
            if candidate is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source candidate not found: {candidate_id}",
                    status_code=404,
                )
            return await self._refresh_candidate_source_fragments(session, candidate)

    async def mark_source_fragments_stale(self, source_scope: str, source_id: str) -> int:
        async with self._database.session() as session:
            now = datetime.now(timezone.utc)
            filters = self._fragment_source_filters(source_scope, source_id)
            result = await session.execute(
                update(SourceFragmentRecord)
                .where(*filters)
                .values(index_status="stale", updated_at=now, last_error=None)
            )
            return int(result.rowcount or 0)

    async def mark_source_fragment_failed(self, fragment_id: str, error: str) -> SourceFragmentRecord:
        async with self._database.session() as session:
            fragment = await session.get(SourceFragmentRecord, fragment_id)
            if fragment is None:
                raise ApplicationError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Source fragment not found: {fragment_id}",
                    status_code=404,
                )
            fragment.index_status = "failed"
            fragment.last_error = error
            fragment.updated_at = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(fragment)
            return fragment

    async def semantic_recommendations(
        self,
        case_id: str,
        query: str | None = None,
        limit: int = 12,
        fragment_limit: int = DEFAULT_FRAGMENT_PREVIEW_LIMIT,
    ) -> SourceSemanticRecallResult:
        async with self._database.session() as session:
            crisis_case = await session.get(CrisisCaseRecord, case_id)
            if crisis_case is None:
                raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

            case_topic_rows = await session.execute(
                select(CaseSourceTopicRecord, SourceTopicRecord)
                .join(SourceTopicRecord, SourceTopicRecord.id == CaseSourceTopicRecord.topic_id)
                .where(CaseSourceTopicRecord.case_id == case_id)
            )
            case_topics = [(case_topic, topic) for case_topic, topic in case_topic_rows.all()]
            query_text = self._build_semantic_query(crisis_case, case_topics, query)
            if not query_text:
                return SourceSemanticRecallResult(False, "empty_query", None, 0, 0, [])

            source_rows = await session.execute(
                select(GlobalSourceDocumentRecord)
                .where(GlobalSourceDocumentRecord.source_status == "active")
                .order_by(GlobalSourceDocumentRecord.updated_at.desc())
                .limit(250)
            )
            global_sources = list(source_rows.scalars().all())
            candidate_rows = await session.execute(
                select(SourceCandidateRecord)
                .where(SourceCandidateRecord.case_id == case_id)
                .order_by(SourceCandidateRecord.total_score.desc(), SourceCandidateRecord.created_at.desc())
                .limit(100)
            )
            candidates = list(candidate_rows.scalars().all())

            for source in global_sources:
                await self._refresh_global_source_fragments(session, source)
            for candidate in candidates:
                await self._refresh_candidate_source_fragments(session, candidate)
            await session.flush()

            global_ids = [str(source.id) for source in global_sources]
            candidate_ids = [str(candidate.id) for candidate in candidates]
            fragment_query = select(SourceFragmentRecord).where(SourceFragmentRecord.index_status == "indexed")
            source_filters = []
            if global_ids:
                source_filters.append(SourceFragmentRecord.global_source_id.in_(global_ids))
            if candidate_ids:
                source_filters.append(SourceFragmentRecord.source_candidate_id.in_(candidate_ids))
            if not source_filters:
                return SourceSemanticRecallResult(False, "no_sources", query_text, 0, 0, [])
            fragment_query = fragment_query.where(or_(*source_filters))

            fragment_rows = await session.execute(fragment_query.order_by(SourceFragmentRecord.fragment_index.asc()))
            fragments = list(fragment_rows.scalars().all())
            if not fragments:
                return SourceSemanticRecallResult(False, "no_indexed_fragments", query_text, 0, 0, [])

            query_vector = self._semantic_index.embed(query_text)
            matches_by_source: dict[tuple[str, str], list[SourceFragmentMatch]] = {}
            for fragment in fragments:
                similarity = self._semantic_index.similarity(query_vector, fragment.embedding_vector)
                if similarity <= 0.01:
                    continue
                source_scope = fragment.source_scope
                source_id = str(fragment.global_source_id or fragment.source_candidate_id)
                matches_by_source.setdefault((source_scope, source_id), []).append(
                    SourceFragmentMatch(
                        fragment=fragment,
                        source_scope=source_scope,
                        source_id=source_id,
                        similarity=similarity,
                    )
                )

            if not matches_by_source:
                return SourceSemanticRecallResult(False, "no_matches", query_text, len(fragments), 0, [])

            assignments = await self._assignments_for_sources(session, global_ids)
            usage_counts = await self._usage_counts(session, global_ids) if global_ids else {}
            attached_ids = await self._attached_source_ids(session, case_id, global_ids) if global_ids else set()
            duplicate_hashes = await self._duplicate_values(session, GlobalSourceDocumentRecord.content_hash)
            duplicate_urls = await self._duplicate_values(session, GlobalSourceDocumentRecord.canonical_url)
            case_topic_ids = {str(topic.id) for _, topic in case_topics}
            source_by_id = {str(source.id): source for source in global_sources}
            candidate_by_id = {str(candidate.id): candidate for candidate in candidates}

            entries: list[SourceSemanticRecommendationEntry] = []
            for (source_scope, source_id), matches in matches_by_source.items():
                sorted_matches = sorted(matches, key=lambda item: item.similarity, reverse=True)
                semantic_support = aggregate_semantic_support([match.similarity for match in sorted_matches])
                top_matches = sorted_matches[: max(1, fragment_limit)]
                if source_scope == "global":
                    source = source_by_id.get(source_id)
                    if source is None:
                        continue
                    source_assignments = assignments.get(source_id, [])
                    duplicate_candidate = (
                        bool(source.content_hash and source.content_hash in duplicate_hashes)
                        or bool(source.canonical_url and source.canonical_url in duplicate_urls)
                    )
                    final_score = self._global_semantic_score(
                        source=source,
                        assignments=source_assignments,
                        usage_count=usage_counts.get(source_id, 0),
                        semantic_support=semantic_support,
                        case_topic_ids=case_topic_ids,
                    )
                    ranking_reasons = self._global_ranking_reasons(
                        source=source,
                        assignments=source_assignments,
                        semantic_support=semantic_support,
                        case_topic_ids=case_topic_ids,
                    )
                    entries.append(
                        SourceSemanticRecommendationEntry(
                            source_scope="global",
                            source=source,
                            candidate=None,
                            assignments=source_assignments,
                            usage_count=usage_counts.get(source_id, 0),
                            duplicate_candidate=duplicate_candidate,
                            already_in_case=source_id in attached_ids,
                            semantic_support=semantic_support,
                            final_score=final_score,
                            matched_fragments=top_matches,
                            ranking_reasons=ranking_reasons,
                        )
                    )
                    continue

                candidate = candidate_by_id.get(source_id)
                if candidate is None:
                    continue
                final_score = self._candidate_semantic_score(candidate, semantic_support)
                entries.append(
                    SourceSemanticRecommendationEntry(
                        source_scope="candidate",
                        source=None,
                        candidate=candidate,
                        assignments=[],
                        usage_count=0,
                        duplicate_candidate=False,
                        already_in_case=False,
                        semantic_support=semantic_support,
                        final_score=final_score,
                        matched_fragments=top_matches,
                        ranking_reasons=self._candidate_ranking_reasons(candidate, semantic_support),
                    )
                )

            ranked = self._diversity_rerank(entries)[: max(1, limit)]
            return SourceSemanticRecallResult(
                applied=True,
                reason=None,
                query=query_text,
                indexed_fragment_count=len(fragments),
                matched_fragment_count=sum(len(matches) for matches in matches_by_source.values()),
                entries=ranked,
            )

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
            await self._refresh_candidate_source_fragments(session, candidate)
            await self._refresh_global_source_fragments(session, source)
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
            attached_ids = await self._attached_source_ids(session, case_id, source_ids)
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

    async def _attached_source_ids(self, session, case_id: str, source_ids: list[str]) -> set[str]:
        if not source_ids:
            return set()
        attached_rows = await session.execute(
            select(SourceDocumentRecord.global_source_id).where(
                SourceDocumentRecord.case_id == case_id,
                SourceDocumentRecord.global_source_id.in_(source_ids),
            )
        )
        return {str(row[0]) for row in attached_rows.all() if row[0]}

    async def _refresh_global_source_fragments(
        self,
        session,
        source: GlobalSourceDocumentRecord,
    ) -> list[SourceFragmentRecord]:
        return await self._replace_fragments(
            session=session,
            source_scope="global",
            source_id=str(source.id),
            content=source.content,
        )

    async def _refresh_candidate_source_fragments(
        self,
        session,
        candidate: SourceCandidateRecord,
    ) -> list[SourceFragmentRecord]:
        return await self._replace_fragments(
            session=session,
            source_scope="candidate",
            source_id=str(candidate.id),
            content=candidate.content or candidate.excerpt,
        )

    async def _replace_fragments(
        self,
        session,
        source_scope: str,
        source_id: str,
        content: str,
    ) -> list[SourceFragmentRecord]:
        now = datetime.now(timezone.utc)
        text_fragments = chunk_source_text(content)
        existing_rows = await session.execute(
            select(SourceFragmentRecord)
            .where(*self._fragment_source_filters(source_scope, source_id))
            .order_by(SourceFragmentRecord.fragment_index.asc())
        )
        existing = list(existing_rows.scalars().all())
        if self._fragments_current(existing, text_fragments):
            return existing

        if existing:
            await session.execute(
                update(SourceFragmentRecord)
                .where(*self._fragment_source_filters(source_scope, source_id))
                .values(index_status="stale", updated_at=now, last_error=None)
            )
            await session.flush()
            await session.execute(delete(SourceFragmentRecord).where(*self._fragment_source_filters(source_scope, source_id)))

        rows: list[SourceFragmentRecord] = []
        for fragment in text_fragments:
            vector = self._semantic_index.embed(fragment.text)
            row = SourceFragmentRecord(
                source_scope=source_scope,
                global_source_id=source_id if source_scope == "global" else None,
                source_candidate_id=source_id if source_scope == "candidate" else None,
                fragment_index=fragment.index,
                fragment_text=fragment.text,
                content_hash=fragment.content_hash,
                embedding_model=EMBEDDING_MODEL,
                embedding_version=EMBEDDING_VERSION,
                embedding_vector=vector,
                vector_index_id=f"{source_scope}:{source_id}:{fragment.index}",
                index_status="indexed",
                last_indexed_at=now,
                last_error=None,
                created_at=now,
                updated_at=now,
            )
            rows.append(row)
        if rows:
            session.add_all(rows)
            await session.flush()
            for row in rows:
                await session.refresh(row)
        return rows

    def _fragments_current(self, existing: list[SourceFragmentRecord], text_fragments) -> bool:
        if len(existing) != len(text_fragments):
            return False
        for row, fragment in zip(existing, text_fragments, strict=True):
            if row.fragment_index != fragment.index:
                return False
            if row.content_hash != fragment.content_hash:
                return False
            if row.embedding_model != EMBEDDING_MODEL or row.embedding_version != EMBEDDING_VERSION:
                return False
            if row.index_status != "indexed" or not row.embedding_vector:
                return False
        return True

    def _fragment_source_filters(self, source_scope: str, source_id: str):
        if source_scope == "global":
            return (
                SourceFragmentRecord.source_scope == "global",
                SourceFragmentRecord.global_source_id == source_id,
            )
        if source_scope == "candidate":
            return (
                SourceFragmentRecord.source_scope == "candidate",
                SourceFragmentRecord.source_candidate_id == source_id,
            )
        raise ApplicationError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid source fragment scope: {source_scope}",
            status_code=400,
        )

    def _build_semantic_query(
        self,
        crisis_case: CrisisCaseRecord,
        case_topics: list[tuple[CaseSourceTopicRecord, SourceTopicRecord]],
        query: str | None,
    ) -> str:
        parts = [query or "", crisis_case.title, crisis_case.description]
        for case_topic, topic in case_topics:
            parts.extend([topic.name, topic.description, case_topic.reason])
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()

    def _global_semantic_score(
        self,
        source: GlobalSourceDocumentRecord,
        assignments: list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]],
        usage_count: int,
        semantic_support: float,
        case_topic_ids: set[str],
    ) -> float:
        topic_score = max(
            [
                assignment.relevance_score
                for assignment, topic in assignments
                if not case_topic_ids or str(topic.id) in case_topic_ids
            ]
            or [0.0]
        )
        authority_score = _authority_score(source.authority_level)
        freshness_score = _freshness_score(source.freshness_status)
        usage_score = min(1.0, usage_count / 5)
        score = (
            semantic_support * 0.4
            + topic_score * 0.2
            + authority_score * 0.15
            + freshness_score * 0.1
            + usage_score * 0.05
            + _source_quality_score(source.source_kind) * 0.1
        )
        return round(score, 6)

    def _candidate_semantic_score(self, candidate: SourceCandidateRecord, semantic_support: float) -> float:
        score = (
            semantic_support * 0.45
            + float(candidate.relevance or 0) * 0.15
            + float(candidate.authority or 0) * 0.12
            + float(candidate.freshness or 0) * 0.08
            + float(candidate.grounding_value or 0) * 0.15
            + float(candidate.total_score or 0) * 0.05
        )
        return round(score, 6)

    def _global_ranking_reasons(
        self,
        source: GlobalSourceDocumentRecord,
        assignments: list[tuple[SourceTopicAssignmentRecord, SourceTopicRecord]],
        semantic_support: float,
        case_topic_ids: set[str],
    ) -> list[SourceRankingReason]:
        topic_matches = [topic for assignment, topic in assignments if str(topic.id) in case_topic_ids]
        reasons = [
            SourceRankingReason(
                key="semantic_support",
                label="Semantic support",
                value=f"{round(semantic_support * 100)} match",
                score=semantic_support,
            ),
            SourceRankingReason(
                key="authority",
                label="Authority",
                value=source.authority_level,
                score=_authority_score(source.authority_level),
            ),
            SourceRankingReason(
                key="freshness",
                label="Freshness",
                value=source.freshness_status,
                score=_freshness_score(source.freshness_status),
            ),
        ]
        if topic_matches:
            reasons.append(
                SourceRankingReason(
                    key="topic_relationship",
                    label="Topic relationship",
                    value=", ".join(topic.name for topic in topic_matches[:2]),
                    score=max(
                        [
                            assignment.relevance_score
                            for assignment, topic in assignments
                            if str(topic.id) in case_topic_ids
                        ]
                        or [0.0]
                    ),
                )
            )
        reasons.append(
            SourceRankingReason(
                key="diversity",
                label="Diversity",
                value=source.source_kind,
                score=_source_quality_score(source.source_kind),
            )
        )
        return reasons

    def _candidate_ranking_reasons(
        self,
        candidate: SourceCandidateRecord,
        semantic_support: float,
    ) -> list[SourceRankingReason]:
        return [
            SourceRankingReason(
                key="semantic_support",
                label="Semantic support",
                value=f"{round(semantic_support * 100)} match",
                score=semantic_support,
            ),
            SourceRankingReason(
                key="candidate_review_status",
                label="Review status",
                value=str(candidate.review_status),
                score=None,
            ),
            SourceRankingReason(
                key="grounding_value",
                label="Grounding value",
                value=f"{round(float(candidate.grounding_value or 0) * 100)}",
                score=float(candidate.grounding_value or 0),
            ),
            SourceRankingReason(
                key="diversity",
                label="Diversity",
                value=candidate.source_type or candidate.classification,
                score=float(candidate.diversity or 0),
            ),
        ]

    def _diversity_rerank(
        self,
        entries: list[SourceSemanticRecommendationEntry],
    ) -> list[SourceSemanticRecommendationEntry]:
        if not entries:
            return []
        strongest = max(entries, key=lambda entry: (entry.semantic_support, entry.final_score))
        remaining = [entry for entry in entries if entry is not strongest]
        result = [strongest]
        seen_buckets = {self._diversity_bucket(strongest)}

        while remaining:
            best_index = 0
            best_score = -1.0
            for index, entry in enumerate(remaining):
                bucket = self._diversity_bucket(entry)
                diversity_bonus = 0.08 if bucket not in seen_buckets else -0.04
                adjusted_score = entry.final_score + diversity_bonus
                if adjusted_score > best_score:
                    best_index = index
                    best_score = adjusted_score
            selected = remaining.pop(best_index)
            result.append(selected)
            seen_buckets.add(self._diversity_bucket(selected))
        return result

    def _diversity_bucket(self, entry: SourceSemanticRecommendationEntry) -> str:
        if entry.source is not None:
            return f"global:{entry.source.source_kind}:{entry.source.authority_level}"
        if entry.candidate is not None:
            return f"candidate:{entry.candidate.source_type}:{entry.candidate.provider}:{entry.candidate.region}"
        return entry.source_scope

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


def _authority_score(authority_level: str) -> float:
    return {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.35,
    }.get((authority_level or "").lower(), 0.6)


def _freshness_score(freshness_status: str) -> float:
    return {
        "current": 1.0,
        "recent": 0.85,
        "stale": 0.25,
        "unknown": 0.5,
    }.get((freshness_status or "").lower(), 0.6)


def _source_quality_score(source_kind: str) -> float:
    return {
        "official": 1.0,
        "research": 0.9,
        "news": 0.75,
        "complaint": 0.6,
        "social": 0.55,
        "community": 0.55,
    }.get((source_kind or "").lower(), 0.65)
