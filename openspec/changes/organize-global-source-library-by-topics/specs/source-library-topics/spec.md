## ADDED Requirements

### Requirement: Topic-based source library organization
The system SHALL organize reusable global sources through source topics or collections that can be hierarchical and typed.

#### Scenario: User creates a source topic
- **WHEN** a user creates a source topic with a name, optional description, optional parent topic, and topic type
- **THEN** the system persists the source topic
- **AND** the topic can be used as a collection in the Global Source Library

#### Scenario: User browses topic collections
- **WHEN** a user opens the Global Source Library
- **THEN** the page presents topic or collection navigation before the complete raw source list
- **AND** the user can open a topic to see sources assigned to that topic

#### Scenario: Topic has a parent topic
- **WHEN** a topic is created with a valid parent topic
- **THEN** the system preserves the parent-child relationship
- **AND** the library can show the child topic under its parent collection

### Requirement: Multi-topic source assignments
The system SHALL allow one reusable global source to belong to multiple source topics with assignment metadata.

#### Scenario: User assigns a source to a topic
- **WHEN** a user assigns a global source to a source topic
- **THEN** the system persists the source-topic assignment
- **AND** the assignment records the relevance score, assignment reason, assignment provenance, and creation time when provided

#### Scenario: User assigns one source to multiple topics
- **WHEN** a user assigns the same global source to more than one source topic
- **THEN** the system keeps one reusable global source record
- **AND** the system stores separate topic assignments for each topic

#### Scenario: User removes a source from a topic
- **WHEN** a user removes a source-topic assignment
- **THEN** the source is no longer listed inside that topic
- **AND** the reusable source remains available in the global registry and in any other topics that still reference it

### Requirement: Reusable source registry metadata
The system SHALL preserve registry-oriented metadata for global sources so that sources can be deduplicated, filtered, and maintained across topics.

#### Scenario: Global source is created or updated
- **WHEN** a global source is created or updated
- **THEN** the system stores title, content, document type compatibility, source kind, canonical URL when available, content hash, authority level, freshness status, source status, creation time, and update time

#### Scenario: Potential duplicate source is detected
- **WHEN** a global source has the same canonical URL or content hash as another global source
- **THEN** the system can mark or list the source as a duplicate candidate
- **AND** the system does not merge or delete either source without user action

#### Scenario: User filters sources by metadata
- **WHEN** a user filters the source registry by source kind, authority level, freshness status, source status, or text query
- **THEN** the system returns matching sources without requiring the user to browse unrelated topic collections

### Requirement: Source library smart views
The system SHALL provide smart views for common source-maintenance workflows without treating those views as exclusive folders.

#### Scenario: User opens the Unassigned smart view
- **WHEN** a user opens the Unassigned smart view
- **THEN** the system lists global sources that have no active source-topic assignment
- **AND** sources with at least one active topic assignment are excluded from that view

#### Scenario: User opens maintenance smart views
- **WHEN** a user opens Recently Used, High Authority, Duplicate Candidates, or Stale Sources
- **THEN** the system lists sources matching the selected view criteria
- **AND** each listed source still retains its topic assignments and registry metadata

### Requirement: Case-local source snapshots from reusable sources
The system SHALL create case-local source document snapshots when reusable global sources are attached to a crisis case.

#### Scenario: User adds a global source to a case
- **WHEN** a user adds a global source to a crisis case from a topic, smart view, or global search result
- **THEN** the system creates a case-local `source_documents` record
- **AND** the snapshot preserves source content, source type compatibility, global source identifier, selected topic or assignment provenance when available, source origin, and registry metadata needed for traceability

#### Scenario: Global source changes after case attachment
- **WHEN** a global source is edited after it has been attached to a crisis case
- **THEN** existing case-local source document snapshots remain unchanged
- **AND** future attachments use the current global source content and metadata

#### Scenario: User tries to add the same source twice to one case
- **WHEN** a user attempts to add a global source that is already attached to the current crisis case
- **THEN** the system prevents duplicate attachment
- **AND** the selection UI marks the source as already in the case

### Requirement: Topic-aware case source selection
The system SHALL prioritize case-relevant sources before the full global repository when users add sources to a crisis case.

#### Scenario: User opens case source selection
- **WHEN** a user opens source selection for a crisis case
- **THEN** the interface groups available sources into Recommended for this case, Same topic collections, Related collections, Global search, and Manual upload sections
- **AND** the complete global source list is not the default first section

#### Scenario: Case has topic associations
- **WHEN** the current crisis case is associated with one or more source topics
- **THEN** the same-topic section lists sources from those topics
- **AND** related sections can list sources from parent, child, or otherwise related topics

#### Scenario: Source is already in the case
- **WHEN** a source listed in case source selection is already attached to the current case
- **THEN** the interface clearly marks it as already in the case
- **AND** the source cannot be selected again for the same case

### Requirement: Source usage visibility
The system SHALL show where reusable sources have been used across topics and crisis cases.

#### Scenario: User opens source details
- **WHEN** a user opens details for a reusable global source
- **THEN** the system shows the source's topic assignments
- **AND** the system shows case usage records derived from case-local source documents

#### Scenario: Source has never been used in a case
- **WHEN** a reusable global source has no linked case-local source documents
- **THEN** the usage view indicates that the source has not yet been used in any case
