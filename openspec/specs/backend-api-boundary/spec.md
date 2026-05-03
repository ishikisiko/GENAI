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

### Requirement: Source discovery assistant API endpoint
The system SHALL expose Python API contracts for bounded source discovery assistant requests and structured assistant responses.

#### Scenario: Search planning request is submitted
- **WHEN** the frontend sends a source discovery assistant request in search planning mode with case and discovery form context
- **THEN** the Python API returns a structured assistant response containing planning guidance, suggested search directions, and any form-applicable suggestions
- **AND** the response does not require the frontend to call an LLM provider directly
- **AND** the request does not create a source discovery job unless the user later submits the existing source discovery form

#### Scenario: Source interpretation request is submitted
- **WHEN** the frontend sends a source discovery assistant request in source interpretation mode for a discovery job
- **THEN** the Python API assembles grounding context from the current discovery job and its candidate sources
- **AND** the Python API returns a structured assistant response containing answer text and any available timeline items, event stages, source conflicts, evidence gaps, follow-up search directions, and citations
- **AND** successful completion does not require the frontend to query Supabase, an LLM provider, an embedding provider, or a vector index directly

#### Scenario: Assistant request fails
- **WHEN** a source discovery assistant request fails because the mode is invalid, required context is missing, the discovery job is not found, LLM configuration is unavailable, or the LLM request fails
- **THEN** the Python API returns the shared product error envelope with a stable machine-readable error code, human-readable message, and request correlation data

### Requirement: Search-backed briefing API contract
The system SHALL expose Python API behavior for search-backed source briefing without requiring the frontend to call search, content fetch, LLM, or storage providers directly.

#### Scenario: Search-backed briefing request is submitted
- **WHEN** the frontend sends a source discovery assistant request in search-backed briefing mode with topic or case context
- **THEN** the Python API executes bounded search and content gathering through backend-owned providers
- **AND** the Python API returns a structured briefing response with citations, preliminary timeline, source summaries, evidence gaps, follow-up searches, and recommended discovery settings when available
- **AND** the response does not require the frontend to call an external search provider, content fetcher, LLM provider, or database directly

#### Scenario: Briefing request is invalid
- **WHEN** a search-backed briefing request is missing topic and case context, asks for unsupported limits, or references invalid mode data
- **THEN** the Python API returns the shared product error envelope with a stable validation error code and request correlation data

#### Scenario: Briefing request completes
- **WHEN** a search-backed briefing request completes successfully
- **THEN** the API does not create a source discovery job, source candidate, evidence pack, graph extraction job, or simulation run as a side effect

### Requirement: Simulation API accepts strategy sequence submissions
The system SHALL expose Python API simulation submission behavior that accepts planned per-round strategy sequences for intervention runs.

#### Scenario: Frontend submits a strategy sequence run
- **WHEN** the frontend sends `POST /api/simulations` for an intervention run with a valid strategy sequence
- **THEN** the Python API validates the sequence against the submitted total rounds
- **AND** the API creates a simulation run and durable job containing the sequence payload
- **AND** the response uses the existing asynchronous simulation submission contract

#### Scenario: Frontend submits incompatible intervention fields
- **WHEN** the frontend sends `POST /api/simulations` with both a strategy sequence and legacy single-strategy injection fields
- **THEN** the Python API rejects the request with the shared product validation error envelope
- **AND** the API does not create a simulation run or durable job

#### Scenario: Frontend submits baseline with sequence fields
- **WHEN** the frontend sends `POST /api/simulations` for a baseline run with strategy sequence fields
- **THEN** the Python API rejects the request with the shared product validation error envelope
- **AND** the API does not create a simulation run or durable job

### Requirement: Expensive product endpoints are rate limited
The system SHALL apply backend-owned rate limiting to expensive product API endpoints that can trigger worker jobs or external LLM/search work.

#### Scenario: Simulation submission is rate limited
- **WHEN** a caller sends `POST /api/simulations`
- **THEN** the Python API evaluates the request against the configured simulation submission rate limit before creating a durable job
- **AND** requests within the limit continue to use the existing asynchronous simulation submission contract

#### Scenario: Agent generation is rate limited
- **WHEN** a caller sends `POST /api/agent-generation`
- **THEN** the Python API evaluates the request against the configured agent generation rate limit before calling the LLM-backed generation service
- **AND** requests within the limit continue to return the existing synchronous domain response

#### Scenario: Source discovery job creation is rate limited
- **WHEN** a caller sends `POST /api/source-discovery/jobs`
- **THEN** the Python API evaluates the request against the configured source discovery submission rate limit before creating discovery records or durable jobs
- **AND** requests within the limit continue to use the existing source discovery submission contract

#### Scenario: Source discovery assistant is rate limited
- **WHEN** a caller sends `POST /api/source-discovery/assistant`
- **THEN** the Python API evaluates the request against the configured assistant rate limit before running LLM, search, or content-fetch work
- **AND** requests within the limit continue to use the existing assistant response contract

### Requirement: Rate-limit failures use product error envelope
The system SHALL expose rate-limit rejections through the shared product API error envelope.

#### Scenario: Protected endpoint exceeds rate limit
- **WHEN** a protected product API request exceeds the configured rate limit
- **THEN** the Python API returns HTTP 429
- **AND** the response includes a stable machine-readable error code
- **AND** the response includes request correlation data for troubleshooting
- **AND** no durable job, source discovery job, simulation run, evidence pack, or grounding workflow is created as a side effect of the rejected request

#### Scenario: Rate-limit response includes retry guidance
- **WHEN** the Python API rejects a request because of rate limiting
- **THEN** the response or headers include retry timing guidance derived from the active rate-limit window when available
