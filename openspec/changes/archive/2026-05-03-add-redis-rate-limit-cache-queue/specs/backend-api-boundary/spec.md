## ADDED Requirements

### Requirement: Expensive product endpoints are rate limited
The system SHALL apply backend-owned rate limiting to expensive product API endpoints that can trigger worker jobs or external LLM/search work.

#### Scenario: Simulation submission is rate limited
- **WHEN** a caller sends `POST /api/simulations`
- **THEN** the Python API evaluates the request against the configured simulation submission rate limit before creating a durable job
- **AND** requests within the limit continue to use the existing asynchronous simulation submission contract

#### Scenario: Agent generation is rate limited
- **WHEN** a caller sends `POST /api/agent-generation`
- **THEN** the Python API evaluates the request against the configured agent generation rate limit before calling the LLM-backed generation service
- **AND** requests within the limit continue to return the existing synchronous domain response

#### Scenario: Source discovery job creation is rate limited
- **WHEN** a caller sends `POST /api/source-discovery/jobs`
- **THEN** the Python API evaluates the request against the configured source discovery submission rate limit before creating discovery records or durable jobs
- **AND** requests within the limit continue to use the existing source discovery submission contract

#### Scenario: Source discovery assistant is rate limited
- **WHEN** a caller sends `POST /api/source-discovery/assistant`
- **THEN** the Python API evaluates the request against the configured assistant rate limit before running LLM, search, or content-fetch work
- **AND** requests within the limit continue to use the existing assistant response contract

### Requirement: Rate-limit failures use product error envelope
The system SHALL expose rate-limit rejections through the shared product API error envelope.

#### Scenario: Protected endpoint exceeds rate limit
- **WHEN** a protected product API request exceeds the configured rate limit
- **THEN** the Python API returns HTTP 429
- **AND** the response includes a stable machine-readable error code
- **AND** the response includes request correlation data for troubleshooting
- **AND** no durable job, source discovery job, simulation run, evidence pack, or grounding workflow is created as a side effect of the rejected request

#### Scenario: Rate-limit response includes retry guidance
- **WHEN** the Python API rejects a request because of rate limiting
- **THEN** the response or headers include retry timing guidance derived from the active rate-limit window when available
