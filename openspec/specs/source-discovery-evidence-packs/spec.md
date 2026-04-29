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

### Requirement: Reviewed discovery candidates can enter the source registry
The system SHALL allow user-confirmed discovery candidates to be saved into the global source registry with a selected topic assignment or as Unassigned, without automatically promoting all discovered candidates.

#### Scenario: User saves an accepted candidate to a topic collection
- **WHEN** a user explicitly saves an accepted source candidate to the source registry and selects a source topic
- **THEN** the system creates or reuses the corresponding global source record using canonical URL or content hash matching
- **AND** the system creates a source-topic assignment for the selected topic
- **AND** the assignment preserves the candidate, discovery job, provider, score, and assignment reason metadata needed for traceability

#### Scenario: User saves an accepted candidate as Unassigned
- **WHEN** a user explicitly saves an accepted source candidate to the source registry without selecting a topic
- **THEN** the system creates or reuses the corresponding global source record
- **AND** the source appears in the Unassigned smart view until a topic assignment is added

#### Scenario: Candidate remains local to discovery flow
- **WHEN** a user accepts a source candidate for evidence pack creation but does not save it to the source registry
- **THEN** evidence pack creation remains available
- **AND** the candidate is not added to the global source registry solely because it was accepted

#### Scenario: Rejected candidate is not promoted
- **WHEN** a source candidate has a rejected review status
- **THEN** the system does not offer it as an automatic source registry promotion
- **AND** no global source or topic assignment is created from that rejection

### Requirement: Source discovery assistant frontend integration
The system SHALL expose the source discovery assistant from source discovery setup and candidate source review without bypassing existing human review controls.

#### Scenario: User opens source discovery setup
- **WHEN** the user opens `SourceDiscoverySetupPage` for a crisis case
- **THEN** the page provides access to the assistant in search planning mode
- **AND** the assistant can use the current case title, case description, topic, description, region, language, time range, and selected source types as planning context
- **AND** assistant suggestions require explicit user action before changing discovery form fields or creating a source discovery job

#### Scenario: User reviews discovered candidates
- **WHEN** the user opens `CandidateSourcesReviewPage` for a discovery job
- **THEN** the page provides access to the assistant in source interpretation mode
- **AND** the assistant can use the discovery job settings and current candidate sources as grounding context
- **AND** the page displays assistant citations in a way that lets the user identify the supporting candidate sources

#### Scenario: Assistant does not replace review controls
- **WHEN** the assistant provides timeline, stage, conflict, evidence-gap, or follow-up-search guidance
- **THEN** candidate accept and reject controls remain the only way to change candidate review status
- **AND** evidence pack creation remains available only through the existing explicit evidence pack action

### Requirement: Search-backed briefing frontend integration
The system SHALL expose search-backed briefing from source discovery setup as a user-triggered assistant action.

#### Scenario: User opens source discovery setup
- **WHEN** the user opens `SourceDiscoverySetupPage`
- **THEN** the page provides a distinct action to request a search-backed initial briefing
- **AND** the page distinguishes search-backed briefing from non-search search planning guidance
- **AND** the page does not automatically run briefing before the user triggers that action

#### Scenario: Briefing results are displayed
- **WHEN** search-backed briefing completes
- **THEN** the page displays preliminary timeline, key actors, stage summary, source citations, evidence gaps, follow-up searches, and recommended discovery settings when present
- **AND** citations identify the searched sources used by the briefing

#### Scenario: Recommended settings are applied
- **WHEN** the user applies briefing recommendations to the discovery form
- **THEN** the form fields update from the selected recommendation
- **AND** the page does not create a source discovery job until the user submits the existing discovery form
