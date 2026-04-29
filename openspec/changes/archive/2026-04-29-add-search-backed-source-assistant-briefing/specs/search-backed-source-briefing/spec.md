## ADDED Requirements

### Requirement: User-confirmed search-backed briefing
The system SHALL provide a search-backed briefing mode that runs only after an explicit user action and returns preliminary event context grounded in searched sources.

#### Scenario: User requests an initial briefing
- **WHEN** the user requests a search-backed briefing from source discovery setup with a topic or description
- **THEN** the system runs a bounded first-pass source search through configured backend providers
- **AND** the system returns a preliminary briefing without creating a source discovery job
- **AND** the briefing is marked as preliminary guidance for discovery setup

#### Scenario: User has not requested briefing
- **WHEN** the user edits topic, description, region, language, time range, or source type fields
- **THEN** the system does not automatically run search-backed briefing
- **AND** no search provider calls are made solely because form fields changed

### Requirement: Bounded search execution
The system SHALL enforce backend-owned limits for search-backed briefing execution.

#### Scenario: Briefing search is executed
- **WHEN** the backend executes a search-backed briefing request
- **THEN** it limits the number of generated queries, results per query, total fetched sources, fetched content length, and request duration
- **AND** the frontend cannot override those limits with unbounded values

#### Scenario: Search provider is unavailable
- **WHEN** the configured search provider, content fetcher, or LLM provider cannot complete the briefing
- **THEN** the API returns a stable product error
- **AND** no source discovery job, candidate source, evidence pack, grounding job, or simulation run is created

### Requirement: Cited preliminary event brief
The system SHALL produce a structured preliminary event brief with citations to searched sources when evidence is available.

#### Scenario: Search returns enough source evidence
- **WHEN** searched sources contain enough evidence for an initial event brief
- **THEN** the response includes answer text, cited timeline items, key actors, controversy focus, likely event stage, cited source summaries, evidence gaps, follow-up searches, and recommended discovery settings
- **AND** timeline and event-stage claims cite supporting sources
- **AND** the response distinguishes source publication dates from event occurrence dates when the sources support that distinction

#### Scenario: Search returns weak or insufficient evidence
- **WHEN** searched sources do not support a reliable preliminary timeline or event-stage summary
- **THEN** the response marks the briefing as insufficient evidence
- **AND** the response explains what is missing
- **AND** the response suggests follow-up queries, source types, or time ranges that could improve formal discovery

### Requirement: Briefing-to-discovery handoff
The system SHALL allow users to apply briefing recommendations to discovery settings without automatically submitting discovery.

#### Scenario: User applies briefing recommendations
- **WHEN** the user applies recommended discovery settings from a briefing
- **THEN** the source discovery setup form updates with the selected recommendation values
- **AND** the user must still explicitly submit the form before a source discovery job is created

#### Scenario: User ignores briefing recommendations
- **WHEN** the user does not apply briefing recommendations
- **THEN** existing source discovery setup behavior remains unchanged
