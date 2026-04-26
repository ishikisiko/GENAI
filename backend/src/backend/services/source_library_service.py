from __future__ import annotations

from datetime import datetime, timezone

from backend.domain.simulation_records import (
    CaseSourceTopicRecord,
    SourceDocumentRecord,
    SourceTopicAssignmentRecord,
    SourceTopicRecord,
)
from backend.repository.source_library_repository import SourceLibraryRepository, SourceRegistryEntry
from backend.services.source_discovery_contracts import (
    SourceCandidateLibrarySaveRequest,
    SourceCandidateLibrarySaveResponse,
)
from backend.services.source_library_contracts import (
    AttachGlobalSourceRequest,
    CaseSourceSelectionResponse,
    CaseSourceSelectionSection,
    CaseSourceTopicCreateRequest,
    CaseSourceTopicResponse,
    SourceDocumentSnapshotResponse,
    SourceRegistryAssignmentSummary,
    SourceRegistryListResponse,
    SourceRegistrySourceResponse,
    SourceTopicAssignmentCreateRequest,
    SourceTopicAssignmentResponse,
    SourceTopicCreateRequest,
    SourceTopicListResponse,
    SourceTopicResponse,
    SourceTopicUpdateRequest,
    SourceUsageCaseResponse,
    SourceUsageResponse,
)
from backend.shared.errors import ApplicationError, ErrorCode


SMART_VIEWS = {"unassigned", "recently_used", "high_authority", "duplicate_candidates", "stale"}


class SourceLibraryService:
    def __init__(self, repository: SourceLibraryRepository) -> None:
        self._repository = repository

    async def create_topic(self, request: SourceTopicCreateRequest) -> SourceTopicResponse:
        return self._topic_response(await self._repository.create_topic(request))

    async def update_topic(self, topic_id: str, request: SourceTopicUpdateRequest) -> SourceTopicResponse:
        return self._topic_response(await self._repository.update_topic(topic_id, request))

    async def get_topic(self, topic_id: str) -> SourceTopicResponse:
        return self._topic_response(await self._repository.get_topic(topic_id))

    async def list_topics(self) -> SourceTopicListResponse:
        topics = await self._repository.list_topics()
        return SourceTopicListResponse(topics=[self._topic_response(topic) for topic in topics])

    async def create_case_topic(self, request: CaseSourceTopicCreateRequest) -> CaseSourceTopicResponse:
        return self._case_topic_response(await self._repository.create_case_topic(request))

    async def create_assignment(
        self,
        request: SourceTopicAssignmentCreateRequest,
    ) -> SourceTopicAssignmentResponse:
        return self._assignment_response(await self._repository.create_assignment(request))

    async def remove_assignment(self, assignment_id: str) -> SourceTopicAssignmentResponse:
        return self._assignment_response(await self._repository.remove_assignment(assignment_id))

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
    ) -> SourceRegistryListResponse:
        if smart_view and smart_view not in SMART_VIEWS:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid source smart view: {smart_view}",
                status_code=400,
            )
        entries = await self._repository.list_registry(
            topic_id=topic_id,
            smart_view=smart_view,
            query=query,
            source_kind=source_kind,
            authority_level=authority_level,
            freshness_status=freshness_status,
            source_status=source_status,
            case_id=case_id,
        )
        return SourceRegistryListResponse(
            sources=[self._registry_source_response(entry) for entry in entries],
            topic_id=topic_id,
            smart_view=smart_view,
        )

    async def get_usage(self, global_source_id: str) -> SourceUsageResponse:
        source, assignments, usage = await self._repository.get_usage(global_source_id)
        return SourceUsageResponse(
            global_source_id=str(source.id),
            topic_assignments=[self._assignment_response(assignment, topic) for assignment, topic in assignments],
            cases=[
                SourceUsageCaseResponse(
                    case_id=str(entry.crisis_case.id),
                    case_title=entry.crisis_case.title,
                    source_document_id=str(entry.document.id),
                    source_origin=entry.document.source_origin,
                    source_topic_id=str(entry.document.source_topic_id) if entry.document.source_topic_id else None,
                    created_at=format_dt(entry.document.created_at) or "",
                )
                for entry in usage
            ],
            usage_count=len(usage),
        )

    async def get_case_selection(self, case_id: str, query: str | None = None) -> CaseSourceSelectionResponse:
        case_topics = await self._repository.list_case_topics(case_id)
        topic_ids = [str(topic.id) for _, topic in case_topics]

        same_entries = await self._entries_for_topics(topic_ids, case_id)
        related_topic_ids = await self._repository.related_topic_ids(topic_ids)
        related_entries = await self._entries_for_topics(related_topic_ids, case_id)
        recommended_entries = [
            entry
            for entry in sorted(
                same_entries,
                key=lambda item: (
                    item.already_in_case,
                    -max([assignment.relevance_score for assignment, _ in item.assignments] or [0.0]),
                    -item.usage_count,
                ),
            )
            if not entry.already_in_case
        ][:8]
        global_entries = await self._repository.list_registry(query=query or None, case_id=case_id, limit=50)

        sections = [
            CaseSourceSelectionSection(
                key="recommended",
                title="Recommended for this case",
                description="Sources from the current case topics that are not already attached.",
                sources=[self._registry_source_response(entry) for entry in recommended_entries],
            ),
            CaseSourceSelectionSection(
                key="same_topic",
                title="Same topic collections",
                description="Sources assigned to this case's selected topics.",
                sources=[self._registry_source_response(entry) for entry in same_entries],
            ),
            CaseSourceSelectionSection(
                key="related",
                title="Related collections",
                description="Sources from parent or child topics related to the current case.",
                sources=[self._registry_source_response(entry) for entry in related_entries],
            ),
            CaseSourceSelectionSection(
                key="global_search",
                title="Global search",
                description="Search across the full reusable source registry.",
                sources=[self._registry_source_response(entry) for entry in global_entries],
            ),
            CaseSourceSelectionSection(
                key="manual_upload",
                title="Manual upload",
                description="Create a new case-local document and reusable source when no registry source fits.",
                sources=[],
            ),
        ]
        return CaseSourceSelectionResponse(
            case_id=case_id,
            case_topics=[self._case_topic_response(case_topic) for case_topic, _ in case_topics],
            sections=sections,
        )

    async def attach_global_source(self, request: AttachGlobalSourceRequest) -> SourceDocumentSnapshotResponse:
        return self._snapshot_response(await self._repository.attach_global_source(request))

    async def save_candidate_to_library(
        self,
        candidate_id: str,
        request: SourceCandidateLibrarySaveRequest,
    ) -> SourceCandidateLibrarySaveResponse:
        result = await self._repository.save_candidate_to_library(candidate_id, request)
        return SourceCandidateLibrarySaveResponse(
            candidate_id=candidate_id,
            global_source_id=str(result.source.id),
            topic_id=str(result.assignment.topic_id) if result.assignment else None,
            topic_assignment_id=str(result.assignment.id) if result.assignment else None,
            duplicate_reused=result.duplicate_reused,
        )

    async def _entries_for_topics(self, topic_ids: list[str], case_id: str) -> list[SourceRegistryEntry]:
        entries: list[SourceRegistryEntry] = []
        seen: set[str] = set()
        for topic_id in topic_ids:
            for entry in await self._repository.list_registry(topic_id=topic_id, case_id=case_id):
                source_id = str(entry.source.id)
                if source_id in seen:
                    continue
                seen.add(source_id)
                entries.append(entry)
        return entries

    @staticmethod
    def _topic_response(topic: SourceTopicRecord) -> SourceTopicResponse:
        return SourceTopicResponse(
            id=str(topic.id),
            name=topic.name,
            description=topic.description,
            parent_topic_id=str(topic.parent_topic_id) if topic.parent_topic_id else None,
            topic_type=topic.topic_type,
            status=topic.status,
            created_at=format_dt(topic.created_at) or "",
            updated_at=format_dt(topic.updated_at) or "",
        )

    @staticmethod
    def _case_topic_response(row: CaseSourceTopicRecord) -> CaseSourceTopicResponse:
        return CaseSourceTopicResponse(
            id=str(row.id),
            case_id=str(row.case_id),
            topic_id=str(row.topic_id),
            relation_type=row.relation_type,
            reason=row.reason,
            created_at=format_dt(row.created_at) or "",
            updated_at=format_dt(row.updated_at) or "",
        )

    @staticmethod
    def _assignment_response(
        assignment: SourceTopicAssignmentRecord,
        topic: SourceTopicRecord | None = None,
    ) -> SourceTopicAssignmentResponse:
        return SourceTopicAssignmentResponse(
            id=str(assignment.id),
            global_source_id=str(assignment.global_source_id),
            topic_id=str(assignment.topic_id),
            topic_name=topic.name if topic is not None else None,
            relevance_score=assignment.relevance_score,
            reason=assignment.reason,
            assigned_by=assignment.assigned_by,
            source_candidate_id=str(assignment.source_candidate_id) if assignment.source_candidate_id else None,
            discovery_job_id=str(assignment.discovery_job_id) if assignment.discovery_job_id else None,
            assignment_metadata=assignment.assignment_metadata or {},
            status=assignment.status,
            created_at=format_dt(assignment.created_at) or "",
            updated_at=format_dt(assignment.updated_at) or "",
        )

    @staticmethod
    def _registry_source_response(entry: SourceRegistryEntry) -> SourceRegistrySourceResponse:
        source = entry.source
        return SourceRegistrySourceResponse(
            id=str(source.id),
            title=source.title,
            content=source.content,
            doc_type=source.doc_type,
            canonical_url=source.canonical_url,
            content_hash=source.content_hash,
            source_kind=source.source_kind,
            authority_level=source.authority_level,
            freshness_status=source.freshness_status,
            source_status=source.source_status,
            source_metadata=source.source_metadata or {},
            created_at=format_dt(source.created_at) or "",
            updated_at=format_dt(source.updated_at) or "",
            topic_assignments=[
                SourceRegistryAssignmentSummary(
                    assignment_id=str(assignment.id),
                    topic_id=str(topic.id),
                    topic_name=topic.name,
                    relevance_score=assignment.relevance_score,
                    reason=assignment.reason,
                    assigned_by=assignment.assigned_by,
                    status=assignment.status,
                )
                for assignment, topic in entry.assignments
            ],
            usage_count=entry.usage_count,
            duplicate_candidate=entry.duplicate_candidate,
            already_in_case=entry.already_in_case,
        )

    @staticmethod
    def _snapshot_response(document: SourceDocumentRecord) -> SourceDocumentSnapshotResponse:
        return SourceDocumentSnapshotResponse(
            id=str(document.id),
            case_id=str(document.case_id),
            global_source_id=str(document.global_source_id) if document.global_source_id else None,
            source_topic_id=str(document.source_topic_id) if document.source_topic_id else None,
            source_topic_assignment_id=(
                str(document.source_topic_assignment_id) if document.source_topic_assignment_id else None
            ),
            source_origin=document.source_origin,
            title=document.title,
            content=document.content,
            doc_type=document.doc_type,
            source_metadata=document.source_metadata or {},
            created_at=format_dt(document.created_at) or "",
        )


def format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
