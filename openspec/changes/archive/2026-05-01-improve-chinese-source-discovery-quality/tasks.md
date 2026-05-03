## 1. Discovery Planning Inputs

- [x] 1.1 Extend source discovery planning contracts/types with optional core entities, event aliases, language variants, and evidence bucket hints.
- [x] 1.2 Persist or pass assistant planning hints from source discovery setup to backend discovery submission without requiring an assistant response.
- [x] 1.3 Add backwards-compatible frontend typing for structured assistant planning hints.

## 2. Query Expansion

- [x] 2.1 Replace generic-only query expansion with bounded evidence-bucket query generation for timeline, official response, regulatory context, social evidence, and impact evidence.
- [x] 2.2 Add Chinese query templates that combine core entities, aliases, actor names, and bucket-specific terms.
- [x] 2.3 Deduplicate and truncate generated queries deterministically within existing backend provider limits.
- [x] 2.4 Preserve evidence bucket labels in query plan metadata where the existing API shape allows it, or document any fallback representation.

## 3. Relevance Scoring

- [x] 3.1 Add deterministic Chinese relevance term extraction using core phrases, aliases, and bounded CJK n-grams.
- [x] 3.2 Combine topic, description, case context, and optional assistant hints when deriving core relevance terms.
- [x] 3.3 Keep generic crisis/source vocabulary low-weight and cap candidates that lack core entity or event alignment.
- [x] 3.4 Add regression tests for Chinese variants such as `西贝预制菜风波`, `预制菜之争`, `罗永浩吐槽西贝事件`, and unrelated social-platform pages.

## 4. Candidate Quality And Classification

- [x] 4.1 Filter or low-rank mock/test candidates when a real search provider is configured while keeping mock provider behavior available for tests.
- [x] 4.2 Detect generic background pages that do not match event-specific entities or aliases and reduce their relevance and grounding value.
- [x] 4.3 Replace broad keyword-based official classification with conservative domain, URL, provider metadata, and source-type rules.
- [x] 4.4 Add tests showing media articles quoting official statements remain media/news unless the source itself is official.

## 5. Review And Verification

- [x] 5.1 Ensure candidate review still displays relevance, authority, freshness, claim richness, diversity, grounding value, and total score separately.
- [x] 5.2 Verify accepted/rejected review controls and evidence pack creation behavior remain unchanged.
- [x] 5.3 Run targeted backend source discovery tests and relevant frontend type/build checks.
- [x] 5.4 Document operational behavior for new discovery jobs versus historical candidates that require explicit rescoring.
