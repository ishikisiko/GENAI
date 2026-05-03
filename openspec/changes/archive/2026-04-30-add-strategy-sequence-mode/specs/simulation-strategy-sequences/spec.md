## ADDED Requirements

### Requirement: Intervention runs can use a planned strategy sequence
The system SHALL allow an intervention simulation run to define a planned sequence of per-round strategies before execution starts.

#### Scenario: User submits a valid strategy sequence
- **WHEN** a user submits an intervention simulation with one or more valid sequence steps within the configured total rounds
- **THEN** the system creates a simulation run containing the planned strategy sequence
- **AND** the run is executed by the existing asynchronous simulation workflow

#### Scenario: Sequence includes rounds without interventions
- **WHEN** a strategy sequence omits a round within the configured total rounds
- **THEN** the simulator treats that round as a no-op intervention round
- **AND** the round is still simulated using the narrative state from prior rounds

### Requirement: Strategy sequence validation
The system SHALL validate planned strategy sequences before creating a simulation run or durable job.

#### Scenario: Sequence step references an invalid round
- **WHEN** a sequence step has a round number lower than 1 or greater than the submitted total rounds
- **THEN** the system rejects the submission with a validation error
- **AND** no simulation run or durable job is created

#### Scenario: Sequence has duplicate round steps
- **WHEN** multiple sequence steps target the same round number
- **THEN** the system rejects the submission with a validation error
- **AND** no simulation run or durable job is created

#### Scenario: Sequence step omits strategy type
- **WHEN** a sequence step is present without a valid strategy type
- **THEN** the system rejects the submission with a validation error
- **AND** no simulation run or durable job is created

### Requirement: Sequence execution records applied strategies per round
The worker SHALL apply the configured strategy for each sequence step during the matching round and record the applied strategy in the round result.

#### Scenario: Worker reaches a planned strategy round
- **WHEN** the worker simulates a round that has a configured sequence step
- **THEN** the prompt includes the strategy type and message for that round
- **AND** the persisted round state records the strategy as applied for that round

#### Scenario: Worker simulates after prior sequence steps
- **WHEN** the worker simulates a round after one or more sequence strategies have already been issued
- **THEN** the prompt includes bounded context that prior public responses may have ongoing effects
- **AND** the worker continues to evolve the narrative from the previous round state

### Requirement: Existing single-strategy interventions remain supported
The system SHALL continue to support intervention runs that use a single strategy and injection round without requiring a strategy sequence.

#### Scenario: User submits a legacy single-strategy intervention
- **WHEN** a user submits an intervention simulation with `strategy_type` and `injection_round` but no strategy sequence
- **THEN** the system validates and executes the run using the existing single-injection behavior
- **AND** downstream result readers can compare it with baseline and sequence runs
