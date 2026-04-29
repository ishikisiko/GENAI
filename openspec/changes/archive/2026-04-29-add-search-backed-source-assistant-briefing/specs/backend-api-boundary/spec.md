## ADDED Requirements

### Requirement: Search-backed briefing API contract
The system SHALL expose Python API behavior for search-backed source briefing without requiring the frontend to call search, content fetch, LLM, or storage providers directly.

#### Scenario: Search-backed briefing request is submitted
- **WHEN** the frontend sends a source discovery assistant request in search-backed briefing mode with topic or case context
- **THEN** the Python API executes bounded search and content gathering through backend-owned providers
- **AND** the Python API returns a structured briefing response with citations, preliminary timeline, source summaries, evidence gaps, follow-up searches, and recommended discovery settings when available
- **AND** the response does not require the frontend to call an external search provider, content fetcher, LLM provider, or database directly

#### Scenario: Briefing request is invalid
- **WHEN** a search-backed briefing request is missing topic and case context, asks for unsupported limits, or references invalid mode data
- **THEN** the Python API returns the shared product error envelope with a stable validation error code and request correlation data

#### Scenario: Briefing request completes
- **WHEN** a search-backed briefing request completes successfully
- **THEN** the API does not create a source discovery job, source candidate, evidence pack, graph extraction job, or simulation run as a side effect
