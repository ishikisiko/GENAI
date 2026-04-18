# Async Simulation Rollout

This change moves `run-simulation` execution onto the Python API + worker while keeping the legacy Supabase Edge Function available for rollback.

## Migration

1. Apply the backend migration for durable job heartbeats:
   `cd backend && backend-migrate`
2. Apply the Supabase migration that links `simulation_runs.job_id`:
   `npx supabase db push`
3. Configure the backend worker environment:
   - `APP_DATABASE_URL` must point at the same Postgres instance used by Supabase.
   - `LLM_API_KEY` / `OPENAI_API_KEY` (or Anthropic equivalents) must be present.
   - `SIMULATION_STALE_RUN_TIMEOUT_SECONDS` controls worker-owned stale failure recovery.
4. Start the API and worker:
   - `cd backend && backend-api`
   - `cd backend && backend-worker`
5. Keep frontend `VITE_BACKEND_URL=http://127.0.0.1:8000` so simulation calls use the Python API by default.

## Runtime Expectations

- Submission is now lightweight: `POST /api/simulations` creates a `simulation_runs` row and a durable `jobs` row, then returns immediately.
- The worker owns execution. It heartbeats both `jobs.heartbeat_at` and `simulation_runs.last_heartbeat_at` while rounds are running.
- The UI polls `GET /api/jobs/{job_id}` and `GET /api/simulation-runs/{run_id}` until `should_poll` becomes `false`, then reloads full run results from Supabase.
- Stale recovery is backend-owned. Running jobs whose heartbeat exceeds `SIMULATION_STALE_RUN_TIMEOUT_SECONDS` are failed by the worker and their linked simulation run is marked failed with a timeout/interruption message.

## Rollback

1. If needed for rollback, route simulation submissions back to the legacy Supabase `run-simulation` edge function until legacy behavior is no longer required.
3. Leave existing async-created `jobs` and `simulation_runs` rows in place for investigation; the result tables remain readable and compatible.

## Operational Notes

- `simulation_runs.status in ('pending', 'running')` is treated as an active run conflict for a case.
- `GET /api/jobs/{job_id}` is the canonical operational view for worker state and failure metadata.
- `GET /api/simulation-runs/{run_id}` is the product-facing polling surface and returns round completion progress for the frontend.
