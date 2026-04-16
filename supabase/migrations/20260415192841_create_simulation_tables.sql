/*
  # Simulation Engine Tables

  ## Summary
  Creates tables for managing agent profiles, simulation runs, and per-round state.
  These tables store the evolving state of each simulation trajectory.

  ## New Tables
  1. `agent_profiles` - Stakeholder agents grounded by GraphRAG results
     - Role: 'consumer' | 'supporter' | 'critic' | 'media'
     - Attributes: stance, concern, emotional_sensitivity (1-10), spread_tendency (1-10)
     - `initial_beliefs` (jsonb) - grounded knowledge from GraphRAG

  2. `simulation_runs` - A single simulation execution (baseline or intervention)
     - `run_type`: 'baseline' | 'intervention'
     - `strategy_type`: 'apology' | 'clarification' | 'compensation' | 'rebuttal' | null
     - `injection_round`: which round the strategy was injected
     - `status`: 'pending' | 'running' | 'completed' | 'failed'
     - `total_rounds`: number of rounds to simulate

  3. `round_states` - Per-round snapshot of simulation state
     - `round_number` (int)
     - `agent_responses` (jsonb) - array of {agent_id, role, response, sentiment_delta}
     - `overall_sentiment` (float) - -1.0 to 1.0
     - `polarization_level` (float) - 0.0 to 1.0
     - `narrative_state` (text) - brief summary of current narrative

  4. `metric_snapshots` - Time-series metrics per round per run
     - `sentiment_score` (float)
     - `polarization_score` (float)
     - `negative_claim_spread` (float)
     - `stabilization_indicator` (float)

  ## Security
  - RLS enabled, anon access allowed for demo
*/

CREATE TABLE IF NOT EXISTS agent_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'consumer',
  stance text NOT NULL DEFAULT 'neutral',
  concern text NOT NULL DEFAULT '',
  emotional_sensitivity integer NOT NULL DEFAULT 5,
  spread_tendency integer NOT NULL DEFAULT 5,
  initial_beliefs jsonb NOT NULL DEFAULT '[]'::jsonb,
  persona_description text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE agent_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read agent_profiles"
  ON agent_profiles FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert agent_profiles"
  ON agent_profiles FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update agent_profiles"
  ON agent_profiles FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete agent_profiles"
  ON agent_profiles FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_agent_profiles_case_id ON agent_profiles(case_id);

CREATE TABLE IF NOT EXISTS simulation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  run_type text NOT NULL DEFAULT 'baseline',
  strategy_type text,
  strategy_message text,
  injection_round integer,
  total_rounds integer NOT NULL DEFAULT 5,
  status text NOT NULL DEFAULT 'pending',
  error_message text,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

ALTER TABLE simulation_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read simulation_runs"
  ON simulation_runs FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert simulation_runs"
  ON simulation_runs FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update simulation_runs"
  ON simulation_runs FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete simulation_runs"
  ON simulation_runs FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_simulation_runs_case_id ON simulation_runs(case_id);

CREATE TABLE IF NOT EXISTS round_states (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
  round_number integer NOT NULL DEFAULT 1,
  agent_responses jsonb NOT NULL DEFAULT '[]'::jsonb,
  overall_sentiment float NOT NULL DEFAULT 0.0,
  polarization_level float NOT NULL DEFAULT 0.0,
  narrative_state text NOT NULL DEFAULT '',
  strategy_applied text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE round_states ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read round_states"
  ON round_states FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert round_states"
  ON round_states FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update round_states"
  ON round_states FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete round_states"
  ON round_states FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_round_states_run_id ON round_states(run_id);

CREATE TABLE IF NOT EXISTS metric_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
  round_number integer NOT NULL DEFAULT 0,
  sentiment_score float NOT NULL DEFAULT 0.0,
  polarization_score float NOT NULL DEFAULT 0.0,
  negative_claim_spread float NOT NULL DEFAULT 0.0,
  stabilization_indicator float NOT NULL DEFAULT 0.0,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE metric_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read metric_snapshots"
  ON metric_snapshots FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert metric_snapshots"
  ON metric_snapshots FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update metric_snapshots"
  ON metric_snapshots FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete metric_snapshots"
  ON metric_snapshots FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_run_id ON metric_snapshots(run_id);
