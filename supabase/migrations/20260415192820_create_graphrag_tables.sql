/*
  # GraphRAG Grounding Tables

  ## Summary
  Creates tables for storing the structured knowledge graph extracted from crisis documents.
  These tables form the "grounding" layer that makes agent behavior fact-based.

  ## New Tables
  1. `entities` - Named entities extracted from documents
     - `id` (uuid, primary key)
     - `case_id` (uuid, FK)
     - `name` (text) - Entity name
     - `entity_type` (text) - 'person' | 'organization' | 'product' | 'event' | 'location'
     - `description` (text) - Brief description of entity's role

  2. `relations` - Relationships between entities
     - `id` (uuid, primary key)
     - `case_id` (uuid, FK)
     - `source_entity_id` (uuid, FK to entities)
     - `target_entity_id` (uuid, FK to entities)
     - `relation_type` (text) - e.g. 'caused', 'responded_to', 'affiliated_with'
     - `description` (text)

  3. `claims` - Key factual claims, allegations, or events from documents
     - `id` (uuid, primary key)
     - `case_id` (uuid, FK)
     - `content` (text) - The claim text
     - `claim_type` (text) - 'allegation' | 'fact' | 'statement' | 'event'
     - `credibility` (text) - 'high' | 'medium' | 'low'
     - `source_doc_id` (uuid, FK to source_documents, nullable)

  ## Security
  - RLS enabled, anon access allowed for demo
*/

CREATE TABLE IF NOT EXISTS entities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  name text NOT NULL DEFAULT '',
  entity_type text NOT NULL DEFAULT 'organization',
  description text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read entities"
  ON entities FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert entities"
  ON entities FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update entities"
  ON entities FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete entities"
  ON entities FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_entities_case_id ON entities(case_id);

CREATE TABLE IF NOT EXISTS relations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  source_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
  target_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
  relation_type text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE relations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read relations"
  ON relations FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert relations"
  ON relations FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update relations"
  ON relations FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete relations"
  ON relations FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_relations_case_id ON relations(case_id);

CREATE TABLE IF NOT EXISTS claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES crisis_cases(id) ON DELETE CASCADE,
  content text NOT NULL DEFAULT '',
  claim_type text NOT NULL DEFAULT 'fact',
  credibility text NOT NULL DEFAULT 'medium',
  source_doc_id uuid REFERENCES source_documents(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read claims"
  ON claims FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert claims"
  ON claims FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon update claims"
  ON claims FOR UPDATE TO anon USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon delete claims"
  ON claims FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS idx_claims_case_id ON claims(case_id);
