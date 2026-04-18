## ADDED Requirements

### Requirement: Running jobs expose heartbeat liveness
The system SHALL persist heartbeat timestamps for running jobs so long-running work can prove liveness after the initial claim and before terminal completion.

#### Scenario: Worker heartbeats a running job
- **WHEN** a worker reports progress for a running job
- **THEN** the job record stores an updated heartbeat timestamp that is newer than its claim time

### Requirement: Stale running jobs are recovered by the worker system
The system SHALL detect running jobs whose heartbeat age exceeds the configured stale timeout and SHALL transition those jobs to a terminal failure state without requiring user traffic or browser cleanup.

#### Scenario: Running job becomes stale
- **WHEN** a running job has not emitted a heartbeat within the configured stale timeout
- **THEN** the worker system marks the job `failed`
- **AND** the current job attempt is closed with failure details explaining the stale timeout or interruption
