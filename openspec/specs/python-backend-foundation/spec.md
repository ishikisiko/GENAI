# python-backend-foundation Specification

## Purpose
TBD - created by archiving change bootstrap-python-backend-foundation. Update Purpose after archive.
## Requirements
### Requirement: Python backend workspace and entrypoints
The repository SHALL provide a dedicated Python backend workspace that contains a shared application package and separate runtime entrypoints for the API process and the worker process.

#### Scenario: Backend workspace is initialized
- **WHEN** the backend foundation is created
- **THEN** the repository contains a Python backend workspace with API and worker entrypoints that import shared application modules rather than duplicating runtime code

### Requirement: Shared runtime conventions
The Python backend SHALL centralize configuration loading, structured logging, and application error modeling in shared modules that are used consistently by both API and worker runtimes.

#### Scenario: Service starts with invalid configuration
- **WHEN** a required backend setting is missing or malformed at startup
- **THEN** the service fails fast before reporting readiness and emits a structured startup error

### Requirement: Database access layer
The Python backend SHALL provide a database access layer that owns connection management, transaction boundaries, and reusable data access primitives for service code and worker code.

#### Scenario: API and worker use shared database primitives
- **WHEN** an API handler and a worker execution path both need database access
- **THEN** they obtain database connectivity through the shared backend data access layer instead of opening ad hoc connections in feature code

### Requirement: Supabase responsibility boundary
The backend foundation SHALL retain Supabase as the owning platform for Postgres, Auth, and RLS, and SHALL treat Supabase Realtime as optional infrastructure rather than a required dependency of the backend runtime.

#### Scenario: Backend architecture is evaluated
- **WHEN** the new Python backend foundation is introduced
- **THEN** Postgres persistence, authentication, and row-level security remain assigned to Supabase
- **AND** the backend foundation does not require Realtime to provide core API or job execution behavior

### Requirement: Shared product request context
The Python backend SHALL apply one shared request-context layer to all product-facing API endpoints that assigns request correlation data, applies the configured auth rule, and exposes that context to downstream handlers and logs.

#### Scenario: Product request enters the Python API
- **WHEN** a request targets a product-facing Python API endpoint
- **THEN** the backend establishes a shared request context before business logic runs
- **AND** that context includes request-correlation data and auth-derived request metadata

### Requirement: Operator endpoints use a separate boundary
The Python backend SHALL keep health and operational endpoints on an explicit operator boundary that is configured separately from product-facing business endpoints.

#### Scenario: Operator checks service health
- **WHEN** an operator calls a health or operations endpoint
- **THEN** the request is handled through the operator boundary rather than the product endpoint flow
- **AND** the endpoint does not rely on product-specific business handlers to serve that request

### Requirement: Uniform product error payloads
The Python backend SHALL return product-facing errors through a shared envelope that includes a stable error code, a human-readable message, structured details, and request-correlation data.

#### Scenario: Product endpoint returns an application error
- **WHEN** a Python API product endpoint fails with a handled application error
- **THEN** the response uses the shared error envelope
- **AND** the response includes request-correlation data that matches backend logs for the same request
