## ADDED Requirements

### Requirement: Chinese and alias-aware candidate relevance
The system SHALL score source candidate relevance for Chinese-language crisis events using core entities, event terms, and known aliases from discovery context rather than relying only on whitespace-delimited topic tokens.

#### Scenario: Chinese event title uses wording variant
- **WHEN** a discovery topic such as `西贝预制菜事件` has a candidate source titled with a variant such as `西贝预制菜风波`, `预制菜之争`, or `罗永浩吐槽西贝事件`
- **THEN** the candidate can receive direct relevance credit for matching the core entity and event meaning
- **AND** the candidate is not capped as unrelated solely because the exact topic phrase is absent

#### Scenario: Candidate lacks core Chinese event alignment
- **WHEN** a Chinese-language or bilingual candidate matches only broad words such as `事件`, `社交媒体`, `平台`, `新闻`, or `时间线`
- **THEN** the candidate relevance score remains low
- **AND** high authority, freshness, or content length does not cause the candidate to rank above directly relevant event sources

#### Scenario: Assistant planning hints provide aliases
- **WHEN** optional assistant planning context includes core entities or event aliases
- **THEN** the scorer MAY use those hints as additional deterministic relevance terms
- **AND** scoring remains available when assistant hints are absent

### Requirement: Evidence-bucketed discovery query expansion
The system SHALL generate bounded source discovery queries by evidence bucket so discovery seeks coverage across timeline, official response, regulatory context, social-media evidence, and downstream impact.

#### Scenario: Worker expands queries for a Chinese crisis event
- **WHEN** the worker processes a discovery job with Chinese core entities or event aliases
- **THEN** it generates labeled queries for event timeline, official response, regulatory or standards context, original social-media evidence, and impact or consequence evidence within backend-owned limits
- **AND** the query plan remains persisted for operator and review visibility

#### Scenario: Social-media evidence is requested
- **WHEN** a discovery job requests social source types or social-media evidence
- **THEN** generated queries combine the event's core entities or aliases with platform, original-post, or author terms
- **AND** generic pages about social-media platforms alone are not treated as satisfying event-specific social evidence

#### Scenario: Query limits are enforced
- **WHEN** evidence buckets produce more query candidates than the backend limit allows
- **THEN** the system deduplicates and truncates the query plan deterministically
- **AND** discovery processing remains bounded for the configured search provider

### Requirement: Formal discovery excludes mock and low-evidence generic candidates
The system SHALL prevent mock, test, and low-evidence generic background pages from appearing as high-quality formal discovery candidates when real source discovery is expected.

#### Scenario: Real provider discovery encounters mock results
- **WHEN** a source discovery job is configured to use a real search provider
- **AND** a candidate URL or provider metadata identifies a mock or test source
- **THEN** the system excludes the candidate from formal candidate ranking or marks it with low review value
- **AND** the candidate does not appear as a high-scoring source

#### Scenario: Candidate is generic background material
- **WHEN** a candidate describes a broad platform, industry, or background topic without matching the event's core entities or aliases
- **THEN** the system gives the candidate low relevance and low grounding value
- **AND** directly relevant event sources rank above it by default

#### Scenario: Mock provider is explicitly configured
- **WHEN** the backend is configured with the deterministic mock search provider
- **THEN** mock candidates remain available for local development and tests
- **AND** they are identifiable through provider or metadata fields

### Requirement: Conservative source classification
The system SHALL classify discovered candidates using conservative source-type rules so official, media, social, and research classifications reflect the source itself rather than quoted claims inside the source.

#### Scenario: Media article quotes official statements
- **WHEN** a media article mentions regulators, official statements, company responses, or government standards
- **THEN** the system classifies the candidate as media or news unless the source domain or provider metadata identifies the page as an official source
- **AND** the authority score reflects the candidate's classified source type

#### Scenario: Official source is discovered
- **WHEN** a candidate comes from a government, regulator, company-owned, or otherwise verified official publication channel
- **THEN** the system can classify the candidate as official
- **AND** quoted media coverage is not required for official classification

#### Scenario: Social or discussion source is discovered
- **WHEN** a candidate comes from a social platform, discussion forum, creator post, or user-generated source
- **THEN** the system can classify the candidate as social
- **AND** social classification does not depend on the page merely containing the words `social` or `media`
