export type CaseStatus = "draft" | "grounded" | "agents_ready" | "simulated";
export type DocType = "news" | "complaint" | "statement";
export type SourceOrigin = "case_upload" | "global_library" | "evidence_pack";
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
  evidence_pack_id: string | null;
  evidence_pack_source_id: string | null;
  source_topic_id: string | null;
  source_topic_assignment_id: string | null;
  source_origin: SourceOrigin;
  title: string;
  content: string;
  doc_type: DocType;
  source_metadata: Record<string, unknown>;
  created_at: string;
}

export interface GlobalSourceDocument {
  id: string;
  title: string;
  content: string;
  doc_type: DocType;
  canonical_url: string | null;
  content_hash: string | null;
  source_kind: string;
  authority_level: string;
  freshness_status: string;
  source_status: string;
  source_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SourceTopic {
  id: string;
  name: string;
  description: string;
  parent_topic_id: string | null;
  topic_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CaseSourceTopic {
  id: string;
  case_id: string;
  topic_id: string;
  relation_type: string;
  reason: string;
  created_at: string;
  updated_at: string;
}

export interface SourceTopicAssignment {
  id: string;
  global_source_id: string;
  topic_id: string;
  topic_name: string | null;
  relevance_score: number;
  reason: string;
  assigned_by: string;
  source_candidate_id: string | null;
  discovery_job_id: string | null;
  assignment_metadata: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SourceRegistryAssignmentSummary {
  assignment_id: string;
  topic_id: string;
  topic_name: string;
  relevance_score: number;
  reason: string;
  assigned_by: string;
  status: string;
}

export interface SourceMatchedFragment {
  id: string;
  source_scope: "global" | "candidate";
  source_id: string;
  fragment_index: number;
  text: string;
  similarity: number;
  content_hash: string;
}

export interface SourceRankingReason {
  key: string;
  label: string;
  value: string;
  score: number | null;
}

export interface SemanticRecallStatus {
  applied: boolean;
  reason: string | null;
  query: string | null;
  indexed_fragment_count: number;
  matched_fragment_count: number;
}

export interface SourceRegistrySource {
  id: string;
  source_scope?: "global" | "candidate";
  global_source_id?: string | null;
  candidate_id?: string | null;
  candidate_review_status?: CandidateReviewStatus | string | null;
  title: string;
  content: string;
  doc_type: DocType;
  canonical_url: string | null;
  content_hash: string | null;
  source_kind: string;
  authority_level: string;
  freshness_status: string;
  source_status: string;
  source_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  topic_assignments: SourceRegistryAssignmentSummary[];
  usage_count: number;
  duplicate_candidate: boolean;
  already_in_case: boolean;
  semantic_support?: number | null;
  final_score?: number | null;
  matched_fragments?: SourceMatchedFragment[];
  ranking_reasons?: SourceRankingReason[];
}

export interface SourceRegistryListResponse {
  outcome: "completed";
  sources: SourceRegistrySource[];
  topic_id: string | null;
  smart_view: string | null;
}

export interface SourceUsageCase {
  case_id: string;
  case_title: string;
  source_document_id: string;
  source_origin: string;
  source_topic_id: string | null;
  created_at: string;
}

export interface SourceUsageResponse {
  outcome: "completed";
  global_source_id: string;
  topic_assignments: SourceTopicAssignment[];
  cases: SourceUsageCase[];
  usage_count: number;
}

export interface CaseSourceSelectionSection {
  key: string;
  title: string;
  description: string;
  sources: SourceRegistrySource[];
}

export interface CaseSourceSelectionResponse {
  outcome: "completed";
  case_id: string;
  case_topics: CaseSourceTopic[];
  sections: CaseSourceSelectionSection[];
  semantic_recall?: SemanticRecallStatus;
}

export interface SourceDocumentSnapshotResponse {
  outcome: "created";
  id: string;
  case_id: string;
  global_source_id: string | null;
  source_topic_id: string | null;
  source_topic_assignment_id: string | null;
  source_origin: string;
  title: string;
  content: string;
  doc_type: DocType;
  source_metadata: Record<string, unknown>;
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
  job_id: string | null;
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

export interface AgentGenerationRequest {
  case_id: string;
}

export interface AgentGenerationResponse {
  outcome: "completed";
  case_id: string;
  case_status: string;
  agents: {
    role: AgentRole;
    stance: string;
    concern: string;
    emotional_sensitivity: number;
    spread_tendency: number;
    persona_description: string;
    initial_beliefs: string[];
  }[];
}

export interface SimulationSubmissionResponse {
  outcome: "accepted";
  run_id: string;
  job_id: string;
  job_status: string;
  run_status: SimStatus;
  should_poll: boolean;
  job_type: string;
  job_status_path: string;
  status_path: string | null;
}

export interface AsyncSubmissionResponse {
  outcome: "accepted";
  job_id: string;
  job_type: string;
  job_status: string;
  should_poll: boolean;
  job_status_path: string;
  status_path: string | null;
}

export interface GraphExtractionSubmissionResponse extends AsyncSubmissionResponse {
  case_id: string;
  document_count: number;
}

export interface JobStatusResponse {
  outcome: "status";
  id: string;
  job_id: string;
  job_type: string;
  status: string;
  should_poll: boolean;
  job_status_path: string;
  status_path: string | null;
  run_id: string | null;
  last_error: string | null;
  last_error_code: string | null;
  locked_at: string | null;
  heartbeat_at: string | null;
  updated_at: string | null;
  created_at: string | null;
}

export interface SimulationRunStatusResponse {
  outcome: "status";
  id: string;
  job_type: string;
  job_id: string | null;
  status: SimStatus;
  job_status_path: string;
  status_path: string | null;
  error_message: string | null;
  total_rounds: number;
  completed_rounds: number;
  last_completed_round: number;
  last_heartbeat_at: string | null;
  created_at: string;
  completed_at: string | null;
  should_poll: boolean;
}

export interface GraphExtractionStatusResponse {
  outcome: "status";
  job_id: string;
  case_id: string;
  job_type: string;
  status: string;
  job_status_path: string;
  status_path: string | null;
  document_count: number;
  processed_documents: number;
  failed_documents: number;
  entities_count: number;
  relations_count: number;
  claims_count: number;
  last_error: string | null;
  last_error_code: string | null;
  created_at: string | null;
  updated_at: string | null;
  should_poll: boolean;
}

export type SourceDiscoveryStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CandidateReviewStatus = "pending" | "accepted" | "rejected";
export type EvidencePackStatus = "draft" | "grounding_started";

export interface SourceScoreDimensions {
  relevance: number;
  authority: number;
  freshness: number;
  claim_richness: number;
  diversity: number;
  grounding_value: number;
}

export interface SourceCandidate {
  id: string;
  discovery_job_id: string;
  case_id: string;
  title: string;
  url: string | null;
  canonical_url: string | null;
  source_type: string;
  language: string;
  region: string;
  published_at: string | null;
  provider: string;
  provider_metadata: Record<string, unknown>;
  content: string;
  excerpt: string;
  content_hash: string;
  classification: string;
  claim_previews: Record<string, unknown>[];
  stakeholder_previews: Record<string, unknown>[];
  review_status: CandidateReviewStatus;
  scores: SourceScoreDimensions;
  total_score: number;
  duplicate_of: string | null;
  created_at: string;
  updated_at: string;
  semantic_support?: number | null;
  matched_fragments?: SourceMatchedFragment[];
  ranking_reasons?: SourceRankingReason[];
}

export interface SourceDiscoveryJobResponse {
  outcome: "accepted" | "status";
  source_discovery_job_id: string;
  case_id: string;
  job_id: string;
  job_type: string;
  status: SourceDiscoveryStatus;
  job_status: string;
  job_status_path: string;
  status_path: string;
  should_poll: boolean;
  topic: string;
  description: string;
  region: string;
  language: string;
  time_range: string;
  source_types: string[];
  max_sources: number;
  query_plan: string[];
  candidate_count: number;
  accepted_count: number;
  rejected_count: number;
  last_error: string | null;
  last_error_code: string | null;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface EvidencePackSource {
  id: string;
  evidence_pack_id: string;
  candidate_id: string;
  source_document_id: string | null;
  sort_order: number;
  title: string;
  url: string | null;
  source_type: string;
  language: string;
  region: string;
  published_at: string | null;
  provider: string;
  provider_metadata: Record<string, unknown>;
  content: string;
  excerpt: string;
  score_dimensions: SourceScoreDimensions;
  total_score: number;
  claim_previews: Record<string, unknown>[];
  stakeholder_previews: Record<string, unknown>[];
  created_at: string;
}

export interface EvidencePack {
  id: string;
  case_id: string;
  discovery_job_id: string | null;
  title: string;
  status: EvidencePackStatus;
  source_count: number;
  sources: EvidencePackSource[];
  created_at: string;
  updated_at: string;
  grounded_at: string | null;
}

export interface EvidencePackCreationResponse {
  outcome: "created";
  evidence_pack_id: string;
  case_id: string;
  source_count: number;
  evidence_pack: EvidencePack;
}

export interface EvidencePackGroundingResponse extends GraphExtractionSubmissionResponse {
  evidence_pack_id: string;
  materialized_document_count: number;
}

export type SourceDiscoveryAssistantMode = "search_planning" | "source_interpretation" | "search_backed_briefing";

export interface SourceDiscoveryAssistantRequest {
  mode: SourceDiscoveryAssistantMode;
  question?: string;
  case_id?: string | null;
  discovery_job_id?: string | null;
  topic?: string;
  description?: string;
  region?: string;
  language?: string;
  time_range?: string;
  source_types?: string[];
  max_sources?: number | null;
}

export interface SourceDiscoveryAssistantCitation {
  candidate_id: string | null;
  title: string;
  url: string | null;
  published_at: string | null;
  quote: string;
}

export interface SourceDiscoveryAssistantPlanningSuggestion {
  label: string;
  rationale: string;
  topic: string | null;
  description: string | null;
  region: string | null;
  language: string | null;
  time_range: string | null;
  source_types: string[];
  queries: string[];
}

export interface SourceDiscoveryAssistantRecommendedSettings {
  topic: string | null;
  description: string | null;
  region: string | null;
  language: string | null;
  time_range: string | null;
  source_types: string[];
  max_sources: number | null;
  queries: string[];
}

export interface SourceDiscoveryAssistantSourceSummary {
  title: string;
  url: string | null;
  source_type: string;
  provider: string;
  published_at: string | null;
  summary: string;
  citation: SourceDiscoveryAssistantCitation | null;
}

export interface SourceDiscoveryAssistantBriefingLimit {
  max_queries: number;
  max_results_per_query: number;
  max_total_sources: number;
  max_content_chars_per_source: number;
}

export interface SourceDiscoveryAssistantTimelineItem {
  event_date: string | null;
  reporting_date: string | null;
  title: string;
  summary: string;
  citations: SourceDiscoveryAssistantCitation[];
}

export interface SourceDiscoveryAssistantEventStage {
  name: string;
  summary: string;
  confidence: "low" | "medium" | "high";
  citations: SourceDiscoveryAssistantCitation[];
}

export interface SourceDiscoveryAssistantSourceConflict {
  summary: string;
  sides: string[];
  citations: SourceDiscoveryAssistantCitation[];
}

export interface SourceDiscoveryAssistantEvidenceGap {
  summary: string;
  follow_up_searches: string[];
}

export interface SourceDiscoveryAssistantResponse {
  outcome: "completed";
  mode: SourceDiscoveryAssistantMode;
  answer: string;
  insufficient_evidence: boolean;
  planning_suggestions: SourceDiscoveryAssistantPlanningSuggestion[];
  recommended_settings: SourceDiscoveryAssistantRecommendedSettings | null;
  source_summaries: SourceDiscoveryAssistantSourceSummary[];
  key_actors: string[];
  controversy_focus: string[];
  briefing_limits: SourceDiscoveryAssistantBriefingLimit | null;
  timeline: SourceDiscoveryAssistantTimelineItem[];
  event_stages: SourceDiscoveryAssistantEventStage[];
  citations: SourceDiscoveryAssistantCitation[];
  conflicts: SourceDiscoveryAssistantSourceConflict[];
  evidence_gaps: SourceDiscoveryAssistantEvidenceGap[];
  follow_up_searches: string[];
}

export interface SourceCandidateLibrarySaveResponse {
  outcome: "saved";
  candidate_id: string;
  global_source_id: string;
  topic_id: string | null;
  topic_assignment_id: string | null;
  duplicate_reused: boolean;
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
      source_topics: { Row: SourceTopic; Insert: Partial<SourceTopic>; Update: Partial<SourceTopic> };
      case_source_topics: { Row: CaseSourceTopic; Insert: Partial<CaseSourceTopic>; Update: Partial<CaseSourceTopic> };
      source_topic_assignments: { Row: SourceTopicAssignment; Insert: Partial<SourceTopicAssignment>; Update: Partial<SourceTopicAssignment> };
      source_fragments: { Row: SourceMatchedFragment; Insert: Partial<SourceMatchedFragment>; Update: Partial<SourceMatchedFragment> };
      source_discovery_jobs: { Row: SourceDiscoveryJobResponse; Insert: Partial<SourceDiscoveryJobResponse>; Update: Partial<SourceDiscoveryJobResponse> };
      source_candidates: { Row: SourceCandidate; Insert: Partial<SourceCandidate>; Update: Partial<SourceCandidate> };
      evidence_packs: { Row: EvidencePack; Insert: Partial<EvidencePack>; Update: Partial<EvidencePack> };
      evidence_pack_sources: { Row: EvidencePackSource; Insert: Partial<EvidencePackSource>; Update: Partial<EvidencePackSource> };
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
