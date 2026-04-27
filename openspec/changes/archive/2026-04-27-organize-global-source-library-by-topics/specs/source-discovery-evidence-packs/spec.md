## ADDED Requirements

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
