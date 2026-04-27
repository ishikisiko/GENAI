# backend-api-boundary Specification

## Purpose
Define the canonical product-facing Python API contract for synchronous operations, asynchronous job-backed workflows, product error envelopes, request tracing, and temporary compatibility-layer behavior.
## Requirements
### Requirement: Python API is the primary product backend contract
The system SHALL route frontend-owned business operations through Python API endpoints rather than direct frontend calls to Supabase Edge Functions.

#### Scenario: Frontend triggers a product workflow
- **WHEN** a user action in the frontend starts a backend-owned business operation
- **THEN** the frontend sends that request to a Python API endpoint
- **AND** successful completion does not require the frontend to call a Supabase Edge Function directly

### Requirement: Synchronous operations return final domain results directly
The system SHALL treat bounded request-scoped operations as synchronous API calls that return final domain results without creating durable background jobs.

#### Scenario: Synchronous product operation succeeds
- **WHEN** the frontend calls a synchronous Python API operation
- **THEN** the response contains the final domain result needed by the UI
- **AND** the caller does not need to poll a job endpoint to observe completion

### Requirement: Asynchronous operations use a standard job-backed contract
The system SHALL expose long-running or worker-owned product workflows through a standard asynchronous submission contract that returns durable job metadata and status references.

#### Scenario: Long-running workflow is submitted
- **WHEN** the frontend submits a job-backed product workflow
- **THEN** the API returns a durable `job_id`
- **AND** the response includes a canonical job-status reference
- **AND** the response includes any domain-specific status reference required by the UI

### Requirement: Product API failures include stable error and request-tracing data
The system SHALL expose product API failures through a shared error envelope and SHALL include request correlation data that can be used to match client-visible failures with backend logs.

#### Scenario: Product API request fails
- **WHEN** a Python API product endpoint returns an error
- **THEN** the response includes a stable machine-readable error code
- **AND** the response includes a human-readable message
- **AND** the response includes request correlation data for troubleshooting

### Requirement: Compatibility layers are explicit and temporary
The system SHALL classify any retained legacy Edge Function path as a compatibility layer with documented rollback purpose and removal criteria.

#### Scenario: Legacy Edge Function remains after Python API cutover
- **WHEN** a Supabase Edge Function path is retained after the Python API path is available
- **THEN** that function is documented as compatibility-only rather than the primary product path
- **AND** the system defines the rollback purpose or removal condition for that function

### Requirement: Source discovery API endpoints
The system SHALL expose Python API endpoints for creating and observing source discovery jobs, listing and updating source candidates, creating evidence packs, and starting grounding from an evidence pack.

#### Scenario: Source discovery job is created through the API
- **WHEN** the frontend sends `POST /api/source-discovery/jobs` with a valid crisis case and discovery settings
- **THEN** the Python API returns the source discovery job identifier
- **AND** the response includes the linked durable job identifier and status references needed for polling
- **AND** successful completion does not require calling a Supabase Edge Function

#### Scenario: Source discovery job status is fetched
- **WHEN** the frontend sends `GET /api/source-discovery/jobs/{job_id}`
- **THEN** the Python API returns the source discovery job status, canonical job status, request settings, candidate counts, and polling guidance

#### Scenario: Source candidates are listed
- **WHEN** the frontend sends `GET /api/source-candidates` with a case or discovery job filter
- **THEN** the Python API returns matching source candidates with review status, metadata, preview data, and score dimensions

#### Scenario: Source candidate review status is updated
- **WHEN** the frontend sends `PATCH /api/source-candidates/{source_id}` with a valid review decision
- **THEN** the Python API persists the review decision
- **AND** the response returns the updated candidate

#### Scenario: Evidence pack is created
- **WHEN** the frontend sends `POST /api/evidence-packs` with a crisis case and selected or accepted candidate identifiers
- **THEN** the Python API creates an evidence pack from user-confirmed candidates
- **AND** the response returns the evidence pack identifier and source count

#### Scenario: Evidence pack grounding is started
- **WHEN** the frontend sends `POST /api/evidence-packs/{evidence_pack_id}/start-grounding`
- **THEN** the Python API materializes evidence pack sources as document inputs
- **AND** the Python API starts the existing graph extraction grounding workflow
- **AND** the response returns the graph extraction job status references

### Requirement: Source library topic API endpoints
The system SHALL expose Python API endpoints for source topics, topic assignments, source registry listing, smart views, source usage, and case source selection operations.

#### Scenario: Source topics are managed through the API
- **WHEN** the frontend creates, updates, lists, or fetches source topics
- **THEN** the frontend sends the request to Python API source-library topic endpoints
- **AND** the response includes the topic identifiers and fields needed for topic-first library navigation

#### Scenario: Source topic assignment is updated through the API
- **WHEN** the frontend assigns a global source to a topic or removes a source from a topic
- **THEN** the frontend sends the request to a Python API endpoint
- **AND** the API persists the assignment change with relevance, reason, and assignment provenance when provided

#### Scenario: Source registry is queried through the API
- **WHEN** the frontend requests source library results by topic, smart view, metadata filter, or text query
- **THEN** the frontend sends the request to a Python API source registry endpoint
- **AND** the API returns matching global sources with topic assignment summaries, duplicate/status metadata, and case usage counts needed by the UI

#### Scenario: Case source selection is queried through the API
- **WHEN** the frontend opens source selection for a crisis case
- **THEN** the frontend sends the request to a Python API case source selection endpoint
- **AND** the API returns Recommended for this case, Same topic collections, Related collections, Global search entry data, and already-in-case markers

#### Scenario: Global source is attached to a case through the API
- **WHEN** the frontend requests that a reusable global source be added to a crisis case
- **THEN** the frontend sends the request to a Python API endpoint
- **AND** the API creates the case-local source document snapshot or rejects a duplicate attachment with a stable product error

#### Scenario: Source usage is fetched through the API
- **WHEN** the frontend requests usage details for a reusable source
- **THEN** the Python API returns topic assignment information and linked crisis case usage derived from case-local source documents

### Requirement: Semantic source recommendation API contract
The system SHALL expose Python API response contracts for semantically supported source recommendations without requiring the frontend to call storage or vector-index services directly.

#### Scenario: Case source recommendations are requested
- **WHEN** the frontend requests source recommendations for a crisis case through the Python API
- **THEN** the response includes source recommendation records with source identity, source scope, source metadata, semantic support when available, matched fragment previews when available, ranking reasons, and already-attached status
- **AND** successful completion does not require the frontend to query Supabase, an embedding provider, or a vector index directly

#### Scenario: Semantic recall is unavailable
- **WHEN** the frontend requests source recommendations and semantic recall cannot be applied
- **THEN** the Python API returns recommendations using existing non-semantic selection behavior
- **AND** the response includes a machine-readable indication that semantic recall was not applied

#### Scenario: Recommendation includes candidate source content
- **WHEN** a source recommendation is based on candidate source content
- **THEN** the Python API response preserves candidate identity and review status
- **AND** the response does not represent the candidate as attached to the case or accepted into an evidence pack unless the existing human review workflow has confirmed it
