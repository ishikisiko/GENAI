## Context

CrisisSim currently creates a crisis case, lets users add or reuse source documents, and then starts Python-owned graph extraction through the existing asynchronous job system. The frontend still writes some document data directly through Supabase, but backend-owned product workflows are expected to use the Python API. Worker-owned flows already share the `jobs` and `job_attempts` lifecycle and GraphRAG grounding reads case-local `source_documents`.

The requested source discovery module spans storage, API, worker orchestration, search/fetch/provider abstractions, candidate review UI, and grounding integration. The design therefore keeps discovery as a separate workflow until the user explicitly confirms candidate sources and starts grounding.

## Goals / Non-Goals

**Goals:**
- Let users create topic-based discovery jobs for an existing crisis case.
- Persist discovery request parameters, discovered candidates, scoring dimensions, evidence packs, and selected pack sources.
- Execute discovery asynchronously in the existing Python worker model.
- Support a mock first search provider through a replaceable `SearchProvider` interface.
- Preserve a human confirmation step before evidence pack creation and before grounding.
- Convert evidence pack sources into grounding documents with source provenance metadata intact.
- Add focused backend and frontend surfaces without changing simulation startup semantics.

**Non-Goals:**
- Automatic simulation launch after source discovery or grounding.
- Real-time streaming search status; polling the job/status surfaces is sufficient for the first version.
- Production-grade crawling of arbitrary websites, paywall bypassing, or advanced PDF/media extraction.
- Ranking model training or external credibility databases.
- Replacing the existing manual document upload/global library flow.

## Decisions

### Reuse the existing durable job lifecycle

Source discovery will create a row in `jobs` with job type `source_discovery.run` and a linked row in `source_discovery_jobs` for domain status, request parameters, and aggregate counts. The worker registers a handler for `source_discovery.run`, and job status remains observable through the canonical job APIs.

Alternative considered: a separate scheduler/table lifecycle only for discovery. That would duplicate retry, claim, and failure semantics already solved by `jobs` and make worker operations harder to reason about.

### Keep discovery domain records separate from source documents

Candidates remain in `source_candidates` until the user selects them. Evidence packs are represented by `evidence_packs` and `evidence_pack_sources`; only when grounding starts are selected pack sources materialized as `source_documents` for the existing extraction pipeline.

Alternative considered: write every discovered item directly into `source_documents`. That would pollute case grounding inputs with unreviewed sources and violate the human-in-the-loop requirement.

### Preserve provenance in metadata while staying compatible with existing documents

Evidence-pack grounding will create case-local `source_documents` using the existing fields required by extraction, and will retain discovery metadata through either explicit source-document metadata columns introduced in the migration or a companion mapping from `evidence_pack_sources` to generated `source_document_id`. The extraction service continues to receive document IDs and does not need to understand the discovery provider.

Alternative considered: teach graph extraction to read directly from `evidence_pack_sources`. That creates a second document input path and increases the chance that future extraction behavior diverges between manual and discovered sources.

### Use provider interfaces with deterministic mock defaults

Discovery pipeline stages are implemented behind small interfaces: query expansion, search provider, content fetcher, classifier, scorer, and preview extractor. The first implementation can use deterministic local/mock search results so tests and demos run without external credentials. Search provider configuration can later switch to a real provider without changing API contracts.

Alternative considered: hard-code a real provider in the first version. That would slow local development, require secrets, and make basic tests brittle.

### Score candidates as structured dimensions plus total score

Each candidate stores `relevance`, `authority`, `freshness`, `claim_richness`, `diversity`, and `grounding_value`, plus a derived `total_score`. Listing endpoints sort by total score by default while exposing dimensions so the UI can explain why a candidate is recommended.

Alternative considered: store only one score. That would simplify sorting but make review less transparent and make future ranking changes harder to test.

## Risks / Trade-offs

- External content fetches may fail or return low-quality text -> Store fetch status/error metadata, keep candidates with degraded previews when useful, and let users reject them.
- Mock provider can mask real provider edge cases -> Keep provider contracts explicit and test the service against interface-level fixtures.
- Dedupe can merge distinct but similar sources -> Use canonical URL plus content fingerprint and retain duplicate references in candidate metadata when available.
- Evidence pack materialization can duplicate existing case documents -> Check existing global/source document links and content fingerprints before insertion where practical.
- Scoring can imply false precision -> Treat dimensions as review aids, expose the values, and keep user confirmation mandatory.
- New tables need both backend migrations and Supabase local schema alignment -> Add migrations in the backend migration path and mirror RLS/demo policies where the frontend still reads relevant tables directly.

## Migration Plan

1. Add database migration for discovery/evidence-pack tables, indexes, foreign keys, status constraints, and source metadata/linkage needed for provenance.
2. Add backend domain models and repositories before wiring routes.
3. Add contracts and services with mock provider defaults and deterministic scoring tests.
4. Register API routes and worker handler.
5. Add frontend API helpers, types, routes, and pages.
6. Roll out with mock provider enabled by default; real providers can be added behind configuration later.

Rollback is additive: disable frontend routes and worker handler, then leave the new tables unused. Existing case creation, manual document upload, grounding, and simulation paths continue to work.

## Open Questions

- Which real search provider should be configured first after the mock implementation: Tavily, SerpAPI, Bing, or another provider?
- Should evidence pack previews support manual content edits before grounding, or only source accept/reject decisions in the first version?
- Should discovered sources also be promoted to the global source library after user confirmation, or remain case-local unless explicitly saved later?
