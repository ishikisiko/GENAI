## Why

Source discovery candidate relevance currently over-rewards generic overlap such as "incident", "social", or "media", allowing unrelated sources to appear highly relevant when they share broad crisis-research terms. This makes candidate review noisier and can mislead users into trusting high total scores for sources that do not match the case's core entity or event.

## What Changes

- Replace generic token-overlap relevance scoring with a relevance gate that distinguishes core entity/event tokens from broad source-discovery terms.
- Add hybrid relevance signals that can combine exact phrase/entity matching, lexical relevance, and semantic support when available.
- Ensure unrelated candidates that only match generic terms receive low relevance and cannot be lifted to high total rank solely by authority, freshness, or content length.
- Preserve explainability for relevance score dimensions so users can understand why a candidate was ranked.
- Keep human review behavior unchanged: users still accept or reject candidates explicitly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-discovery-evidence-packs`: Candidate scoring requirements will distinguish direct case relevance from generic source quality, and candidate ranking will guard against unrelated high-authority sources receiving high relevance.

## Impact

- Backend source discovery scoring logic in `backend/src/backend/services/source_discovery_service.py`.
- Candidate persistence and review data returned by existing source discovery APIs.
- Source candidate review UI remains API-compatible but displays more trustworthy relevance and total scores.
- Tests for source discovery scoring, candidate ordering, and regression cases involving generic-term false positives.
