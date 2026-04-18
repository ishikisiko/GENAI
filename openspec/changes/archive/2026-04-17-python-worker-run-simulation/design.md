## Context

The current simulation flow is driven by `supabase/functions/run-simulation`, which performs request validation, loads case context, executes the round loop inline, writes `simulation_runs`, `round_states`, and `metric_snapshots`, and returns only after the full run finishes. The frontend waits on that long request and also contains stale-run cleanup logic, so execution ownership is split across the edge function, the browser, and the database tables.

The repository now also contains a Python backend foundation with:

- FastAPI entrypoints for health and operational endpoints.
- A polling worker runtime.
- Durable `jobs` and `job_attempts` persistence.

This change needs to move `run-simulation` onto that backend foundation while preserving the existing result model and business behavior:

- `simulation_runs`, `round_states`, and `metric_snapshots` remain the source of truth for simulation output.
- `extract-graph` and `generate-agents` stay on their current paths.
- Simulation prompts, round logic, and intervention semantics do not change.
- The legacy synchronous path remains available temporarily for rollback or gradual rollout.

## Goals / Non-Goals

**Goals:**

- Replace synchronous simulation execution with API submission plus worker execution.
- Ensure the API creates both the durable simulation run record and the durable background job.
- Let the worker own round execution, heartbeat updates, stale-run recovery, and failure recording.
- Provide polling-friendly job status and run status interfaces for the frontend.
- Preserve current simulation result tables and their downstream consumers.
- Keep a temporary fallback path to the legacy synchronous invocation.

**Non-Goals:**

- Changing simulation prompts, scoring, or round-by-round business behavior.
- Migrating `extract-graph` or `generate-agents`.
- Replacing `simulation_runs`, `round_states`, or `metric_snapshots` with a new result model.
- Introducing realtime subscriptions as a requirement for progress updates.

## Decisions

### 1. The Python API becomes the submission boundary for simulation execution

The new submission flow will move from direct browser-to-edge execution to a backend API endpoint that validates the request, enforces "one active run per case" semantics, creates a `simulation_runs` row, creates a `jobs` row, and returns both identifiers to the client.

The API response will become the contract the frontend uses to start polling:

- `run_id`
- `job_id`
- initial job status
- initial run status

Rationale:

- The run record exists immediately for downstream reads and comparison pages.
- The job record becomes the durable execution lease owned by the worker system.
- The frontend no longer needs to keep a long request open.

Alternatives considered:

- Create only a job and let the worker create `simulation_runs`.
  Rejected because the UI and downstream readers need a stable run identity immediately, and rollback to the legacy path becomes harder.
- Keep browser-to-edge submission and only move stale cleanup to the worker.
  Rejected because it preserves the fundamental long-request failure mode.

### 2. The simulation round loop is extracted into shared Python orchestration code

The worker handler for the simulation job type will execute the existing simulation lifecycle in Python using shared services:

- load case, agents, claims, and entities
- transition the run to `running`
- execute rounds sequentially
- write `round_states` and `metric_snapshots` with the existing semantics
- finalize `simulation_runs` as `completed` or `failed`

The implementation should keep the execution logic isolated from the transport layer so the same orchestration service can be called from worker code and, if needed, a temporary legacy bridge.

Rationale:

- Transport concerns move to API/worker entrypoints.
- The execution logic becomes testable without HTTP wrappers.
- The data-write contract for existing UI pages remains unchanged.

Alternatives considered:

- Have the worker call the existing edge function.
  Rejected because it preserves a nested long-running request path and duplicates retry/error handling.
- Rewrite the simulation output model at the same time.
  Rejected because it would expand scope and violate the request to preserve current table semantics.

### 3. Job liveness is tracked explicitly and projected onto the simulation run

Long-running simulation jobs need explicit liveness beyond the existing `locked_at` timestamp. The backend will extend job persistence to record heartbeat updates for running jobs and will continue updating `simulation_runs.last_heartbeat_at` so existing run-oriented consumers remain meaningful.

The worker will:

- heartbeat the claimed job while a simulation is running
- heartbeat the linked simulation run on each round and on terminal transitions
- write terminal failure metadata to both the job attempt and the linked simulation run

Rationale:

- Job-level heartbeat enables worker-owned stale-job recovery.
- Run-level heartbeat preserves current run visibility and stale-run meaning.
- Failure details remain queryable from both operational and product-oriented views.

Alternatives considered:

- Use only `simulation_runs.last_heartbeat_at`.
  Rejected because stale recovery belongs to the job system and should not depend on a feature-specific table alone.
- Use only `jobs.locked_at`.
  Rejected because claim time is not a sufficient signal for long-running work.

### 4. Stale recovery is owned by the worker runtime, not by the browser or request handlers

The current stale-run cleanup appears in both the edge function and the frontend page. The new design moves stale detection and recovery into backend-owned execution paths:

- before or during polling cycles, workers scan running simulation jobs whose heartbeat is older than a configured timeout
- stale jobs are marked `failed`
- the active attempt is closed with structured failure details
- the linked `simulation_runs` row is marked `failed` with a timeout/interruption message

Rationale:

- Recovery happens even if no user is actively viewing the page.
- Runtime ownership becomes explicit and observable.
- Browser code stops mutating authoritative execution state.

Alternatives considered:

- Keep frontend cleanup as the primary recovery path.
  Rejected because it depends on page visits and duplicates backend logic.
- Keep API submission endpoints responsible for cleanup.
  Rejected because stale jobs may need recovery even when no new submissions arrive.

### 5. Rollout is gated so the legacy path remains available

The migration will preserve the current `run-simulation` path for a limited period behind an explicit rollout mechanism. The preferred default is:

- frontend feature flag or backend-configured route selection uses the new async path
- legacy edge function remains callable for rollback or controlled exposure

The new backend path should not delete or silently repurpose the old function during this change.

Rationale:

- Rollback stays low-risk.
- Gradual adoption is possible while validating parity.

Alternatives considered:

- Immediate hard cutover.
  Rejected because the execution path is changing across browser, API, worker, and persistence.

## Risks / Trade-offs

- [Behavior drift between the TypeScript edge function and new Python worker implementation] -> Keep the round loop contract narrow, port existing execution rules directly, and explicitly preserve current write semantics for `round_states` and `metric_snapshots`.
- [Run and job state can diverge during partial failures] -> Make API submission transactional where possible and ensure worker terminal handlers always update both job state and linked run state in the same service boundary.
- [Polling can increase request volume] -> Return compact status payloads and keep polling endpoints separate from heavy run detail queries.
- [Stale recovery can incorrectly fail slow but healthy work] -> Use configurable timeouts and update heartbeats at deterministic points in the simulation loop.
- [Fallback path can mask bugs if left indefinitely] -> Make the rollout flag explicit and treat legacy retention as temporary migration support only.

## Migration Plan

1. Extend the backend job model/repository for heartbeat updates and stale-job recovery.
2. Add simulation-specific persistence linkage and API endpoints for submission and status queries.
3. Port the simulation execution loop into Python worker code while preserving current result-table writes.
4. Update the frontend simulation page to submit jobs and poll status instead of waiting on the synchronous edge function.
5. Gate rollout so the legacy `run-simulation` function remains available during validation.
6. After parity is established, remove browser-side stale cleanup and retire the legacy path in a later change.

Rollback:

- Switch traffic back to the legacy synchronous path via the rollout gate.
- Leave new job/run records intact for inspection; do not delete them during rollback.
- Because result tables are unchanged, existing readers continue to work in either mode.

## Open Questions

- Whether the frontend should poll separate `job` and `run` endpoints, or a single composed status endpoint that returns both objects in one response.
- Whether active-run conflict enforcement should remain "one running or pending run per case" or stay strictly "one running run per case" during the migration window.
