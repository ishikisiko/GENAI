ALTER TABLE simulation_runs
  ADD COLUMN IF NOT EXISTS strategy_sequence jsonb;
