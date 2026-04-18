## Context

`extract-graph` is the next business flow that still mixes request handling, orchestration, extraction, merge, and persistence concerns too close to the API/runtime path. The repository already has a Python backend foundation and a durable job-processing foundation, so this migration should reuse those primitives rather than introduce a parallel execution model. The main constraint is compatibility: existing callers and stored graph consumers should continue to see broadly stable `entities`, `relations`, and `claims` semantics even though execution ownership moves to the worker.

## Goals / Non-Goals

**Goals:**
- Move `extract-graph` execution behind a durable worker-owned job boundary.
- Keep the API responsible only for request validation, extraction job creation, and status exposure.
- Define a layered extraction pipeline with explicit stages: document input, extraction, normalization, merge, and persistence.
- Preserve current persisted graph semantics as closely as possible while making merge and normalization logic easier to extend.
- Create clear extension points for later NLP or graph-processing stages without changing the submission contract again.

**Non-Goals:**
- Changing the simulation execution model.
- Changing `generate-agents`.
- Redesigning the frontend beyond the status and invocation changes required by the new job flow.
- Reworking the storage schema for `entities`, `relations`, and `claims` beyond what compatibility requires for this migration.

## Decisions

### 1. `extract-graph` becomes an explicit worker job type

The API will stop executing graph extraction work inline. Instead, it will validate the request, create a durable extraction job, and return the job identity/status handle used by current callers.

Why:
- Reuses the existing job-processing foundation instead of introducing a second execution path.
- Gives extraction a retryable, inspectable lifecycle.
- Removes long-running graph work from the API request path.

Alternatives considered:
- Keep extraction inline in the API and only move heavy substeps to the worker. Rejected because orchestration ownership would remain split and hard to evolve.
- Build a flow specific to graph extraction outside the jobs foundation. Rejected because it would duplicate lifecycle and worker-claiming behavior already established elsewhere.

### 2. The worker owns a staged extraction pipeline

The worker handler will execute extraction through explicit internal stages:
1. Load and validate document inputs for the job.
2. Run single-document extraction to produce intermediate graph candidates.
3. Normalize extracted entities, relations, and claims into canonical merge inputs.
4. Merge normalized outputs across documents.
5. Persist the final aggregate graph and mark job outcome.

Why:
- Makes the business flow legible and testable at stage boundaries.
- Allows future NLP or graph enrichments to plug into one stage without rewriting the full handler.
- Contains failure handling and diagnostics at predictable boundaries.

Alternatives considered:
- One monolithic worker function. Rejected because it would repeat the current coupling in a different process.
- Persist every intermediate stage as a first-class external contract. Rejected for now because it increases schema and compatibility scope without immediate product value.

### 3. Compatibility is preserved through a stable persistence contract

Normalization and merge will be internal worker concerns, but persistence will target the existing graph-facing contract as closely as possible. Any necessary representation shifts will be hidden behind a persistence adapter that maps normalized aggregate results into the current `entities`, `relations`, and `claims` semantics.

Why:
- Reduces downstream churn.
- Lets the migration focus on execution ownership and pipeline clarity.
- Leaves room to improve internal modeling later without immediately forcing API or UI changes.

Alternatives considered:
- Introduce a new graph schema and migrate all consumers now. Rejected because it expands the change far beyond the job migration objective.

### 4. Merge is aggregate-first, with document-scoped intermediates

Per-document extraction results will remain document-scoped until normalization completes. Cross-document deduplication and conflict handling will happen only in the aggregate merge stage, using deterministic merge keys/rules so reruns are idempotent at the job level.

Why:
- Keeps single-document extraction simple.
- Makes merge behavior explicit and easier to tune.
- Supports future heuristics or learned normalization without changing job submission.

Alternatives considered:
- Merge opportunistically during document extraction. Rejected because it couples extraction order to final graph shape.

### 5. Status surfaces stay job-oriented

Frontend and API status reporting will remain aligned to canonical job states, optionally with lightweight extraction summary metadata, but will not expose worker-internal stage machinery as a required client contract in this change.

Why:
- Avoids accidental frontend coupling to pipeline internals.
- Keeps the migration small while still supporting required status display updates.

Alternatives considered:
- Expose every stage transition to clients immediately. Rejected because it turns an internal pipeline design into a public contract too early.

## Risks / Trade-offs

- [Merge behavior drifts from current semantics] -> Keep the persistence adapter aligned with the existing graph contract and explicitly validate compatibility during implementation.
- [Long-running extraction jobs increase operational latency visibility] -> Rely on durable job states and expose enough job status for callers to distinguish queued, running, failed, and completed states.
- [Stage boundaries add implementation structure overhead] -> Accept the extra abstraction now because it is the main lever for future NLP and graph-processing evolution.
- [Partial failures could leave inconsistent graph writes] -> Keep final persistence transactional at the aggregate-output boundary and only mark the job completed after persistence succeeds.

## Migration Plan

1. Introduce the extraction job payload/handler contract in the API and worker codepaths.
2. Implement the worker-owned staged pipeline behind the new handler.
3. Route `extract-graph` API requests to job creation instead of inline execution.
4. Update required status surfaces so callers and UI can follow the extraction job lifecycle.
5. Remove or retire the old inline extraction orchestration once the worker path is the sole entrypoint.

Rollback:
- Restore the API-to-inline execution path and stop creating new extraction jobs.
- Leave the new worker handler dormant; job-processing foundation remains intact because this change does not alter the shared lifecycle model.

## Open Questions

- Do we need to persist document-level intermediate extraction artifacts for operator debugging, or is job-level failure metadata sufficient for now?
- Should normalization/merge diagnostics be stored only in worker logs, or should a compact summary be attached to the job record?
- Is there any caller that currently assumes `extract-graph` is synchronous enough that API response semantics must be shimmed during rollout?
