## Context

Source discovery already has a deterministic query expander, search provider abstraction, content fetcher, simple source classifier, relevance scorer, and human review workflow. Recent scoring changes reduce generic-term false positives, but Chinese event topics such as `西贝预制菜事件` can still be treated as a single opaque token, causing genuinely relevant Chinese sources to receive low relevance when titles use variants such as `预制菜风波`, `预制菜之争`, or `罗永浩吐槽西贝事件`.

The current query expansion also mixes source intent into broad terms. A request for social-media evidence can retrieve pages about Chinese social-media platforms instead of event-specific original posts, and simple classification can label media reports as official when the article mentions official statements or regulators.

## Goals / Non-Goals

**Goals:**

- Improve Chinese-language event relevance by matching core entities, event phrases, aliases, and short Chinese token sequences.
- Generate discovery queries by evidence bucket so formal discovery seeks timeline, official response, regulatory context, social-media evidence, and downstream impact coverage.
- Filter or demote mock/test results and generic background pages when they do not provide event-specific evidence.
- Make source classification conservative and domain-aware so official, media, social, and research classifications remain interpretable.
- Allow assistant planning output to provide structured entities, aliases, and evidence buckets as advisory discovery context.

**Non-Goals:**

- No automatic candidate acceptance or rejection.
- No mandatory LLM judging for every candidate.
- No new external search provider requirement.
- No automatic rescore of historical candidates unless explicitly run by an operator.
- No replacement of the existing source discovery setup and review pages.

## Decisions

1. Use deterministic Chinese tokenization and alias expansion before semantic support.

   The scorer will derive relevance terms from topic, case description, and optional assistant planning hints. For CJK text, it will create stable matching units such as known entity phrases, alias phrases, and bounded character n-grams rather than relying only on whitespace splitting. This preserves deterministic tests and avoids making embeddings mandatory.

   Alternative considered: use a full Chinese segmentation dependency. That can improve token quality, but it adds packaging and dictionary behavior that may be harder to keep stable in local and CI environments. A lightweight phrase and n-gram approach is sufficient for crisis event matching and can be replaced later.

2. Model query expansion as evidence buckets.

   Query generation will produce labeled searches for timeline, official response, regulatory context, social-media evidence, and downstream impact. Each bucket will combine core entities, aliases, and bucket-specific terms. This keeps query intent explicit and makes coverage gaps easier to inspect after a job completes.

   Alternative considered: keep the current generic query list and tune constants. That does not address the main failure mode where "social media" retrieves platform background pages instead of event evidence.

3. Treat assistant planning context as advisory structured hints.

   The assistant can expose `core_entities`, `event_aliases`, and `evidence_buckets` in structured suggestions. Discovery may use these hints to enrich query generation and scoring, but the user still explicitly starts discovery and reviews candidates.

   Alternative considered: have the assistant directly create discovery jobs or accept candidates. That would bypass existing human review controls and conflict with the current workflow.

4. Keep candidate quality filtering explainable and conservative.

   Mock results are allowed only when the mock provider is explicitly configured. Real discovery should filter or mark mock/test URLs. Generic background pages can be persisted only with low relevance and low grounding value unless they contain event-specific core entities or aliases.

   Alternative considered: hard-block all encyclopedic/background pages. That could remove useful regulatory or platform context, so the gate should focus on event-specific evidence and score impact.

5. Make classification domain- and URL-aware.

   Official classification should require official domains or strong official-source signals, not just quoted official language inside media content. Media, social, and research classifications should be determined using provider metadata, URL/domain patterns, source type, and content signals.

   Alternative considered: classify only by search-provider source type. Provider labels are useful but not always reliable enough for authority scoring.

## Risks / Trade-offs

- [Risk] Lightweight Chinese tokenization may still miss uncommon aliases or slang. -> Mitigation: include assistant-derived aliases and regression tests for known variants.
- [Risk] Evidence-bucket searches increase provider calls. -> Mitigation: keep backend-owned query and result limits, dedupe across buckets, and cap fetched candidates.
- [Risk] Conservative classification may reduce authority scores for legitimate official statements republished by media. -> Mitigation: classify the page as media while preserving quoted official claims in previews and citations.
- [Risk] Filtering generic sources could remove useful context. -> Mitigation: demote rather than discard when a source has contextual value but lacks direct event evidence.
- [Risk] Historical candidates keep older review decisions after rescoring. -> Mitigation: keep review status human-owned and add tests/docs for score-only recalculation behavior if a rescore command is implemented.

## Migration Plan

- Deploy backend scoring, query expansion, filtering, and classification changes behind existing discovery contracts.
- Update assistant response parsing to accept new structured planning fields as optional, backwards-compatible fields.
- Restart API and worker processes so new source discovery jobs use the updated pipeline.
- Existing candidates keep prior scores until an operator runs a rescore workflow; evidence pack snapshots remain historical unless separately regenerated.
