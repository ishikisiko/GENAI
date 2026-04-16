/*
  # Crisis Response Simulator - Core Tables

  ## Summary
  Creates the foundational tables for the crisis response simulator.

  ## New Tables
  1. `crisis_cases` - Top-level crisis scenario container
     - `id` (uuid, primary key)
     - `title` (text) - Name of the crisis
     - `description` (text) - Brief description
     - `status` (text) - 'draft' | 'grounded' | 'agents_ready' | 'simulated'
     - `created_at` (timestamptz)
     - `updated_at` (timestamptz)

  2. `source_documents` - Raw input materials for a crisis case
     - `id` (uuid, primary key)
     - `case_id` (uuid, FK to crisis_cases)
     - `content` (text) - Full document text
     - `doc_type` (text) - 'news' | 'complaint' | 'statement'
     - `title` (text) - Optional document title
     - `created_at` (timestamptz)

  ## Security
  - RLS enabled on both tables
  - Public read/write allowed for demo purposes (anon role)
*/

CREATE TABLE IF NOT EXISTS crisis_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'draft',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE crisis_cases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read crisis_cases"
  ON crisis_cases FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anon insert crisis_cases"
  ON crisis_cases FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anon update crisis_cases"
  ON crisis_cases FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow anon delete crisis_cases"
  ON crisis_cases FOR DELETE
  TO anon
  USING (true);

CREATE TABLE IF NOT EXISTS source_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT '',
  content text NOT NULL DEFAULT '',
  doc_type text NOT NULL DEFAULT 'news',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read source_documents"
  ON source_documents FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anon insert source_documents"
  ON source_documents FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anon update source_documents"
  ON source_documents FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow anon delete source_documents"
  ON source_documents FOR DELETE
  TO anon
  USING (true);

CREATE INDEX IF NOT EXISTS idx_source_documents_case_id ON source_documents(case_id);
