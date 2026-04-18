import { BACKEND_API_BASE } from "./supabase";
import { getErrorMessage } from "./errors";

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  } | string;
}

export class BackendApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public requestId?: string,
    public route?: string,
  ) {
    super(message);
    this.name = "BackendApiError";
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

export async function requestBackend<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (!BACKEND_API_BASE) {
    throw new Error("BACKEND API URL is not configured.");
  }

  const response = await fetch(`${BACKEND_API_BASE}${normalizePath(path)}`, {
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
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
    throw new BackendApiError(
      response.status,
      message,
      typeof details === "object" && details && !Array.isArray(details) && "error" in details && typeof details.error !== "string"
        ? (details.error as { code?: string }).code
        : undefined,
      response.headers.get("x-request-id") || undefined,
      path,
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
