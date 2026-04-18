## ADDED Requirements

### Requirement: Python-owned agent generation submission
The system SHALL provide a Python API endpoint that accepts agent-generation requests for a crisis case without requiring the frontend to invoke a Supabase Edge Function.

#### Scenario: Valid agent-generation request is submitted
- **WHEN** the frontend submits an agent-generation request for an existing case
- **THEN** the request is handled by the Python API
- **AND** the backend validates the target case before running generation

### Requirement: Agent generation completes synchronously
The system SHALL execute agent generation within the request lifecycle and SHALL return completion results directly when successful.

#### Scenario: Agent generation succeeds
- **WHEN** the Python API completes agent generation successfully
- **THEN** the response includes the generated agent result needed by the caller
- **AND** the caller does not need to poll a job endpoint for completion

### Requirement: Agent persistence remains compatible with the simulation handoff
The system SHALL persist generated agents using the existing agent-profile data model and SHALL update the case state needed for the simulation flow to continue.

#### Scenario: Generated agents are persisted
- **WHEN** the Python API finishes a successful agent-generation request
- **THEN** the case's generated agent profiles are written using the existing persistence model
- **AND** the case is marked ready for the next simulation step using the existing case-status semantics

### Requirement: Agent-generation failures avoid partial success signaling
The system SHALL report agent-generation failures through the shared product error contract and SHALL NOT signal the case as ready for simulation when generation does not complete successfully.

#### Scenario: Agent generation fails before completion
- **WHEN** agent generation encounters a validation, dependency, or model-execution failure
- **THEN** the API returns a product error response
- **AND** the case is not advanced to a ready-for-simulation state by that failed request
