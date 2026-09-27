# 07 — Backend & API Specification

> FastAPI service. Implements idea doc §24. Routers live under `app/routers/`, business logic in `app/services/` (`03` Part A), data access in `app/repositories/` (`06`).

---

## 1. Service Layout

```text
app/main.py            # app factory, middleware, router registration
app/core/config.py     # pydantic-settings (env in §8)
app/core/security.py   # JWT issue/verify, device fingerprint
app/core/logging.py    # structlog, request-id
app/routers/           # thin: validate → call service → map errors
  auth.py tasks.py sessions.py profile.py content.py lock.py admin.py
app/services/          # see 03-functions.md
app/schemas/           # pydantic request/response (codegen from shared-types)
```

Middleware order: request-id → access log → CORS (desktop origin only) → auth → rate-limit (`rate:{user}:{route}`, 60 req/min default, 10/min on `POST /sessions`) → error envelope.

---

## 2. Authentication

**MVP: anonymous device accounts.**
1. First launch → `POST /auth/session` with device fingerprint → server creates `users` row → returns `{access_token (JWT, 2 h), refresh_token (30 d, rotating)}`.
2. Refresh rotates and detects reuse (old refresh seen twice → revoke family, re-auth silently from device_fp).
3. Email linking (magic link) is post-MVP; endpoint stubbed.

All endpoints below require `Authorization: Bearer <access>` except `/auth/session`.

## 3. Error Model

```json
{ "error": { "code": "LOCKED", "message": "Warm-up locked until 16:12 UTC.",
             "details": { "lock_until": "2026-09-24T16:12:00Z" } } }
```

| Code family | HTTP | Examples |
|---|---|---|
| `VALIDATION` | 422 | empty prompt, bad duration |
| `AUTH` | 401/403 | expired token, wrong user |
| `LOCKED` | 409 | session create while locked |
| `NOT_FOUND` | 404 | session/content id |
| `CONFLICT` | 409 | duplicate idempotency outcome |
| `UPSTREAM` | 502 | provider/LLM failure |
| `RATE_LIMITED` | 429 | — |
| `INTERNAL` | 500 | — |

---

## 4. Endpoint Specifications

Base: `/api/v1`. Schemas referenced: `TaskObject` (03 A.2), `ContentCard` (below).

### 4.1 `POST /auth/session`
Req `{ "device_fp": "sha256…" }` → `201 { "access_token", "refresh_token", "user_id", "is_new_user": true }`

### 4.2 `POST /tasks/parse`
Parses natural-language intention (`TaskParserService.parse_task`).
Req:
```json
{ "raw_text": "I need to study thermodynamics for my exam tomorrow, I'm weak at physics" }
```
Res `200`:
```json
{ "task_id": "tsk_01J…",
  "task": { "goal": "exam_prep", "category": "education", "subject": "physics",
            "topic": "thermodynamics", "subtopics": ["entropy", "second law"],
            "level": "beginner", "urgency": "tomorrow", "language": "hinglish",
            "duration_minutes": null, "confidence": 0.91 },
  "clarification": null }
```
With missing essentials (`04` §8):
```json
{ "task_id": "…", "task": { …, "level": null },
  "clarification": { "field": "level",
    "question": "How familiar are you with thermodynamics?",
    "options": ["beginner", "intermediate", "advanced"] } }
```
- `POST /tasks/{task_id}/clarify` — req `{"answer": "beginner"}` → returns refined `task`.

### 4.3 `POST /sessions`
Body `{ "task_id", "duration_minutes": 10 }` + header `X-Idempotency-Key: uuid`.
Runs pipeline (`02` §6). → `201`:
```json
{ "session_id": "ses_01J…", "status": "SESSION_ACTIVE",
  "started_at": "…", "ends_at": "…T10:00Z", "planned_items": 10,
  "experiment_arm": "treatment" }
```
Errors: `409 LOCKED` (details `{lock_until}`) · `422 VALIDATION` · `502 UPSTREAM` (pool+generation both failed — client offers rephrase, `04` §8).

### 4.4 `GET /sessions/{id}`
→ `{ "session_id", "status", "task": TaskObject, "duration_minutes", "started_at", "ends_at", "items": [ {"content_id","position","phase","planned_seconds"} … ] }`

### 4.5 `GET /sessions/{id}/items`
Full card payloads, ordered. The client fetches once and plays locally.
```json
{ "items": [ {
    "content_id": "cnt_01J…", "position": 0, "phase": "entertainment",
    "planned_seconds": 45, "type": "meme",
    "title": "Thermodynamics students be like", "body": "",
    "media": { "kind": "image", "url": "https://…/…jpg", "width": 800, "height": 600 },
    "attribution": { "required": true, "text": "CC-BY · uploader …", "source_url": "…" },
    "interaction": { "kind": "none" } },
  { "…": "…", "type": "poll",
    "interaction": { "kind": "poll", "question": "Which first?", "options": ["Carnot cycle","Entropy"] } },
  { "…": "…", "type": "first_work_action", "position": 9,
    "interaction": { "kind": "finish" },
    "body": "Open your notes: start with the second law." } ] }
```

### 4.6 `POST /sessions/{id}/events` (heartbeat + item events)
```json
{ "events": [
  {"type":"item_shown","content_id":"cnt_…","position":2,"ts":"…"},
  {"type":"item_done","content_id":"cnt_…","position":1,"dwell_ms":31000,"skipped":false,
   "engagement":{"poll_choice":0}},
  {"type":"heartbeat","cursor":2,"client_now":"…"} ] }
```
→ `200 { "server_now": "…", "force_complete": false }` — `force_complete:true` when past `ends_at`+grace (`04` §2-2). Clock drift > 60 s → `409 VALIDATION details{server_now}` triggers re-sync.

### 4.7 `POST /sessions/{id}/feedback`
Body `{ "items": [ {"content_id","rating":1}, {"content_id","rating":-1,"reason":"not funny"} ] }` → `204`. Optional per session; lightweight thumbs, **not** a social like system.

### 4.8 `POST /sessions/{id}/complete`
Body `{ "started_work_confirmed": true|false, "abandoned": false, "abandon_reason"?: "string" }`
→ `200 { "status": "LOCKED", "lock": { "lock_until": "…", "minutes": 120 } }`
Idempotent (double-tap safe). Server stores initiation flag (`06 sessions.started_work_confirmed`).

### 4.9 `GET /profile`
→ full profile (`06.user_profiles` shape) + computed `effective_level_defaults`.

### 4.10 `PATCH /profile`
Partial update; echoes updated profile. Updating `lock_minutes` applies to **next** lock only ( `05` §10.7). `POST /profile/reset-personalization` clears learned preferences (keeps explicit settings; `14` §4).

- `GET /history?limit=30` — session list for History screen (topic, status, initiation badge).
- `POST /sessions/{id}/initiation` — retro initiation self-report `{ "started": true }` (History screen, `05` §11).

### 4.11 `GET /lock/status`
→ `200 { "locked": true, "lock_until": "…", "remaining_seconds": 7052, "session_id": "…" }` or `{ "locked": false }`.
`POST /lock/emergency-unlock` — body `{ "confirm": "I NEED TO STOP" }` → unlocks, logs `lock_break`, returns status (`05` §9).

### 4.12 `GET /content/search` (internal/debug + admin preview)
`?q=&type=&topic=&limit=` → ranked candidates. Auth: admin role. Useful during development of the ranker.

### 4.13 `POST /content/report`
`{ "content_id", "session_id"?, "reason", "comment"? }` → `201 { "report_id", "replacement_item": ContentCard|null }` (replacement card keeps playback seamless, `05` §7).

### 4.14 Admin (role-gated; idea doc §24)
| Endpoint | Purpose |
|---|---|
| `POST /admin/ingestion/run` `{provider, queries[], limit}` | enqueue ingestion jobs (`11`) |
| `GET /admin/moderation/queue?status=pending` | human review list (`12`) |
| `POST /admin/moderation/review` `{queue_id, action: approve|remove}` | resolve + update content.status |
| `POST /admin/content/reindex` | recompute embeddings |
| `POST /admin/content/re-score` | re-run quality scoring (model upgrade) |

---

## 5. Background Jobs (ARQ worker; queues per `11`)

| Job | Schedule | What |
|---|---|---|
| `ingest_source` | cron 03:00 + manual | prefetch top topics (`08` §8) |
| `process_asset` | chained | OCR → classify → moderate → score → embed → store |
| `sweep_locks` | every 60 s | expire locks (`04` §5) |
| `daily_aggregates` | 01:00 | analytics rollups (`13`) |
| `refresh_hot_sources` | 6 h | refresh trending topic pools |
| `reembed_pending` | 30 min | drain embedding backlog |

All jobs idempotent; retries: 3, exponential backoff w/ jitter.

---

## 6. Idempotency, Caching, Rate Limits

- `POST /sessions` requires `X-Idempotency-Key`; repeated key returns the **original** response (client refresh-safe).
- Rank cache key: `rankcache:{sha256(task_object + profile_sig + config_version)}` TTL 6 h — makes repeated identical prompts fast while `SequencePlanner` still re-sorts for variety (`10` §8).
- Rate limits: `POST /sessions` 10/min (also limited by lock invariant anyway); `POST /content/report` 10/min; parse 30/min.

---

## 7. Observability & Health

- Structlog JSON, `request_id` propagated to worker jobs; Sentry for API + Tauri crash reporting.
- Metrics (Prometheus): `session_create_seconds` histogram per pipeline stage, `llm_call_seconds{provider,tier}`, `external_fetch_total{provider,code}`, `rank_cache_hit_ratio`.
- `GET /healthz` (liveness) / `GET /readyz` (db+redis+llm-ping, used by deploy gate).

---

## 8. Configuration (env)

| Var | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgres+psycopg://…/pique` | pg16 + pgvector |
| `REDIS_URL` | `redis://…/0` | |
| `JWT_SECRET` | 64-byte | rotate via dual-kid header |
| `LLM_PROVIDERS` (design; slice uses the 3 vars below) | `gemini,groq` | ordered fallback chain |
| `PIQUE_LLM_PROVIDER` | `none\|gemini\|groq` | `none` = heuristic parser + template generator (offline-safe) |
| `PIQUE_LLM_API_KEY` | AI Studio / Groq key | free tiers; never in repo — see `infra/env.example` |
| `PIQUE_LLM_MODEL` | `gemini-flash-latest` / `llama-3.3-70b-versatile` | defaults target live aliases; pin only if needed |
| `PIQUE_<PROVIDER>_ENABLED` | `true/false` | `WIKIPEDIA/WIKIMEDIA/OPENVERSE/GUTENBERG` flags |
| `EMBEDDING_PROVIDER` | `openai:text-embedding-3-small@1024` | dimension must match `content.embedding` |
| `OCR_ENGINE` | `tesseract|paddle` | |
| `OPENVERSE_*`, `UNSPLASH_*`, `GIPHY_*`, `SMITHSONIAN_*` | keys | per-provider `08` |
| `OBJECT_STORE_*` | R2 creds | optional |
| `RANKING_WEIGHTS` | json override | defaults from `config` table |
| `LOCK_DEFAULT_MINUTES` | `120` | profile overridable |
| `ENV` | `dev|staging|prod` | |

Secrets via mounted files / platform secret store; never env-in-repo (`14` §5).
