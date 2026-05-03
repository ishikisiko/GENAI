## ADDED Requirements

### Requirement: Structured discovery planning hints
The source discovery assistant SHALL be able to return structured planning hints for core entities, event aliases, and evidence buckets without creating or mutating a source discovery job.

#### Scenario: Assistant suggests Chinese event search context
- **WHEN** a user requests search planning for a Chinese-language or bilingual crisis event
- **THEN** the assistant response can include structured core entities, actor names, event aliases, language variants, and suggested evidence buckets
- **AND** those hints are presented as planning guidance rather than verified event findings

#### Scenario: Discovery uses assistant planning hints
- **WHEN** a user explicitly starts source discovery after applying or retaining assistant planning context
- **THEN** the backend may use the structured planning hints to enrich query expansion and candidate relevance scoring
- **AND** discovery still follows the existing explicit submission and human review workflow

#### Scenario: Assistant hints are absent
- **WHEN** no assistant planning response exists for a case or the response lacks structured hints
- **THEN** source discovery still generates bounded queries and deterministic candidate scores from the submitted discovery settings
- **AND** no assistant call is required to run discovery
