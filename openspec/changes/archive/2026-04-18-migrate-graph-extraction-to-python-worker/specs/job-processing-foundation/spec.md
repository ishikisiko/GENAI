## ADDED Requirements

### Requirement: API-created graph extraction jobs
The system SHALL represent each `extract-graph` request as a durable job created by the API with the payload required for a worker to identify the target extraction inputs and execute the graph extraction pipeline later.

#### Scenario: API accepts an extraction request
- **WHEN** the API receives a valid `extract-graph` request
- **THEN** it persists a durable job for graph extraction instead of executing the extraction flow inline
- **AND** the job payload contains the identifiers or references needed for the worker to load the requested documents

### Requirement: Job lifecycle backs extraction status reporting
The system SHALL use the canonical job lifecycle to report graph extraction progress and outcome to callers and required UI status surfaces.

#### Scenario: Extraction job progresses asynchronously
- **WHEN** a graph extraction job moves through pending, running, completed, or failed states
- **THEN** callers and required UI surfaces observe extraction progress through that canonical job state
- **AND** they do not depend on the API process keeping the extraction execution in memory
