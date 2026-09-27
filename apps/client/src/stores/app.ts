// Session + lock orchestration (docs/03 B.2 stores; B.4 handlers).
import { create } from "zustand";
import { api, ApiError } from "../lib/api";
import type { ContentCard, Duration, LockStatus, SessionOut, TaskObject } from "../types";

export type Screen = "home" | "generating" | "player" | "complete" | "locked";
export type Modal = "none" | "clarify" | "report" | "endEarly" | "emergencyUnlock";

interface ItemProgress {
  shownAt: number | null;
  dwellMs: number;
  skipped: boolean;
  engagement?: Record<string, unknown>;
}

interface AppState {
  ready: boolean;
  screen: Screen;
  modal: Modal;
  toast: string | null;

  taskId: string | null;
  task: TaskObject | null;
  clarifyOptions: string[] | null;
  clarifyQuestion: string | null;
  duration: Duration;

  session: SessionOut | null;
  items: ContentCard[];
  cursor: number;
  progress: Record<number, ItemProgress>;
  abandoned: boolean;

  lock: LockStatus | null;
  error: string | null;

  init(): Promise<void>;
  setToast(t: string | null): void;
  setModal(m: Modal): void;

  submitPrompt(text: string): Promise<void>;
  answerClarify(answer: string): void;
  skipClarify(): void;
  setDuration(d: Duration): void;
  startSession(): Promise<void>;
  cancelGeneration(): void;

  markShown(i: number): void;
  setEngagement(i: number, e: Record<string, unknown>): void;
  nextCard(): void;
  goTo(i: number): void;
  endEarly(): Promise<void>;
  completeSession(startedWork: boolean | null): Promise<void>;

  emergencyUnlock(confirm: string): Promise<void>;
  pollLock(): Promise<void>;
  hardTimeout(): Promise<void>;
}

let heartbeat: number | null = null;
let generatingAbort = false;

export const useApp = create<AppState>((set, get) => ({
  ready: false, screen: "home", modal: "none", toast: null,
  taskId: null, task: null, clarifyOptions: null, clarifyQuestion: null, duration: 10,
  session: null, items: [], cursor: 0, progress: {}, abandoned: false,
  lock: null, error: null,

  async init() {
    set({ ready: true });
    try {
      const lock = await api.lockStatus();
      if (lock.locked) set({ lock, screen: "locked" });
    } catch (e) {
      if (e instanceof ApiError && e.code === "API_UNREACHABLE") set({ error: e.message });
    }
  },

  setToast: (toast) => { set({ toast }); if (toast) setTimeout(() => set({ toast: null }), 2500); },
  setModal: (modal) => set({ modal }),

  async submitPrompt(text) {
    set({ error: null });
    try {
      const r = await api.parseTask(text);
      set({ taskId: r.task_id, task: r.task });
      if (r.task.duration_minutes && [5, 10, 15, 20].includes(r.task.duration_minutes)) {
        set({ duration: r.task.duration_minutes as Duration });
      }
      if (r.clarification) {
        set({ clarifyOptions: r.clarification.options, clarifyQuestion: r.clarification.question, modal: "clarify" });
      } else {
        void get().startSession();
      }
    } catch (e) { set({ error: e instanceof ApiError ? e.message : "Could not parse task" }); }
  },

  answerClarify(answer) {
    const { taskId, task } = get();
    set({ modal: "none" });
    if (task && ["beginner", "intermediate", "advanced"].includes(answer)) {
      set({ task: { ...task, level: answer as TaskObject["level"] } });
    }
    if (taskId) void api.clarify(taskId, answer).catch(() => undefined);
    void get().startSession();
  },

  skipClarify() { set({ modal: "none" }); void get().startSession(); },
  setDuration: (duration) => set({ duration }),

  async startSession() {
    const { taskId, duration } = get();
    if (!taskId) return;
    set({ screen: "generating", error: null });
    generatingAbort = false;
    try {
      const session = await api.createSession(taskId, duration);
      if (generatingAbort) return;
      const { items } = await api.sessionItems(session.session_id);
      if (generatingAbort) return;
      set({ session, items, cursor: 0, progress: {}, abandoned: false, screen: "player" });
      startHeartbeat(set, get);
    } catch (e) {
      if (e instanceof ApiError && e.code === "LOCKED") {
        const lock = await api.lockStatus().catch(() => null);
        set({ lock, screen: "locked" });
      } else {
        set({ screen: "home", error: e instanceof ApiError ? e.message : "Could not start session" });
      }
    }
  },

  cancelGeneration() { generatingAbort = true; set({ screen: "home" }); },

  markShown(i) {
    const p = get().progress;
    if (!p[i]?.shownAt) set({ progress: { ...p, [i]: { shownAt: Date.now(), dwellMs: 0, skipped: false } } });
    if (get().session) {
      const it = get().items[i];
      api.sendEvents(get().session!.session_id,
        [{ type: "item_shown", position: i, content_id: it?.content_id }]).catch(() => undefined);
    }
  },

  setEngagement(i, e) {
    const p = get().progress;
    set({ progress: { ...p, [i]: { ...(p[i] ?? { shownAt: Date.now(), dwellMs: 0, skipped: false }), engagement: e } } });
  },

  nextCard() { get().goTo(get().cursor + 1); },

  goTo(i) {
    const { items, session, cursor, progress } = get();
    if (i >= items.length) return;
    const cur = progress[cursor];
    if (session && cur) {
      const ev = [{
        type: "item_done" as const, position: cursor, content_id: items[cursor]?.content_id,
        dwell_ms: Date.now() - (cur.shownAt ?? Date.now()), skipped: cur.skipped || undefined,
        engagement: cur.engagement,
      }];
      api.sendEvents(session.session_id, ev).catch(() => undefined);
    }
    set({ cursor: i });
    get().markShown(i);
  },

  async endEarly() {
    set({ modal: "none", abandoned: true });
    await get().completeSession(null);
  },

  async completeSession(startedWork) {
    const { session } = get();
    if (!session) return;
    stopHeartbeat();
    try {
      const r = await api.completeSession(session.session_id,
        { started_work_confirmed: startedWork, abandoned: get().abandoned });
      const lock = await api.lockStatus();
      set({ lock, screen: "locked", session: null, items: [] });
      void r;
    } catch { set({ screen: "locked" }); }
  },

  async emergencyUnlock(confirm) {
    await api.emergencyUnlock(confirm);
    set({ modal: "none", lock: null, screen: "home" });
  },

  async pollLock() {
    try {
      const lock = await api.lockStatus();
      if (!lock.locked && get().screen === "locked") set({ lock: null, screen: "home" });
      else set({ lock });
    } catch { /* keep local countdown */ }
  },

  async hardTimeout() {
    const { session } = get();
    if (!session) return;
    stopHeartbeat();
    set({ screen: "complete" });
  },
}));

function startHeartbeat(_set: unknown, get: () => AppState) {
  stopHeartbeat();
  heartbeat = window.setInterval(async () => {
    const s = get();
    if (!s.session) { stopHeartbeat(); return; }
    const endsAt = new Date(s.session.ends_at).getTime();
    if (Date.now() >= endsAt) { await s.hardTimeout(); return; }
    try {
      const r = await api.sendEvents(s.session.session_id, [{ type: "heartbeat" }]);
      if (r.force_complete) await s.hardTimeout();
    } catch { /* offline: countdown continues locally (docs/04 §9) */ }
  }, 30_000);
  // also a 1s hard-stop ticker so the timer is exact even before first heartbeat
}

function stopHeartbeat() {
  if (heartbeat !== null) { clearInterval(heartbeat); heartbeat = null; }
}
