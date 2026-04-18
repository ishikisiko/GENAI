## 1. Extraction job contract and API submission

- [x] 1.1 Define the graph extraction job type, payload shape, and shared repository/service interfaces needed for durable job creation
- [x] 1.2 Update the `extract-graph` API path so it validates requests, creates an extraction job, and returns the job-oriented response expected by existing callers
- [x] 1.3 Update the extraction status/query surface and only the required frontend/status plumbing so callers can observe the asynchronous job lifecycle

## 2. Worker-owned extraction pipeline

- [x] 2.1 Implement the worker handler that claims graph extraction jobs and drives the staged pipeline context
- [x] 2.2 Implement document input loading and single-document extraction as separate worker pipeline stages
- [x] 2.3 Implement normalization and aggregate merge stages for entities, relations, and claims before final persistence

## 3. Persistence and compatibility

- [x] 3.1 Add the persistence adapter that writes merged extraction outputs back into the existing `entities`, `relations`, and `claims` contract
- [x] 3.2 Ensure extraction jobs report canonical completion and failure outcomes, including the metadata needed for required status displays and operator diagnostics
- [x] 3.3 Remove or retire the old inline `extract-graph` orchestration path once the worker path is the sole execution flow

## 4. Cutover safety and follow-up

- [x] 4.1 Add implementation-time compatibility checks or fixtures that compare worker-produced graph outputs against current persisted semantics for representative extraction cases
- [x] 4.2 Document rollout and rollback steps for switching `extract-graph` from API-owned execution to worker-owned execution
