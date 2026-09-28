// Session/lock orchestration store (docs/03 B.2) driving the Figma screens.
import { create as createStore } from "zustand";
import { api, ApiError, getToken } from "./lib/api";
import { deviceFp } from "./lib/device";
import type { ContentCard, Duration, LockStatus, SessionOut, TaskObject } from "./types";

export type Screen = "welcome" | "how" | "details" | "session" | "locked";
export type Sheet = "none" | "clarify" | "report" | "endEarly" | "emergency";

interface Progress { shownAt: number; skipped: boolean; engagement?: Record<string, unknown> }

interface AppState {
  ready: boolean;
  screen: Screen;
  sheet: Sheet;
  toast: string | null;
  error: string | null;

  taskId: string | null;
  task: TaskObject | null;
  clarifyOptions: string[] | null;
  clarifyQuestion: string | null;
  busy: boolean;
  selectedDuration: Duration;
  selectedLockMinutes: number;

  session: SessionOut | null;
  items: ContentCard[];
  cursor: number;
  progress: Record<number, Progress>;
  abandoned: boolean;

  lock: LockStatus | null;

  boot(): Promise<void>;
  setScreen(s: Screen): void;
  setSheet(s: Sheet): void;
  setToast(t: string | null): void;

  startFlow(taskText: string, duration: Duration, lockMinutes?: number): Promise<void>;
  answerClarify(answer: string): Promise<void>;
  skipClarify(): Promise<void>;

  markShown(i: number): void;
  setEngagement(i: number, e: Record<string, unknown>): void;
  nextCard(): void;
  endEarly(): Promise<void>;
  completeSession(startedWork: boolean | null): Promise<void>;

  reportCurrent(reason: string, comment?: string): Promise<void>;
  emergencyUnlock(confirm: string): Promise<void>;
  pollLock(): Promise<void>;
}

let heartbeat: number | null = null;

export const useApp = createStore<AppState>()((set, get) => ({
  ready: false, screen: "welcome", sheet: "none", toast: null, error: null,
  taskId: null, task: null, clarifyOptions: null, clarifyQuestion: null, busy: false,
  selectedDuration: 10,
  selectedLockMinutes: 120,
  session: null, items: [], cursor: 0, progress: {}, abandoned: false,
  lock: null,

  async boot() {
    try {
      if (!getToken()) await api.auth(deviceFp());
      const lock = await api.lockStatus();
      if (lock.locked) { set({ lock, screen: "locked", ready: true }); return; }
    } catch (e) {
      set({ error: e instanceof ApiError ? e.message : "Backend unreachable" });
    }
    set({ ready: true });
  },

  setScreen: (screen: Screen) => set({ screen }),
  setSheet: (sheet: Sheet) => set({ sheet }),
  setToast: (toast: string | null) => { set({ toast }); if (toast) setTimeout(() => set({ toast: null }), 2500); },

  async startFlow(taskText: string, duration: Duration, lockMinutes = 120) {
    const finalLock = Math.max(60, lockMinutes);
    set({ busy: true, error: null, selectedDuration: duration, selectedLockMinutes: finalLock });
    try {
      const r = await api.parseTask(taskText);
      set({ taskId: r.task_id, task: r.task });
      if (r.clarification) {
        set({ busy: false, clarifyOptions: r.clarification.options,
              clarifyQuestion: r.clarification.question, sheet: "clarify" });
        return;
      }
      await startSessionWith(set, get, r.task_id, duration, finalLock);
    } catch (e) {
      set({ busy: false, error: e instanceof ApiError ? e.message : "Could not parse task" });
    }
  },

  async answerClarify(answer: string) {
    const { taskId, task } = get();
    set({ sheet: "none", busy: true });
    if (task && ["beginner", "intermediate", "advanced"].includes(answer)) {
      set({ task: { ...task, level: answer as TaskObject["level"] } });
    }
    if (taskId) await api.clarify(taskId, answer).catch(() => undefined);
    await startSessionWith(set, get, taskId!);
  },

  async skipClarify() {
    set({ sheet: "none", busy: true });
    const { taskId } = get();
    await startSessionWith(set, get, taskId!);
  },

  markShown(i: number) {
    const p = get().progress;
    if (!p[i]) {
      set({ progress: { ...p, [i]: { shownAt: Date.now(), skipped: false } } });
      const { session, items } = get();
      if (session) {
        api.sendEvents(session.session_id,
          [{ type: "item_shown", position: i, content_id: items[i]?.content_id }]).catch(() => undefined);
      }
    }
  },

  setEngagement(i: number, e: Record<string, unknown>) {
    const p = get().progress;
    set({ progress: { ...p, [i]: { ...(p[i] ?? { shownAt: Date.now(), skipped: false }), engagement: e } } });
  },

  nextCard() {
    const { cursor, items, session, progress } = get();
    const cur = progress[cursor];
    if (session && cur) {
      api.sendEvents(session.session_id, [{
        type: "item_done", position: cursor, content_id: items[cursor]?.content_id,
        dwell_ms: Date.now() - cur.shownAt, skipped: cur.skipped || undefined,
        engagement: cur.engagement,
      }]).catch(() => undefined);
    }
    if (cursor + 1 < items.length) {
      set({ cursor: cursor + 1 });
      get().markShown(cursor + 1);
    }
  },

  async endEarly() {
    set({ sheet: "none", abandoned: true });
    await get().completeSession(null);
  },

  async completeSession(startedWork: boolean | null) {
    const { session, selectedLockMinutes } = get();
    stopHeartbeat();
    if (!session) { set({ screen: "locked" }); return; }
    try {
      const res = await api.completeSession(session.session_id, {
        started_work_confirmed: startedWork, abandoned: get().abandoned });
      if (res?.lock) {
        set({
          lock: {
            locked: true,
            lock_until: res.lock.lock_until,
            remaining_seconds: (res.lock.minutes ?? selectedLockMinutes ?? 120) * 60,
            session_id: session.session_id,
            minutes: res.lock.minutes ?? selectedLockMinutes ?? 120,
          },
        });
      }
    } catch { /* lock applies locally regardless */ }
    const lock = await api.lockStatus().catch(() => get().lock);
    set({ lock, screen: "locked", session: null, items: [], cursor: 0, abandoned: false });
  },

  async reportCurrent(reason: string, comment?: string) {
    const { items, cursor, session } = get();
    const card = items[cursor];
    if (card) {
      await api.reportContent({ content_id: card.content_id, session_id: session?.session_id,
        reason, comment }).catch(() => undefined);
    }
    set({ sheet: "none" });
    get().setToast("Reported — thanks for flagging it.");
  },

  async emergencyUnlock(confirm: string) {
    await api.emergencyUnlock(confirm);
    set({ sheet: "none", lock: null, screen: "welcome" });
  },

  async pollLock() {
    try {
      const lock = await api.lockStatus();
      if (!lock.locked) set({ lock: null, screen: "welcome" });
      else set({ lock });
    } catch { /* keep local countdown */ }
  },
}));

async function startSessionWith(
  set: (s: Partial<AppState>) => void, get: () => AppState, taskId: string,
  durationOverride?: Duration,
  lockMinutesOverride?: number,
) {
  const duration = durationOverride ?? get().selectedDuration;
  const lockMinutes = lockMinutesOverride ?? get().selectedLockMinutes ?? 120;
  try {
    const session = await api.createSession(taskId, duration, lockMinutes);
    const { items } = await api.sessionItems(session.session_id);
    set({ session, items, cursor: 0, progress: {}, abandoned: false, busy: false, screen: "session" });
    get().markShown(0);
    startHeartbeat(get);
  } catch (e) {
    if (e instanceof ApiError && e.code === "LOCKED") {
      const lock = await api.lockStatus().catch(() => null);
      set({ lock, screen: "locked", busy: false });
    } else {
      set({ busy: false, error: e instanceof ApiError ? e.message : "Could not start session" });
    }
  }
}

function startHeartbeat(get: () => AppState) {
  stopHeartbeat();
  heartbeat = window.setInterval(async () => {
    const s = get();
    if (!s.session) { stopHeartbeat(); return; }
    if (Date.now() >= new Date(s.session.ends_at).getTime()) {
      await s.completeSession(null);      // hard stop: countdown owns the session
      return;
    }
    try {
      const r = await api.sendEvents(s.session.session_id, [{ type: "heartbeat" }]);
      if (r.force_complete) await s.completeSession(null);
    } catch { /* offline: countdown continues locally (docs/04 §9) */ }
  }, 30_000);
}

function stopHeartbeat() {
  if (heartbeat !== null) { clearInterval(heartbeat); heartbeat = null; }
}
