## ADDED Requirements

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
