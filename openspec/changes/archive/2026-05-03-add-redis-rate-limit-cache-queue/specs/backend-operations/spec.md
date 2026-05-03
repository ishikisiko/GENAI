## ADDED Requirements

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
