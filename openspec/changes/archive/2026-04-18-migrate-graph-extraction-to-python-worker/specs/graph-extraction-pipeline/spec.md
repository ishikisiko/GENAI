## ADDED Requirements

### Requirement: Worker-owned extraction pipeline
The system SHALL execute each `extract-graph` request as a worker-owned pipeline that processes a durable extraction job through document input loading, per-document extraction, normalization, aggregate merge, and persistence stages.

#### Scenario: Worker executes an extraction job
- **WHEN** a worker claims a pending graph extraction job
- **THEN** the worker executes the pipeline stages in order for that job
- **AND** the job is marked completed only after the persistence stage succeeds

### Requirement: Document-scoped extraction before aggregate merge
The system SHALL extract graph candidates independently for each input document before combining them into a single aggregate result for the job.

#### Scenario: Extraction job contains multiple documents
- **WHEN** a graph extraction job references more than one source document
- **THEN** the system produces document-scoped intermediate extraction outputs for each document
- **AND** the final persisted graph is derived from the aggregate merge of those intermediate outputs

### Requirement: Normalization and compatibility-preserving merge
The system SHALL normalize intermediate entities, relations, and claims before persistence and SHALL merge overlapping graph outputs in a way that preserves existing external `entities`, `relations`, and `claims` semantics as closely as possible.

#### Scenario: Multiple documents describe the same entity or claim
- **WHEN** normalized extraction outputs from different documents overlap
- **THEN** the system merges the overlapping outputs before persistence
- **AND** the persisted graph remains compatible with existing consumers of `entities`, `relations`, and `claims`

### Requirement: Extensible pipeline stage interfaces
The system SHALL keep extraction, normalization, merge, and persistence as separable worker-internal stages so that future NLP or graph-processing steps can be inserted without changing the API submission contract.

#### Scenario: A new normalization or enrichment stage is added later
- **WHEN** a future implementation introduces an additional NLP or graph-processing step
- **THEN** the new step can be inserted into the worker pipeline between existing stages
- **AND** API callers continue to submit extraction requests through the same job-creation interface

### Requirement: Observable extraction job outcome
The system SHALL record extraction job completion or failure through the canonical job lifecycle so callers can observe extraction progress without depending on in-process API execution.

#### Scenario: Caller checks extraction status after submission
- **WHEN** the API has created a graph extraction job for a caller
- **THEN** the caller can observe whether the job is pending, running, completed, or failed through the existing job-oriented status surface
- **AND** completion indicates that persisted graph outputs are available for retrieval
