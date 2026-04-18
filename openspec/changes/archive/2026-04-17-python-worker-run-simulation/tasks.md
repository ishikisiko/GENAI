## 1. Job foundation and persistence

- [x] 1.1 Extend the Python job schema/models/repository with running-job heartbeat fields and stale-recovery helpers.
- [x] 1.2 Add simulation-to-job linkage in persistence so a submitted simulation run can be traced from `simulation_runs` to its durable job.
- [x] 1.3 Implement repository-level terminal update helpers that record stale-timeout and execution failures in both jobs and job attempts.

## 2. Simulation orchestration in Python worker

- [x] 2.1 Extract the current `run-simulation` request body contract and simulation execution inputs into shared Python data models/services.
- [x] 2.2 Port the simulation round loop into Python worker orchestration while preserving current writes to `simulation_runs`, `round_states`, and `metric_snapshots`.
- [x] 2.3 Add worker heartbeat updates during simulation execution and project completion/failure outcomes back onto the linked simulation run.
- [x] 2.4 Add worker-owned stale recovery for simulation jobs, including timeout failure messaging on the linked run.

## 3. API submission and status surfaces

- [x] 3.1 Add a simulation submission endpoint in the Python API that validates input, enforces active-run concurrency, creates the `simulation_runs` row, and enqueues the simulation job.
- [x] 3.2 Add a job status endpoint that returns canonical job state, failure metadata, and the linked simulation run identifier.
- [x] 3.3 Add a simulation run status endpoint that returns polling-friendly run state and progress metadata for async-submitted runs.

## 4. Frontend async simulation flow

- [x] 4.1 Replace the simulation page's synchronous `run-simulation` invocation with the new submission endpoint and local polling state.
- [x] 4.2 Update the simulation page to poll job/run status until terminal state and then refresh full run results.
- [x] 4.3 Remove browser-owned stale-run cleanup from the main frontend path once backend-owned recovery is in place.

## 5. Rollout and legacy fallback

- [x] 5.1 Add an explicit rollout gate that allows traffic to use the new async path while keeping the legacy `run-simulation` function available for rollback.
- [x] 5.2 Document the migration/rollback flow and operational expectations for heartbeat timeout, stale recovery, and legacy fallback usage.
