## Context

The existing source discovery scoring model exposes relevance, authority, freshness, claim richness, diversity, and grounding value. These dimensions are source-level signals. They do not directly measure whether a reusable source or candidate source contains passages that semantically match the current case, discovery topic, or user query.

Semantic recall must operate at fragment level, but recommendation ranking must remain source-level. This distinction prevents long documents or repeated near-duplicate passages from dominating the recommendation list. Semantic recall is fragment-level; recommendation ranking remains source-level.

## Goals / Non-Goals

**Goals:**

- Retrieve semantically relevant fragments across reusable global sources and candidate source content.
- Convert fragment-level matches into bounded source-level semantic support scores.
- Combine semantic support with source quality, topic/case relevance, authority, freshness, grounding value, and diversity signals.
- Expose matched fragments and ranking reasons so users can inspect why a source appears.
- Preserve human-confirmed source review, evidence pack creation, and grounding behavior.
- Provide fallback behavior when embeddings or vector search are unavailable.

**Non-Goals:**

- Replacing configured source discovery search providers.
- Ranking sources only by vector similarity.
- Automatically attaching semantically recalled sources to a case.
- Automatically promoting candidate sources into the global source library.
- Automatically merging duplicate or semantically similar sources.
- Building a trained credibility or authority model.

## Decisions

### Use fragment recall as a ranking signal, not the final ranking

The system will retrieve semantically similar fragments across available source content, then aggregate those matches into a bounded source-level `semantic_support` score. Final recommendation ranking will combine semantic support with source quality and diversity signals.

Alternative considered: sort source recommendations directly by raw vector similarity. This is simpler, but it lets long sources, boilerplate-heavy sources, or repeated fragments monopolize the recommendation list.

### Store source fragments additively

Add an additive fragment/index representation for global source documents and candidate sources. Each indexed fragment should retain source identity, source scope, fragment text, stable ordering metadata, embedding/index status, and timestamps. The embedding storage can be a database vector column, an external vector index reference, or an equivalent local index abstraction, but the repository/service contract should hide that choice from API handlers.

Alternative considered: compute embeddings only at request time. That avoids storage migration, but it makes source selection latency unpredictable and prevents efficient cross-source recall as the library grows.

### Aggregate before sorting sources

Fragment matches will be grouped by source before recommendation ranking. The preferred aggregation is `max(top fragment)` or `average(top N fragments)` with a small N such as 3. The implementation must not sum all matching fragments directly.

Alternative considered: boost a source for every matching fragment. This over-rewards long documents and duplicate passages, and it conflicts with the multi-perspective source selection goal.

### Apply diversity-aware reranking after source scoring

Recommendation ranking will apply diversity controls after initial source-level scoring. Controls should consider available metadata such as source kind, topic assignment, provider, region, and stakeholder angle. The ranking should still include the strongest semantic match, but it must preserve room for distinct high-quality perspectives.

Alternative considered: encode diversity as only one averaged score dimension. That makes the behavior hard to reason about and can still produce a top list dominated by one source type.

### Keep recommendations explainable

API responses should return matched fragment previews, semantic support score, ranking reasons, source quality signals, topic relationship, and already-attached status. The UI should show matched evidence next to source-level quality indicators so semantic similarity does not imply authority by itself.

Alternative considered: expose only a final rank and snippets. That hides important trade-offs and makes human review weaker.

## Risks / Trade-offs

- Vector similarity can overvalue lexical resemblance or repeated boilerplate -> Aggregate fragment scores conservatively and keep authority, freshness, and diversity in final ranking.
- Embedding storage increases operational complexity -> Introduce additive schema and fallback to existing source selection when embeddings are unavailable.
- Matched fragments can look authoritative even when the source is weak -> Display source quality and provenance signals alongside semantic matches.
- Diversity reranking can lower the absolute top semantic match -> Treat this as intentional for case preparation, where coverage across perspectives matters more than a single highest-similarity source.
- Embedding model changes can invalidate stored vectors -> Track embedding model/version metadata and support reindexing stale fragments.

## Migration Plan

1. Add additive fragment and embedding/index metadata storage for global sources and candidate sources.
2. Backfill fragments for existing reusable source content without changing current source selection behavior.
3. Add an embedding/index refresh path that records indexed, stale, and failed states.
4. Add semantic recall repository/service contracts with fallback to existing non-semantic source selection.
5. Add source-level aggregation and diversity-aware ranking behind the Python API.
6. Extend frontend source selection and review surfaces to show matched fragments and ranking reasons.
7. Validate ranking behavior with fixtures covering long documents, duplicate fragments, mixed source kinds, and already-attached sources.

Rollback is additive: disable semantic recommendation usage in the API/UI and continue using existing topic, global search, source discovery, evidence pack, and grounding flows. Fragment/index tables can remain unused.

## Open Questions

- Which embedding provider or local embedding model should be used first?
- Should candidate source fragments be indexed immediately after discovery or only after user acceptance?
- What initial diversity buckets are available reliably across global sources and candidates: source kind, provider, topic, region, stakeholder angle, or a smaller subset?
- What top-N fragment cap should be exposed in API responses for review surfaces?
