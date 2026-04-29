## Context

The source discovery assistant currently supports search planning from case/form context and source interpretation from an existing discovery job's candidate sources. That leaves a gap for users who know only a vague topic and need an initial, cited event timeline before they can choose useful discovery settings.

The existing source discovery pipeline already has query expansion, configured search providers, content fetching, classification/scoring, and candidate persistence. Search-backed briefing should reuse the same provider and fetcher boundaries, but it should not persist candidates or create a discovery job until the user explicitly submits the normal discovery form.

## Goals / Non-Goals

**Goals:**

- Add a user-triggered briefing mode that performs bounded search and returns a cited preliminary event brief.
- Help users understand initial timeline, actors, controversy focus, event stage, source landscape, and evidence gaps before formal discovery.
- Keep search execution controlled by server-side limits and existing provider configuration.
- Let users apply recommended discovery settings to the form without automatically submitting the job.
- Preserve the existing human review model for candidate acceptance and evidence pack creation.

**Non-Goals:**

- Letting the LLM freely choose arbitrary tools or unlimited search loops.
- Persisting briefing results as accepted candidates or evidence pack sources.
- Replacing the formal source discovery job, candidate review, evidence pack, grounding, or simulation workflows.
- Guaranteeing a complete timeline from a small first-pass search.

## Decisions

### Decision: Add a third assistant mode, not a separate chatbot

Extend the existing source discovery assistant API with a `search_backed_briefing` mode. This keeps UI and client concepts unified while making grounding behavior explicit and testable.

Alternatives considered:

- Separate briefing endpoint. This would isolate behavior but duplicate assistant request/response wiring.
- Free-form agent tool calls. This would be flexible but would be harder to audit, limit, and explain.

### Decision: Server owns the search plan and limits

The backend should derive or accept a bounded set of search queries, then enforce maximum query count, results per query, total fetched sources, content length, and request timeout. Defaults should be conservative, with configuration constants or settings rather than user-controlled unlimited values.

Alternatives considered:

- Let the LLM run iterative searches. This increases cost, latency, and audit complexity.
- Let the frontend call search providers directly. This exposes provider behavior and secrets outside the Python API boundary.

### Decision: Briefing context is transient unless the user starts discovery

Search-backed briefing should return source summaries and citations in the assistant response but should not write `source_candidates` or create `source_discovery_jobs`. The user can apply recommended settings and then submit the existing form to create a durable discovery job.

Alternatives considered:

- Persist briefing sources as candidates immediately. This blurs the difference between preliminary research and formal discovery review.

### Decision: Use citations as the trust boundary

All timeline, actor, stage, and controversy claims in the briefing must cite searched sources. If search returns too little evidence, the response should mark itself insufficient and focus on follow-up searches.

Alternatives considered:

- Allow uncited LLM background knowledge. This is useful for brainstorming but unsafe for event timelines and current controversies.

## Risks / Trade-offs

- Search provider cost or rate limits -> enforce small query/result caps and reuse existing provider rate-limit behavior.
- Weak first-pass results -> return insufficient-evidence briefing with follow-up queries instead of overclaiming.
- Users treat preliminary brief as verified truth -> label briefing as preliminary and require formal discovery/review before evidence pack use.
- Prompt or context bloat -> cap fetched content and prefer source metadata, snippets, excerpts, and short extracted passages.
- Duplicate work with discovery jobs -> keep briefing lightweight and use it to improve discovery settings rather than replacing discovery.
- Provider unavailable -> return the shared product error envelope and leave search planning mode available as a non-search fallback.
