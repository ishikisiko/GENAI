BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS source_fragments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_scope varchar(32) NOT NULL,
  global_source_id uuid REFERENCES global_source_documents (id) ON DELETE CASCADE,
  source_candidate_id uuid REFERENCES source_candidates (id) ON DELETE CASCADE,
  fragment_index integer NOT NULL,
  fragment_text text NOT NULL,
  content_hash varchar(128) NOT NULL,
  embedding_model varchar(128) NOT NULL DEFAULT 'local-token-hash',
  embedding_version varchar(64) NOT NULL DEFAULT 'v1',
  embedding_vector jsonb,
  vector_index_id text,
  index_status varchar(32) NOT NULL DEFAULT 'pending',
  last_indexed_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (
      source_scope = 'global'
      AND global_source_id IS NOT NULL
      AND source_candidate_id IS NULL
    )
    OR (
      source_scope = 'candidate'
      AND source_candidate_id IS NOT NULL
      AND global_source_id IS NULL
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS source_fragments_global_fragment_idx
ON source_fragments (global_source_id, fragment_index)
WHERE source_scope = 'global' AND global_source_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS source_fragments_candidate_fragment_idx
ON source_fragments (source_candidate_id, fragment_index)
WHERE source_scope = 'candidate' AND source_candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS source_fragments_status_idx
ON source_fragments (index_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS source_fragments_global_idx
ON source_fragments (global_source_id, index_status, fragment_index)
WHERE global_source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS source_fragments_candidate_idx
ON source_fragments (source_candidate_id, index_status, fragment_index)
WHERE source_candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS source_fragments_embedding_version_idx
ON source_fragments (embedding_model, embedding_version, updated_at DESC);

CREATE INDEX IF NOT EXISTS source_fragments_content_hash_idx
ON source_fragments (content_hash);

COMMIT;
