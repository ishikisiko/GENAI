## ADDED Requirements

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
