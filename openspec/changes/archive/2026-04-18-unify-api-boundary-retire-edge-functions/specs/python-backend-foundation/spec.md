## ADDED Requirements

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
