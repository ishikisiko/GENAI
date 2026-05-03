## Why

Source discovery currently under-scores relevant Chinese event sources because Chinese crisis topics can be treated as one opaque token, while broad English queries can over-retrieve generic social-media background pages. This makes candidate review noisy for Chinese-language cases and can leave key evidence types, such as original social posts, official responses, and regulatory context, under-covered.

## What Changes

- Improve Chinese relevance scoring so core entities, event terms, and common aliases can match across Chinese wording variants such as `西贝预制菜事件`, `西贝预制菜风波`, and `预制菜之争`.
- Generate evidence-bucketed discovery queries for timeline, official response, regulatory context, social-media evidence, and downstream impact instead of relying only on generic topic expansion.
- Filter or clearly demote mock, test, and low-evidence generic background pages from formal candidate ranking when real search discovery is expected.
- Make source classification more conservative so media reports are not labeled official merely because they mention official statements, regulators, or company responses.
- Use source discovery assistant planning context, when available, as structured entity, alias, and evidence-bucket guidance for discovery without bypassing user review.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-discovery-evidence-packs`: Discovery query expansion, candidate filtering, classification, and relevance scoring requirements become stronger for Chinese-language and evidence-bucketed source discovery.
- `source-discovery-llm-assistant`: Planning suggestions can expose structured core entities, aliases, and evidence buckets that discovery may use as advisory search context.

## Impact

- Backend source discovery query expansion, source classification, candidate filtering, and scoring logic.
- Source discovery assistant response contracts and frontend handoff, if structured planning fields are surfaced.
- Backend tests for Chinese relevance, alias matching, evidence-bucket queries, mock/generic-source filtering, and conservative classification.
- Frontend candidate review may display more trustworthy ranking and source types without changing human accept/reject controls.
