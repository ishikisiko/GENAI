ALTER TABLE simulation_runs
ADD COLUMN IF NOT EXISTS job_id uuid REFERENCES jobs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_simulation_runs_job_id
ON simulation_runs(job_id);
