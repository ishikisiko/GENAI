import { BACKEND_API_BASE, supabase } from "./supabase";
import { getErrorMessage } from "./errors";
import type {
  AgentGenerationResponse,
  GraphExtractionStatusResponse,
  GraphExtractionSubmissionResponse,
  JobStatusResponse,
  SimulationRunStatusResponse,
  SimulationSubmissionResponse,
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
    headers.set("x-request-id", crypto.randomUUID());
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
