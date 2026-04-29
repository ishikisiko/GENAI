## ADDED Requirements

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
