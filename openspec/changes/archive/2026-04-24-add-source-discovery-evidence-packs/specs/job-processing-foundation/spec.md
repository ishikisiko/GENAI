## ADDED Requirements

### Requirement: API-created source discovery jobs
The system SHALL represent each accepted source discovery request as a durable worker-owned job using the existing canonical job lifecycle.

#### Scenario: API accepts a source discovery request
- **WHEN** the API receives a valid source discovery request
- **THEN** it persists a durable job with a source discovery job type
- **AND** it persists a linked `source_discovery_jobs` domain record
- **AND** the job payload contains the identifiers and parameters required for a worker to execute source discovery later

#### Scenario: Worker claims a source discovery job
- **WHEN** a worker claims a pending source discovery job
- **THEN** the worker uses the existing job attempt tracking, heartbeat, completion, failure, and retry behavior
- **AND** the source discovery domain status remains consistent with the canonical job lifecycle
