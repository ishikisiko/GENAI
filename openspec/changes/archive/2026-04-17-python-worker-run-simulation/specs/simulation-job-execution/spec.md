## ADDED Requirements

### Requirement: Simulation submission creates a durable run and job
The system SHALL expose an API submission path for simulation execution that validates the request, enforces the active-run concurrency policy for the case, creates a `simulation_runs` record, creates a durable background job for that run, and returns identifiers for both resources without waiting for the simulation to finish.

#### Scenario: Client submits a baseline simulation
- **WHEN** a client submits a valid baseline simulation request through the new API
- **THEN** the system creates a `simulation_runs` row for that request
- **AND** the system creates a durable background job linked to that run
- **AND** the response includes the created `run_id`, `job_id`, job status, and run status

#### Scenario: Another active run already exists for the case
- **WHEN** a client submits a new simulation request for a case that already has an active simulation run under the rollout policy
- **THEN** the system rejects the submission
- **AND** the system does not create a second active simulation job for that case

### Requirement: Worker execution preserves simulation result semantics
The worker SHALL execute simulation jobs round by round using the existing simulation business logic and SHALL continue writing `simulation_runs`, `round_states`, and `metric_snapshots` with semantics compatible with current downstream readers.

#### Scenario: Worker processes a claimed simulation job
- **WHEN** a worker starts executing a claimed simulation job
- **THEN** the linked `simulation_runs` row transitions to `running`
- **AND** each completed round writes the expected `round_states` and `metric_snapshots` records for that run
- **AND** downstream consumers can continue reading the result tables without requiring a new schema

### Requirement: Simulation terminal state is projected from worker outcomes
The system SHALL project worker execution outcomes onto the linked simulation run so that run status remains the product-facing source of truth for whether a simulation is pending, running, completed, or failed.

#### Scenario: Simulation completes successfully
- **WHEN** the worker finishes the final round without error
- **THEN** the linked `simulation_runs` row is marked `completed`
- **AND** the run records a completion timestamp

#### Scenario: Simulation execution fails
- **WHEN** the worker encounters a terminal execution error for a simulation job
- **THEN** the linked `simulation_runs` row is marked `failed`
- **AND** the run stores an error message describing the failure

### Requirement: Clients can poll job and run status
The system SHALL provide polling-friendly status interfaces for both the durable job and the linked simulation run so the frontend can track progress without holding open the original submission request.

#### Scenario: Client queries job status
- **WHEN** a client requests the status of a simulation job
- **THEN** the system returns the canonical job status and failure metadata safe for client polling
- **AND** the response identifies the linked simulation run

#### Scenario: Client queries simulation run status
- **WHEN** a client requests the status of a simulation run that was submitted asynchronously
- **THEN** the system returns the current run status
- **AND** the response includes enough progress information for the client to decide whether to continue polling or reload full run results

### Requirement: Legacy synchronous execution remains available during rollout
The system SHALL retain the existing synchronous `run-simulation` path for a temporary migration window so operators can roll back or selectively gate traffic while the new worker-backed path is validated.

#### Scenario: Rollout is reverted
- **WHEN** the rollout control is switched back to the legacy execution path
- **THEN** new simulation requests can continue to use the legacy synchronous flow
- **AND** existing async-created simulation records remain readable for investigation
