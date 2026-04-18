## Context

The backend foundation is no longer purely preparatory. The Python API already owns async simulation submission/status and async graph extraction submission/status, with shared logging, request correlation, and error taxonomy in place. At the same time, the frontend and local developer workflow still treat Supabase Edge Functions as part of the main product backend surface:

- `run-simulation` has a Python API + worker path, but rollback notes and frontend gating still preserve the old Edge Function flow.
- `extract-graph` has moved to Python API + worker, but local docs still describe Edge Functions as a primary runtime.
- `generate-agents` remains a direct frontend call to `functions/v1/generate-agents`.
- Frontend integration mixes `VITE_BACKEND_URL`, `EDGE_FN_BASE`, and Edge Function-style headers.
- Python API error/logging conventions exist, but auth enforcement and operator/product boundary rules are not yet defined as one contract.

This change is the convergence step: the Python API becomes the canonical product-facing backend boundary, Edge Functions stop owning core business responsibilities, and the remaining mixed conventions are cleaned up without reworking domain semantics.

## Goals / Non-Goals

**Goals:**
- Make the Python API the single product-facing backend contract for frontend business flows.
- Define a consistent contract split between synchronous API operations and asynchronous job-backed operations.
- Move `generate-agents` off the product-critical Edge Function path.
- Standardize auth handling, permission boundaries, error payloads, request tracing, and operational logging across Python API and worker paths.
- Decide the disposition of legacy Edge Functions and document explicit rollback/decommission rules.
- Remove local scripts and docs that still present the mixed Edge Function model as the default.

**Non-Goals:**
- Rewriting simulation, graph extraction, or agent generation business semantics.
- Redesigning the entire URI space into a new versioned API.
- Introducing a new end-user role model, new product permissions, or a new external observability vendor.
- Adding unrelated product features while touching these flows.

## Decisions

### 1. Python API becomes the only primary product backend surface

Frontend-owned business actions will target Python API endpoints, not Supabase Edge Functions. Supabase remains the owner of Postgres, Auth, and RLS, but product orchestration moves behind the Python API and worker boundary.

This means:
- frontend pages use `BACKEND_API_BASE` for backend-owned operations
- Edge Functions are no longer treated as first-class product endpoints
- any remaining Edge Functions are explicitly marked as temporary compatibility paths or deleted

Alternatives considered:
- Keep mixed ownership and migrate opportunistically later. Rejected because the repository already has enough Python backend surface that the remaining split mostly creates inconsistency, not flexibility.
- Move all backend logic back behind Edge Functions. Rejected because it would undo the worker foundation and the shared runtime conventions already established in Python.

### 2. The API contract is unified by execution model, not by forcing a full URI redesign

This change standardizes behavior and response shape first, while keeping path churn minimal.

Synchronous operations:
- complete within the request/response cycle
- return final domain results directly
- do not create durable job rows
- use ordinary 2xx success responses and the shared error envelope on failure

Asynchronous operations:
- create a durable job and return immediately
- expose canonical job metadata plus domain-specific status references
- use `GET /api/jobs/{job_id}` as the operator-facing status surface
- keep domain status endpoints for product polling where the UI needs domain-specific progress detail

The existing async endpoints for simulation and graph extraction stay in place unless a path change is required to remove ambiguity. The convergence target is a shared submission/status contract, not cosmetic URI churn.

Alternatives considered:
- Redesign every endpoint into a new nested REST hierarchy in the same change. Rejected because it adds migration noise without changing the core boundary problem.
- Keep each workflow with its own bespoke async contract. Rejected because it preserves the fragmentation this change is supposed to remove.

### 3. `generate-agents` moves to a synchronous Python API endpoint

The current `generate-agents` flow performs one request-scoped LLM generation, replaces `agent_profiles`, updates the case status, and then navigates the user into simulation. That is materially different from graph extraction and simulation, which already justify durable jobs because they are longer-running, multi-stage, or worker-owned.

The recommended design is:
- add a Python API endpoint for agent generation
- keep request and result semantics close to the current Edge Function behavior
- return the generated agent set plus the updated case status in one synchronous response
- let the frontend continue the current immediate navigation behavior after success

Decision rule for future work:
- bounded, single-request workflows stay synchronous
- long-running or worker-owned workflows use the job system

Alternatives considered:
- Move `generate-agents` into the job system now. Rejected because it adds job plumbing, polling, and state coordination without solving a present reliability problem.
- Keep `generate-agents` on the Edge Function indefinitely. Rejected because it leaves the frontend/API boundary split exactly where this change is meant to close it.

### 4. Shared auth, permission, error, and observability conventions are enforced in the Python API

The Python API will use one shared request-context layer for:
- request ID propagation
- auth header parsing and validation rules
- separation between product endpoints and operator endpoints
- uniform error envelopes
- structured log fields that correlate API requests, worker jobs, and downstream failures

Scope for this change:
- preserve the current product auth model rather than inventing a new one
- require product endpoints to flow through one shared auth dependency instead of ad hoc header handling
- keep `/health/*` and `/ops` on a separate operational boundary
- include request correlation data in both success-path logs and failure payloads

This is a contract cleanup, not an auth-model redesign. The backend should become stricter and more uniform about how the existing access model is interpreted.

Alternatives considered:
- Leave auth and permission checks implicit until a future product-auth project exists. Rejected because the mixed boundary is already forcing endpoint-by-endpoint behavior drift.
- Introduce a full new user/role system here. Rejected because it is materially larger than the problem being solved.

### 5. Legacy Edge Functions are temporary compatibility adapters, not long-term dual ownership

The repository may retain selected Edge Functions for rollback during rollout, but only under explicit rules:
- they are compatibility-only, not the documented primary path
- they must not diverge in business behavior from the Python-owned path
- they should forward or fail fast rather than remain independent business implementations where practical
- each retained function needs a removal criterion and cleanup task

Recommended disposition:
- `generate-agents`: replace with Python API ownership and remove the old Edge Function once the frontend cutover is complete
- `extract-graph` and `run-simulation`: keep only if rollback coverage is still required, otherwise retire from product docs and local defaults immediately

Alternatives considered:
- Preserve all three Edge Functions as permanent parallel entrypoints. Rejected because it doubles the contract surface and weakens operational clarity.
- Delete every legacy function before frontend cutover. Rejected because it removes rollback flexibility too early.

### 6. Local development defaults move to the Python-owned path

Repo docs and scripts should describe:
- backend API + worker as the normal product backend runtime
- Edge Functions as legacy compatibility tooling only when still needed
- environment variables and frontend config in terms of backend ownership first

Cleanup includes:
- removing stale README language that says all three Edge Functions are part of the main product stack
- updating rollout docs to reflect the converged end state, not just migration waypoints
- pruning scripts or flags that only existed to support the old mixed ownership model

## Risks / Trade-offs

- [A synchronous `generate-agents` request grows slower over time] → Keep the endpoint contract narrow and explicit; if it later exceeds acceptable latency, it can move into the job system behind the same Python API boundary without reopening the Edge Function path.
- [Temporary compatibility wrappers drift from the Python path] → Treat wrappers as forwarders or short-lived rollback-only paths with explicit removal criteria.
- [Frontend migration leaves inconsistent API clients or headers behind] → Centralize backend request helpers so pages stop constructing backend/Edge Function requests independently.
- [Auth tightening breaks local workflows] → Preserve the current access model semantics during this change and document the exact local headers/env expectations.
- [Operational visibility remains split between domain status and job status] → Keep `GET /api/jobs/{job_id}` as the canonical operational surface and document domain status endpoints as product-facing projections.

## Migration Plan

1. Define the shared Python API contract for synchronous and asynchronous endpoints, including error shape, request IDs, and auth/operator boundary rules.
2. Add the Python-owned `generate-agents` endpoint and migrate the frontend grounding flow to call it through a shared backend client.
3. Align simulation and graph-extraction frontend integrations with the unified backend client and async response conventions.
4. Reclassify any remaining Edge Functions as compatibility-only paths, then remove or forward them according to the chosen rollback posture.
5. Update local development docs, rollout docs, and scripts so the Python-owned path is the documented default.

Rollback:
- frontend can temporarily point back to compatibility wrappers only while they are intentionally retained
- backend-owned tables and job records remain valid because this change does not redefine core business data
- if rollback is required, the repo documentation must still describe which compatibility functions remain deployable and under what conditions

## Open Questions

- Should retained rollback wrappers stay in-repo until the first stable release after cutover, or should they be removed immediately once the frontend is switched? This is a release-management choice, not an architectural blocker.
