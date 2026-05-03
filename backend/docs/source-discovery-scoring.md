# Source Discovery Scoring

Source discovery ranks candidates with separate score dimensions for relevance, authority, freshness, claim richness, diversity, and grounding value.

## Relevance

Relevance is the case-fit dimension. It distinguishes core entity/event terms from generic discovery vocabulary such as "incident", "social", "media", "source", "official", and "timeline".

- Candidates that only match generic discovery terms receive low relevance.
- Candidates that match core entity or event terms can receive higher relevance.
- Exact phrase matches can boost relevance after direct case relevance is established.
- Optional local semantic support can raise relevance for directly related candidates, but it cannot bypass the core relevance gate for unrelated candidates.
- Chinese-language topics use deterministic phrase and short-token expansion so variants such as `西贝预制菜事件`, `西贝预制菜风波`, `预制菜之争`, and related assistant-provided aliases can match without requiring exact phrase equality.

## Query Expansion

New discovery jobs generate bounded, labeled query plans by evidence bucket. The current labels are timeline, official response, regulatory context, social evidence, and impact. Labels are stored in `source_discovery_jobs.query_plan` as a readable prefix, while the worker strips the prefix before sending the query to the search provider.

Assistant planning hints can optionally add core entities, actor names, event aliases, language variants, and evidence-bucket queries. These hints improve query generation and scoring, but source discovery still runs only after the user submits the discovery form.

## Source Quality

Mock and test results are kept for explicitly configured mock discovery, but real-provider discovery filters or demotes mock/test candidates so they do not appear as high-scoring formal sources. Generic background pages, such as platform guides without event-specific entity or alias matches, remain low relevance and low grounding value.

Source classification is conservative: media articles quoting official statements remain news/media unless the source itself is official. Official classification should reflect the publication channel, not just quoted language inside the page.

## Total Score

Total score remains derived from the score dimensions, but low relevance constrains the total score. This prevents high-authority or content-rich but unrelated sources from ranking as highly relevant discovery candidates.

## Historical Candidates

Existing `source_candidates` rows keep the scores that were written when their discovery job ran. The updated scorer applies to new source discovery jobs. Recomputing historical candidates requires a separate rescore operation.
