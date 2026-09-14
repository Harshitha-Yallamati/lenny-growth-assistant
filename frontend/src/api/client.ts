import type {
  ChatResponsePayload,
  ConfigPayload,
  Provider,
  SessionDetail,
  SessionSummary,
  Skill,
  ArtifactFormat,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, "Could not reach the backend. Is it running?");
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  createSession: (userMetadata: Record<string, unknown> = {}) =>
    request<SessionSummary>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ user_metadata: userMetadata }),
    }),

  listSessions: () => request<SessionSummary[]>("/api/sessions"),

  getSession: (sessionId: string) => request<SessionDetail>(`/api/sessions/${sessionId}`),

  deleteSession: (sessionId: string) =>
    request<void>(`/api/sessions/${sessionId}`, { method: "DELETE" }),

  sendMessage: (
    sessionId: string,
    message: string,
    skill?: Skill,
    artifactFormat?: ArtifactFormat
  ) =>
    request<ChatResponsePayload>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
        skill: skill ?? null,
        artifact_format: artifactFormat ?? null,
      }),
    }),

  getConfig: () => request<ConfigPayload>("/api/config"),

  setProvider: (provider: Provider) =>
    request<ConfigPayload>("/api/config", {
      method: "POST",
      body: JSON.stringify({ provider }),
    }),
};
