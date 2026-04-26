CREATE TABLE IF NOT EXISTS source_discovery_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases (id) ON DELETE CASCADE,
  job_id uuid NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
  status varchar(32) NOT NULL DEFAULT 'pending',
  topic text NOT NULL,
  description text NOT NULL DEFAULT '',
  region varchar(128) NOT NULL DEFAULT '',
  language varchar(32) NOT NULL DEFAULT 'en',
  time_range varchar(64) NOT NULL DEFAULT '',
  source_types jsonb NOT NULL DEFAULT '[]'::jsonb,
  max_sources integer NOT NULL DEFAULT 10,
  query_plan jsonb NOT NULL DEFAULT '[]'::jsonb,
  candidate_count integer NOT NULL DEFAULT 0,
  accepted_count integer NOT NULL DEFAULT 0,
  rejected_count integer NOT NULL DEFAULT 0,
  last_error text,
  last_error_code varchar(80),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS source_discovery_jobs_case_created_idx
ON source_discovery_jobs (case_id, created_at DESC);

CREATE INDEX IF NOT EXISTS source_discovery_jobs_job_idx
ON source_discovery_jobs (job_id);

CREATE TABLE IF NOT EXISTS source_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  discovery_job_id uuid NOT NULL REFERENCES source_discovery_jobs (id) ON DELETE CASCADE,
  case_id uuid NOT NULL REFERENCES crisis_cases (id) ON DELETE CASCADE,
  title text NOT NULL,
  url text,
  canonical_url text,
  source_type varchar(64) NOT NULL DEFAULT 'news',
  language varchar(32) NOT NULL DEFAULT 'en',
  region varchar(128) NOT NULL DEFAULT '',
  published_at timestamptz,
  provider varchar(64) NOT NULL DEFAULT 'mock',
  provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  content text NOT NULL DEFAULT '',
  excerpt text NOT NULL DEFAULT '',
  content_hash varchar(128) NOT NULL DEFAULT '',
  classification varchar(64) NOT NULL DEFAULT 'news',
  claim_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  stakeholder_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status varchar(32) NOT NULL DEFAULT 'pending',
  relevance double precision NOT NULL DEFAULT 0,
  authority double precision NOT NULL DEFAULT 0,
  freshness double precision NOT NULL DEFAULT 0,
  claim_richness double precision NOT NULL DEFAULT 0,
  diversity double precision NOT NULL DEFAULT 0,
  grounding_value double precision NOT NULL DEFAULT 0,
  total_score double precision NOT NULL DEFAULT 0,
  duplicate_of uuid REFERENCES source_candidates (id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_candidates_job_score_idx
ON source_candidates (discovery_job_id, total_score DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS source_candidates_case_review_idx
ON source_candidates (case_id, review_status, total_score DESC);

CREATE INDEX IF NOT EXISTS source_candidates_canonical_idx
ON source_candidates (discovery_job_id, canonical_url);

CREATE TABLE IF NOT EXISTS evidence_packs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases (id) ON DELETE CASCADE,
  discovery_job_id uuid REFERENCES source_discovery_jobs (id) ON DELETE SET NULL,
  title text NOT NULL DEFAULT '',
  status varchar(32) NOT NULL DEFAULT 'draft',
  source_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  grounded_at timestamptz
);

CREATE INDEX IF NOT EXISTS evidence_packs_case_created_idx
ON evidence_packs (case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS evidence_pack_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_pack_id uuid NOT NULL REFERENCES evidence_packs (id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES source_candidates (id) ON DELETE RESTRICT,
  source_document_id uuid REFERENCES source_documents (id) ON DELETE SET NULL,
  sort_order integer NOT NULL DEFAULT 0,
  title text NOT NULL,
  url text,
  source_type varchar(64) NOT NULL DEFAULT 'news',
  language varchar(32) NOT NULL DEFAULT 'en',
  region varchar(128) NOT NULL DEFAULT '',
  published_at timestamptz,
  provider varchar(64) NOT NULL DEFAULT 'mock',
  provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  content text NOT NULL DEFAULT '',
  excerpt text NOT NULL DEFAULT '',
  score_dimensions jsonb NOT NULL DEFAULT '{}'::jsonb,
  total_score double precision NOT NULL DEFAULT 0,
  claim_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  stakeholder_previews jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS evidence_pack_sources_pack_candidate_idx
ON evidence_pack_sources (evidence_pack_id, candidate_id);

CREATE INDEX IF NOT EXISTS evidence_pack_sources_pack_order_idx
ON evidence_pack_sources (evidence_pack_id, sort_order);

ALTER TABLE source_documents
  ADD COLUMN IF NOT EXISTS evidence_pack_id uuid REFERENCES evidence_packs (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS evidence_pack_source_id uuid REFERENCES evidence_pack_sources (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS source_documents_evidence_pack_idx
ON source_documents (evidence_pack_id);
