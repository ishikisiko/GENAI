# source-discovery-evidence-packs Specification

## Purpose
TBD - created by archiving change add-source-discovery-evidence-packs. Update Purpose after archive.
## Requirements
### Requirement: Topic-based source discovery job creation
The system SHALL allow a user to create a source discovery job for an existing crisis case using topic, description, region, language, time range, source types, and max source count.

#### Scenario: User submits discovery settings
- **WHEN** the user submits valid discovery settings for an existing crisis case
- **THEN** the system persists a `source_discovery_jobs` record linked to the case
- **AND** the system stores the submitted topic, description, region, language, time range, source types, and max source count
- **AND** the system creates the worker-owned job needed to process discovery asynchronously

#### Scenario: User submits discovery settings for a missing case
- **WHEN** the user submits discovery settings for a crisis case that does not exist
- **THEN** the system rejects the request
- **AND** no source discovery job or candidate sources are created

### Requirement: Source discovery pipeline
The system SHALL process each source discovery job through query expansion, search provider calls, content fetch, deduplication, source classification, source scoring, claim preview extraction, stakeholder preview extraction, and candidate persistence.

#### Scenario: Worker processes a discovery job
- **WHEN** a worker claims a pending source discovery job
- **THEN** the worker expands one or more search queries from the submitted topic and description
- **AND** the worker calls a configured `SearchProvider`
- **AND** the worker fetches candidate content when available
- **AND** the worker deduplicates candidates before persistence
- **AND** the worker classifies, scores, and extracts preview data before writing candidates

#### Scenario: Mock provider is configured
- **WHEN** the system is configured without real search provider credentials
- **THEN** the discovery pipeline uses a deterministic mock search provider
- **AND** the API and worker contracts remain the same as they would for a real provider

### Requirement: Source candidate persistence and scoring
The system SHALL persist discovered source candidates with review status, source metadata, classification, preview fields, score dimensions, and total score.

#### Scenario: Candidate is written after discovery
- **WHEN** the discovery worker accepts a deduplicated candidate
- **THEN** the system writes a `source_candidates` record linked to the source discovery job and case
- **AND** the candidate includes title, URL when available, source type, language, region, published time when available, fetched content or excerpt, provider metadata, and preview metadata
- **AND** the candidate includes score dimensions for relevance, authority, freshness, claim richness, diversity, and grounding value
- **AND** the candidate includes a derived total score used for default ranking

#### Scenario: Candidates are listed for review
- **WHEN** the user opens candidate review for a discovery job or case
- **THEN** the system returns candidates sorted by total score descending by default
- **AND** the user can inspect score dimensions and extracted claim and stakeholder previews

### Requirement: Candidate human review
The system SHALL require user review before a candidate can become part of an evidence pack.

#### Scenario: User accepts or rejects a candidate
- **WHEN** the user updates a candidate review decision
- **THEN** the system persists the candidate review status
- **AND** the candidate remains linked to its original discovery job and case

#### Scenario: Evidence pack creation is requested without accepted candidates
- **WHEN** the user requests an evidence pack from a discovery job that has no accepted candidates
- **THEN** the system rejects evidence pack creation
- **AND** no evidence pack sources are created

### Requirement: Evidence pack creation
The system SHALL create evidence packs only from user-confirmed source candidates.

#### Scenario: User creates an evidence pack from accepted candidates
- **WHEN** the user confirms one or more accepted source candidates for an existing crisis case
- **THEN** the system creates an `evidence_packs` record linked to the case
- **AND** the system creates `evidence_pack_sources` records for the confirmed candidates
- **AND** the evidence pack records preserve source metadata, score dimensions, source content or excerpt, and preview data needed for review and grounding

### Requirement: Human-in-the-loop grounding control
The system SHALL NOT automatically start grounding or simulation after source discovery or evidence pack creation.

#### Scenario: Discovery job completes
- **WHEN** a source discovery job finishes successfully
- **THEN** the system makes candidates available for review
- **AND** the system does not create an evidence pack automatically
- **AND** the system does not start grounding or simulation automatically

#### Scenario: Evidence pack is created
- **WHEN** an evidence pack is created from confirmed candidates
- **THEN** the system makes the evidence pack available for preview
- **AND** the system does not start grounding or simulation until the user explicitly starts grounding

### Requirement: Source discovery frontend flow
The system SHALL provide frontend pages for discovery setup, candidate source review, and evidence pack preview within the crisis case workflow.

#### Scenario: User configures discovery
- **WHEN** the user opens `SourceDiscoverySetupPage` for a crisis case
- **THEN** the page allows the user to submit topic, description, region, language, time range, source types, and max source count
- **AND** the page starts a source discovery job through the Python API

#### Scenario: User reviews candidates
- **WHEN** the user opens `CandidateSourcesReviewPage` for a completed or running discovery job
- **THEN** the page displays source candidates with review controls, classifications, score dimensions, and preview data
- **AND** the page allows the user to accept or reject candidates before evidence pack creation

#### Scenario: User previews evidence pack
- **WHEN** the user opens `EvidencePackPreviewPage`
- **THEN** the page displays evidence pack sources and preserved metadata
- **AND** the page provides an explicit action to start grounding from the evidence pack

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
