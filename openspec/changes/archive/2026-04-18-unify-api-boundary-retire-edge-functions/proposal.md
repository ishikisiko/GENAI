## Why

The repository now has a split backend model: graph extraction and simulation already have Python API ownership, while agent generation and parts of frontend integration still depend on Supabase Edge Functions as product-facing business endpoints. That leaves API style, auth boundaries, error handling, rollout posture, and local developer workflow inconsistent right at the point where the backend foundation is mature enough to become the single contract.

## What Changes

- Move frontend product flows to target the Python API as the primary backend contract instead of calling Supabase Edge Functions for core business actions.
- Define one backend API boundary for synchronous resource operations and one backend API boundary for asynchronous task submission and status polling, with explicit rules for endpoint shape, response payloads, request IDs, and failure envelopes.
- Decide the final ownership model for `generate-agents`:
  - Python API synchronous execution if it remains a short-lived request/response operation, or
  - durable job execution if it should follow the same async model as other long-running workflows.
- Introduce a Python-owned agent generation capability so `generate-agents` no longer remains a product-critical Edge Function path.
- Standardize auth enforcement, permission checks, error payloads, structured logs, and operational observability across the Python API and worker surfaces.
- Define whether legacy Edge Functions remain as temporary compatibility wrappers or are retired from the product call chain, with explicit rollback and decommission criteria.
- Clean up outdated local development scripts, rollout notes, and README guidance that still present Edge Functions as the main product backend path.
- Do not change crisis simulation, graph extraction, or agent-generation business semantics beyond what is required to move ownership and unify contracts.

## Capabilities

### New Capabilities
- `backend-api-boundary`: Defines the canonical frontend-to-backend contract for Python-owned synchronous resources, asynchronous task submission/status endpoints, shared auth rules, error envelopes, request tracing, and compatibility-layer expectations.
- `agent-generation-pipeline`: Defines Python-owned agent generation submission, execution ownership, persistence behavior, and completion semantics for the grounding-to-simulation transition.

### Modified Capabilities
- `python-backend-foundation`: Expand the backend foundation requirements so all product-facing Python endpoints follow the same authentication, authorization, error, logging, and monitoring conventions.
- `job-processing-foundation`: Refine the async job contract so long-running product workflows use one standard submission/status model and so `generate-agents` can be evaluated consistently against that model.

## Impact

- Frontend integration in `src/`, especially the remaining `functions/v1/generate-agents` call path and any config that still assumes Edge Functions are product-facing.
- Python API and worker contracts in `backend/src/backend/entrypoints/api/`, service modules, and shared runtime conventions for auth, errors, and logging.
- Supabase Edge Functions under `supabase/functions/` that currently execute core product business logic or remain referenced by local development workflows.
- Local development and rollout documentation in `README.md`, `backend/README.md`, and backend rollout docs that still describe mixed backend ownership.
- Operational posture for request tracing, job visibility, rollback strategy, and eventual decommissioning of legacy compatibility layers.
