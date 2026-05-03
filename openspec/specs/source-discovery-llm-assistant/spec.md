# source-discovery-llm-assistant Specification

## Purpose
Define the source discovery LLM assistant modes, grounding boundaries, advisory behavior, search planning, source-grounded interpretation, and search-backed briefing behavior.

## Requirements
### Requirement: Source discovery assistant modes
The system SHALL provide a source discovery LLM assistant with explicit context-aware modes for search planning and source interpretation.

#### Scenario: Assistant is used before discovery
- **WHEN** a user invokes the assistant from source discovery setup before a discovery job exists
- **THEN** the system uses search planning mode
- **AND** the assistant response is scoped to case and discovery form context
- **AND** the assistant does not present unsupported event claims as confirmed facts

#### Scenario: Assistant is used during candidate review
- **WHEN** a user invokes the assistant from candidate source review for a discovery job
- **THEN** the system uses source interpretation mode
- **AND** the assistant response is scoped to the current discovery job's candidate sources
- **AND** the assistant does not use unrelated cases, unrelated discovery jobs, or arbitrary external browsing as grounding material

### Requirement: Search planning assistance
The system SHALL help users generate source discovery directions from incomplete event knowledge without treating those directions as verified facts.

#### Scenario: User asks how to begin searching
- **WHEN** the user asks the assistant for search help from source discovery setup
- **THEN** the assistant returns suggested search directions, keywords, alternate terms, actor names when inferable, source types, language variants, and initial time range guidance
- **AND** the response marks these outputs as planning suggestions rather than confirmed event findings

#### Scenario: Planning suggestions can inform discovery settings
- **WHEN** the assistant returns structured search planning suggestions
- **THEN** the response includes fields that the frontend can use to apply or copy suggested topic, description, region, language, time range, source type, or query direction values
- **AND** applying suggestions still requires an explicit user action before a source discovery job is created

### Requirement: Source-grounded event interpretation
The system SHALL answer event timeline and stage questions from candidate source context when enough source evidence is available.

#### Scenario: User asks for the event timeline
- **WHEN** the user asks the assistant to summarize the timeline from candidate review
- **THEN** the assistant returns timeline items derived from available candidate sources
- **AND** each timeline item includes citations to the supporting candidate sources
- **AND** each timeline item distinguishes event occurrence dates from source publication dates when the available evidence supports that distinction

#### Scenario: User asks for event stage
- **WHEN** the user asks what stage the event appears to be in
- **THEN** the assistant returns a stage summary grounded in candidate sources
- **AND** the response identifies the source evidence used to support the stage assessment
- **AND** the response explains uncertainty when the candidate set does not support a confident stage assessment

### Requirement: Evidence gaps and source conflicts
The system SHALL identify evidence gaps and source conflicts without resolving them as facts unless the candidate evidence supports a resolution.

#### Scenario: Candidate sources disagree
- **WHEN** candidate sources contain conflicting claims, dates, actors, or event-stage signals
- **THEN** the assistant response identifies the conflict
- **AND** the response cites the candidate sources supporting each side of the conflict
- **AND** the response avoids declaring a winner unless available source evidence justifies that conclusion

#### Scenario: Candidate sources are incomplete
- **WHEN** the candidate set lacks enough evidence to answer a timeline or stage question
- **THEN** the assistant returns an insufficient-evidence response
- **AND** the response suggests follow-up search directions that could fill the missing timeline, actor, source-type, or date-range evidence

### Requirement: Assistant safety boundaries
The system SHALL keep the assistant advisory and SHALL NOT allow assistant output to mutate review, evidence pack, grounding, or simulation state.

#### Scenario: Assistant suggests next steps
- **WHEN** the assistant suggests accepting a source, creating an evidence pack, starting grounding, or starting simulation
- **THEN** the system presents the suggestion as advisory text only
- **AND** the underlying workflow state is unchanged unless the user performs the existing explicit product action

#### Scenario: Assistant is asked unrelated questions
- **WHEN** the user asks a question unrelated to the current case, source discovery setup, discovery job, candidate sources, or source review workflow
- **THEN** the assistant refuses or redirects the request back to the source discovery context

### Requirement: Search-backed briefing assistant mode
The source discovery assistant SHALL support a user-confirmed `search_backed_briefing` mode in addition to search planning and source interpretation modes.

#### Scenario: Briefing mode is requested
- **WHEN** the frontend submits an assistant request with `mode` set to `search_backed_briefing`
- **THEN** the assistant uses searched source context as its grounding scope
- **AND** the assistant response includes searched-source citations for event timeline, actor, stage, and controversy claims
- **AND** the assistant does not use arbitrary external browsing beyond backend-authorized search execution

#### Scenario: Briefing mode recommends next actions
- **WHEN** the assistant recommends discovery settings, source types, or follow-up searches from briefing mode
- **THEN** those recommendations remain advisory
- **AND** workflow state is unchanged unless the user performs an existing explicit product action

### Requirement: Briefing mode safety boundaries
The assistant SHALL keep search-backed briefing bounded to discovery preparation and SHALL NOT perform autonomous workflow mutations.

#### Scenario: Briefing identifies promising sources
- **WHEN** briefing mode identifies sources that appear useful for the event timeline
- **THEN** the assistant may cite and summarize those sources
- **AND** the assistant does not mark them as accepted candidates or evidence pack sources

#### Scenario: User asks briefing mode to complete downstream work
- **WHEN** the user asks briefing mode to accept sources, create an evidence pack, start grounding, or start simulation
- **THEN** the assistant refuses or redirects the user to the explicit existing workflow action

### Requirement: Structured discovery planning hints
The source discovery assistant SHALL be able to return structured planning hints for core entities, event aliases, and evidence buckets without creating or mutating a source discovery job.

#### Scenario: Assistant suggests Chinese event search context
- **WHEN** a user requests search planning for a Chinese-language or bilingual crisis event
- **THEN** the assistant response can include structured core entities, actor names, event aliases, language variants, and suggested evidence buckets
- **AND** those hints are presented as planning guidance rather than verified event findings

#### Scenario: Discovery uses assistant planning hints
- **WHEN** a user explicitly starts source discovery after applying or retaining assistant planning context
- **THEN** the backend may use the structured planning hints to enrich query expansion and candidate relevance scoring
- **AND** discovery still follows the existing explicit submission and human review workflow

#### Scenario: Assistant hints are absent
- **WHEN** no assistant planning response exists for a case or the response lacks structured hints
- **THEN** source discovery still generates bounded queries and deterministic candidate scores from the submitted discovery settings
- **AND** no assistant call is required to run discovery
