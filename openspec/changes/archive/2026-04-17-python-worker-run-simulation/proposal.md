## Why

`run-simulation` still runs as a long-lived synchronous request, which makes the UI wait on a fragile edge invocation and pushes execution, heartbeat, and stale-run cleanup into one request path. The repository already has a Python backend and durable job foundation, so this is the point to move simulation execution onto that worker model without changing the simulation business logic itself.

## What Changes

- Add an asynchronous simulation submission flow where the API creates both a `simulation_runs` row and a durable `jobs` row instead of executing the full simulation inline.
- Add Python worker handling for simulation jobs, including round-by-round execution, periodic heartbeat updates, stale-job recovery, and durable failure recording.
- Add API endpoints to query job status and simulation run status so the frontend can poll instead of holding a long request open.
- Update the frontend simulation flow from "call `run-simulation` and wait" to "create simulation job, poll status, then reload run data".
- Preserve the existing meanings of `simulation_runs`, `round_states`, and `metric_snapshots`, and keep the legacy synchronous path available temporarily for rollback or gradual rollout.
- Exclude `extract-graph` and `generate-agents` from this migration.
- Keep the existing simulation prompts, round logic, and domain behavior unchanged in this change.

## Capabilities

### New Capabilities
- `simulation-job-execution`: Asynchronous submission, execution, status query, and recovery semantics for simulation runs backed by the Python API and worker.

### Modified Capabilities
- `job-processing-foundation`: Extend durable job lifecycle requirements to cover worker heartbeat tracking, stale running-job recovery, and failure metadata needed by long-running simulation execution.

## Impact

- Python backend API routes, worker handlers, and shared simulation orchestration code.
- Job persistence schema and repositories for simulation-specific payloads and runtime metadata.
- Frontend simulation page flow and polling behavior.
- Existing Supabase `run-simulation` edge function, which remains temporarily for fallback/gradual rollout.
