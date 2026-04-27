## 1. Data Model and Contracts

- [x] 1.1 Add additive backend and Supabase migrations for source fragments, embedding/index metadata, source scope, fragment order, index status, embedding model/version, and refresh timestamps.
- [x] 1.2 Add backend domain records and repository methods for creating, refreshing, listing, and marking source fragments as indexed, stale, or failed.
- [x] 1.3 Add Pydantic contracts for matched fragments, semantic support scores, ranking reasons, semantic recall availability, and source recommendation responses.
- [x] 1.4 Add TypeScript types for semantic source recommendations, matched fragment previews, ranking reasons, and recall availability.

## 2. Fragment Indexing and Recall

- [x] 2.1 Implement deterministic source content chunking for reusable global sources and candidate sources with stable fragment ordering.
- [x] 2.2 Implement an embedding/index abstraction that can store or reference vector data without exposing provider-specific details to API handlers.
- [x] 2.3 Add indexing refresh logic for new or changed global sources and candidate sources.
- [x] 2.4 Implement semantic fragment retrieval for case topic, case description, and user query inputs.
- [x] 2.5 Implement fallback behavior that returns non-semantic recommendations when embeddings or vector search are unavailable.

## 3. Aggregation and Ranking

- [x] 3.1 Implement bounded fragment-to-source aggregation using a max or top-N average semantic support score.
- [x] 3.2 Cap returned matched fragment previews per source and preserve source/fragment traceability.
- [x] 3.3 Extend source recommendation scoring to combine semantic support with topic/case relevance, authority, freshness, grounding value, and source quality signals.
- [x] 3.4 Implement diversity-aware reranking across available source kind, topic, provider, region, and stakeholder metadata.
- [x] 3.5 Preserve already-attached source detection so semantically recalled sources cannot be attached twice to the same case.

## 4. API and UI

- [x] 4.1 Extend Python API source recommendation responses with semantic support, matched fragments, ranking reasons, recall availability, and candidate review status when applicable.
- [x] 4.2 Ensure the frontend uses the Python API for semantic recommendations without direct Supabase, embedding provider, or vector-index calls.
- [x] 4.3 Update case source selection to show matched semantic snippets without replacing recommended, same-topic, related, global search, or manual upload sections.
- [x] 4.4 Update source review surfaces to show semantic ranking reasons alongside authority, freshness, source kind, topic relationship, and grounding value.

## 5. Verification

- [x] 5.1 Add backend tests for fragment creation, index state transitions, semantic recall fallback, and candidate/global source scope handling.
- [x] 5.2 Add backend tests for bounded aggregation so long documents or repeated fragments do not receive unbounded ranking advantage.
- [x] 5.3 Add backend tests for diversity-aware ranking, strongest semantic match preservation, mixed-source coverage, and already-attached source handling.
- [x] 5.4 Add API contract tests for semantic recommendation fields, recall availability, matched fragment previews, ranking reasons, and candidate review status.
- [x] 5.5 Add focused frontend tests or fixtures for matched snippet display, ranking reason display, fallback display, and duplicate attachment prevention.
- [x] 5.6 Run OpenSpec validation and the relevant backend/frontend test suites.
