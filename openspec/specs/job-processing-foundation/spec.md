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

### Requirement: Optional Redis Streams job dispatch
The system SHALL support optional Redis Streams dispatch for worker-owned jobs while preserving Postgres `jobs` and `job_attempts` as the canonical durable lifecycle.

#### Scenario: Job is created while Redis Streams dispatch is enabled
- **WHEN** application code creates a worker-owned durable job
- **THEN** the system persists the job in Postgres before publishing a Redis Stream message
- **AND** the stream message contains the durable job identifier and job type required for a worker to claim the job

#### Scenario: Worker receives a Redis Stream message
- **WHEN** a worker consumes a Redis Stream message for a job
- **THEN** the worker claims the referenced job through the existing Postgres job lifecycle
- **AND** execution proceeds only if the Postgres claim succeeds

#### Scenario: Worker completes a Redis-dispatched job
- **WHEN** a worker completes or fails a Redis-dispatched job
- **THEN** the worker records the result in the canonical Postgres job and attempt records
- **AND** the worker acknowledges the Redis Stream message only after the Postgres state update succeeds

#### Scenario: Redis Stream message is delivered more than once
- **WHEN** Redis redelivers a message for a job that is already running, completed, failed, or cancelled in Postgres
- **THEN** the worker does not execute duplicate domain work for that message
- **AND** the worker handles the message according to the canonical Postgres job state

### Requirement: Postgres polling fallback remains available
The system SHALL retain Postgres polling as a fallback dispatch mode for worker-owned jobs.

#### Scenario: Redis dispatch is disabled
- **WHEN** Redis Streams dispatch is disabled by configuration
- **THEN** workers claim pending jobs using the existing Postgres polling behavior
- **AND** durable job status reporting remains unchanged

#### Scenario: Redis dispatch is unavailable in optional mode
- **WHEN** Redis Streams dispatch is enabled but Redis is unavailable and Redis is configured as optional
- **THEN** workers continue processing jobs through Postgres polling
- **AND** the backend emits structured degraded-dispatch telemetry

### Requirement: Redis-dispatched jobs preserve attempt history
The system SHALL preserve the existing attempt-history semantics for jobs that are dispatched through Redis Streams.

#### Scenario: Redis-dispatched job is claimed
- **WHEN** a worker successfully claims a Redis-dispatched pending job
- **THEN** the system creates a `job_attempts` row linked to that job
- **AND** the attempt records worker identity, attempt number, start time, and eventual completion or failure details

#### Scenario: Redis-dispatched job is retried
- **WHEN** retry logic or an operator requeues a failed Redis-dispatched job
- **THEN** the job transitions through the canonical Postgres state machine
- **AND** the next execution creates a new `job_attempts` row instead of mutating prior attempt history
