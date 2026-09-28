// Contracts mirroring services/api/app/schemas (kept in sync manually for the slice;
// packages/shared-types codegen arrives in a later phase).

export type Duration = 5 | 10 | 15 | 20;

export interface TaskObject {
  goal: string;
  category: string;
  subject: string | null;
  topic: string;
  subtopics: string[];
  level: "beginner" | "intermediate" | "advanced" | null;
  urgency: string | null;
  duration_minutes: number | null;
  language: string;
  confidence: number;
}

export interface ClarifyingQuestion {
  field: string;
  question: string;
  options: string[];
}

export interface ParseResponse {
  task_id: string;
  task: TaskObject;
  clarification: ClarifyingQuestion | null;
}

export interface Interaction {
  kind: "none" | "poll" | "question" | "challenge" | "reveal" | "finish";
  question?: string | null;
  options?: string[] | null;
  hint?: string | null;
  answer?: string | null;
  reveal?: string | null;
}

export interface ContentCard {
  content_id: string;
  position: number;
  phase: string;
  planned_seconds: number;
  type: string;
  title: string | null;
  body: string;
  media: { kind: string; url?: string | null } | null;
  attribution: { required: boolean; text?: string; source_url?: string } | null;
  interaction: Interaction | null;
}

export interface SessionOut {
  session_id: string;
  status: string;
  task: TaskObject;
  duration_minutes: number;
  planned_items: number;
  started_at: string;
  ends_at: string;
}

export interface LockStatus {
  locked: boolean;
  lock_until: string | null;
  remaining_seconds: number;
  session_id: string | null;
  minutes?: number;
}

export type SessionEventPayload = {
  type: "item_shown" | "item_done" | "heartbeat" | "initiation_reported";
  content_id?: string;
  position?: number;
  dwell_ms?: number;
  skipped?: boolean;
  engagement?: Record<string, unknown>;
  started?: boolean;
};
