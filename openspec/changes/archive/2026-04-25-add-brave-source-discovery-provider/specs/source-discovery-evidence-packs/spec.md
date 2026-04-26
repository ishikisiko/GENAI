## ADDED Requirements

### Requirement: Configured Brave source discovery provider
The system SHALL support Brave Search as a configurable real search provider for source discovery jobs while retaining mock discovery for local and unconfigured environments.

#### Scenario: Worker uses Brave Search when configured
- **WHEN** the backend is configured with `SOURCE_DISCOVERY_SEARCH_PROVIDER=brave` and a valid `BRAVE_SEARCH_API_KEY`
- **THEN** the source discovery worker calls the Brave web search API for expanded discovery queries
- **AND** discovered candidates persist with `provider` set to `brave`
- **AND** Brave result metadata is preserved in `provider_metadata`

#### Scenario: Brave provider respects subscription rate limit
- **WHEN** one source discovery job issues multiple Brave searches
- **THEN** the backend spaces Brave API requests so no more than one request is sent per second by the provider process

#### Scenario: Mock provider remains available
- **WHEN** the backend is configured with `SOURCE_DISCOVERY_SEARCH_PROVIDER=mock`
- **THEN** source discovery uses the deterministic mock search provider
- **AND** no Brave API key is required

#### Scenario: Brave connectivity can be verified
- **WHEN** an operator configures a Brave API key for local backend usage
- **THEN** the project provides a non-secret-leaking way to verify that the backend can reach Brave Search and map at least one result
