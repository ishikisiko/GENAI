## Context

The repository currently centers on a frontend plus local Supabase services, with backend execution living in Supabase Edge Functions. That arrangement keeps the current product running, but it mixes durable platform concerns with short-lived function execution and leaves no standard place for a Python API service, background workers, shared configuration, or operational conventions.

This change introduces a parallel backend foundation instead of a migration. Existing frontend call paths, prompts, business rules, and current Edge Function behavior remain unchanged. The new backend is additive and will initially exist as infrastructure that later changes can adopt incrementally.

Primary constraints:

- Supabase remains the platform boundary for Postgres, Auth, and RLS.
- The new backend must be able to run both synchronous API handlers and asynchronous workers from one shared codebase.
- The first iteration should establish conventions and durable primitives, not re-home existing business logic.

## Goals / Non-Goals

**Goals:**

- Create a Python backend workspace with a stable package layout and a clear separation between API, worker, domain, and infrastructure layers.
- Standardize configuration loading, structured logging, error modeling, and database access patterns.
- Introduce durable job infrastructure with `jobs` and `job_attempts` tables, explicit worker semantics, and a canonical job lifecycle.
- Expose liveness/readiness and basic operational endpoints so the new service can be deployed and observed safely.
- Document the ownership boundary between the Python backend and Supabase.

**Non-Goals:**

- Migrating the three existing Edge Functions or changing their business logic.
- Changing frontend network flows or introducing a cutover to the new backend in this change.
- Rewriting prompts, model policies, or application rules.
- Building full scheduling, rate limiting, or domain-specific worker orchestration beyond the shared job primitives.

## Decisions

### 1. Create a dedicated Python backend workspace inside the repository

The repository will gain a new backend workspace, for example `backend/`, with a modern Python project layout and a single application package used by both HTTP and worker entrypoints.

Rationale:

- Keeps the new backend isolated from the existing frontend and Supabase assets.
- Makes later migration work incremental because new endpoints and workers can be added without disturbing current flows.
- Allows API and worker code to share configuration, error handling, models, and database code.

Alternatives considered:

- Extending only the existing Edge Functions. Rejected because it does not create a durable Python runtime or shared backend conventions.
- Creating separate repositories for API and worker. Rejected because the first phase benefits from a single codebase and a small integration surface.

### 2. Use one codebase with two runtime entrypoints: API and worker

The backend will expose:

- an API process for health, readiness, and future application endpoints
- a worker process for polling, claiming, and executing jobs

Both entrypoints will import shared modules for settings, logging, errors, database sessions, and domain services.

Rationale:

- Reduces duplicate infrastructure code.
- Ensures API-triggered job creation and worker-side job execution use the same domain contracts.
- Makes operational behavior more consistent across processes.

Alternatives considered:

- Embedding job execution inside the API service. Rejected because background work should scale and fail independently.
- Creating separate codebases for API and worker. Rejected because it adds coordination overhead before there is enough complexity to justify it.

### 3. Standardize the runtime stack around typed configuration, structured logs, and a stable error model

The backend foundation will use:

- a typed configuration layer for environment-based settings
- structured JSON logging with request and job correlation fields
- a shared application error model that maps domain/infrastructure failures into stable API and worker behavior

Rationale:

- Startup-time validation prevents misconfigured services from appearing healthy.
- Structured logs are required once there are multiple processes and asynchronous jobs.
- A shared error taxonomy prevents each endpoint or worker from inventing its own failure format.

Alternatives considered:

- Ad hoc environment variable access and free-form logs. Rejected because it scales poorly and makes operations ambiguous.

### 4. Keep Supabase for Postgres, Auth, and RLS; treat Realtime as optional

The Python backend will integrate with Supabase-backed Postgres and honor Auth and RLS as platform responsibilities. Supabase Realtime may be used later for notifications or event fan-out, but it is not required for the initial backend foundation and must not become a hard dependency of the job system.

Rationale:

- Preserves the parts of Supabase the current system already depends on.
- Avoids unnecessary platform churn while still moving application orchestration into Python.
- Keeps the job system durable even if Realtime is unavailable or not adopted.

Alternatives considered:

- Replacing Supabase Auth/RLS with custom backend authorization. Rejected because it would expand scope and duplicate platform features.
- Making Realtime part of the core worker path. Rejected because persistence and retries should depend on Postgres, not an optional event channel.

### 5. Use Postgres-backed job coordination with `jobs` and `job_attempts`

The task system will be modeled with:

- `jobs` as the durable unit of work
- `job_attempts` as execution records for each claim/run cycle

`jobs` owns the canonical status, payload, job type, scheduling metadata, and aggregate attempt counters. `job_attempts` captures worker identity, start/end times, error details, and per-attempt outcomes.

Rationale:

- Separates business-level job identity from execution history.
- Supports retries without losing the audit trail.
- Keeps the source of truth in Postgres where workers can coordinate transactionally.

Alternatives considered:

- A single `jobs` table with overwritten attempt metadata. Rejected because it loses execution history and complicates debugging.
- An external queue as the first step. Rejected because the immediate goal is foundational infrastructure with minimal platform expansion.

### 6. Define a small explicit job state machine

The canonical job statuses are:

- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

Allowed transitions:

- `pending -> running`
- `pending -> cancelled`
- `running -> completed`
- `running -> failed`
- `running -> cancelled`
- `failed -> pending` for retry requeue

`completed` and `cancelled` are terminal. `failed` is terminal unless an explicit retry policy or operator action requeues the job to `pending`. Every transition into `running` must create a new `job_attempts` row.

Rationale:

- Keeps worker behavior understandable and auditable.
- Supports retries without inventing extra job states before they are needed.
- Provides a clear contract for future APIs and operators.

Alternatives considered:

- Introducing more granular states such as `queued`, `retrying`, or `timed_out` immediately. Rejected because they are not needed for the foundation and would add migration burden early.

### 7. Expose operations endpoints that are safe by default

The new API surface will start with:

- liveness endpoint: process is up
- readiness endpoint: process can serve because critical dependencies are available
- basic operational endpoint(s): low-risk service metadata or job system summaries without secrets or raw payload disclosure

Rationale:

- Deployment systems need a fast liveness/readiness contract before the backend is used for real traffic.
- Operators need minimal introspection into the new runtime before business endpoints exist.

Alternatives considered:

- Deferring all operational surfaces until later. Rejected because it makes the new service hard to validate or run safely.

## Risks / Trade-offs

- [Two backend worlds during transition] -> Mitigation: keep the new Python backend additive and avoid cutover in this change.
- [Job schema chosen too narrowly] -> Mitigation: store normalized core fields now and keep job payload/result fields extensible.
- [Worker races when claiming jobs] -> Mitigation: use transactional claim/update behavior and require `job_attempts` creation to be coupled to the claim path.
- [Operational endpoint leakage] -> Mitigation: limit initial ops responses to health summaries, counts, and identifiers; exclude secrets and full payload bodies.
- [Supabase boundary ambiguity] -> Mitigation: document retained platform responsibilities explicitly in code and specs.

## Migration Plan

1. Add the backend workspace, dependency management, and shared application skeleton.
2. Add migration tooling and database schema for `jobs` and `job_attempts`.
3. Land health/readiness and basic ops endpoints.
4. Land worker polling/claiming primitives against the new job tables.
5. Validate the backend in parallel with the current system without changing frontend or Edge Function behavior.
6. Use follow-up changes to migrate specific business flows onto the new foundation incrementally.

Rollback strategy:

- Because this change is additive, rollback is primarily disabling deployment of the new backend and not routing any production traffic to it.
- Database rollback can remove the new tables if the change has not yet become a dependency of later migrations.

## Open Questions

- Which exact Python packaging tool will be standardized in implementation (`uv`, Poetry, or another team-preferred workflow)?
- Which job metadata fields should be mandatory in the first migration versus deferred until the first domain job is implemented?
- Should the initial operational endpoint expose only health and version data, or also aggregate job counts by status?
