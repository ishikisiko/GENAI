## ADDED Requirements

### Requirement: Evidence pack sources can ground a case
The system SHALL allow confirmed evidence pack sources to be converted into document inputs for the existing worker-owned graph extraction pipeline.

#### Scenario: User starts grounding from an evidence pack
- **WHEN** the user explicitly starts grounding for an evidence pack
- **THEN** the system materializes each evidence pack source as a case-local document input compatible with graph extraction
- **AND** the graph extraction request references those materialized documents
- **AND** the extraction job follows the existing worker-owned graph extraction lifecycle

#### Scenario: Evidence pack source metadata is preserved
- **WHEN** evidence pack sources are materialized for grounding
- **THEN** the system preserves metadata including original URL when available, title, source type, provider, published time, score dimensions, candidate identifier, and evidence pack identifier
- **AND** persisted graph claims remain traceable to the source document created from the evidence pack source
