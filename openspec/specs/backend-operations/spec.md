# backend-operations Specification

## Purpose
TBD - created by archiving change bootstrap-python-backend-foundation. Update Purpose after archive.
## Requirements
### Requirement: Liveness endpoint
The backend API SHALL expose a liveness endpoint that confirms the process is running without requiring dependency checks.

#### Scenario: Process liveness is checked
- **WHEN** an operator or orchestration platform calls the liveness endpoint
- **THEN** the backend returns a successful liveness response if the process is up

### Requirement: Readiness endpoint
The backend API SHALL expose a readiness endpoint that reports whether the service can safely serve traffic based on critical dependency health, including database availability.

#### Scenario: Database dependency is unavailable
- **WHEN** the readiness endpoint is called while the backend cannot reach its required database dependency
- **THEN** the backend returns a non-ready response
- **AND** the response indicates the service is not safe to receive traffic

### Requirement: Basic operational introspection
The backend API SHALL expose a basic operations surface for low-risk runtime inspection, such as service version data or aggregate job counts, without disclosing secrets or raw job payload bodies.

#### Scenario: Operator inspects backend runtime
- **WHEN** an operator calls the basic operations endpoint
- **THEN** the backend returns operational metadata that is safe for routine inspection
- **AND** the response omits secrets, credentials, and raw task payload contents

### Requirement: Structured failure signaling
The backend SHALL report health and operational failures using the shared backend error and logging conventions so that readiness failures and worker issues can be correlated consistently.

#### Scenario: Readiness check fails
- **WHEN** the backend determines that a readiness dependency is degraded
- **THEN** the API response reflects the failure
- **AND** the backend emits a structured log entry describing the degraded dependency and failure context

### Requirement: Redis readiness reporting
The backend API SHALL report Redis readiness according to whether Redis-backed features are disabled, optional, or required.

#### Scenario: Redis is disabled
- **WHEN** the readiness endpoint is called and Redis support is disabled
- **THEN** readiness is not blocked by Redis availability
- **AND** Redis is reported as disabled in operational status surfaces

#### Scenario: Redis is required and unavailable
- **WHEN** the readiness endpoint is called while Redis is configured as required and cannot be reached
- **THEN** the backend returns a non-ready response
- **AND** the response indicates the service is not safe to receive traffic

#### Scenario: Redis is optional and unavailable
- **WHEN** the readiness endpoint is called while Redis is configured as optional and cannot be reached
- **THEN** readiness remains governed by required dependencies such as the database
- **AND** Redis degraded state is visible through the operations surface

### Requirement: Redis operations metadata is safe for inspection
The backend SHALL include Redis-related operational metadata without disclosing secrets, credentials, cached payloads, or raw stream message bodies.

#### Scenario: Operator inspects operations endpoint
- **WHEN** an operator calls the basic operations endpoint
- **THEN** the response includes Redis enablement, requirement mode, availability, and feature usage summary when available
- **AND** the response omits Redis credentials, raw connection URLs, cache values, and stream payload bodies

#### Scenario: Redis-backed feature is degraded
- **WHEN** a Redis-backed feature enters fallback behavior
- **THEN** the operations surface exposes a non-secret degraded indicator for that feature
- **AND** structured logs can be correlated with request IDs or worker IDs when available
