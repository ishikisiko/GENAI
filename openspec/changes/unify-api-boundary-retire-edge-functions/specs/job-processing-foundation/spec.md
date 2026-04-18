## ADDED Requirements

### Requirement: Standard async submission response
The system SHALL return a consistent submission response for job-backed product workflows that identifies the durable job and the status surfaces the caller can use next.

#### Scenario: Caller submits an async workflow
- **WHEN** the API accepts a job-backed product workflow such as simulation or graph extraction
- **THEN** the response identifies the durable job created for that workflow
- **AND** the response identifies the status surface or surfaces the caller can use to observe progress

### Requirement: Durable jobs are reserved for worker-owned or long-running work
The system SHALL create durable jobs only for workflows that require worker-owned or long-running execution rather than for bounded synchronous operations.

#### Scenario: Bounded operation is invoked
- **WHEN** a product workflow can complete within the request lifecycle without worker ownership
- **THEN** the system does not create a durable job for that request
- **AND** the operation completes through the synchronous API contract instead
