## ADDED Requirements

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
