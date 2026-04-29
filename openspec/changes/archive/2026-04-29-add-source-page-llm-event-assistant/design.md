## Context

Source discovery currently asks users to provide topic, description, region, language, time range, source types, and max source count before creating an asynchronous discovery job. Candidate review then presents ranked candidate sources, score dimensions, previews, semantic fragments when available, and human review controls for accepting or rejecting candidates before evidence pack creation.

This change adds a bounded, request-scoped LLM assistant to that workflow. The assistant must help users plan searches before enough sources exist, and help users interpret candidate sources after discovery has produced a grounding set. The existing Python API is the primary product backend contract, and existing LLM configuration and client patterns should be reused.

## Goals / Non-Goals

**Goals:**

- Provide one assistant product entry point across source discovery setup and candidate review.
- Support two context-aware modes: search planning before discovery and source-grounded interpretation after candidate sources exist.
- Return structured assistant output that the UI can render as suggestions, timeline stages, citations, conflicts, evidence gaps, and follow-up search directions.
- Keep assistant behavior bounded to the current case, discovery settings, or discovery job.
- Preserve existing human-in-the-loop review controls for accepting candidates, creating evidence packs, grounding, and simulation.

**Non-Goals:**

- Creating a general-purpose chatbot for arbitrary questions.
- Treating search planning suggestions as verified event facts.
- Automatically accepting or rejecting candidates.
- Automatically creating evidence packs, starting grounding, or starting simulation.
- Introducing a durable background job for the first assistant version.

## Decisions

### Decision: Use one assistant API with explicit mode

Expose a Python API operation for source discovery assistant requests with an explicit mode such as `search_planning` or `source_interpretation`. This keeps the frontend integration simple while making grounding rules testable.

Alternatives considered:

- Separate endpoints per page. This would make page-specific behavior obvious but duplicate contracts and UI client code.
- One free-form chat endpoint. This would be flexible but too easy to misuse outside the source discovery workflow.

### Decision: Treat assistant calls as synchronous request-scoped operations

Assistant answers should run as bounded API calls and return final structured responses. The first version does not need durable job tracking because the expected prompts are scoped to form fields or a bounded candidate set.

Alternatives considered:

- Durable assistant jobs. This is better if future timeline synthesis becomes long-running across many documents, but it adds polling and lifecycle complexity before there is evidence it is needed.

### Decision: Enforce different grounding rules by mode

Search planning mode may use case and discovery form context to suggest query directions, keywords, actors, source types, language variants, and time ranges, but it must not present unsupported event claims as confirmed facts.

Source interpretation mode must assemble context from the current discovery job's candidates and require citations for event timeline, stage, conflict, and evidence-gap claims. Timeline output must distinguish source publication time from event occurrence time when possible.

Alternatives considered:

- Reuse the same prompt rules everywhere. This would blur the difference between exploratory search guidance and source-grounded factual interpretation.

### Decision: Return structured assistant output instead of plain text only

The response should include answer text plus structured fields for search suggestions, timeline items, event stages, citations, conflicts, evidence gaps, and follow-up searches when relevant. This lets the UI offer apply-to-form actions on setup and source-linked evidence review on candidate pages.

Alternatives considered:

- Plain text responses only. This is faster to build but makes citations, form-fill actions, and timeline rendering fragile.

### Decision: Reuse existing candidate content and semantic fragments when available

Source interpretation should use candidate metadata, excerpts/content, claim previews, stakeholder previews, published timestamps, and matched fragments when available. If semantic fragment recall is unavailable, the assistant can still use bounded candidate excerpts and metadata.

Alternatives considered:

- Require semantic recall for all assistant answers. This would block useful answers in environments without embeddings or vector search.

## Risks / Trade-offs

- Hallucinated facts -> constrain prompts by mode, require citations for source-grounded answers, and return insufficient-evidence responses when candidate context cannot support an answer.
- Timeline confusion -> distinguish reporting dates from event dates and include the source used for each timeline point.
- Over-large prompts -> bound the candidate context by score, review status, freshness, and fragment count; truncate content to safe excerpts.
- User over-trusts search planning -> label planning output as search guidance and prevent it from being rendered as confirmed timeline facts.
- LLM latency -> keep calls synchronous initially but show loading states and maintain stable error handling through the existing API error envelope.
- Source review automation creep -> do not expose assistant actions that mutate candidate review, evidence pack, grounding, or simulation state.
