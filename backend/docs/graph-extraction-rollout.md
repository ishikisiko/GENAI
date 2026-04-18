# Graph Extraction Rollout

## Goal

Move graph extraction from the Supabase Edge Function call path to the Python API plus worker pipeline without changing the downstream graph tables or the grounding page contract.

## Rollout steps

1. Start the Python API and worker alongside the existing frontend.
2. Configure `VITE_BACKEND_URL` so the documents page submits extraction requests to `POST /api/graph-extractions`.
3. Confirm the worker is running before enabling user traffic; extraction is now asynchronous and requires the `graph.extract` handler.
4. Watch `GET /api/graph-extractions/{job_id}` and `/ops` for pending, running, completed, and failed extraction jobs during rollout.
5. Once the backend path is stable, keep legacy `extract-graph` usage retired from the product call chain and route users through `api/graph-extractions`.

## Rollback

1. Stop routing the frontend to the backend extraction API by removing `VITE_BACKEND_URL` or reverting the documents page change.
2. Re-enable the previous `extract-graph` edge function path only if rollback is explicitly required.
3. Leave the backend worker deployed if needed; no schema rollback is required because this change reuses existing tables.
4. Investigate any failed `graph.extract` jobs from the `jobs` and `job_attempts` tables before attempting the migration again.
