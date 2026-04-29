## Why

Users may know only a vague topic, such as a brand and controversy name, and may not know the event timeline well enough to choose useful discovery settings. A search-backed briefing mode lets the source assistant perform a bounded, auditable first-pass search and generate a cited initial event brief before the user creates a formal source discovery job.

## What Changes

- Add a user-confirmed search-backed briefing mode to the source discovery assistant.
- Let users request an initial event brief from `SourceDiscoverySetupPage` using a topic, description, region, language, and optional time range.
- Run a bounded search through configured source discovery search/content providers with explicit limits on query count, result count, content fetching, timeout, and grounding context size.
- Generate a structured, cited briefing that includes an initial timeline, key actors, event stage, controversy focus, source list, evidence gaps, and recommended discovery settings.
- Allow users to apply briefing recommendations to the source discovery form, while still requiring explicit submission before creating a source discovery job.
- Keep the assistant advisory: it must not autonomously search without a user action, create discovery jobs, accept sources, create evidence packs, start grounding, or start simulation.

## Capabilities

### New Capabilities

- `search-backed-source-briefing`: Bounded search-backed initial event briefing for users who need timeline and context before formal source discovery.

### Modified Capabilities

- `source-discovery-llm-assistant`: Extend assistant modes to include user-confirmed search-backed briefing while preserving scoped grounding rules.
- `source-discovery-evidence-packs`: Extend source discovery setup flow so briefing recommendations can inform, but not submit, discovery settings.
- `backend-api-boundary`: Add Python API contracts for search-backed briefing requests, responses, limits, citations, and failure behavior.

## Impact

- Frontend: `SourceDiscoverySetupPage`, shared assistant UI, and backend client types/helpers.
- Backend: source discovery assistant service, search provider/content fetcher reuse, request limits, structured briefing response mapping, and product error handling.
- External systems: configured source discovery search provider may be called from an assistant request only after explicit user action.
- Safety: search-backed briefing results must be cited, bounded, and treated as preliminary context until the user confirms sources through the existing discovery and review workflow.
