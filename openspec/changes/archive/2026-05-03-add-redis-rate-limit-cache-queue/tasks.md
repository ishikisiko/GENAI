## 1. Redis Foundation

- [x] 1.1 Add backend Redis dependency and typed configuration fields for enablement, requirement mode, URL, timeout, cache TTLs, rate-limit windows, and stream names.
- [x] 1.2 Implement a shared async Redis client boundary with connect, ping, counter, cache, and stream operations.
- [x] 1.3 Implement an in-memory or fake Redis boundary for unit tests.
- [x] 1.4 Wire Redis provider construction into API and worker startup without requiring Redis when disabled.

## 2. Rate Limiting

- [x] 2.1 Add a rate limiter service using the Redis boundary with route-scoped and identity-scoped keys.
- [x] 2.2 Apply rate limiting to `POST /api/simulations`, `POST /api/agent-generation`, `POST /api/source-discovery/jobs`, and `POST /api/source-discovery/assistant`.
- [x] 2.3 Return HTTP 429 through the shared product error envelope with request correlation data and retry guidance when a limit is exceeded.
- [x] 2.4 Add tests for allowed requests, exceeded limits, anonymous and authenticated keying, and optional-mode Redis failure behavior.

## 3. External Dependency Cache

- [x] 3.1 Add cache key helpers with feature prefix, version, provider identity, normalized parameters, and hashed prompt or URL input.
- [x] 3.2 Add Redis TTL cache support around `LlmJsonClient.chat_json` without changing caller-visible response contracts.
- [x] 3.3 Add Redis TTL cache support around Brave search provider calls.
- [x] 3.4 Add Redis TTL cache support around HTTP page content fetches.
- [x] 3.5 Add tests for cache hit, cache miss, TTL write, key safety, disabled cache behavior, and optional-mode Redis failure fallback.

## 4. Redis Streams Job Dispatch

- [x] 4.1 Add optional Redis Stream publishing after durable Postgres job creation for worker-owned job types.
- [x] 4.2 Add worker consume logic for Redis Streams consumer groups that treats stream messages as hints and still claims jobs through Postgres.
- [x] 4.3 Acknowledge Redis Stream messages only after canonical Postgres job state updates succeed.
- [x] 4.4 Preserve existing Postgres polling behavior when Redis dispatch is disabled or degraded in optional mode.
- [x] 4.5 Add tests for publish-after-persist, stream consume and claim, duplicate delivery, ack-after-update, and polling fallback.

## 5. Operations and Documentation

- [x] 5.1 Extend readiness and operations responses with non-secret Redis disabled, available, required-unavailable, and optional-degraded states.
- [x] 5.2 Add structured logs for Redis rate-limit, cache, stream, and health failures without logging secrets or cached payload bodies.
- [x] 5.3 Update `.env.local.example` with Redis configuration defaults and comments.
- [x] 5.4 Update backend README with Redis architecture, local setup, fallback modes, and interview-relevant talking points.

## 6. Verification

- [x] 6.1 Run backend unit tests and add any missing focused tests for Redis feature contracts.
- [x] 6.2 Run frontend lint/build checks to confirm API contract changes do not break existing client code.
- [x] 6.3 Manually verify local startup in Redis-disabled mode.
- [x] 6.4 Manually verify Redis-enabled mode for rate limiting, cache hit behavior, and worker dispatch fallback.
