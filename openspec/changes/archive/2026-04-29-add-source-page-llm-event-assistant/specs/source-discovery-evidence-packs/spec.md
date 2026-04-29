## ADDED Requirements

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
