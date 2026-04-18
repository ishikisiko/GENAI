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
