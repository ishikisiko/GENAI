ALTER TABLE simulation_runs
ADD COLUMN IF NOT EXISTS last_heartbeat_at timestamptz;

UPDATE simulation_runs
SET last_heartbeat_at = COALESCE(last_heartbeat_at, completed_at, created_at)
WHERE last_heartbeat_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_simulation_runs_case_status_heartbeat
ON simulation_runs(case_id, status, last_heartbeat_at);
