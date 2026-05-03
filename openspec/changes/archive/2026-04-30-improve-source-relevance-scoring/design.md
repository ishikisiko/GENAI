## Context

Source discovery candidates are currently scored across relevance, authority, freshness, claim richness, diversity, and grounding value, then ranked by the average total score. Relevance is the only dimension intended to answer "is this candidate about the case?", but the existing simple token overlap can treat broad terms as meaningful matches. In practice, an unrelated high-authority page can receive moderate relevance from generic terms and then receive a high total score from non-relevance dimensions.

The system already has human review controls, candidate score dimensions, provider metadata, and semantic fragment recall elsewhere in the source library flow. The design should improve discovery-time ranking without changing the review workflow or requiring a new user action.

## Goals / Non-Goals

**Goals:**
- Make candidate relevance reflect direct case/entity/event alignment rather than generic crisis vocabulary.
- Keep the scoring explainable and deterministic enough for tests.
- Allow semantic support to improve ranking when available, while keeping lexical/core-token gating as a reliable fallback.
- Prevent high authority or long content from making unrelated candidates look strongly relevant.
- Preserve existing API shapes unless a later task explicitly adds explanation fields.

**Non-Goals:**
- Fully automate candidate acceptance or rejection.
- Replace Brave Search ranking or provider-side filtering.
- Introduce mandatory LLM judging for every candidate.
- Recompute historical candidate scores automatically.

## Decisions

1. Use layered relevance scoring rather than a single token overlap score.

   The relevance scorer will separate topic tokens into core/specific tokens and generic discovery tokens. Core token matches carry most of the score; generic terms such as "incident", "social", "media", "source", "timeline", and "official" carry limited weight. If the topic contains core tokens and a candidate matches none of them, relevance is capped at a low value.

   Alternative considered: keep token overlap and tune constants. This was rejected because the core failure is not just calibration; generic words and proper nouns need different semantics.

2. Add phrase and entity-style boosts only after core-token matching.

   Exact phrase matches and multi-token entity/event matches can increase relevance, but they cannot bypass the core-token gate. This keeps direct matches strong while preventing broad text from receiving high relevance.

   Alternative considered: use phrase matching only. This was rejected because real results may contain translated, reordered, or partially phrased event descriptions.

3. Treat semantic support as an optional reranking input, not the only gate.

   When semantic embeddings or fragment recall are available, they can add confidence for semantically aligned candidates. However, lexical/core-token gating remains necessary to guard against broad semantic similarity in long unrelated pages.

   Alternative considered: switch entirely to embeddings. This was rejected because embeddings can be opaque, require chunking, and may still over-score broad topical proximity without entity checks.

4. Keep total score bounded by relevance for unrelated candidates.

   A candidate with low relevance should not receive a high total rank only because authority, freshness, diversity, or claim richness are high. Total score should incorporate a relevance-sensitive cap or penalty for low-relevance candidates.

   Alternative considered: leave total score as an average of dimensions. This was rejected because the current average lets non-relevance dimensions mask direct irrelevance.

## Risks / Trade-offs

- Conservative scoring may demote cross-language or alias-heavy sources that do not share obvious core tokens. Mitigation: include alias extraction from assistant/planning context and optional semantic support.
- Relevance gates depend on good generic-token and core-token classification. Mitigation: maintain explicit tests for known false positives and true positives, and keep the generic list easy to adjust.
- Historical candidates keep old scores. Mitigation: document that rescoring applies to new discovery runs unless a later migration/recompute task is added.
- Semantic support may be unavailable in local environments. Mitigation: lexical scoring remains functional without embeddings.
