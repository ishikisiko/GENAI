# Python Backend Foundation

This folder contains a minimal, additive Python backend workspace that hosts:

- API entrypoint with health and operations endpoints.
- Worker entrypoint with polling and job-attempt recording.
- Async simulation submission, execution, heartbeat, and polling endpoints.
- Async graph extraction submission, worker execution, and polling endpoints.
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
- The documents page uses `VITE_BACKEND_URL` to call `POST /api/graph-extractions`.
- The simulation page uses `POST /api/simulations`.
- The backend treats Supabase as the platform owner for Postgres, Auth, and RLS.
- Realtime is optional and not required for core API/worker operation.

## Migration workflow

1. Add new migration SQL in `migrations/` using a timestamped file name.
2. Run:
   `python -m backend.scripts.migrate --database-url <db-url> --migrations-dir backend/migrations`
3. Commit schema SQL and script output records in `_backend_migrations`.
