Backend migrations are versioned SQL files that describe durable job infrastructure
and are applied by `backend.scripts.migrate`.

Required workflow:

1. Create a new SQL file under this directory with a timestamped filename.
2. Run `backend-migrate --database-url <url> --migrations-dir backend/migrations`.
3. New files are inserted into `_backend_migrations` and only run once.
