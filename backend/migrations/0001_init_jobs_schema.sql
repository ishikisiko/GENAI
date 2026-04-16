BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type varchar(128) NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  max_attempts smallint NOT NULL DEFAULT 5,
  attempt_count integer NOT NULL DEFAULT 0,
  locked_by varchar(128),
  locked_at timestamptz,
  scheduled_at timestamptz,
  next_retry_at timestamptz,
  last_error text,
  last_error_code varchar(80),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_status_created_at_idx ON jobs (status, created_at DESC, scheduled_at);

CREATE TABLE IF NOT EXISTS job_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
  attempt_number smallint NOT NULL,
  worker_id varchar(128) NOT NULL,
  status varchar(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  error_code varchar(80),
  error_message text,
  payload_snapshot jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (job_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS job_attempts_job_id_idx ON job_attempts (job_id);
CREATE INDEX IF NOT EXISTS job_attempts_status_idx ON job_attempts (status);

COMMIT;
