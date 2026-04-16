export type CaseStatus = "draft" | "grounded" | "agents_ready" | "simulated";
export type DocType = "news" | "complaint" | "statement";
export type SourceOrigin = "case_upload" | "global_library";
export type EntityType = "person" | "organization" | "product" | "event" | "location";
export type ClaimType = "allegation" | "fact" | "statement" | "event";
export type Credibility = "high" | "medium" | "low";
export type AgentRole = "consumer" | "supporter" | "critic" | "media";
export type RunType = "baseline" | "intervention";
export type SimStatus = "pending" | "running" | "completed" | "failed";
export type StrategyType = "apology" | "clarification" | "compensation" | "rebuttal";

export interface CrisisCase {
  id: string;
  title: string;
  description: string;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
}

export interface SourceDocument {
  id: string;
  case_id: string;
  global_source_id: string | null;
  source_origin: SourceOrigin;
  title: string;
  content: string;
  doc_type: DocType;
  created_at: string;
}

export interface GlobalSourceDocument {
  id: string;
  title: string;
  content: string;
  doc_type: DocType;
  created_at: string;
}

export interface Entity {
  id: string;
  case_id: string;
  name: string;
  entity_type: EntityType;
  description: string;
  created_at: string;
}

export interface Relation {
  id: string;
  case_id: string;
  source_entity_id: string | null;
  target_entity_id: string | null;
  relation_type: string;
  description: string;
  created_at: string;
  source_entity?: Entity;
  target_entity?: Entity;
}

export interface Claim {
  id: string;
  case_id: string;
  content: string;
  claim_type: ClaimType;
  credibility: Credibility;
  source_doc_id: string | null;
  created_at: string;
}

export interface AgentProfile {
  id: string;
  case_id: string;
  role: AgentRole;
  stance: string;
  concern: string;
  emotional_sensitivity: number;
  spread_tendency: number;
  initial_beliefs: string[];
  persona_description: string;
  created_at: string;
}

export interface SimulationRun {
  id: string;
  case_id: string;
  run_type: RunType;
  strategy_type: StrategyType | null;
  strategy_message: string | null;
  injection_round: number | null;
  total_rounds: number;
  status: SimStatus;
  error_message: string | null;
  created_at: string;
  last_heartbeat_at: string | null;
  completed_at: string | null;
}

export interface AgentResponse {
  agent_id: string;
  role: AgentRole;
  response: string;
  sentiment_delta: number;
  amplification: number;
}

export interface RoundState {
  id: string;
  run_id: string;
  round_number: number;
  agent_responses: AgentResponse[];
  overall_sentiment: number;
  polarization_level: number;
  narrative_state: string;
  strategy_applied: string | null;
  created_at: string;
}

export interface MetricSnapshot {
  id: string;
  run_id: string;
  round_number: number;
  sentiment_score: number;
  polarization_score: number;
  negative_claim_spread: number;
  stabilization_indicator: number;
  created_at: string;
}

export interface Database {
  public: {
    Tables: {
      crisis_cases: { Row: CrisisCase; Insert: Omit<CrisisCase, "id" | "created_at" | "updated_at">; Update: Partial<CrisisCase> };
      source_documents: { Row: SourceDocument; Insert: Omit<SourceDocument, "id" | "created_at">; Update: Partial<SourceDocument> };
      global_source_documents: { Row: GlobalSourceDocument; Insert: Omit<GlobalSourceDocument, "id" | "created_at">; Update: Partial<GlobalSourceDocument> };
      entities: { Row: Entity; Insert: Omit<Entity, "id" | "created_at">; Update: Partial<Entity> };
      relations: { Row: Relation; Insert: Omit<Relation, "id" | "created_at">; Update: Partial<Relation> };
      claims: { Row: Claim; Insert: Omit<Claim, "id" | "created_at">; Update: Partial<Claim> };
      agent_profiles: { Row: AgentProfile; Insert: Omit<AgentProfile, "id" | "created_at">; Update: Partial<AgentProfile> };
      simulation_runs: { Row: SimulationRun; Insert: Omit<SimulationRun, "id" | "created_at">; Update: Partial<SimulationRun> };
      round_states: { Row: RoundState; Insert: Omit<RoundState, "id" | "created_at">; Update: Partial<RoundState> };
      metric_snapshots: { Row: MetricSnapshot; Insert: Omit<MetricSnapshot, "id" | "created_at">; Update: Partial<MetricSnapshot> };
    };
  };
}
