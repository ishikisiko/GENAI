## ADDED Requirements

### Requirement: Source discovery assistant API endpoint
The system SHALL expose Python API contracts for bounded source discovery assistant requests and structured assistant responses.

#### Scenario: Search planning request is submitted
- **WHEN** the frontend sends a source discovery assistant request in search planning mode with case and discovery form context
- **THEN** the Python API returns a structured assistant response containing planning guidance, suggested search directions, and any form-applicable suggestions
- **AND** the response does not require the frontend to call an LLM provider directly
- **AND** the request does not create a source discovery job unless the user later submits the existing source discovery form

#### Scenario: Source interpretation request is submitted
- **WHEN** the frontend sends a source discovery assistant request in source interpretation mode for a discovery job
- **THEN** the Python API assembles grounding context from the current discovery job and its candidate sources
- **AND** the Python API returns a structured assistant response containing answer text and any available timeline items, event stages, source conflicts, evidence gaps, follow-up search directions, and citations
- **AND** successful completion does not require the frontend to query Supabase, an LLM provider, an embedding provider, or a vector index directly

#### Scenario: Assistant request fails
- **WHEN** a source discovery assistant request fails because the mode is invalid, required context is missing, the discovery job is not found, LLM configuration is unavailable, or the LLM request fails
- **THEN** the Python API returns the shared product error envelope with a stable machine-readable error code, human-readable message, and request correlation data
