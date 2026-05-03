## 1. Scoring Model

- [x] 1.1 Replace generic token-overlap relevance with a layered scorer that separates core entity/event terms from generic discovery vocabulary.
- [x] 1.2 Add phrase and multi-token event matching boosts that only apply after direct case relevance is established.
- [x] 1.3 Constrain total candidate score when relevance is low so source quality dimensions cannot mask irrelevance.
- [x] 1.4 Keep the scorer deterministic when semantic support is unavailable.

## 2. Hybrid Signals

- [x] 2.1 Identify whether existing semantic fragment support can be reused during discovery candidate scoring without requiring new infrastructure.
- [x] 2.2 Add optional semantic support as a bounded relevance signal when candidate content can be embedded or matched.
- [x] 2.3 Ensure semantic support cannot bypass the low-relevance cap for candidates that lack core entity/event alignment.

## 3. Review Surface

- [x] 3.1 Preserve existing candidate review API shape or add backwards-compatible explanation fields if needed.
- [x] 3.2 Ensure the frontend continues to display relevance separately from authority, freshness, claim richness, diversity, grounding value, and total score.
- [x] 3.3 Confirm rejected/accepted review controls remain unchanged.

## 4. Tests and Verification

- [x] 4.1 Add regression tests for false positives that only match generic terms such as "incident", "social", and "media".
- [x] 4.2 Add positive tests for directly relevant candidates that match the case entity/event.
- [x] 4.3 Add tests showing low-relevance candidates cannot rank highly solely from authority, claim richness, or diversity.
- [x] 4.4 Run backend source discovery tests and frontend build/lint checks.

## 5. Operations

- [x] 5.1 Document that historical candidates keep prior scores unless a separate rescore job is run.
- [x] 5.2 Restart backend API and worker processes after deployment so new discovery jobs use the updated scorer.
