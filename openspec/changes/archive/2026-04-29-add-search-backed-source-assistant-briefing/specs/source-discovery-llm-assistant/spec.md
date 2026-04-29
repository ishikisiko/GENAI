## ADDED Requirements

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
