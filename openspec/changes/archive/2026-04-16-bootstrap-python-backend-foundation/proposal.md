## Why

The current system relies on Supabase Edge Functions for backend execution, which is sufficient for the existing flow but does not provide a durable foundation for a larger Python service boundary, background workers, or standardized operational concerns. We need to build the "new world" first so later migrations can happen incrementally without forcing an immediate cutover of business logic or frontend integration.

## What Changes

- Introduce a new Python backend project skeleton with clear API, worker, configuration, logging, error handling, and database access layers.
- Define a baseline service architecture that keeps Supabase for Postgres, Auth, and RLS, while allowing the Python backend to own application orchestration and background job execution.
- Add foundational task infrastructure with `jobs` and `job_attempts` tables, a canonical task lifecycle, and worker-safe state transitions.
- Add health check and basic operations endpoints for service readiness, liveness, and operational introspection.
- Preserve existing frontend call chains, prompt behavior, and current Edge Function business logic during this change.

## Capabilities

### New Capabilities
- `python-backend-foundation`: Establishes the Python service structure, shared runtime conventions, and Supabase integration boundary.
- `job-processing-foundation`: Defines durable job tables, status transitions, and worker execution semantics for asynchronous tasks.
- `backend-operations`: Defines health and operational endpoints required to run and observe the new backend safely.

### Modified Capabilities

None.

## Impact

- Adds a new Python backend workspace and supporting package/dependency management.
- Adds shared application modules for API routing, worker runtime, config loading, logging, error modeling, and database access.
- Adds new database schema artifacts for `jobs` and `job_attempts`.
- Establishes architecture rules for how the Python backend, Supabase Postgres/Auth/RLS, and optional Realtime interact.
- Creates a foundation for later business migrations without changing current frontend contracts in this change.
