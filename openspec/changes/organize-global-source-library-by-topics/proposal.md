## Why

The current Global Source Library is a flat, time-sorted document list, which will become hard to navigate as multiple crisis cases, discovery topics, manual uploads, and evidence packs accumulate. Sources need durable topic context and reuse metadata so users can find relevant evidence by case/topic intent instead of browsing an undifferentiated repository.

## What Changes

- Introduce topic/collection organization for reusable global sources, including hierarchical topics, assignment reasons, assignment provenance, and relevance scores.
- Extend global source metadata so reusable sources can carry canonical URL/content hash dedupe fields, source kind, authority/freshness/status fields, and update timestamps.
- Add source-library smart views for unassigned sources, recently used sources, high-authority sources, duplicate candidates, and stale sources.
- Preserve case-local source snapshots when a global source is attached to a case so later global edits do not change already selected or grounded case evidence.
- Change case source selection so it defaults to case-relevant recommendations, same-topic collections, related collections, global search, and manual upload rather than showing the entire global library first.
- Allow user-confirmed discovery candidates to be assigned to a topic collection or routed to Unassigned without automatically promoting all discovered candidates into the global repository.
- Add source usage visibility so users can see which cases and topics already use a reusable source.

## Capabilities

### New Capabilities
- `source-library-topics`: Topic/collection organization, reusable source metadata, source-topic assignments, source smart views, case source selection, usage visibility, and case-local snapshot behavior for global source reuse.

### Modified Capabilities
- `backend-api-boundary`: Add Python API endpoints for source topic, source registry, topic assignment, smart view, and case source selection operations that are part of the product workflow.
- `source-discovery-evidence-packs`: Let user-confirmed discovery candidates be assigned to topic collections or Unassigned while preserving human review and avoiding automatic promotion of all candidates.

## Impact

- Database: add topic and assignment tables; extend global source and case source document metadata; add dedupe, status, and usage indexes.
- Backend: add repositories, service contracts, API routes, validation, dedupe helpers, and source selection query surfaces.
- Frontend: update Global Source Library into a topic-first registry view; update Case Documents source selection into recommended/topic/global/manual sections; surface assignment, usage, status, and duplicate indicators.
- Existing flows: manual upload, global library selection, source discovery, evidence pack creation, and evidence pack grounding remain available and continue to use case-local source documents for grounding.
