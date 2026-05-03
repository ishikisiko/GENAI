## ADDED Requirements

### Requirement: Redis configuration and client boundary
The system SHALL provide typed Redis configuration and a shared mockable Redis client boundary for rate limiting, caching, stream dispatch, health checks, and tests.

#### Scenario: Redis is disabled for local development
- **WHEN** Redis support is disabled by configuration
- **THEN** the backend starts without opening a Redis connection
- **AND** Redis-backed protections and caches use documented fallback behavior

#### Scenario: Redis is enabled
- **WHEN** Redis support is enabled with a valid Redis URL
- **THEN** backend runtime code accesses Redis through the shared client boundary
- **AND** feature code does not instantiate third-party Redis clients directly

#### Scenario: Tests need deterministic Redis behavior
- **WHEN** unit tests exercise Redis-backed rate limiting, caching, or streams
- **THEN** the system can use a fake or in-memory Redis-compatible test boundary
- **AND** tests do not require a network Redis service unless explicitly marked as integration tests

### Requirement: Redis-backed rate limiting
The system SHALL support shared Redis-backed rate limiting for expensive backend product operations.

#### Scenario: Request is within the configured limit
- **WHEN** a caller invokes a protected endpoint below the configured route and identity limit
- **THEN** the request proceeds to the existing endpoint behavior
- **AND** the rate-limit counter is recorded with an expiration window

#### Scenario: Request exceeds the configured limit
- **WHEN** a caller invokes a protected endpoint above the configured route and identity limit
- **THEN** the backend rejects the request with HTTP 429
- **AND** the response uses the shared product error envelope with request correlation data

#### Scenario: Redis is unavailable in optional mode
- **WHEN** Redis-backed rate limiting cannot reach Redis and Redis is configured as optional
- **THEN** the request is allowed to continue
- **AND** the backend emits structured degraded-protection telemetry

### Requirement: Redis TTL cache for external dependency calls
The system SHALL support Redis TTL caching for deterministic LLM JSON responses, search-provider responses, and fetched page content.

#### Scenario: Cache entry exists
- **WHEN** a cacheable external dependency request has a valid Redis cache entry
- **THEN** the backend returns the cached response without calling the external provider
- **AND** the caller-visible domain contract remains unchanged

#### Scenario: Cache entry is missing
- **WHEN** a cacheable external dependency request does not have a valid Redis cache entry
- **THEN** the backend calls the configured external provider
- **AND** the backend stores the successful response using a configured TTL

#### Scenario: Cache key is built
- **WHEN** the backend stores or reads an external dependency cache entry
- **THEN** the cache key includes a feature prefix, version, provider identity, normalized request parameters, and a hash of variable prompt or URL content
- **AND** the key does not contain raw secrets or full sensitive payloads

#### Scenario: Redis cache is unavailable
- **WHEN** Redis caching is enabled but Redis cannot complete the cache operation in optional mode
- **THEN** the backend falls back to the external provider path
- **AND** the cache failure does not change the product API response shape

### Requirement: Redis operational visibility
The system SHALL expose non-secret Redis status for operational inspection.

#### Scenario: Operator checks Redis status
- **WHEN** an operator calls the backend operations surface
- **THEN** the response indicates whether Redis is disabled, available, or degraded
- **AND** the response does not include Redis credentials or raw connection strings

#### Scenario: Redis operation fails
- **WHEN** a Redis-backed rate-limit, cache, stream, or health operation fails
- **THEN** the backend emits a structured log entry with operation type, degraded mode, and request or worker correlation data when available
- **AND** the log entry does not include Redis credentials or cached payload bodies
