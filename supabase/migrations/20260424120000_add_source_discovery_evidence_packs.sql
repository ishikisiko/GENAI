CREATE TABLE IF NOT EXISTS source_discovery_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  job_id uuid,
  status text NOT NULL DEFAULT 'pending',
  topic text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  region text NOT NULL DEFAULT '',
  language text NOT NULL DEFAULT 'en',
  time_range text NOT NULL DEFAULT '',
  source_types jsonb NOT NULL DEFAULT '[]'::jsonb,
  max_sources integer NOT NULL DEFAULT 10,
  query_plan jsonb NOT NULL DEFAULT '[]'::jsonb,
  candidate_count integer NOT NULL DEFAULT 0,
  accepted_count integer NOT NULL DEFAULT 0,
  rejected_count integer NOT NULL DEFAULT 0,
  last_error text,
  last_error_code text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

ALTER TABLE source_discovery_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read source_discovery_jobs"
  ON source_discovery_jobs FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert source_discovery_jobs"
  ON source_discovery_jobs FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update source_discovery_jobs"
  ON source_discovery_jobs FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_source_discovery_jobs_case_id ON source_discovery_jobs(case_id);

CREATE TABLE IF NOT EXISTS source_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  discovery_job_id uuid NOT NULL REFERENCES source_discovery_jobs(id) ON DELETE CASCADE,
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT '',
  url text,
  canonical_url text,
  source_type text NOT NULL DEFAULT 'news',
  language text NOT NULL DEFAULT 'en',
  region text NOT NULL DEFAULT '',
  published_at timestamptz,
  provider text NOT NULL DEFAULT 'mock',
  provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  content text NOT NULL DEFAULT '',
  excerpt text NOT NULL DEFAULT '',
  content_hash text NOT NULL DEFAULT '',
  classification text NOT NULL DEFAULT 'news',
  claim_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  stakeholder_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status text NOT NULL DEFAULT 'pending',
  relevance double precision NOT NULL DEFAULT 0,
  authority double precision NOT NULL DEFAULT 0,
  freshness double precision NOT NULL DEFAULT 0,
  claim_richness double precision NOT NULL DEFAULT 0,
  diversity double precision NOT NULL DEFAULT 0,
  grounding_value double precision NOT NULL DEFAULT 0,
  total_score double precision NOT NULL DEFAULT 0,
  duplicate_of uuid REFERENCES source_candidates(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE source_candidates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read source_candidates"
  ON source_candidates FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon update source_candidates"
  ON source_candidates FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_source_candidates_job_score ON source_candidates(discovery_job_id, total_score DESC);
CREATE INDEX IF NOT EXISTS idx_source_candidates_case_review ON source_candidates(case_id, review_status);

CREATE TABLE IF NOT EXISTS evidence_packs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  discovery_job_id uuid REFERENCES source_discovery_jobs(id) ON DELETE SET NULL,
  title text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'draft',
  source_count integer NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  grounded_at timestamptz
);

ALTER TABLE evidence_packs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read evidence_packs"
  ON evidence_packs FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert evidence_packs"
  ON evidence_packs FOR INSERT TO anon WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_evidence_packs_case_id ON evidence_packs(case_id);

CREATE TABLE IF NOT EXISTS evidence_pack_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_pack_id uuid NOT NULL REFERENCES evidence_packs(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES source_candidates(id) ON DELETE RESTRICT,
  source_document_id uuid REFERENCES source_documents(id) ON DELETE SET NULL,
  sort_order integer NOT NULL DEFAULT 0,
  title text NOT NULL DEFAULT '',
  url text,
  source_type text NOT NULL DEFAULT 'news',
  language text NOT NULL DEFAULT 'en',
  region text NOT NULL DEFAULT '',
  published_at timestamptz,
  provider text NOT NULL DEFAULT 'mock',
  provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  content text NOT NULL DEFAULT '',
  excerpt text NOT NULL DEFAULT '',
  score_dimensions jsonb NOT NULL DEFAULT '{}'::jsonb,
  total_score double precision NOT NULL DEFAULT 0,
  claim_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  stakeholder_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE evidence_pack_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read evidence_pack_sources"
  ON evidence_pack_sources FOR SELECT TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_evidence_pack_sources_pack_id ON evidence_pack_sources(evidence_pack_id);

ALTER TABLE source_documents
  ADD COLUMN IF NOT EXISTS evidence_pack_id uuid REFERENCES evidence_packs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS evidence_pack_source_id uuid REFERENCES evidence_pack_sources(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
