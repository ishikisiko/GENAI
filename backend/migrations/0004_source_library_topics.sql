BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS source_topics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  parent_topic_id uuid REFERENCES source_topics (id) ON DELETE SET NULL,
  topic_type varchar(64) NOT NULL DEFAULT 'collection',
  status varchar(32) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS source_topics_parent_name_idx
ON source_topics (COALESCE(parent_topic_id, '00000000-0000-0000-0000-000000000000'::uuid), lower(name));

CREATE INDEX IF NOT EXISTS source_topics_parent_idx
ON source_topics (parent_topic_id, name);

CREATE INDEX IF NOT EXISTS source_topics_type_status_idx
ON source_topics (topic_type, status, name);

CREATE TABLE IF NOT EXISTS case_source_topics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases (id) ON DELETE CASCADE,
  topic_id uuid NOT NULL REFERENCES source_topics (id) ON DELETE CASCADE,
  relation_type varchar(64) NOT NULL DEFAULT 'primary',
  reason text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (case_id, topic_id)
);

CREATE INDEX IF NOT EXISTS case_source_topics_case_idx
ON case_source_topics (case_id, relation_type);

CREATE INDEX IF NOT EXISTS case_source_topics_topic_idx
ON case_source_topics (topic_id, case_id);

ALTER TABLE global_source_documents
  ADD COLUMN IF NOT EXISTS canonical_url text,
  ADD COLUMN IF NOT EXISTS content_hash varchar(128),
  ADD COLUMN IF NOT EXISTS source_kind varchar(64) NOT NULL DEFAULT 'news',
  ADD COLUMN IF NOT EXISTS authority_level varchar(32) NOT NULL DEFAULT 'medium',
  ADD COLUMN IF NOT EXISTS freshness_status varchar(32) NOT NULL DEFAULT 'current',
  ADD COLUMN IF NOT EXISTS source_status varchar(32) NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

UPDATE global_source_documents
SET
  source_kind = CASE
    WHEN doc_type = 'statement' THEN 'official'
    WHEN doc_type = 'complaint' THEN 'complaint'
    ELSE COALESCE(NULLIF(source_kind, ''), doc_type, 'news')
  END,
  authority_level = CASE
    WHEN doc_type = 'statement' THEN 'high'
    WHEN doc_type = 'news' THEN 'medium'
    ELSE COALESCE(NULLIF(authority_level, ''), 'medium')
  END,
  freshness_status = COALESCE(NULLIF(freshness_status, ''), 'current'),
  source_status = COALESCE(NULLIF(source_status, ''), 'active'),
  content_hash = COALESCE(
    NULLIF(content_hash, ''),
    encode(digest(lower(regexp_replace(trim(content), '\s+', ' ', 'g')), 'sha256'), 'hex')
  ),
  updated_at = COALESCE(updated_at, created_at, now())
WHERE content_hash IS NULL
   OR content_hash = ''
   OR source_kind = ''
   OR authority_level = ''
   OR freshness_status = ''
   OR source_status = '';

CREATE INDEX IF NOT EXISTS global_source_documents_canonical_url_idx
ON global_source_documents (canonical_url)
WHERE canonical_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS global_source_documents_content_hash_idx
ON global_source_documents (content_hash)
WHERE content_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS global_source_documents_kind_status_idx
ON global_source_documents (source_kind, source_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS global_source_documents_authority_freshness_idx
ON global_source_documents (authority_level, freshness_status, updated_at DESC);

CREATE TABLE IF NOT EXISTS source_topic_assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  global_source_id uuid NOT NULL REFERENCES global_source_documents (id) ON DELETE CASCADE,
  topic_id uuid NOT NULL REFERENCES source_topics (id) ON DELETE CASCADE,
  relevance_score double precision NOT NULL DEFAULT 1,
  reason text NOT NULL DEFAULT '',
  assigned_by varchar(64) NOT NULL DEFAULT 'user',
  source_candidate_id uuid REFERENCES source_candidates (id) ON DELETE SET NULL,
  discovery_job_id uuid REFERENCES source_discovery_jobs (id) ON DELETE SET NULL,
  assignment_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  status varchar(32) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (global_source_id, topic_id)
);

CREATE INDEX IF NOT EXISTS source_topic_assignments_source_idx
ON source_topic_assignments (global_source_id, status);

CREATE INDEX IF NOT EXISTS source_topic_assignments_topic_idx
ON source_topic_assignments (topic_id, status, relevance_score DESC);

CREATE INDEX IF NOT EXISTS source_topic_assignments_candidate_idx
ON source_topic_assignments (source_candidate_id)
WHERE source_candidate_id IS NOT NULL;

ALTER TABLE source_documents
  ADD COLUMN IF NOT EXISTS source_topic_id uuid REFERENCES source_topics (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_topic_assignment_id uuid REFERENCES source_topic_assignments (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS source_documents_topic_idx
ON source_documents (source_topic_id);

CREATE INDEX IF NOT EXISTS source_documents_global_case_idx
ON source_documents (global_source_id, case_id)
WHERE global_source_id IS NOT NULL;

COMMIT;
