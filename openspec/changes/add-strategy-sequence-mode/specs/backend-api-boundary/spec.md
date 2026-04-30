## ADDED Requirements

### Requirement: Simulation API accepts strategy sequence submissions
The system SHALL expose Python API simulation submission behavior that accepts planned per-round strategy sequences for intervention runs.

#### Scenario: Frontend submits a strategy sequence run
- **WHEN** the frontend sends `POST /api/simulations` for an intervention run with a valid strategy sequence
- **THEN** the Python API validates the sequence against the submitted total rounds
- **AND** the API creates a simulation run and durable job containing the sequence payload
- **AND** the response uses the existing asynchronous simulation submission contract

#### Scenario: Frontend submits incompatible intervention fields
- **WHEN** the frontend sends `POST /api/simulations` with both a strategy sequence and legacy single-strategy injection fields
- **THEN** the Python API rejects the request with the shared product validation error envelope
- **AND** the API does not create a simulation run or durable job

#### Scenario: Frontend submits baseline with sequence fields
- **WHEN** the frontend sends `POST /api/simulations` for a baseline run with strategy sequence fields
- **THEN** the Python API rejects the request with the shared product validation error envelope
- **AND** the API does not create a simulation run or durable job
