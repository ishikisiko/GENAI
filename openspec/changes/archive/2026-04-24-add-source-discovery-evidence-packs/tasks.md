## 1. Database and Domain Model

- [x] 1.1 Add backend migration for `source_discovery_jobs`, `source_candidates`, `evidence_packs`, and `evidence_pack_sources` with indexes, foreign keys, status constraints, score columns, and provenance fields.
- [x] 1.2 Mirror required Supabase local schema/RLS changes for any discovery or evidence-pack tables read by the frontend during local demo flows.
- [x] 1.3 Add SQLAlchemy domain records and enums for discovery jobs, candidate review states, evidence packs, and evidence pack sources.
- [x] 1.4 Add metadata/linkage support so materialized `source_documents` can be traced back to evidence pack sources without breaking existing extraction consumers.

## 2. Backend Contracts and Repository

- [x] 2.1 Add Pydantic request/response contracts for source discovery job creation/status, candidate list/update, evidence pack creation, and evidence-pack grounding startup.
- [x] 2.2 Add repository methods for creating discovery jobs, writing candidates, listing candidates sorted by total score, updating review status, creating evidence packs, and loading pack sources.
- [x] 2.3 Add repository methods to materialize evidence pack sources into case-local `source_documents` while preserving candidate and pack metadata.
- [x] 2.4 Ensure repository operations validate crisis case ownership and reject cross-case candidate or evidence-pack combinations.

## 3. Source Discovery Pipeline

- [x] 3.1 Define replaceable interfaces for query expansion, `SearchProvider`, content fetch, deduplication, classification, scoring, and preview extraction.
- [x] 3.2 Implement a deterministic mock `SearchProvider` and content fetcher suitable for local development and tests.
- [x] 3.3 Implement scoring dimensions for relevance, authority, freshness, claim richness, diversity, and grounding value, including derived total score ordering.
- [x] 3.4 Implement worker pipeline execution that expands queries, searches, fetches, deduplicates, classifies, scores, extracts claim/stakeholder previews, and writes source candidates.
- [x] 3.5 Update discovery job aggregate counts and failure details consistently with the canonical job lifecycle.

## 4. API and Worker Wiring

- [x] 4.1 Add `POST /api/source-discovery/jobs` and `GET /api/source-discovery/jobs/{job_id}` routes to the Python API.
- [x] 4.2 Add `GET /api/source-candidates` and `PATCH /api/source-candidates/{source_id}` routes to the Python API.
- [x] 4.3 Add `POST /api/evidence-packs` and `POST /api/evidence-packs/{evidence_pack_id}/start-grounding` routes to the Python API.
- [x] 4.4 Register the `source_discovery.run` worker handler in `build_worker`.
- [x] 4.5 Wire evidence-pack grounding startup to materialize documents and submit the existing graph extraction workflow without starting simulation.

## 5. Frontend Integration

- [x] 5.1 Add TypeScript types and backend API helpers for discovery jobs, source candidates, evidence packs, and evidence-pack grounding responses.
- [x] 5.2 Add routes for `SourceDiscoverySetupPage`, `CandidateSourcesReviewPage`, and `EvidencePackPreviewPage` under the crisis case workflow.
- [x] 5.3 Implement `SourceDiscoverySetupPage` with topic, description, region, language, time range, source types, and max source controls.
- [x] 5.4 Implement `CandidateSourcesReviewPage` with polling, score display, preview display, and accept/reject controls.
- [x] 5.5 Implement `EvidencePackPreviewPage` with confirmed source metadata and an explicit start-grounding action.
- [x] 5.6 Add navigation entry points from case documents or grounding flow without removing the existing manual document upload path.

## 6. Tests and Verification

- [x] 6.1 Add backend tests for source discovery job creation and invalid case rejection.
- [x] 6.2 Add backend tests for worker candidate writing, deduplication, and deterministic mock provider behavior.
- [x] 6.3 Add backend tests for score dimension persistence and descending total score ordering.
- [x] 6.4 Add backend tests for candidate review updates and evidence pack creation from accepted candidates only.
- [x] 6.5 Add backend tests for evidence-pack grounding startup, document materialization, metadata preservation, and graph extraction job submission.
- [x] 6.6 Add focused frontend tests or type/build verification for the new pages and API helpers.
- [x] 6.7 Run backend test suite and frontend build/lint checks relevant to the changed code.
