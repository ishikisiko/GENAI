ALTER TABLE crisis_cases
  ADD COLUMN IF NOT EXISTS source_discovery_assistant_response jsonb,
  ADD COLUMN IF NOT EXISTS source_discovery_assistant_updated_at timestamptz;
