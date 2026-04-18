# job-processing-foundation Specification

## Purpose
TBD - created by archiving change bootstrap-python-backend-foundation. Update Purpose after archive.
## Requirements
### Requirement: Durable job records
The system SHALL persist asynchronous work in a `jobs` table that stores a durable job identifier, job type, canonical status, execution payload, scheduling metadata, and aggregate attempt information.

#### Scenario: A job is created for asynchronous execution
- **WHEN** application code creates a new background task
- **THEN** a row is persisted in `jobs` with status `pending`
- **AND** the row contains the metadata required for a worker to identify and execute the task later

### Requirement: Attempt history is preserved
The system SHALL persist each execution run of a job in a `job_attempts` table that references the parent job and captures worker identity, start time, end time, per-attempt status, and failure details when present.

#### Scenario: A worker claims a job
- **WHEN** a worker transitions a job from `pending` to `running`
- **THEN** the system creates a new `job_attempts` row linked to that job
- **AND** the attempt records which worker claimed the job and when execution started

### Requirement: Canonical job state machine
The system SHALL support the job statuses `pending`, `running`, `completed`, `failed`, and `cancelled`, and SHALL restrict job transitions to the allowed lifecycle defined by the backend foundation.

#### Scenario: A job completes successfully
- **WHEN** a worker finishes a running job without error
- **THEN** the job transitions from `running` to `completed`
- **AND** the active attempt is marked complete with an end timestamp

#### Scenario: A running job fails
- **WHEN** a worker encounters an execution failure while processing a running job
- **THEN** the job transitions from `running` to `failed`
- **AND** the active attempt stores the failure outcome and diagnostic details

#### Scenario: A failed job is retried
- **WHEN** retry logic or an operator requeues a failed job
- **THEN** the job transitions from `failed` to `pending`
- **AND** the next execution creates a new `job_attempts` row instead of mutating prior attempt history

### Requirement: Worker-safe claiming semantics
The system SHALL coordinate job claiming through transactional database behavior so that only one worker can successfully claim a given pending job for a given attempt.

#### Scenario: Two workers race to claim the same job
- **WHEN** multiple workers try to claim the same `pending` job concurrently
- **THEN** at most one worker succeeds in transitioning that job to `running`
- **AND** at most one corresponding `job_attempts` row is created for that claim cycle

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

### Requirement: Standard async submission response
The system SHALL return a consistent submission response for job-backed product workflows that identifies the durable job and the status surfaces the caller can use next.

#### Scenario: Caller submits an async workflow
- **WHEN** the API accepts a job-backed product workflow such as simulation or graph extraction
- **THEN** the response identifies the durable job created for that workflow
- **AND** the response identifies the status surface or surfaces the caller can use to observe progress

### Requirement: Durable jobs are reserved for worker-owned or long-running work
The system SHALL create durable jobs only for workflows that require worker-owned or long-running execution rather than for bounded synchronous operations.

#### Scenario: Bounded operation is invoked
- **WHEN** a product workflow can complete within the request lifecycle without worker ownership
- **THEN** the system does not create a durable job for that request
- **AND** the operation completes through the synchronous API contract instead
