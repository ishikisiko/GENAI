CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS source_fragments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_scope text NOT NULL,
  global_source_id uuid REFERENCES global_source_documents(id) ON DELETE CASCADE,
  source_candidate_id uuid REFERENCES source_candidates(id) ON DELETE CASCADE,
  fragment_index integer NOT NULL,
  fragment_text text NOT NULL,
  content_hash text NOT NULL,
  embedding_model text NOT NULL DEFAULT 'local-token-hash',
  embedding_version text NOT NULL DEFAULT 'v1',
  embedding_vector jsonb,
  vector_index_id text,
  index_status text NOT NULL DEFAULT 'pending',
  last_indexed_at timestamptz,
  last_error text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
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

ALTER TABLE source_fragments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read source_fragments"
  ON source_fragments FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert source_fragments"
  ON source_fragments FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update source_fragments"
  ON source_fragments FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete source_fragments"
  ON source_fragments FOR DELETE TO anon USING (true);

CREATE UNIQUE INDEX IF NOT EXISTS idx_source_fragments_global_fragment
  ON source_fragments(global_source_id, fragment_index)
  WHERE source_scope = 'global' AND global_source_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_source_fragments_candidate_fragment
  ON source_fragments(source_candidate_id, fragment_index)
  WHERE source_scope = 'candidate' AND source_candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_source_fragments_status
  ON source_fragments(index_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_fragments_global
  ON source_fragments(global_source_id, index_status, fragment_index)
  WHERE global_source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_source_fragments_candidate
  ON source_fragments(source_candidate_id, index_status, fragment_index)
  WHERE source_candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_source_fragments_embedding_version
  ON source_fragments(embedding_model, embedding_version, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_fragments_content_hash
  ON source_fragments(content_hash);
