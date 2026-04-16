# Supabase Responsibility Boundary

This backend foundation uses Supabase only for:

- Postgres database hosting and durability.
- Auth token validation and user identity propagation.
- RLS policy enforcement for table-level authorization.

The Python backend does not replace these responsibilities. It relies on those
platform guarantees for persistence and access control while it focuses on:

- Application orchestration and durable job scheduling.
- API entrypoints for health/readiness/operations.
- Worker execution and attempt recording.

Optional components:

- Supabase Realtime is not part of the required path for API readiness or
  worker claim/execute loops.
- Realtime can be adopted later without changing the base job tables or core
  repository contracts.
