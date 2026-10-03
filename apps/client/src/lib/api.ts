// Typed API client (docs/03 B.1). Handles the stale-token self-heal (401 →
// re-auth device → retry once) and proxy-down messaging.
import type {
  ClarifyingQuestion, ContentCard, Duration, LockStatus, ParseResponse,
  SessionEventPayload, SessionOut, TaskObject,
} from "../types";
import { deviceFp } from "./device";

const DEFAULT_API_URL = "https://pique-api-175706581364.asia-south1.run.app";
const API_HOST = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/+$/, "");
const BASE = `${API_HOST}/api/v1`;
const TOKEN_KEY = "pique_token";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;
  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.status = status; this.code = code; this.details = details;
  }
}

export function getToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
function setToken(t: string) { localStorage.setItem(TOKEN_KEY, t); }

async function req<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(BASE + path, { ...init, headers });
  const text = res.status === 204 ? null : await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) {
    if (res.status >= 500 && !data?.error) {
      throw new ApiError(res.status, "API_UNREACHABLE",
        "Can't reach the Pique API on localhost:8000 — start it (dev.ps1) and retry.");
    }
    if (res.status === 401 && !isRetry && path !== "/auth/session") {
      localStorage.removeItem(TOKEN_KEY);
      await api.auth(deviceFp());
      return req<T>(path, init, true);
    }
    const e = data?.error ?? {};
    throw new ApiError(res.status, e.code ?? "INTERNAL", e.message ?? res.statusText, e.details);
  }
  return data as T;
}

export const api = {
  auth: async (deviceFpStr: string) => {
    const out = await req<{ access_token: string; user_id: string; is_new_user: boolean }>(
      "/auth/session", { method: "POST", body: JSON.stringify({ device_fp: deviceFpStr }) });
    setToken(out.access_token);
    return out;
  },
  parseTask: (raw_text: string) =>
    req<ParseResponse>("/tasks/parse", { method: "POST", body: JSON.stringify({ raw_text }) }),
  clarify: (taskId: string, answer: string) =>
    req<{ task_id: string; task: TaskObject; clarification: ClarifyingQuestion | null }>(
      `/tasks/${taskId}/clarify`, { method: "POST", body: JSON.stringify({ answer }) }),
  createSession: (taskId: string, duration: Duration, lockMinutes?: number) =>
    req<SessionOut>("/sessions", {
      method: "POST",
      body: JSON.stringify({
        task_id: taskId,
        duration_minutes: duration,
        ...(lockMinutes ? { lock_minutes: lockMinutes } : {}),
      }),
    }),
  getActiveSession: () => req<SessionOut | null>("/sessions/active"),
  getSession: (sessionId: string) => req<SessionOut>(`/sessions/${sessionId}`),
  resumeSession: (sessionId: string, remainingSeconds: number, cursor?: number) =>
    req<SessionOut>(`/sessions/${sessionId}/resume`, {
      method: "POST",
      body: JSON.stringify({ remaining_seconds: remainingSeconds, cursor }),
    }),
  patchProfile: (body: { lock_minutes?: number; [key: string]: unknown }) =>
    req<{ lock_minutes: number }>("/profile", { method: "PATCH", body: JSON.stringify(body) }),
  sessionItems: (sessionId: string) =>
    req<{ items: ContentCard[] }>(`/sessions/${sessionId}/items`),
  sendEvents: (sessionId: string, events: SessionEventPayload[]) =>
    req<{ server_now: string; force_complete: boolean }>(
      `/sessions/${sessionId}/events`, { method: "POST", body: JSON.stringify({ events }) }),
  completeSession: (sessionId: string, payload: { started_work_confirmed?: boolean | null;
    abandoned?: boolean; abandon_reason?: string | null }) =>
    req<{ status: string; lock: { lock_until: string; minutes: number } }>(
      `/sessions/${sessionId}/complete`, { method: "POST", body: JSON.stringify(payload) }),
  lockStatus: () => req<LockStatus>("/lock/status"),
  emergencyUnlock: (confirm: string) =>
    req<LockStatus>("/lock/emergency-unlock", { method: "POST", body: JSON.stringify({ confirm }) }),
  reportContent: (payload: { content_id: string; session_id?: string; reason: string; comment?: string }) =>
    req<{ report_id: string }>("/content/report", { method: "POST", body: JSON.stringify(payload) }),
};
