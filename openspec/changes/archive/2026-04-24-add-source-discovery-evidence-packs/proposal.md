## Why

CrisisSim currently depends on users manually pasting or selecting source documents before grounding, which makes new crisis cases slow to prepare and easy to under-source. Adding topic-based source discovery gives users a guided way to find, review, and curate evidence while preserving the existing human-confirmed path into GraphRAG grounding.

## What Changes

- Add a source discovery workflow that accepts topic, description, region, language, time range, source types, and max source count after a crisis case is created.
- Persist source discovery jobs, source candidates, evidence packs, and evidence-pack source selections in dedicated tables.
- Add Python API endpoints for discovery job creation/status, candidate listing/update, evidence pack creation, and evidence-pack grounding startup.
- Add a worker-owned discovery pipeline with query expansion, pluggable search provider calls, content fetch, deduplication, classification, scoring, preview extraction, and candidate persistence.
- Add frontend pages for discovery setup, candidate review, and evidence pack preview.
- Keep a required human-in-the-loop review step: candidates do not become an evidence pack, and evidence packs do not enter simulation, until the user explicitly confirms sources and starts grounding.
- Integrate evidence packs with the existing grounding path by converting confirmed evidence pack sources into source documents with source metadata preserved.

## Capabilities

### New Capabilities
- `source-discovery-evidence-packs`: Covers topic-based source discovery requests, candidate lifecycle, scoring, evidence pack creation, human confirmation, and evidence pack preview behavior.

### Modified Capabilities
- `backend-api-boundary`: Adds Python API routes for source discovery, source candidate review, evidence pack creation, and starting grounding from an evidence pack.
- `job-processing-foundation`: Adds durable source discovery jobs as a worker-owned job type that uses the existing canonical job lifecycle.
- `graph-extraction-pipeline`: Allows evidence pack sources to be materialized as document inputs for the existing grounding pipeline while retaining source metadata.

## Impact

- Backend: new SQLAlchemy models, migrations, repository/service/contract modules, worker handler, and FastAPI routes.
- Database: new tables `source_discovery_jobs`, `source_candidates`, `evidence_packs`, and `evidence_pack_sources`, plus metadata fields or source-document linkage needed to preserve provenance.
- Frontend: new routes and pages for setup, candidate review, and evidence pack preview, using the Python API instead of direct Edge Function calls.
- Tests: backend API/service tests for job creation, candidate writes, scoring sort order, evidence pack generation, and grounding startup; focused frontend coverage where existing test tooling supports it.
- Dependencies: first implementation may use a mock search provider behind a replaceable `SearchProvider` interface, avoiding required external search credentials.
