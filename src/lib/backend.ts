import { BACKEND_API_BASE, supabase } from "./supabase";
import { getErrorMessage } from "./errors";
import type {
  AgentGenerationResponse,
  CandidateReviewStatus,
  CaseSourceSelectionResponse,
  EvidencePack,
  EvidencePackCreationResponse,
  EvidencePackGroundingResponse,
  GraphExtractionStatusResponse,
  GraphExtractionSubmissionResponse,
  JobStatusResponse,
  SimulationRunStatusResponse,
  SimulationSubmissionResponse,
  SourceCandidate,
  SourceCandidateLibrarySaveResponse,
  SourceDiscoveryAssistantRequest,
  SourceDiscoveryAssistantResponse,
  SourceDiscoveryJobResponse,
  SourceDiscoveryPlanningContext,
  SourceDocumentSnapshotResponse,
  SourceRegistryListResponse,
  SourceTopic,
  SourceTopicAssignment,
  SourceUsageResponse,
  StrategySequenceStep,
  StrategyType,
} from "./types";

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
    request_id?: string;
    route?: string;
  } | string;
}

export class BackendApiError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  route?: string;
  details?: unknown;

  constructor(
    status: number,
    message: string,
    code?: string,
    requestId?: string,
    route?: string,
    details?: unknown,
  ) {
    super(message);
    this.name = "BackendApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.route = route;
    this.details = details;
  }
}

function normalizePath(path: string): string {
  if (!path) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

function createRequestId(): string {
  const webCrypto = globalThis.crypto;

  if (typeof webCrypto?.randomUUID === "function") {
    return webCrypto.randomUUID();
  }

  if (typeof webCrypto?.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    webCrypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0"));
    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10, 16).join(""),
    ].join("-");
  }

  return `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

export function parseApiError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as ApiErrorPayload).error;
    if (typeof error === "string") {
      return error;
    }
    if (error?.message) {
      return error.message;
    }
  }
  return fallback;
}

async function buildBackendHeaders(initHeaders: HeadersInit | undefined): Promise<Record<string, string>> {
  const headers = new Headers(initHeaders || {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("x-request-id")) {
    headers.set("x-request-id", createRequestId());
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  return Object.fromEntries(headers.entries());
}

function normalizeStatusPath(pathOrId: string, prefix: string): string {
  if (!pathOrId) return prefix;
  if (pathOrId.startsWith("/api/") || pathOrId.startsWith("api/")) {
    return pathOrId;
  }
  return `${prefix}/${pathOrId}`;
}

export async function requestBackend<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (!BACKEND_API_BASE) {
    throw new Error("BACKEND API URL is not configured.");
  }

  const headers = await buildBackendHeaders(init.headers);
  const response = await fetch(`${BACKEND_API_BASE}${normalizePath(path)}`, {
    headers,
    ...init,
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error: unknown) {
    throw new BackendApiError(
      response.status,
      getErrorMessage(error, "Failed to decode backend response"),
      "INVALID_RESPONSE",
    );
  }

  if (!response.ok) {
    const message = parseApiError(payload, `Backend request failed with status ${response.status}`);
    const details = payload as ApiErrorPayload | undefined;
    const errorPayload =
      typeof details === "object"
      && details
      && !Array.isArray(details)
      && "error" in details
      && typeof details.error !== "string"
        ? details.error as { code?: string; details?: unknown; request_id?: string; route?: string }
        : undefined;
    throw new BackendApiError(
      response.status,
      message,
      errorPayload?.code,
      response.headers.get("x-request-id") || errorPayload?.request_id || undefined,
      errorPayload?.route || path,
      errorPayload?.details,
    );
  }

  return payload as T;
}

export async function parseBackendPayload<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new BackendApiError(response.status, parseApiError(payload, "Backend request failed"));
  }
  return payload as T;
}

export async function generateAgents(caseId: string): Promise<AgentGenerationResponse> {
  return requestBackend<AgentGenerationResponse>("/api/agent-generation", {
    method: "POST",
    body: JSON.stringify({ case_id: caseId }),
  });
}

export async function submitGraphExtraction(caseId: string): Promise<GraphExtractionSubmissionResponse> {
  return requestBackend<GraphExtractionSubmissionResponse>("/api/graph-extractions", {
    method: "POST",
    body: JSON.stringify({ case_id: caseId }),
  });
}

export async function fetchGraphExtractionStatus(pathOrJobId: string): Promise<GraphExtractionStatusResponse> {
  return requestBackend<GraphExtractionStatusResponse>(normalizeStatusPath(pathOrJobId, "/api/graph-extractions"));
}

export interface SubmitSimulationRequest {
  case_id: string;
  run_type: "baseline" | "intervention";
  total_rounds: number;
  strategy_type?: StrategyType;
  strategy_message?: string;
  injection_round?: number;
  strategy_sequence?: StrategySequenceStep[];
}

export async function submitSimulation(payload: SubmitSimulationRequest): Promise<SimulationSubmissionResponse> {
  return requestBackend<SimulationSubmissionResponse>("/api/simulations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchJobStatus(pathOrJobId: string): Promise<JobStatusResponse> {
  return requestBackend<JobStatusResponse>(normalizeStatusPath(pathOrJobId, "/api/jobs"));
}

export async function fetchSimulationRunStatus(pathOrRunId: string): Promise<SimulationRunStatusResponse> {
  return requestBackend<SimulationRunStatusResponse>(normalizeStatusPath(pathOrRunId, "/api/simulation-runs"));
}

export interface CreateSourceDiscoveryJobRequest {
  case_id: string;
  topic: string;
  description: string;
  region: string;
  language: string;
  time_range: string;
  source_types: string[];
  max_sources: number;
  planning_context?: SourceDiscoveryPlanningContext | null;
}

export async function createSourceDiscoveryJob(
  payload: CreateSourceDiscoveryJobRequest,
): Promise<SourceDiscoveryJobResponse> {
  return requestBackend<SourceDiscoveryJobResponse>("/api/source-discovery/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchSourceDiscoveryJob(jobId: string): Promise<SourceDiscoveryJobResponse> {
  return requestBackend<SourceDiscoveryJobResponse>(normalizeStatusPath(jobId, "/api/source-discovery/jobs"));
}

export async function askSourceDiscoveryAssistant(
  payload: SourceDiscoveryAssistantRequest,
): Promise<SourceDiscoveryAssistantResponse> {
  return requestBackend<SourceDiscoveryAssistantResponse>("/api/source-discovery/assistant", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface FetchSourceCandidatesParams {
  case_id?: string;
  discovery_job_id?: string;
  review_status?: CandidateReviewStatus;
}

export async function fetchSourceCandidates(params: FetchSourceCandidatesParams): Promise<SourceCandidate[]> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await requestBackend<{ candidates: SourceCandidate[] }>(`/api/source-candidates${suffix}`);
  return response.candidates;
}

export async function updateSourceCandidateReview(
  sourceId: string,
  reviewStatus: CandidateReviewStatus,
): Promise<SourceCandidate> {
  return requestBackend<SourceCandidate>(`/api/source-candidates/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify({ review_status: reviewStatus }),
  });
}

export async function saveSourceCandidateToLibrary(
  sourceId: string,
  payload: { topic_id?: string | null; reason?: string; assigned_by?: string },
): Promise<SourceCandidateLibrarySaveResponse> {
  return requestBackend<SourceCandidateLibrarySaveResponse>(`/api/source-candidates/${sourceId}/save-to-library`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface CreateEvidencePackRequest {
  case_id: string;
  discovery_job_id?: string;
  candidate_ids: string[];
  title?: string;
}

export async function createEvidencePack(payload: CreateEvidencePackRequest): Promise<EvidencePackCreationResponse> {
  return requestBackend<EvidencePackCreationResponse>("/api/evidence-packs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchEvidencePack(evidencePackId: string): Promise<EvidencePack> {
  return requestBackend<EvidencePack>(`/api/evidence-packs/${evidencePackId}`);
}

export async function startEvidencePackGrounding(evidencePackId: string): Promise<EvidencePackGroundingResponse> {
  return requestBackend<EvidencePackGroundingResponse>(`/api/evidence-packs/${evidencePackId}/start-grounding`, {
    method: "POST",
  });
}

export interface CreateSourceTopicRequest {
  name: string;
  description?: string;
  parent_topic_id?: string | null;
  topic_type?: string;
}

export async function fetchSourceTopics(): Promise<SourceTopic[]> {
  const response = await requestBackend<{ topics: SourceTopic[] }>("/api/source-topics");
  return response.topics;
}

export async function createSourceTopic(payload: CreateSourceTopicRequest): Promise<SourceTopic> {
  return requestBackend<SourceTopic>("/api/source-topics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSourceTopic(
  topicId: string,
  payload: Partial<CreateSourceTopicRequest> & { status?: string },
): Promise<SourceTopic> {
  return requestBackend<SourceTopic>(`/api/source-topics/${topicId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export interface FetchSourceRegistryParams {
  topic_id?: string;
  smart_view?: string;
  query?: string;
  source_kind?: string;
  authority_level?: string;
  freshness_status?: string;
  source_status?: string;
  case_id?: string;
}

function buildQuery(params: Record<string, string | undefined | null>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export async function fetchSourceRegistry(params: FetchSourceRegistryParams = {}): Promise<SourceRegistryListResponse> {
  return requestBackend<SourceRegistryListResponse>(`/api/source-registry${buildQuery({ ...params })}`);
}

export async function fetchSourceUsage(globalSourceId: string): Promise<SourceUsageResponse> {
  return requestBackend<SourceUsageResponse>(`/api/source-registry/${globalSourceId}/usage`);
}

export async function createSourceTopicAssignment(payload: {
  global_source_id: string;
  topic_id: string;
  relevance_score?: number;
  reason?: string;
  assigned_by?: string;
}): Promise<SourceTopicAssignment> {
  return requestBackend<SourceTopicAssignment>("/api/source-topic-assignments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function removeSourceTopicAssignment(assignmentId: string): Promise<SourceTopicAssignment> {
  return requestBackend<SourceTopicAssignment>(`/api/source-topic-assignments/${assignmentId}`, {
    method: "DELETE",
  });
}

export async function fetchCaseSourceSelection(
  caseId: string,
  query?: string,
): Promise<CaseSourceSelectionResponse> {
  return requestBackend<CaseSourceSelectionResponse>(
    `/api/cases/${caseId}/source-selection${buildQuery({ query })}`,
  );
}

export async function attachGlobalSourceToCase(payload: {
  case_id: string;
  global_source_id: string;
  topic_id?: string | null;
  assignment_id?: string | null;
}): Promise<SourceDocumentSnapshotResponse> {
  return requestBackend<SourceDocumentSnapshotResponse>(`/api/cases/${payload.case_id}/source-documents/from-library`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
