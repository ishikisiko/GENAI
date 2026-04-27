# semantic-source-fragment-recall Specification

## Purpose
Define semantic fragment indexing, recall, bounded aggregation, diversity-aware ranking, and explanations for reusable and candidate source recommendations.

## Requirements
### Requirement: Semantic source fragment indexing
The system SHALL maintain indexable semantic fragments for reusable global sources and candidate source content.

#### Scenario: Reusable source is indexed
- **WHEN** a reusable global source has content available for semantic recall
- **THEN** the system stores or refreshes source fragments with stable source identity, fragment text, fragment order, embedding or vector-index metadata, and index status
- **AND** the source remains available through existing non-semantic source selection flows

#### Scenario: Candidate source is indexed
- **WHEN** a candidate source has fetched content or an excerpt available for semantic recall
- **THEN** the system stores or refreshes candidate source fragments with stable candidate identity, fragment text, fragment order, embedding or vector-index metadata, and index status
- **AND** the candidate remains subject to existing human review before evidence pack creation

#### Scenario: Fragment indexing fails
- **WHEN** the system cannot embed or index a source fragment
- **THEN** the system records the failed or stale index state
- **AND** source selection remains available through existing non-semantic ranking and filtering behavior

### Requirement: Semantic source fragment recall
The system SHALL support semantic recall of relevant source fragments across reusable sources and candidate source content for a case, topic, or source-selection query.

#### Scenario: User opens case source recommendations
- **WHEN** a user opens source selection for a crisis case
- **THEN** the system retrieves semantically similar fragments using the case topic, description, or query context when semantic recall is available
- **AND** the system aggregates fragment matches into source-level recommendation signals
- **AND** the system does not rank sources solely by raw fragment similarity

#### Scenario: User enters a source-selection query
- **WHEN** a user submits a source-selection query
- **THEN** the system retrieves semantically similar fragments using that query when semantic recall is available
- **AND** the returned recommendations preserve source-level ranking and explanation fields

#### Scenario: Embeddings are unavailable
- **WHEN** embeddings or vector search are unavailable for the request
- **THEN** the system returns source recommendations using the existing non-semantic selection behavior
- **AND** the response indicates that semantic recall was not applied

### Requirement: Bounded fragment-to-source aggregation
The system SHALL aggregate fragment-level semantic matches into bounded source-level semantic support scores before ranking sources.

#### Scenario: Multiple fragments match the same source
- **WHEN** several fragments from the same source match the query
- **THEN** the system caps or aggregates those fragment scores before ranking the source
- **AND** the source does not receive unbounded ranking advantage from repeated or long-form content

#### Scenario: Matched fragments are returned
- **WHEN** a recommendation includes semantic fragment matches
- **THEN** the system returns only a bounded number of matched fragment previews per source
- **AND** each returned fragment preview remains traceable to its source and fragment order

### Requirement: Diversity-aware semantic source ranking
The system SHALL preserve multi-source and multi-perspective coverage when ranking semantically recalled sources.

#### Scenario: One source has the strongest semantic match
- **WHEN** one source has the highest fragment similarity score
- **THEN** the final ranking balances that semantic support with diversity and source quality signals
- **AND** the system includes other high-quality sources from different source kinds, topics, providers, regions, or stakeholder perspectives when those sources are available

#### Scenario: Similar sources compete for top positions
- **WHEN** several semantically similar sources share the same source kind, topic, provider, region, or stakeholder angle
- **THEN** the system applies diversity-aware reranking before returning recommendations
- **AND** the ranking preserves distinct high-quality perspectives when those perspectives are available

### Requirement: Semantic recommendation explanations
The system SHALL expose explanation evidence for semantically supported source recommendations.

#### Scenario: Recommendations are displayed
- **WHEN** the system returns semantically supported source recommendations
- **THEN** each recommendation includes matched fragment previews when available
- **AND** each recommendation exposes source-level ranking reasons such as semantic support, authority, freshness, topic relationship, grounding value, and diversity contribution

#### Scenario: Source is already attached to the case
- **WHEN** a semantically recalled source is already attached to the current case
- **THEN** the system marks the source as already in the case
- **AND** the source cannot be attached again
