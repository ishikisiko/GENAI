from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from backend.domain.simulation_records import CrisisCaseRecord, SourceCandidateRecord, SourceDiscoveryJobRecord
from backend.repository.source_discovery_repository import SourceDiscoveryRepository
from backend.services.llm_client import LlmJsonClient
from backend.services.source_discovery_contracts import (
    SourceDiscoveryAssistantBriefingLimit,
    SourceDiscoveryAssistantEvidenceGap,
    SourceDiscoveryAssistantRequest,
    SourceDiscoveryAssistantResponse,
    SourceDiscoveryJobPayload,
)
from backend.services.source_discovery_service import (
    ContentFetcher,
    FetchedContent,
    MockContentFetcher,
    MockSearchProvider,
    SearchProvider,
    SearchResult,
    canonicalize_url,
    format_dt,
    hash_content,
)
from backend.shared.errors import ApplicationError, DependencyError, ErrorCode
from backend.shared.logging import get_logger


SEARCH_PLANNING_MODE = "search_planning"
SOURCE_INTERPRETATION_MODE = "source_interpretation"
SEARCH_BACKED_BRIEFING_MODE = "search_backed_briefing"
_SUPPORTED_MODES = {SEARCH_PLANNING_MODE, SOURCE_INTERPRETATION_MODE, SEARCH_BACKED_BRIEFING_MODE}
_MAX_CANDIDATES_FOR_PROMPT = 12
_MAX_TEXT_CHARS_PER_CANDIDATE = 1200
_BRIEFING_MAX_QUERIES = 4
_BRIEFING_MAX_RESULTS_PER_QUERY = 4
_BRIEFING_MAX_TOTAL_SOURCES = 8
_BRIEFING_MAX_CONTENT_CHARS_PER_SOURCE = 1200


class SourceDiscoveryAssistantService:
    def __init__(
        self,
        source_repository: SourceDiscoveryRepository,
        llm_client: LlmJsonClient,
        search_provider: SearchProvider | None = None,
        content_fetcher: ContentFetcher | None = None,
    ) -> None:
        self._source_repository = source_repository
        self._llm_client = llm_client
        self._search_provider = search_provider or MockSearchProvider()
        self._content_fetcher = content_fetcher or MockContentFetcher()
        self._logger = get_logger("backend.source_discovery_assistant")

    async def answer(self, request: SourceDiscoveryAssistantRequest) -> SourceDiscoveryAssistantResponse:
        mode = request.mode.strip()
        if mode not in _SUPPORTED_MODES:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Unsupported source discovery assistant mode: {request.mode}",
                status_code=400,
                details={"supported_modes": sorted(_SUPPORTED_MODES)},
            )

        if mode == SEARCH_PLANNING_MODE:
            return await self._answer_search_planning(request)
        if mode == SEARCH_BACKED_BRIEFING_MODE:
            return await self._answer_search_backed_briefing(request)
        return await self._answer_source_interpretation(request)

    async def _answer_search_planning(
        self,
        request: SourceDiscoveryAssistantRequest,
    ) -> SourceDiscoveryAssistantResponse:
        if not request.case_id:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="case_id is required for search planning assistant requests.",
                status_code=400,
            )

        crisis_case = await self._source_repository.get_case(request.case_id)
        if crisis_case is None:
            raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)

        if not (request.topic.strip() or request.description.strip() or crisis_case.title):
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Search planning requires at least a topic, description, or case title.",
                status_code=400,
            )

        prompt = self._build_search_planning_prompt(request, crisis_case)
        response = await self._chat_response(prompt, expected_mode=SEARCH_PLANNING_MODE)
        self._ensure_assistant_time_ranges(response, request.time_range)
        self._logger.info("source_discovery_assistant_search_planning", extra={"case_id": request.case_id})
        return response

    async def _answer_search_backed_briefing(
        self,
        request: SourceDiscoveryAssistantRequest,
    ) -> SourceDiscoveryAssistantResponse:
        crisis_case = await self._load_optional_case(request.case_id)
        topic = (request.topic or (crisis_case.title if crisis_case else "")).strip()
        description = (request.description or (crisis_case.description if crisis_case else "")).strip()
        if not (topic or description):
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Search-backed briefing requires a topic, description, or case context.",
                status_code=400,
            )

        queries = self._briefing_queries(topic=topic, description=description, request=request)
        sources = await self._collect_briefing_sources(request, topic, description, queries)
        limits = self._briefing_limits()
        if not sources:
            return SourceDiscoveryAssistantResponse(
                mode=SEARCH_BACKED_BRIEFING_MODE,
                answer="I could not gather enough source material for a cited preliminary briefing.",
                insufficient_evidence=True,
                evidence_gaps=[
                    SourceDiscoveryAssistantEvidenceGap(
                        summary="The bounded first-pass search did not return usable source context.",
                        follow_up_searches=queries,
                    )
                ],
                follow_up_searches=queries,
                briefing_limits=limits,
            )

        prompt = self._build_search_backed_briefing_prompt(request, crisis_case, topic, description, queries, sources)
        response = await self._chat_response(prompt, expected_mode=SEARCH_BACKED_BRIEFING_MODE)
        self._ensure_assistant_time_ranges(response, request.time_range)
        response.briefing_limits = response.briefing_limits or limits
        if not response.citations and not response.insufficient_evidence:
            response.insufficient_evidence = True
            response.evidence_gaps.append(
                SourceDiscoveryAssistantEvidenceGap(
                    summary="The briefing response did not include citations, so it cannot be treated as grounded.",
                    follow_up_searches=queries,
                )
            )
        self._logger.info(
            "source_discovery_assistant_search_backed_briefing",
            extra={"case_id": request.case_id, "query_count": len(queries), "source_count": len(sources)},
        )
        return response

    async def _answer_source_interpretation(
        self,
        request: SourceDiscoveryAssistantRequest,
    ) -> SourceDiscoveryAssistantResponse:
        if not request.discovery_job_id:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="discovery_job_id is required for source interpretation assistant requests.",
                status_code=400,
            )

        discovery_job, _job = await self._source_repository.get_discovery_job(request.discovery_job_id)
        candidates = await self._source_repository.list_candidates(discovery_job_id=request.discovery_job_id)
        if not candidates:
            return self._insufficient_candidate_response(discovery_job)

        prompt = self._build_source_interpretation_prompt(request, discovery_job, candidates)
        response = await self._chat_response(prompt, expected_mode=SOURCE_INTERPRETATION_MODE)
        if not response.citations and not response.insufficient_evidence:
            response.insufficient_evidence = True
            response.evidence_gaps.append(
                SourceDiscoveryAssistantEvidenceGap(
                    summary="The assistant response did not include source citations, so it cannot be treated as grounded.",
                    follow_up_searches=self._default_follow_up_searches(discovery_job),
                )
            )
        self._logger.info(
            "source_discovery_assistant_source_interpretation",
            extra={"discovery_job_id": request.discovery_job_id, "candidate_count": len(candidates)},
        )
        return response

    async def _load_optional_case(self, case_id: str | None) -> CrisisCaseRecord | None:
        if not case_id:
            return None
        crisis_case = await self._source_repository.get_case(case_id)
        if crisis_case is None:
            raise ApplicationError(code=ErrorCode.NOT_FOUND, message="Case not found", status_code=404)
        return crisis_case

    async def _chat_response(self, prompt: str, expected_mode: str) -> SourceDiscoveryAssistantResponse:
        try:
            raw_payload = await self._llm_client.chat_json(prompt=prompt, temperature=0.2, max_retries=2)
            payload = self._normalize_llm_payload(raw_payload, expected_mode)
            response = SourceDiscoveryAssistantResponse.model_validate(payload)
        except ValidationError as exc:
            raise DependencyError(
                "llm",
                details={
                    "reason": "LLM returned invalid assistant payload",
                    "validation_errors": exc.errors(include_url=False),
                },
            ) from exc
        return response

    @classmethod
    def _normalize_llm_payload(cls, raw_payload: Any, expected_mode: str) -> dict[str, Any]:
        if not isinstance(raw_payload, dict):
            raise DependencyError("llm", details={"reason": "LLM returned non-object JSON"})

        payload = {**raw_payload, "mode": expected_mode}
        for field in (
            "planning_suggestions",
            "source_summaries",
            "key_actors",
            "controversy_focus",
            "timeline",
            "event_stages",
            "citations",
            "conflicts",
            "evidence_gaps",
            "follow_up_searches",
        ):
            payload[field] = cls._list_value(payload.get(field))

        payload["citations"] = cls._normalize_citations(payload["citations"])
        payload["planning_suggestions"] = [
            cls._normalize_planning_suggestion(item) for item in payload["planning_suggestions"] if isinstance(item, dict)
        ]
        payload["recommended_settings"] = cls._normalize_recommended_settings(payload.get("recommended_settings"))
        payload["source_summaries"] = [
            cls._normalize_source_summary(item) for item in payload["source_summaries"] if isinstance(item, dict)
        ]
        payload["timeline"] = [cls._normalize_timeline_item(item) for item in payload["timeline"] if isinstance(item, dict)]
        payload["event_stages"] = [
            cls._normalize_event_stage(item) for item in payload["event_stages"] if isinstance(item, dict)
        ]
        payload["conflicts"] = [cls._normalize_conflict(item) for item in payload["conflicts"] if isinstance(item, dict)]
        payload["evidence_gaps"] = [cls._normalize_evidence_gap(item) for item in payload["evidence_gaps"]]
        payload["follow_up_searches"] = [str(item) for item in payload["follow_up_searches"] if item]
        payload["key_actors"] = [str(item) for item in payload["key_actors"] if item]
        payload["controversy_focus"] = [str(item) for item in payload["controversy_focus"] if item]
        return payload

    @staticmethod
    def _list_value(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @classmethod
    def _normalize_citations(cls, value: Any) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        for item in cls._list_value(value):
            if isinstance(item, str):
                citations.append({"title": item, "quote": item})
                continue
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("source_title") or item.get("url") or "Untitled source"
            citations.append(
                {
                    **item,
                    "candidate_id": item.get("candidate_id"),
                    "title": str(title),
                    "url": item.get("url"),
                    "published_at": item.get("published_at"),
                    "quote": str(item.get("quote") or item.get("evidence") or ""),
                }
            )
        return citations

    @classmethod
    def _normalize_planning_suggestion(cls, item: dict[str, Any]) -> dict[str, Any]:
        return {
            **item,
            "label": str(item.get("label") or item.get("title") or "Search direction"),
            "rationale": str(item.get("rationale") or item.get("summary") or ""),
            "source_types": [str(value) for value in cls._list_value(item.get("source_types")) if value],
            "queries": [str(value) for value in cls._list_value(item.get("queries")) if value],
            "core_entities": cls._string_list(item.get("core_entities")),
            "actor_names": cls._string_list(item.get("actor_names") or item.get("actors")),
            "event_aliases": cls._string_list(item.get("event_aliases") or item.get("aliases")),
            "language_variants": cls._string_list(item.get("language_variants")),
            "evidence_buckets": cls._normalize_evidence_buckets(item.get("evidence_buckets")),
        }

    @classmethod
    def _normalize_recommended_settings(cls, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        normalized = {**value}
        normalized["source_types"] = [str(item) for item in cls._list_value(value.get("source_types")) if item]
        normalized["queries"] = [str(item) for item in cls._list_value(value.get("queries")) if item]
        normalized["core_entities"] = cls._string_list(value.get("core_entities"))
        normalized["actor_names"] = cls._string_list(value.get("actor_names") or value.get("actors"))
        normalized["event_aliases"] = cls._string_list(value.get("event_aliases") or value.get("aliases"))
        normalized["language_variants"] = cls._string_list(value.get("language_variants"))
        normalized["evidence_buckets"] = cls._normalize_evidence_buckets(value.get("evidence_buckets"))
        if normalized.get("max_sources") is not None:
            try:
                normalized["max_sources"] = min(max(int(normalized["max_sources"]), 1), 50)
            except (TypeError, ValueError):
                normalized["max_sources"] = None
        return normalized

    @classmethod
    def _string_list(cls, value: Any) -> list[str]:
        normalized: list[str] = []
        for item in cls._list_value(value):
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @classmethod
    def _normalize_evidence_buckets(cls, value: Any) -> list[dict[str, Any]]:
        buckets: list[dict[str, Any]] = []
        for item in cls._list_value(value):
            if isinstance(item, str):
                buckets.append({"key": item, "label": item, "queries": []})
                continue
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or item.get("label") or "evidence").strip()
            label = str(item.get("label") or item.get("name") or key).strip()
            buckets.append(
                {
                    "key": key,
                    "label": label,
                    "queries": [str(query) for query in cls._list_value(item.get("queries")) if query],
                }
            )
        return buckets

    @staticmethod
    def _ensure_assistant_time_ranges(response: SourceDiscoveryAssistantResponse, requested_time_range: str) -> None:
        fallback_time_range = requested_time_range.strip() or "anytime"
        for suggestion in response.planning_suggestions:
            if not suggestion.time_range:
                suggestion.time_range = fallback_time_range
        if response.recommended_settings and not response.recommended_settings.time_range:
            response.recommended_settings.time_range = fallback_time_range

    @classmethod
    def _normalize_source_summary(cls, item: dict[str, Any]) -> dict[str, Any]:
        title = str(item.get("title") or item.get("url") or "Untitled source")
        normalized = {
            **item,
            "title": title,
            "source_type": str(item.get("source_type") or "news"),
            "provider": str(item.get("provider") or ""),
            "summary": str(item.get("summary") or item.get("description") or ""),
        }
        citation = item.get("citation")
        normalized["citation"] = cls._normalize_citations(citation)[0] if citation else None
        return normalized

    @classmethod
    def _normalize_timeline_item(cls, item: dict[str, Any]) -> dict[str, Any]:
        title = str(item.get("title") or item.get("summary") or "Timeline item")
        return {
            **item,
            "title": title,
            "summary": str(item.get("summary") or title),
            "citations": cls._normalize_citations(item.get("citations")),
        }

    @classmethod
    def _normalize_event_stage(cls, item: dict[str, Any]) -> dict[str, Any]:
        name = str(item.get("name") or item.get("stage") or "Event stage")
        return {
            **item,
            "name": name,
            "summary": str(item.get("summary") or name),
            "confidence": cls._normalize_confidence(item.get("confidence")),
            "citations": cls._normalize_citations(item.get("citations")),
        }

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if "high" in normalized:
            return "high"
        if "medium" in normalized or "moderate" in normalized:
            return "medium"
        return "low"

    @classmethod
    def _normalize_conflict(cls, item: dict[str, Any]) -> dict[str, Any]:
        return {
            **item,
            "summary": str(item.get("summary") or "Source conflict"),
            "sides": [str(value) for value in cls._list_value(item.get("sides")) if value],
            "citations": cls._normalize_citations(item.get("citations")),
        }

    @classmethod
    def _normalize_evidence_gap(cls, item: Any) -> dict[str, Any]:
        if isinstance(item, str):
            return {"summary": item, "follow_up_searches": []}
        if not isinstance(item, dict):
            return {"summary": str(item), "follow_up_searches": []}
        return {
            **item,
            "summary": str(item.get("summary") or "Evidence gap"),
            "follow_up_searches": [str(value) for value in cls._list_value(item.get("follow_up_searches")) if value],
        }

    def _build_search_planning_prompt(
        self,
        request: SourceDiscoveryAssistantRequest,
        crisis_case: CrisisCaseRecord,
    ) -> str:
        payload = {
            "case": {
                "id": request.case_id,
                "title": crisis_case.title,
                "description": crisis_case.description,
            },
            "form": {
                "topic": request.topic,
                "description": request.description,
                "region": request.region,
                "language": request.language,
                "time_range": request.time_range,
                "source_types": request.source_types,
                "max_sources": request.max_sources,
            },
            "question": request.question or "Help me generate source discovery search directions.",
        }
        return f"""You are a source discovery planning assistant for crisis research.

Use only the case and form context below. Do not claim facts are confirmed because no source
materials have been discovered yet. Produce search planning guidance only. Every
planning_suggestions item must include time_range. Use form.time_range unless recommending
a narrower explicit window. Do not rely on query wording alone to express recency; keep the
time limit in the structured time_range field so downstream search can apply it.

Return ONLY a JSON object with this shape:
{{
  "answer": "short advisory answer",
  "insufficient_evidence": false,
  "planning_suggestions": [
    {{
      "label": "search angle name",
      "rationale": "why this angle helps",
      "topic": "optional improved topic",
      "description": "optional improved description",
      "region": "optional region",
      "language": "optional language",
      "time_range": "optional time range",
      "source_types": ["news", "official"],
      "queries": ["concrete query"],
      "core_entities": ["entity, brand, institution, or product name"],
      "actor_names": ["person or organization name"],
      "event_aliases": ["alternate event wording"],
      "language_variants": ["same concept in another language or script"],
      "evidence_buckets": [
        {{"key": "timeline", "label": "event timeline", "queries": ["timeline-specific query"]}},
        {{"key": "official_response", "label": "official or company response", "queries": ["official-response query"]}},
        {{"key": "regulatory_context", "label": "regulatory or standards context", "queries": ["regulatory query"]}},
        {{"key": "social_evidence", "label": "original social-media evidence", "queries": ["social evidence query"]}},
        {{"key": "impact", "label": "business or public impact", "queries": ["impact query"]}}
      ]
    }}
  ],
  "timeline": [],
  "event_stages": [],
  "citations": [],
  "conflicts": [],
  "evidence_gaps": [],
  "follow_up_searches": ["query to try next"]
}}

Context:
{json.dumps(payload, ensure_ascii=False)}
"""

    def _build_search_backed_briefing_prompt(
        self,
        request: SourceDiscoveryAssistantRequest,
        crisis_case: CrisisCaseRecord | None,
        topic: str,
        description: str,
        queries: list[str],
        sources: list[dict[str, Any]],
    ) -> str:
        payload = {
            "case": {
                "id": request.case_id,
                "title": crisis_case.title if crisis_case else "",
                "description": crisis_case.description if crisis_case else "",
            },
            "briefing_request": {
                "topic": topic,
                "description": description,
                "region": request.region,
                "language": request.language,
                "time_range": request.time_range,
                "source_types": request.source_types,
                "question": request.question
                or "Create a cited preliminary event timeline and discovery briefing.",
                "queries": queries,
                "limits": self._briefing_limits().model_dump(),
            },
            "searched_sources": sources,
        }
        return f"""You are a source-grounded briefing assistant for crisis source discovery.

Use only searched_sources below. Do not use outside knowledge or browsing. The briefing is
preliminary guidance for setting up formal discovery, not verified evidence-pack material.
Every timeline item, actor, controversy focus, event stage, and factual claim must cite searched
sources. If source evidence is weak, set insufficient_evidence to true.

Return ONLY a JSON object with this shape:
{{
  "answer": "short preliminary briefing summary",
  "insufficient_evidence": false,
  "recommended_settings": {{
    "topic": "recommended discovery topic",
    "description": "recommended discovery description",
    "region": "recommended region",
    "language": "recommended language",
    "time_range": "recommended time range",
    "source_types": ["news", "official"],
    "max_sources": 12,
    "queries": ["formal discovery query"],
    "core_entities": ["entity, brand, institution, or product name"],
    "actor_names": ["person or organization name"],
    "event_aliases": ["alternate event wording"],
    "language_variants": ["same concept in another language or script"],
    "evidence_buckets": [
      {{"key": "timeline", "label": "event timeline", "queries": ["timeline-specific query"]}},
      {{"key": "official_response", "label": "official or company response", "queries": ["official-response query"]}},
      {{"key": "regulatory_context", "label": "regulatory or standards context", "queries": ["regulatory query"]}},
      {{"key": "social_evidence", "label": "original social-media evidence", "queries": ["social evidence query"]}},
      {{"key": "impact", "label": "business or public impact", "queries": ["impact query"]}}
    ]
  }},
  "source_summaries": [
    {{
      "title": "source title",
      "url": "source url or null",
      "source_type": "news|official|social|complaint|research",
      "provider": "provider",
      "published_at": "publication date or null",
      "summary": "brief source summary",
      "citation": {{"candidate_id": null, "title": "source title", "url": "source url or null", "published_at": null, "quote": "short evidence phrase"}}
    }}
  ],
  "key_actors": ["actor or institution"],
  "controversy_focus": ["controversy focus"],
  "planning_suggestions": [],
  "timeline": [
    {{
      "event_date": "event date if supported, otherwise null",
      "reporting_date": "source publication date if relevant",
      "title": "timeline point",
      "summary": "what happened",
      "citations": [{{"candidate_id": null, "title": "source title", "url": "source url or null", "published_at": null, "quote": "short evidence phrase"}}]
    }}
  ],
  "event_stages": [
    {{
      "name": "stage name",
      "summary": "stage evidence",
      "confidence": "low|medium|high",
      "citations": [{{"candidate_id": null, "title": "source title", "url": "source url or null", "published_at": null, "quote": "short evidence phrase"}}]
    }}
  ],
  "citations": [{{"candidate_id": null, "title": "source title", "url": "source url or null", "published_at": null, "quote": "short evidence phrase"}}],
  "conflicts": [],
  "evidence_gaps": [{{"summary": "missing evidence", "follow_up_searches": ["query to fill the gap"]}}],
  "follow_up_searches": ["query to try next"]
}}

Context:
{json.dumps(payload, ensure_ascii=False)}
"""

    def _build_source_interpretation_prompt(
        self,
        request: SourceDiscoveryAssistantRequest,
        discovery_job: SourceDiscoveryJobRecord,
        candidates: list[SourceCandidateRecord],
    ) -> str:
        bounded_candidates = [
            self._candidate_prompt_payload(candidate)
            for candidate in sorted(candidates, key=lambda item: item.total_score, reverse=True)[
                :_MAX_CANDIDATES_FOR_PROMPT
            ]
        ]
        payload = {
            "discovery_job": {
                "id": str(discovery_job.id),
                "case_id": str(discovery_job.case_id),
                "topic": discovery_job.topic,
                "description": discovery_job.description,
                "region": discovery_job.region,
                "language": discovery_job.language,
                "time_range": discovery_job.time_range,
                "source_types": list(discovery_job.source_types or []),
                "query_plan": list(discovery_job.query_plan or []),
            },
            "question": request.question or "Summarize the known event timeline and current stage.",
            "candidate_sources": bounded_candidates,
        }
        return f"""You are a source-grounded event interpretation assistant.

Use only the candidate_sources listed below. Do not use outside knowledge or web browsing.
For every timeline item, event stage, conflict, and factual claim, include citations using
candidate_id/title/url/published_at. Distinguish event occurrence dates from source publication
dates when the sources support that distinction. If the candidates do not support an answer,
set insufficient_evidence to true and suggest follow-up searches.

Return ONLY a JSON object with this shape:
{{
  "answer": "short grounded answer",
  "insufficient_evidence": false,
  "planning_suggestions": [],
  "timeline": [
    {{
      "event_date": "event date if supported, otherwise null",
      "reporting_date": "source publication date if relevant",
      "title": "timeline point",
      "summary": "what happened",
      "citations": [{{"candidate_id": "candidate id", "title": "source title", "url": null, "published_at": null, "quote": "short evidence phrase"}}]
    }}
  ],
  "event_stages": [
    {{
      "name": "stage name",
      "summary": "stage evidence",
      "confidence": "low|medium|high",
      "citations": [{{"candidate_id": "candidate id", "title": "source title", "url": null, "published_at": null, "quote": "short evidence phrase"}}]
    }}
  ],
  "citations": [{{"candidate_id": "candidate id", "title": "source title", "url": null, "published_at": null, "quote": "short evidence phrase"}}],
  "conflicts": [
    {{
      "summary": "conflict description",
      "sides": ["side A", "side B"],
      "citations": [{{"candidate_id": "candidate id", "title": "source title", "url": null, "published_at": null, "quote": "short evidence phrase"}}]
    }}
  ],
  "evidence_gaps": [
    {{"summary": "missing evidence", "follow_up_searches": ["query to fill the gap"]}}
  ],
  "follow_up_searches": ["query to try next"]
}}

Context:
{json.dumps(payload, ensure_ascii=False)}
"""

    @staticmethod
    def _candidate_prompt_payload(candidate: SourceCandidateRecord) -> dict[str, Any]:
        text = candidate.content or candidate.excerpt or ""
        previews = {
            "claims": list(candidate.claim_previews or [])[:4],
            "stakeholders": list(candidate.stakeholder_previews or [])[:6],
        }
        return {
            "candidate_id": str(candidate.id),
            "title": candidate.title,
            "url": candidate.url,
            "source_type": candidate.source_type,
            "published_at": str(candidate.published_at) if candidate.published_at else None,
            "provider": candidate.provider,
            "review_status": candidate.review_status.value
            if hasattr(candidate.review_status, "value")
            else str(candidate.review_status),
            "classification": candidate.classification,
            "total_score": candidate.total_score,
            "excerpt": (candidate.excerpt or "")[:_MAX_TEXT_CHARS_PER_CANDIDATE],
            "content": text[:_MAX_TEXT_CHARS_PER_CANDIDATE],
            "previews": previews,
        }

    async def _collect_briefing_sources(
        self,
        request: SourceDiscoveryAssistantRequest,
        topic: str,
        description: str,
        queries: list[str],
    ) -> list[dict[str, Any]]:
        payload = SourceDiscoveryJobPayload(
            source_discovery_job_id="briefing",
            job_id="briefing",
            case_id=request.case_id or "briefing",
            topic=topic or description[:120],
            description=description,
            region=request.region,
            language=request.language or "en",
            time_range=request.time_range,
            source_types=request.source_types or ["news", "official", "social"],
            max_sources=_BRIEFING_MAX_TOTAL_SOURCES,
        )
        seen: set[str] = set()
        sources: list[dict[str, Any]] = []
        for query in queries[:_BRIEFING_MAX_QUERIES]:
            results = await self._search_provider.search(query, payload)
            for result in results[:_BRIEFING_MAX_RESULTS_PER_QUERY]:
                content = await self._content_fetcher.fetch(result)
                dedupe_key = canonicalize_url(result.url) or hash_content(content.content or result.snippet)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                sources.append(self._briefing_source_payload(query, result, content))
                if len(sources) >= _BRIEFING_MAX_TOTAL_SOURCES:
                    return sources
        return sources

    @staticmethod
    def _briefing_source_payload(query: str, result: SearchResult, content: FetchedContent) -> dict[str, Any]:
        return {
            "source_id": hash_content(result.url or f"{result.title}:{query}")[:16],
            "query": query,
            "title": result.title,
            "url": result.url,
            "source_type": result.source_type,
            "provider": result.provider,
            "published_at": format_dt(result.published_at),
            "snippet": result.snippet[:600],
            "excerpt": (content.excerpt or "")[:600],
            "content": (content.content or result.snippet)[:_BRIEFING_MAX_CONTENT_CHARS_PER_SOURCE],
            "metadata": {
                "result": result.metadata or {},
                "fetch": content.metadata or {},
            },
        }

    @staticmethod
    def _briefing_queries(
        topic: str,
        description: str,
        request: SourceDiscoveryAssistantRequest,
    ) -> list[str]:
        region = request.region.strip()
        language = request.language.strip()
        base = " ".join(part for part in [topic, region] if part).strip() or description[:120]
        candidates = [
            f"{base} timeline",
            f"{base} latest update",
            f"{base} controversy official statement",
            f"{base} chronology key dates",
        ]
        if description:
            candidates.append(f"{topic} {description[:80]}".strip())
        if language and language.lower() not in {"en", "english"}:
            candidates.append(f"{base} {language}")
        deduped: list[str] = []
        for query in candidates:
            normalized = " ".join(query.split())
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped[:_BRIEFING_MAX_QUERIES]

    @staticmethod
    def _briefing_limits() -> SourceDiscoveryAssistantBriefingLimit:
        return SourceDiscoveryAssistantBriefingLimit(
            max_queries=_BRIEFING_MAX_QUERIES,
            max_results_per_query=_BRIEFING_MAX_RESULTS_PER_QUERY,
            max_total_sources=_BRIEFING_MAX_TOTAL_SOURCES,
            max_content_chars_per_source=_BRIEFING_MAX_CONTENT_CHARS_PER_SOURCE,
        )

    def _insufficient_candidate_response(
        self,
        discovery_job: SourceDiscoveryJobRecord,
    ) -> SourceDiscoveryAssistantResponse:
        searches = self._default_follow_up_searches(discovery_job)
        return SourceDiscoveryAssistantResponse(
            mode=SOURCE_INTERPRETATION_MODE,
            answer="There are no candidate sources available yet, so I cannot produce a grounded timeline.",
            insufficient_evidence=True,
            evidence_gaps=[
                SourceDiscoveryAssistantEvidenceGap(
                    summary="Candidate source context is empty for this discovery job.",
                    follow_up_searches=searches,
                )
            ],
            follow_up_searches=searches,
        )

    @staticmethod
    def _default_follow_up_searches(discovery_job: SourceDiscoveryJobRecord) -> list[str]:
        topic = discovery_job.topic or "event"
        region = f" {discovery_job.region}" if discovery_job.region else ""
        return [
            f"{topic}{region} timeline",
            f"{topic}{region} latest official update",
            f"{topic}{region} chronology key dates",
        ]
