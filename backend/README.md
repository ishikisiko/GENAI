# Python Backend Foundation

This folder contains a minimal, additive Python backend workspace that hosts:

- API entrypoint with health and operations endpoints.
- Worker entrypoint with polling and job-attempt recording.
- Shared product request context with request IDs, product/operator boundary tagging, and configurable bearer-header enforcement.
- Async simulation submission, execution, heartbeat, and polling endpoints.
- Async graph extraction submission, worker execution, and polling endpoints.
- Synchronous Python-owned agent generation for the grounding-to-simulation handoff.
- Shared configuration, structured logging, error taxonomy, and data-access layers.
- Postgres-backed durable job schema and repository helpers (`jobs` + `job_attempts`).
- Migration tooling to bootstrap and track backend schema changes.

## Quick start

From `backend/`:

```bash
cp ../.env.local.example ../.env.local
pip install -e ".[dev]"
backend-migrate
backend-api
```

Run a worker in another terminal:

```bash
backend-worker
```

Async simulation rollout notes live in [docs/simulation-rollout.md](docs/simulation-rollout.md).
Graph extraction rollout notes live in [docs/graph-extraction-rollout.md](docs/graph-extraction-rollout.md).
Source discovery scoring notes live in [docs/source-discovery-scoring.md](docs/source-discovery-scoring.md).

## Design notes

- The product default call chain is Python API + worker for simulation and graph extraction, with Supabase Edge Functions retained only as optional compatibility shims.
- `POST /api/agent-generation` is the synchronous product path for agent generation.
- The documents page uses `VITE_BACKEND_API_BASE` (or the compatibility alias `VITE_BACKEND_URL`) to call `POST /api/graph-extractions`.
- The simulation page uses `POST /api/simulations`.
- The backend treats Supabase as the platform owner for Postgres, Auth, and RLS.
- Realtime is optional and not required for core API/worker operation.
- Async submissions now return both the canonical operator status path (`job_status_path`) and the product-facing status path (`status_path`).
- `APP_PRODUCT_AUTH_MODE=public` preserves the current public product flow. Switch to `require_bearer` when rollout requires product endpoints to reject missing bearer headers.
- Source discovery defaults to real Brave Search plus HTTP page fetching. Set `BRAVE_SEARCH_API_KEY` in root `.env.local`; keep `BRAVE_SEARCH_RATE_LIMIT_SECONDS=1.0` for one request per second subscriptions. For offline local runs, set `SOURCE_DISCOVERY_SEARCH_PROVIDER=mock` and `SOURCE_DISCOVERY_CONTENT_FETCHER=mock`.
- The backend loads root `.env`, root `.env.local`, and optional `backend/.env` in that order. Keep `backend/.env` only for backend-specific overrides.

## Redis performance infrastructure

Redis is optional by default and is used only for short-lived coordination and performance paths. Postgres/Supabase remains the durable source of truth for cases, jobs, attempts, simulation runs, source candidates, and source-library data.

Enable Redis locally by running a Redis server and setting:

```bash
REDIS_ENABLED=true
REDIS_URL=redis://127.0.0.1:6379/0
```

Useful feature flags:

- `REDIS_RATE_LIMIT_ENABLED=true` protects expensive product endpoints: `POST /api/simulations`, `POST /api/agent-generation`, `POST /api/source-discovery/jobs`, and `POST /api/source-discovery/assistant`.
- `REDIS_CACHE_ENABLED=true` enables TTL caches for LLM JSON responses, Brave search responses, and fetched page content.
- `REDIS_STREAM_DISPATCH_ENABLED=true` publishes worker-owned jobs to Redis Streams after the durable Postgres job is created. Workers still claim and update the canonical Postgres job row before executing work.
- `REDIS_REQUIREMENT_MODE=optional` degrades open when Redis is unavailable. `REDIS_REQUIREMENT_MODE=required` makes readiness fail if Redis cannot be reached.

Operational behavior:

- `/health/ready` checks Redis only when Redis is enabled and required.
- `/ops` reports non-secret Redis enablement, requirement mode, availability, and enabled feature flags.
- Redis keys store counters, cache entries, and stream messages only. They do not replace durable database records.

Interview talking points:

- Rate limiting demonstrates shared protection across horizontally scaled API processes.
- TTL caching reduces LLM/search cost and latency while keeping cache keys secret-safe through hashing.
- Redis Streams provide low-latency worker dispatch, while Postgres preserves retry, attempt history, and final job state.

## Migration workflow

1. Add new migration SQL in `migrations/` using a timestamped file name.
2. Run:
   `python -m backend.scripts.migrate --database-url <db-url> --migrations-dir backend/migrations`
3. Commit schema SQL and script output records in `_backend_migrations`.

## Backend integration tests

Regular `pytest` excludes integration tests by default. The integration suite is opt-in because it requires real services.

The current backend integration test verifies this real infrastructure path:

- apply the backend jobs migrations (`0001` and `0002`) to a disposable Postgres database
- create a durable job through `JobRepository`
- publish the job to a real Redis Stream
- run one worker cycle that consumes the stream message
- claim and complete the canonical Postgres job
- verify the persisted `jobs` and `job_attempts` rows

Start disposable services, for example:

```bash
docker run -d --name genai-integration-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 127.0.0.1:55432:5432 postgres:16-alpine

docker run -d --name genai-integration-redis \
  -p 127.0.0.1:6380:6379 redis:7-alpine
```

Run the integration test:

```bash
cd backend
BACKEND_INTEGRATION_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/postgres \
BACKEND_INTEGRATION_REDIS_URL=redis://127.0.0.1:6380/0 \
RUN_BACKEND_INTEGRATION=1 \
pytest -m integration tests/integration
```

Or with Make:

```bash
BACKEND_INTEGRATION_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/postgres \
BACKEND_INTEGRATION_REDIS_URL=redis://127.0.0.1:6380/0 \
make test-integration
```

Use a disposable database. The test creates backend migration metadata and cleans up its own integration job row, but it intentionally exercises real Postgres and Redis behavior.
