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

### Requirement: Candidate relevance scoring quality gate
The system SHALL score source candidate relevance using direct case/entity/event alignment and SHALL NOT treat generic crisis or source-discovery terms as sufficient evidence of high relevance.

#### Scenario: Candidate only matches generic discovery terms
- **WHEN** a discovered candidate matches generic words such as "incident", "social", "media", "source", "official", or "timeline" but does not match the case's core entity or event tokens
- **THEN** the candidate relevance score is capped at a low value
- **AND** the candidate does not appear highly relevant solely because it has high authority, freshness, diversity, or claim-rich content

#### Scenario: Candidate matches core case terms
- **WHEN** a discovered candidate matches core entity or event tokens from the discovery topic or case context
- **THEN** the candidate can receive a high relevance score proportional to the strength of those core matches
- **AND** exact phrase or multi-token event matches can increase the relevance score

#### Scenario: Candidate has high source quality but low relevance
- **WHEN** a candidate is from a high-authority or content-rich source but lacks direct case relevance
- **THEN** the total score remains constrained by the low relevance signal
- **AND** the candidate is ranked below directly relevant candidates with comparable quality signals

### Requirement: Hybrid candidate relevance signals
The system SHALL support combining deterministic lexical relevance with optional semantic support when scoring discovered candidates.

#### Scenario: Semantic support is available
- **WHEN** semantic fragment or embedding support is available for a discovered candidate
- **THEN** the system can use semantic support as an additional relevance signal
- **AND** semantic support does not bypass the core relevance gate for unrelated candidates

#### Scenario: Semantic support is unavailable
- **WHEN** embeddings, semantic fragments, or vector search are unavailable for a discovery run
- **THEN** the system still computes deterministic lexical relevance
- **AND** discovery job processing remains available without requiring semantic infrastructure

### Requirement: Candidate score explainability
The system SHALL keep candidate score dimensions interpretable for human review.

#### Scenario: User reviews candidate scores
- **WHEN** the user opens candidate source review
- **THEN** the candidate exposes relevance separately from authority, freshness, claim richness, diversity, grounding value, and total score
- **AND** the displayed score dimensions allow the user to distinguish direct relevance from general source quality

### Requirement: Chinese and alias-aware candidate relevance
The system SHALL score source candidate relevance for Chinese-language crisis events using core entities, event terms, and known aliases from discovery context rather than relying only on whitespace-delimited topic tokens.

#### Scenario: Chinese event title uses wording variant
- **WHEN** a discovery topic such as `西贝预制菜事件` has a candidate source titled with a variant such as `西贝预制菜风波`, `预制菜之争`, or `罗永浩吐槽西贝事件`
- **THEN** the candidate can receive direct relevance credit for matching the core entity and event meaning
- **AND** the candidate is not capped as unrelated solely because the exact topic phrase is absent

#### Scenario: Candidate lacks core Chinese event alignment
- **WHEN** a Chinese-language or bilingual candidate matches only broad words such as `事件`, `社交媒体`, `平台`, `新闻`, or `时间线`
- **THEN** the candidate relevance score remains low
- **AND** high authority, freshness, or content length does not cause the candidate to rank above directly relevant event sources

#### Scenario: Assistant planning hints provide aliases
- **WHEN** optional assistant planning context includes core entities or event aliases
- **THEN** the scorer MAY use those hints as additional deterministic relevance terms
- **AND** scoring remains available when assistant hints are absent

### Requirement: Evidence-bucketed discovery query expansion
The system SHALL generate bounded source discovery queries by evidence bucket so discovery seeks coverage across timeline, official response, regulatory context, social-media evidence, and downstream impact.

#### Scenario: Worker expands queries for a Chinese crisis event
- **WHEN** the worker processes a discovery job with Chinese core entities or event aliases
- **THEN** it generates labeled queries for event timeline, official response, regulatory or standards context, original social-media evidence, and impact or consequence evidence within backend-owned limits
- **AND** the query plan remains persisted for operator and review visibility

#### Scenario: Social-media evidence is requested
- **WHEN** a discovery job requests social source types or social-media evidence
- **THEN** generated queries combine the event's core entities or aliases with platform, original-post, or author terms
- **AND** generic pages about social-media platforms alone are not treated as satisfying event-specific social evidence

#### Scenario: Query limits are enforced
- **WHEN** evidence buckets produce more query candidates than the backend limit allows
- **THEN** the system deduplicates and truncates the query plan deterministically
- **AND** discovery processing remains bounded for the configured search provider

### Requirement: Formal discovery excludes mock and low-evidence generic candidates
The system SHALL prevent mock, test, and low-evidence generic background pages from appearing as high-quality formal discovery candidates when real source discovery is expected.

#### Scenario: Real provider discovery encounters mock results
- **WHEN** a source discovery job is configured to use a real search provider
- **AND** a candidate URL or provider metadata identifies a mock or test source
- **THEN** the system excludes the candidate from formal candidate ranking or marks it with low review value
- **AND** the candidate does not appear as a high-scoring source

#### Scenario: Candidate is generic background material
- **WHEN** a candidate describes a broad platform, industry, or background topic without matching the event's core entities or aliases
- **THEN** the system gives the candidate low relevance and low grounding value
- **AND** directly relevant event sources rank above it by default

#### Scenario: Mock provider is explicitly configured
- **WHEN** the backend is configured with the deterministic mock search provider
- **THEN** mock candidates remain available for local development and tests
- **AND** they are identifiable through provider or metadata fields

### Requirement: Conservative source classification
The system SHALL classify discovered candidates using conservative source-type rules so official, media, social, and research classifications reflect the source itself rather than quoted claims inside the source.

#### Scenario: Media article quotes official statements
- **WHEN** a media article mentions regulators, official statements, company responses, or government standards
- **THEN** the system classifies the candidate as media or news unless the source domain or provider metadata identifies the page as an official source
- **AND** the authority score reflects the candidate's classified source type

#### Scenario: Official source is discovered
- **WHEN** a candidate comes from a government, regulator, company-owned, or otherwise verified official publication channel
- **THEN** the system can classify the candidate as official
- **AND** quoted media coverage is not required for official classification

#### Scenario: Social or discussion source is discovered
- **WHEN** a candidate comes from a social platform, discussion forum, creator post, or user-generated source
- **THEN** the system can classify the candidate as social
- **AND** social classification does not depend on the page merely containing the words `social` or `media`
