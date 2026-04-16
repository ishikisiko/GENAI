/*
  # Global Source Library

  ## Summary
  Adds a reusable global source repository while preserving case-level document snapshots.

  ## Changes
  1. New table `global_source_documents`
     - Stores reusable source documents shared across cases
  2. Extend `source_documents`
     - `global_source_id` links a case document to the global repository entry
     - `source_origin` tracks whether the case document came from a direct case upload or from the global library
  3. Safety
     - Prevents duplicate selection of the same global document within a single case
*/

CREATE TABLE IF NOT EXISTS global_source_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL DEFAULT '',
  content text NOT NULL DEFAULT '',
  doc_type text NOT NULL DEFAULT 'news',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE global_source_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read global_source_documents"
  ON global_source_documents FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anon insert global_source_documents"
  ON global_source_documents FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anon update global_source_documents"
  ON global_source_documents FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow anon delete global_source_documents"
  ON global_source_documents FOR DELETE
  TO anon
  USING (true);

ALTER TABLE source_documents
  ADD COLUMN IF NOT EXISTS global_source_id uuid REFERENCES global_source_documents(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_origin text NOT NULL DEFAULT 'case_upload';

UPDATE source_documents
SET source_origin = 'case_upload'
WHERE source_origin IS NULL OR source_origin = '';

CREATE INDEX IF NOT EXISTS idx_global_source_documents_created_at
  ON global_source_documents(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_documents_global_source_id
  ON source_documents(global_source_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_source_documents_case_global_unique
  ON source_documents(case_id, global_source_id)
  WHERE global_source_id IS NOT NULL;
