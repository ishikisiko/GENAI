BEGIN;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz;

UPDATE jobs
SET heartbeat_at = COALESCE(heartbeat_at, locked_at, updated_at)
WHERE status = 'running' AND heartbeat_at IS NULL;

CREATE INDEX IF NOT EXISTS jobs_running_heartbeat_idx
ON jobs (status, heartbeat_at);

COMMIT;
