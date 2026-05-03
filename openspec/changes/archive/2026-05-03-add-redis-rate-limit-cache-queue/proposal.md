## Why

The backend already has durable Postgres-backed jobs and external LLM/search integrations, but expensive endpoints can still be called without shared throttling and repeated provider calls are not cached across requests or workers. Adding Redis creates a focused interview-grade backend enhancement: low-latency rate limiting, short-lived external dependency caching, and an optional queue layer while keeping Postgres as the durable source of truth.

## What Changes

- Add a Redis integration layer with typed configuration, health reporting, and mockable client boundaries for tests.
- Add backend-owned rate limiting for expensive product endpoints, including simulation submission, agent generation, source discovery job creation, and source discovery assistant/briefing requests.
- Add Redis-backed TTL caching for LLM JSON responses, Brave search results, and fetched page content where deterministic cache keys can be derived safely.
- Add optional Redis Streams job dispatch for worker-owned jobs while preserving Postgres `jobs` and `job_attempts` as canonical durable state.
- Add tests and documentation that show fallback behavior when Redis is disabled or unavailable.
- No breaking API changes are intended; rejected rate-limited requests will use the existing product error envelope with HTTP 429.

## Capabilities

### New Capabilities
- `redis-performance-infrastructure`: Redis-backed rate limiting, external dependency caching, configuration, fallback behavior, and operational visibility.

### Modified Capabilities
- `backend-api-boundary`: Expensive Python API product endpoints gain shared rate-limit behavior and stable 429 error responses.
- `backend-operations`: Readiness and operations surfaces include Redis dependency state without leaking connection secrets.
- `job-processing-foundation`: Worker-owned jobs may be dispatched through Redis Streams while Postgres remains the canonical durable job and attempt store.

## Impact

- Backend dependencies: Redis client package for Python, local/test Redis configuration, and optional mock/in-memory client for tests.
- Backend code: shared config, Redis client/provider module, request middleware or endpoint guards, LLM/search/content-fetch cache adapters, job repository/worker dispatch integration, error taxonomy, and health/ops responses.
- Tests: unit tests for rate-limit and cache key behavior, API tests for 429 envelopes, worker tests for Redis stream dispatch/ack/fallback, and integration-oriented tests where available.
- Developer workflow: `.env.local.example`, backend README, and local start guidance should document Redis usage, defaults, and disabled/fallback modes.
