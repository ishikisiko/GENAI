## Why

Current source discovery and source-library recommendation ranking rely on source-level metadata and rule-based score dimensions. As the global source library grows, users need case source selection to surface semantically relevant evidence fragments across reusable sources without letting one long or highly similar source dominate the recommendation list.

## What Changes

- Add semantic fragment recall across reusable global sources and candidate source content.
- Store or compute source fragment embeddings so case/topic queries can retrieve matching passages.
- Aggregate fragment-level vector matches into bounded source-level semantic support scores.
- Extend source recommendation ranking with semantic support while preserving existing source quality, authority, freshness, grounding value, human review, and diversity dimensions.
- Prevent high-similarity sources from monopolizing results by applying per-source fragment caps and source-level diversity-aware reranking.
- Expose matched fragments and ranking reasons as explanation evidence in source selection and review surfaces.

## Capabilities

### New Capabilities
- `semantic-source-fragment-recall`: Semantic fragment indexing, retrieval, source-level aggregation, diversity-aware semantic ranking, and recommendation explanations for reusable and candidate source content.

### Modified Capabilities
- `backend-api-boundary`: Add Python API response contracts for semantically supported source recommendations, matched fragment previews, semantic support scores, and ranking reasons.

## Impact

- Backend: add embedding/indexing support for source fragments, source-level semantic aggregation, fallback behavior, and diversity-aware recommendation ranking.
- API: extend source recommendation and source selection responses with semantic support scores, matched fragment previews, and ranking reasons.
- Database: add additive storage for source fragments, embeddings, vector index metadata, and refresh state.
- Frontend: show matched evidence snippets and ranking reasons in source selection and review surfaces.
- Existing flows: manual upload, topic-based browsing, source discovery, evidence packs, and grounding remain human-confirmed.
