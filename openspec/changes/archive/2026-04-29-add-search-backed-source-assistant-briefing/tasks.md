## 1. Contracts and Limits

- [x] 1.1 Extend assistant mode contracts with `search_backed_briefing`.
- [x] 1.2 Add structured briefing response fields for source summaries, key actors, controversy focus, recommended discovery settings, briefing citations, and insufficient-evidence details.
- [x] 1.3 Define backend-owned limits for query count, results per query, total sources, fetched content length, and request timeout.
- [x] 1.4 Validate that briefing requests include enough topic or case context and reject unbounded client-provided limits.

## 2. Backend Briefing Execution

- [x] 2.1 Extend the source discovery assistant service to build briefing search queries from topic, case, region, language, time range, and user question.
- [x] 2.2 Reuse configured source discovery search provider and content fetcher for bounded briefing search.
- [x] 2.3 Deduplicate briefing sources by canonical URL or content hash before sending context to the LLM.
- [x] 2.4 Build bounded LLM context from searched source metadata, snippets, excerpts, fetched content, and publication dates.
- [x] 2.5 Map LLM output into structured briefing responses and enforce citation/insufficient-evidence behavior.
- [x] 2.6 Ensure briefing execution does not persist source candidates, create source discovery jobs, create evidence packs, start grounding, or start simulation.

## 3. Frontend Integration

- [x] 3.1 Add TypeScript types and backend client support for `search_backed_briefing` request and response fields.
- [x] 3.2 Update the shared assistant UI to expose distinct actions for search planning and search-backed briefing on setup pages.
- [x] 3.3 Render briefing timeline, key actors, controversy focus, source summaries, citations, evidence gaps, follow-up searches, and recommended discovery settings.
- [x] 3.4 Allow explicit user action to apply recommended briefing settings to the discovery form.
- [x] 3.5 Make UI copy distinguish preliminary search-backed briefing from confirmed candidate review evidence.

## 4. Tests and Verification

- [x] 4.1 Add backend tests for briefing validation, provider limit enforcement, deduplication, insufficient-evidence fallback, citation mapping, and no-persistence side effects.
- [x] 4.2 Add endpoint tests for search-backed briefing API behavior and product error envelopes.
- [x] 4.3 Add frontend coverage or build-time verification for briefing rendering and explicit apply-to-form behavior.
- [x] 4.4 Verify source discovery jobs are still created only through the existing discovery form submit action.
- [x] 4.5 Run backend tests, backend lint, frontend lint, and frontend build; record any environment limitations.
