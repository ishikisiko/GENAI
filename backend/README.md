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
cp .env.example .env
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

## Design notes

- The product default call chain is Python API + worker for simulation and graph extraction, with Supabase Edge Functions retained only as optional compatibility shims.
- `POST /api/agent-generation` is the synchronous product path for agent generation.
- The documents page uses `VITE_BACKEND_API_BASE` (or the compatibility alias `VITE_BACKEND_URL`) to call `POST /api/graph-extractions`.
- The simulation page uses `POST /api/simulations`.
- The backend treats Supabase as the platform owner for Postgres, Auth, and RLS.
- Realtime is optional and not required for core API/worker operation.
- Async submissions now return both the canonical operator status path (`job_status_path`) and the product-facing status path (`status_path`).
- `APP_PRODUCT_AUTH_MODE=public` preserves the current public product flow. Switch to `require_bearer` when rollout requires product endpoints to reject missing bearer headers.
- Source discovery defaults to real Brave Search plus HTTP page fetching. Set `BRAVE_SEARCH_API_KEY` in `backend/.env`; keep `BRAVE_SEARCH_RATE_LIMIT_SECONDS=1.0` for one request per second subscriptions. For offline local runs, set `SOURCE_DISCOVERY_SEARCH_PROVIDER=mock` and `SOURCE_DISCOVERY_CONTENT_FETCHER=mock`.

## Migration workflow

1. Add new migration SQL in `migrations/` using a timestamped file name.
2. Run:
   `python -m backend.scripts.migrate --database-url <db-url> --migrations-dir backend/migrations`
3. Commit schema SQL and script output records in `_backend_migrations`.
