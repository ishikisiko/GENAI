## ADDED Requirements

### Requirement: Source library topic API endpoints
The system SHALL expose Python API endpoints for source topics, topic assignments, source registry listing, smart views, source usage, and case source selection operations.

#### Scenario: Source topics are managed through the API
- **WHEN** the frontend creates, updates, lists, or fetches source topics
- **THEN** the frontend sends the request to Python API source-library topic endpoints
- **AND** the response includes the topic identifiers and fields needed for topic-first library navigation

#### Scenario: Source topic assignment is updated through the API
- **WHEN** the frontend assigns a global source to a topic or removes a source from a topic
- **THEN** the frontend sends the request to a Python API endpoint
- **AND** the API persists the assignment change with relevance, reason, and assignment provenance when provided

#### Scenario: Source registry is queried through the API
- **WHEN** the frontend requests source library results by topic, smart view, metadata filter, or text query
- **THEN** the frontend sends the request to a Python API source registry endpoint
- **AND** the API returns matching global sources with topic assignment summaries, duplicate/status metadata, and case usage counts needed by the UI

#### Scenario: Case source selection is queried through the API
- **WHEN** the frontend opens source selection for a crisis case
- **THEN** the frontend sends the request to a Python API case source selection endpoint
- **AND** the API returns Recommended for this case, Same topic collections, Related collections, Global search entry data, and already-in-case markers

#### Scenario: Global source is attached to a case through the API
- **WHEN** the frontend requests that a reusable global source be added to a crisis case
- **THEN** the frontend sends the request to a Python API endpoint
- **AND** the API creates the case-local source document snapshot or rejects a duplicate attachment with a stable product error

#### Scenario: Source usage is fetched through the API
- **WHEN** the frontend requests usage details for a reusable source
- **THEN** the Python API returns topic assignment information and linked crisis case usage derived from case-local source documents
