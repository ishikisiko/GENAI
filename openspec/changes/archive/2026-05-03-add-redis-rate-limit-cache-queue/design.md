## Context

The backend currently uses FastAPI for product endpoints, Postgres/Supabase for durable data, and a Python worker that claims pending jobs from Postgres with transactional locking. Expensive paths include simulation submission, agent generation, source discovery jobs, search-backed assistant requests, LLM JSON calls, Brave Search, and HTTP content fetching.

Redis should complement, not replace, Postgres. Postgres remains the source of truth for jobs, attempts, simulation runs, candidates, and source-library data. Redis is introduced for short-lived coordination and performance concerns: shared rate counters, TTL caches, optional queue fan-out, and operational visibility.

## Goals / Non-Goals

**Goals:**
- Add a mockable Redis client boundary and typed Redis configuration.
- Protect expensive product endpoints with shared Redis-backed rate limiting.
- Cache deterministic external dependency results with explicit TTLs and safe cache keys.
- Add optional Redis Streams job dispatch while preserving Postgres durable job state.
- Keep local development usable when Redis is disabled, and expose degraded state clearly when Redis is required but unavailable.

**Non-Goals:**
- Do not migrate canonical product data from Postgres/Supabase into Redis.
- Do not require Redis for every local development workflow by default.
- Do not replace existing human review, evidence-pack, graph extraction, or simulation domain contracts.
- Do not introduce a full distributed workflow engine; Redis Streams only dispatches worker-owned jobs that are still represented in Postgres.

## Decisions

### Redis Client Boundary

Add a shared Redis provider module that exposes async operations needed by rate limiting, caching, and streams rather than passing a third-party client throughout the codebase. Configuration should include `REDIS_URL`, `REDIS_ENABLED`, Redis requirement mode, operation timeout, cache TTL defaults, rate-limit defaults, and stream names.

Rationale: a narrow boundary keeps tests deterministic and allows an in-memory fake for unit tests. It also prevents direct Redis usage from spreading into domain services.

Alternative considered: instantiate Redis clients directly in each feature. That would be faster to code but makes fallback, timeouts, instrumentation, and tests inconsistent.

### Rate Limiting

Implement rate limiting as backend-owned endpoint protection for known expensive routes. Use Redis atomic counters with TTL or a Lua/token-bucket implementation. Limits should be keyed by authenticated subject when present, otherwise by request IP or a stable anonymous key, and should include route scope.

Rationale: the existing request context already normalizes request IDs and auth mode. Adding shared rate checks near the API boundary keeps services focused on domain work and gives clients a stable 429 error envelope.

Alternative considered: per-process in-memory throttling. That is simpler but does not protect horizontally scaled API processes.

### External Dependency Caching

Add Redis TTL caches around deterministic external dependency calls:
- LLM JSON responses keyed by provider, model, temperature, prompt hash, and relevant output constraints.
- Brave Search results keyed by provider settings and normalized query/request parameters.
- HTTP fetched content keyed by canonical URL and fetcher settings.

Rationale: these calls are expensive, slow, and failure-prone. TTL caches reduce cost and make repeated demos more stable without changing durable domain records.

Alternative considered: persist provider responses in Postgres. That improves auditability but adds schema overhead and is not necessary for short-lived reuse.

### Redis Streams Job Dispatch

Keep Postgres job creation as the durable write. When Redis Streams are enabled, job creation also publishes a lightweight message containing job id and job type. Workers consume from a Redis consumer group, claim the referenced Postgres job, execute the existing handler, and acknowledge the stream message only after the Postgres state transition succeeds. If Redis dispatch is disabled or unavailable in optional mode, workers continue polling Postgres.

Rationale: this preserves the current correctness model and adds lower-latency dispatch plus scalable worker coordination. Postgres remains authoritative if Redis loses messages or needs rebuilding.

Alternative considered: move the job lifecycle entirely to Redis. That would be a larger reliability change and would weaken the existing durable job/attempt history.

### Fallback and Readiness

Redis should support two modes:
- Optional mode: rate limiting and cache features degrade open, streams fall back to Postgres polling, and operations report Redis as disabled/degraded.
- Required mode: readiness fails if Redis is unreachable.

Rationale: optional mode keeps local development and demos easy; required mode is available for production-like deployments where Redis-backed protections are part of the service contract.

## Risks / Trade-offs

- Redis outage causes cache misses or disabled throttling in optional mode -> emit structured logs and expose degraded ops state so the operator can see protection is reduced.
- Incorrect cache keys can return stale or cross-context data -> include provider, model, normalized parameters, prompt hash, and version prefix in every cache key; avoid caching requests with unsafe or user-specific side effects.
- Redis Streams can duplicate delivery -> workers must treat Redis messages as hints and still claim the Postgres job transactionally before execution.
- Rate limiting can block valid demo usage -> defaults should be documented and configurable, with tests covering headers and error envelopes.
- Caching LLM responses can hide provider changes during debugging -> allow per-environment cache disablement and use short default TTLs for LLM cache entries.

## Migration Plan

1. Add Redis dependency, configuration, fake client, and documentation with Redis disabled by default for compatibility.
2. Add health/ops reporting and tests for disabled, available, degraded, optional, and required modes.
3. Add rate limiting for expensive endpoints using the Redis boundary and stable product error envelope.
4. Add cache wrappers for LLM JSON, Brave search, and HTTP fetch calls behind feature flags and TTL config.
5. Add optional Redis Streams publish/consume path while keeping existing Postgres polling fallback.
6. Update README and `.env.local.example`; optionally extend local startup scripts to start or validate Redis.

Rollback is configuration-based: disable Redis features and return to existing Postgres polling and uncached provider behavior. Code rollback should not require data migration because Redis stores only derived, short-lived state.

## Open Questions

- Should local `npm run start:all` start Redis through Docker, or should Redis remain a documented prerequisite?
- What production-like default limits should be used per route for interview demos?
- Should LLM cache keys include a manual prompt-version field per service so prompt edits invalidate old entries predictably?
