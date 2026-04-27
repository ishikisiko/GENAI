## ADDED Requirements

### Requirement: Semantic source recommendation API contract
The system SHALL expose Python API response contracts for semantically supported source recommendations without requiring the frontend to call storage or vector-index services directly.

#### Scenario: Case source recommendations are requested
- **WHEN** the frontend requests source recommendations for a crisis case through the Python API
- **THEN** the response includes source recommendation records with source identity, source scope, source metadata, semantic support when available, matched fragment previews when available, ranking reasons, and already-attached status
- **AND** successful completion does not require the frontend to query Supabase, an embedding provider, or a vector index directly

#### Scenario: Semantic recall is unavailable
- **WHEN** the frontend requests source recommendations and semantic recall cannot be applied
- **THEN** the Python API returns recommendations using existing non-semantic selection behavior
- **AND** the response includes a machine-readable indication that semantic recall was not applied

#### Scenario: Recommendation includes candidate source content
- **WHEN** a source recommendation is based on candidate source content
- **THEN** the Python API response preserves candidate identity and review status
- **AND** the response does not represent the candidate as attached to the case or accepted into an evidence pack unless the existing human review workflow has confirmed it
