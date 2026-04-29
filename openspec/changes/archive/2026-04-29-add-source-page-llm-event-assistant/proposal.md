## Why

Users often begin source discovery without a clear understanding of the event timeline, key actors, terminology, or useful search angles. After discovery returns candidates, users also need help turning a ranked source list into a grounded understanding of what happened, what changed recently, which sources support each stage, and where evidence remains thin or conflicting.

## What Changes

- Add a unified LLM assistant entry point across the source discovery workflow.
- Support search planning mode on `SourceDiscoverySetupPage`, using case topic, description, region, language, and optional time range to suggest search directions, keywords, source types, language variants, and initial discovery settings.
- Support source interpretation mode on `CandidateSourcesReviewPage`, using the current discovery job's candidate sources as the grounding scope for timeline, event-stage, conflict, evidence-gap, and follow-up-search questions.
- Require source-grounded answers to include citations and to distinguish reporting dates from event dates when timeline claims are made.
- Return clear insufficient-evidence responses when the assistant cannot answer reliably from available context.
- Keep all source acceptance, evidence pack creation, grounding, and simulation actions under existing explicit human control.

## Capabilities

### New Capabilities

- `source-discovery-llm-assistant`: Context-aware assistant behavior for search planning and source-grounded event interpretation in the source discovery workflow.

### Modified Capabilities

- `source-discovery-evidence-packs`: Extend source discovery frontend flow requirements so setup and candidate review pages expose the assistant without bypassing human review.
- `backend-api-boundary`: Add Python API contracts for submitting assistant requests and receiving structured, grounded assistant responses.

## Impact

- Frontend: `SourceDiscoverySetupPage`, `CandidateSourcesReviewPage`, shared assistant UI components, and backend client helpers.
- Backend: Python API endpoint, request/response contracts, source-discovery service integration, LLM client usage, and candidate-source grounding assembly.
- Data and jobs: no new durable job type is required for the first version; assistant requests are bounded request-scoped API operations.
- Safety: assistant output must remain scoped to the current case or discovery job and must not automatically accept sources, create evidence packs, start grounding, or start simulation.
