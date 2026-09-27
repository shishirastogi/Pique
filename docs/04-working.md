# 04 — How the System Works (End-to-End)

> The operational story: state machine, timing, lock mechanics, and full walkthroughs with real API calls. UI details per screen are in `05-ui-spec.md`; endpoint payloads in `07-backend-api.md`.

---

## 1. The Complete Lifecycle

```text
LAUNCH
  │  app boots → auth device token → GET /lock/status
  ▼
IDLE ─────────────────────────────────────────────────────────────┐
  │  user types "I need to study thermodynamics for my exam"       │
  ▼  POST /tasks/parse                                             │
TASK_INPUT ──(parser returns TaskObject)──► TASK_PARSED            │
  │                                          │                     │
  │  level missing? ◄── ClarifyingQuestion ──┘ (≤ 1 question)      │
  ▼  duration chips 5/10/15/20                                     │
SESSION_GENERATING  POST /sessions                                 │
  │  retrieve → rank → sequence → generate → safety → persist      │
  ▼                                                                │
SESSION_ACTIVE   GET /sessions/{id}/items, card playback           │
  │  heartbeat POST /sessions/{id}/events every 30 s + per-card    │
  ▼  last card = first_work_action                                 │
SESSION_ENDING   POST /sessions/{id}/complete                      │
  │                                                                │
  ▼                                                                │
LOCKED   lock_until = now + 120 min (server) ──► overlay           │
  │  GET /lock/status re-checks; no POST /sessions allowed         │
  ▼  housekeeper clears expired locks                              │
UNLOCKED ──────────────────────────────────────────────────────────┘
```

---

## 2. Session State Machine (authoritative)

Mirrors idea doc §23. Server stores `sessions.status`; client mirrors it in `useSessionStore`.

| State | Entered when | Allowed exits | Side effects on entry |
|---|---|---|---|
| `IDLE` | boot, unlock, abandon-from-idle | `TASK_INPUT` | clear session store |
| `TASK_INPUT` | user focuses prompt | `TASK_PARSED`, `IDLE` | — |
| `TASK_PARSED` | parse response OK | `SESSION_GENERATING`, `TASK_INPUT` (edit) | cache `TaskObject` |
| `SESSION_GENERATING` | `POST /sessions` accepted | `SESSION_ACTIVE`, `TASK_INPUT` (failure) | server: full generation pipeline |
| `SESSION_ACTIVE` | items ready | `SESSION_ENDING`, `LOCKED` (hard timeout) | countdown starts |
| `SESSION_ENDING` | last item shown **or** hard end | `LOCKED` | completion metrics |
| `LOCKED` | complete/abandon/timeout | `UNLOCKED` | `lock_until` set; overlay |
| `UNLOCKED` | `lock_until` passed | `IDLE` | history entry finalized |

**Transition triggers (server-enforced invariants):**

1. `POST /sessions` while `LOCKED` → `409 {code:"LOCKED", lock_until}` — client never even shows the home composer when locked.
2. `SESSION_ACTIVE` exceeding `ends_at + grace(30s)` → server auto-completes on next heartbeat; client immediately renders Session Complete.
3. Abandon (End Early) from `SESSION_ACTIVE` **still locks** — *Decision:* otherwise End Early becomes a loophole to re-roll content. Rationale + copy in `05` §8.

---

## 3. Timing Model

| Element | Authority | Mechanism |
|---|---|---|
| Session end | **Server** (`sessions.ends_at`) | client mirrors; heartbeat re-syncs; 30 s grace |
| Countdown UI | Client | `useCountdown` corrected by `useServerClock` offset |
| Lock expiry | **Server** (`lock_until`, DB + Redis TTL `lock:{user_id}`) | housekeeper job sweeps expiries; relaunch re-checks |
| Per-card dwell | Client guidance | `planned_seconds` per item; soft auto-advance ON is an opt-in setting, default **manual Next** (Decision: auto-advance encourages passive consumption — off by default) |
| Heartbeat | Client → `POST /sessions/{id}/events` every 30 s + on card transitions | carries cursor position, clock sanity, skipped flags |

---

## 4. Playback Mechanics

1. Client fetches **all** items once (`GET /sessions/{id}/items`): payload includes rendered text, media URLs, per-item `planned_seconds`, `position`, `phase`.
2. Client preloads images/GIFs of next 2 items; generation placeholders render skeleton cards.
3. Item events sent on transition: `{content_id, position, dwell_ms, skipped}` — feeds ranking + analytics (`13`).
4. Interactive items (poll, question, challenge) record the answer in `engagement` jsonb.
5. Final card is always `first_work_action` (e.g. *"Open your notes: start with the second law."*). Next is replaced by **Finish Warm-up**.
6. `SESSION_ENDING` screen shows summary + "I'm starting now" button (initiation self-report) → `POST /sessions/{id}/complete` → `LOCKED`.

---

## 5. Lock Mechanics

```text
complete_session()
  lock = LockService.start_lock(user, session, minutes=settings.lock_minutes)
  ├─ INSERT lock_state(user_id, lock_until, session_id)
  └─ SETEX lock:{user_id} <ttl_seconds> {lock_until}      # Redis, fast path
```

- **Reads:** `GET /lock/status` checks Redis first, falls back to DB.
- **Expiry:** housekeeper worker every 60 s: `DELETE FROM lock_state WHERE lock_until < now()`; TTL handles Redis automatically.
- **Offline relaunch:** the client reads locally cached `lock_until` (secure storage on device); stays locked if unreachable.
- **Emergency unlock (Decision):** exists (*Settings ▸ Locked screen ▸ Emergency unlock*) gated by type-to-confirm sentence; logged as `lock_break` event with reason; shown in History. Default ON for MVP because hard-locking a desktop app the user could force-quit anyway creates dishonesty without safety. Phase 4 may replace with OS-level enforcement where the escape hatch can disappear.

---

## 6. End Early & Abandonment

- **End Early** button in player → confirmation modal ("You'll still be locked for 2 h — End early?") → `abandon_session(reason)` → `LOCKED`. Recorded as `session_abandon` metric with drop-off position (`13`).
- **Window closed / crash:** client heartbeat stops; server marks session `SESSION_ENDING` after 90 s silence and applies lock at original `ends_at`. Prevents "kill the app to dodge the lock" while staying fair on real crashes (lock starts from original end time, not restart).

---

## 7. Worked Example — Student, End to End

Profile: `{interests:["cricket"], humor:"sarcastic", language:"hinglish", default level: beginner}`

**Step 1 — parse**
```http
POST /api/v1/tasks/parse
{"raw_text": "I need to study thermodynamics for my exam tomorrow, I'm weak at physics"}
→ 200 {"task": {"goal":"exam_prep","category":"education","subject":"physics",
        "topic":"thermodynamics","subtopics":["entropy","laws of thermodynamics"],
        "level":"beginner","urgency":"tomorrow","language":"hinglish","confidence":0.91},
       "clarification": null}
```
Parser inferred `level` from "weak at physics" (confidence 0.91 ≥ 0.6) → **no clarifying question**.

**Step 2 — create session**
```http
POST /api/v1/sessions
{"task_id":"tsk_01H…","duration_minutes":10}
```
Server pipeline (~4.8 s): 96 retrieved candidates + 7 generated (poll, question, 2 analogies incl. cricket bridge, micro-lesson, joke, first-work-action) → ranked → 10-slot plan → safety pass → persisted.

`→ 201 {"session_id":"ses_01J…","status":"SESSION_ACTIVE","ends_at":"…T+10min","item_count":10}`

**Step 3 — playback**: client pulls 10 items; sequence (per `10` §7): hook meme → surprising entropy image → entropy fact → why-question → Carnot engine visual → **cricket-energy analogy** → joke → poll → micro-lesson → first work action ("Open notes: start with the second law").

Heartbeats at :30 s marks; user skips card 7 (recorded).

**Step 4 — complete**
```http
POST /api/v1/sessions/ses_01J…/complete
{"started_work_confirmed": true}
→ 200 {"lock": {"lock_until":"…T+120min"}}
```
UI shows WARM-UP COMPLETE → LOCKED overlay with `02:00:00` countdown → user minimizes to work.

---

## 8. Edge Cases & Failure Handling

| Case | Handling |
|---|---|
| Duplicate prompt re-entered | Allowed after unlock; rank cache (`hash(task+profile+replan_count)`) partially reused but sequence re-planned to vary items |
| Empty candidate pool (obscure topic) | Generation-only session (LLM writes all cards); quality-scored; if generation also fails → graceful message + suggest rephrase, no session created, no lock |
| Clarification answered with "skip" | defaults: `level=intermediate`… **Decision:** MVP default `beginner` — safer to under- than over-estimate |
| Provider API down during on-demand fetch | circuit-open for 5 min; proceed with DB-only pool |
| Session creation > 12 s | client cancels with new idempotency key? — no: keeps polling same key once; server is idempotent on `X-Idempotency-Key` (`07` §6). Timeout UX: `05` §4 |
| User edits system clock | countdowns never trust local clock (`07` server stamps; heartbeat detects drift > 60 s and forces re-sync) |
| Multi-device same account | Lock is per-user → second device receives `409 LOCKED`; active session takeover transfers cursor via last heartbeat |
| Content reported mid-session | card immediately replaced by reserve item at same position (server returns replacement in report response) |

---

## 9. Offline Mode (MVP-lite)

- Full task parse + AI generation require connectivity. Offline path serves a **generic curiosity mini-session** from the ~30 locally seeded cards + last 1–2 topics' cached cards; clearly badged "Offline warm-up"; lock still applies from local state.
- Queue-and-sync: completion + events flush when connectivity returns (`analytics_events` carry `client_ts` + `server_ts`).
