# 02 — System Architecture

> Source: `pique-idea.md` §§20–23, 41. Implementation-level architecture for the MVP with an explicit upgrade path.

---

## 1. High-Level Architecture

```text
                        ┌──────────────────────────┐
                        │        CLIENT APP        │
                        │  React + TS (Vite) ·     │
                        │  Capacitor: Android/iOS  │
                        │                          │
                        │  Task input UI           │
                        │  Session player          │
                        │  Countdown / Lock UI     │
                        │  Profile & settings      │
                        │  Local cache (offline)   │
                        └────────────┬─────────────┘
                                     │ HTTPS /api/v1 (JWT)
                        ┌────────────▼─────────────┐
                        │        API SERVER        │
                        │     Python + FastAPI     │
                        │                          │
                        │  Auth · Sessions · Lock  │
                        │  Profile · Feedback      │
                        │  Content API · Reports   │
                        └──────┬───────┬───────┬───┘
                               │       │       │
                ┌──────────────▼─┐   ┌─▼──────────────┐   ┌────────────────┐
                │ AI ORCHESTRATION│   │ CONTENT SERVICE│   │  DATA STORAGE  │
                │                │   │                │   │                │
                │ Task parser    │   │ Retrieval      │   │ PostgreSQL     │
                │ Sequence plan  │   │ Ranking        │   │  + pgvector    │
                │ Generation     │   │ Generation mix │   │ Redis          │
                │ Personalization│   │ Provenance     │   │ Object store*  │
                │ Quality/safety │   └───────┬────────┘   └────────────────┘
                └──────┬─────────┘           │
                       │                     │
            ┌──────────┼──────┐   ┌──────────▼──────────────────────┐
            ▼          ▼      ▼   ▼          ▼          ▼            ▼
           LLM     Embeddings  OCR   Openverse  Wikimedia  Smithsonian  Gutenberg
           provider provider  svc    LoC · Unsplash(opt) · GIPHY(opt)

   ┌─────────────────────────────────────────────────────────────────────┐
   │ INGESTION WORKER (async job runner)                                 │
   │ prefetch → normalize → provenance → OCR → classify → moderate →     │
   │ score → embed → store                                               │
   └─────────────────────────────────────────────────────────────────────┘
```

\* Object storage only for assets we are **permitted** to store (see `08-data-fetching.md` §6). Third-party hotlink-only providers are never copied.

---

## 2. Component Responsibilities

| Component | Tech | Responsibility | Failure budget |
|---|---|---|---|
| **Client app** | React 18 + TypeScript + Vite, Zustand; **Android/iOS via Capacitor (final target — user-confirmed)** | All UI, local countdown mirror, offline fallback, in-app lock enforcement | Must remain usable read-only offline |
| **API server** | FastAPI (Python 3.12), Uvicorn/Gunicorn | Authn/z, session lifecycle, lock authority, ranking/generation orchestration, profile, feedback | 99.5% MVP target; sessions must degrade gracefully |
| **Ingestion worker** | ARQ (Redis-backed) or Celery | Content pipeline jobs on schedule + on-demand | At-least-once, idempotent jobs |
| **PostgreSQL 16 + pgvector** | — | System of record + semantic search | Daily backup, PITR later |
| **Redis 7** | — | Lock TTLs, session live-state, rank cache, rate limits, job queue | Ephemeral — no source of truth |
| **LLM layer** | Provider abstraction (`03` §AI) | Parse, generate, classify, score | Fallback chain + cached canned content |
| **Object storage** | R2/S3 | Licensed-cacheable assets + generated images/cards | Optional at MVP |
| **OCR** | PaddleOCR or Tesseract sidecar | Text extraction from images | Queue-backed; non-blocking |

**Decision — final product is Android + iOS (user-confirmed).** One React/Vite codebase serves the vertical slice as a web app, then **Capacitor** wraps it into Android/iOS shells (supersedes the idea doc's Tauri-desktop-first suggestion; desktop shell optional later). Mobile lock reality per idea doc §8 stands: an app cannot hard-lock the OS — MVP lock is **in-app** (no new sessions + full-screen lock state); OS-level focus integration (Android App Timers / iOS Screen Time & Family Controls) is a later phase.

**Decision — anonymous-first auth for MVP.** Device-token account (no email required) so onboarding friction stays near zero; email linking later (`07` §2, `14` §3).

---

## 3. Tech Stack Decision Table

| Layer | Choice | Alternatives considered | Why |
|---|---|---|---|
| App shell (ship) | **Capacitor** wrapping the web build (Android/iOS) | React Native, Flutter, Tauri desktop-first | One codebase, native focus APIs later; RN/Flutter would fork UI work; desktop is not the final target (user decision) |
| UI | **React + TypeScript + Vite** | Svelte/Solid | Team familiarity, ecosystem, fast iteration, Capacitor-compatible |
| Client state | **Zustand** (TanStack Query arrives with real content fetching, 08-phase) | Redux | Minimal boilerplate for the slice; Query later for server cache/retries |
| API | **FastAPI** | Django, Node/Nest | AI ecosystem, async, pydantic schema-first |
| DB | **PostgreSQL + pgvector** | Separate vector DB | One store for relational + vectors at MVP scale |
| Cache/queue | **Redis** | RabbitMQ/SQS | Lock TTLs, rate limits, and job queue in one |
| Jobs | **ARQ** | Celery | Async-native, lightweight; Celery if we outgrow it |
| Embeddings | Provider-neutral `EmbeddingService` (default: OpenAI `text-embedding-3-small` @1024d or `bge-large` self-host) | Cohere, local e5 | Pluggable; dimension pinned in DB |
| LLM | Provider abstraction (`ChatProvider`) with ≥2 providers configured | — | Idea doc §21: never hard-wire one model vendor |
| OCR | Pluggable: Tesseract default, PaddleOCR optional | Cloud OCR | Not coupled to one provider (§21) |
| Infra | **Docker + docker-compose** (dev), single VPS or Fly.io/Render (MVP prod) | K8s | Explicitly *not* k8s at MVP — see §9 |

---

## 4. Repository Layout (monorepo)

```text
pique-project/
├─ docs/                        # ← this implementation plan
├─ apps/
│  └─ client/                   # one React+Vite codebase; Capacitor android/ios later
│     ├─ src/
│     │  ├─ screens/            # 1 per screen, mirrors 05-ui-spec.md
│     │  │  ├─ Onboarding/
│     │  │  ├─ Home/
│     │  │  ├─ SessionPlayer/
│     │  │  ├─ SessionComplete/
│     │  │  ├─ Locked/
│     │  │  ├─ History/
│     │  │  └─ Settings/
│     │  ├─ components/
│     │  │  ├─ cards/           # one renderer per content type
│     │  │  ├─ Countdown.tsx
│     │  │  ├─ ProgressDots.tsx
│     │  │  └─ ...
│     │  ├─ hooks/              # useSession, useCountdown, useLockStatus...
│     │  ├─ stores/             # zustand slices: session, profile, lock
│     │  ├─ lib/
│     │  │  ├─ api/             # typed client, 1 module per router
│     │  │  └─ time.ts
│     │  └─ types/              # generated from packages/shared-types
│     ├─ capacitor.config.ts    # when wrapping (later)
│     └─ android/ ios/          # Capacitor-generated native projects (later)
├─ services/
│  ├─ api/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ core/               # config, security, logging
│  │  │  ├─ routers/            # auth.py tasks.py sessions.py profile.py
│  │  │  │                       content.py lock.py admin.py
│  │  │  ├─ services/           # business logic (see 03-functions.md)
│  │  │  ├─ repositories/       # SQL/CRUD (see 06-database.md)
│  │  │  ├─ schemas/            # pydantic in/out models
│  │  │  ├─ ai/                 # providers, prompts, parsers
│  │  │  └─ workers/            # job handlers (ARQ)
│  │  ├─ alembic/               # migrations
│  │  └─ tests/
│  └─ ingestion-worker/         # shares app/ package; own entrypoint
├─ packages/
│  └─ shared-types/             # JSON schemas → TS + pydantic codegen
├─ infra/
│  ├─ docker-compose.yml        # api, worker, postgres(+pgvector), redis
│  ├─ docker-compose.prod.yml
│  └─ env.example
└─ pique-idea.md
```

**Shared-types contract:** canonical schemas are JSON Schema in `packages/shared-types`; a codegen step emits TS types and pydantic models so client/server can never drift.

---

## 5. Request-Flow Map (runtime)

| Flow | Path | Detail doc |
|---|---|---|
| Enter task | client → `POST /tasks/parse` → AI task parser → optional clarify | 07 §4.2 |
| Start session | client → `POST /sessions` → retrieve → rank → sequence → generate → safety check → session items persisted | 07 §4.3, 09, 10 |
| Playback | client pulls `GET /sessions/{id}/items` once, renders locally, heartbeats every 30 s | 04 §4 |
| Complete + lock | client → `POST /sessions/{id}/complete` → server sets `lock_until` → Redis TTL + DB row | 04 §5 |
| Lock check | client polls/ls `GET /lock/status`; server authoritative | 07 §4.11 |
| Feedback/report | `POST /sessions/{id}/feedback`, `POST /content/report` → moderation queue | 07, 12 |
| Ingestion | scheduler enqueues jobs → worker pipeline stages (11) | 08, 11 |

---

## 6. Session Generation — Service Interaction (critical path)

```text
POST /sessions {task_id, duration}
  │
  ├─ SessionService.create()  ──► sessions row (status=SESSION_GENERATING)
  ├─ RetrievalService.fetch_candidates(task, profile, k≈120)
  │     ├─ pgvector semantic search + FTS + filters        (09 §3)
  │     └─ on-demand external fetch if pool thin           (08 §5)
  ├─ GenerationService.fill_gaps(task, profile, missing_types)
  ├─ RankingService.rank(candidates, ctx)                  (09)
  ├─ SequencePlanner.plan(ranked, duration)                (10)
  ├─ SafetyGate.check(plan)                                (12)
  ├─ persist session_items; status=SESSION_ACTIVE
  └─ return session + first N items (client preloads)
```

Target latency: **p95 < 8 s** from `POST /sessions` to playable sequence. Mitigations: candidate prefetch for recent topics, parallel retrieve+generate, Redis rank cache for near-duplicate task objects (`07` §6, `09` §10).

---

## 7. Time Authority & Lock Enforcement (architecture view)

- **Server is the clock.** `sessions.ends_at`, `lock_until` are server-computed. Client countdown mirrors server values and re-syncs on each heartbeat (`POST /sessions/{id}/events`).
- **Client-side enforcement (MVP reality):** the client renders a full-screen lock state when `LOCKED`; quitting/reopening re-fetches `/lock/status`. Local encrypted storage caches `lock_until` so an offline re-launch stays locked (Capacitor Secure Storage when native). **Decision:** a determined user can bypass an in-app lock; OS-level focus APIs (later phase) strengthen it. Product framing (consent + friction) matters more than arms-race enforcement.
- Server replays guard: generation endpoints refuse to create a new session while `lock_until > now` unless the woman-in-the-middle edge case — client clock skew — resolves server-side.

---

## 8. Offline & Degradation Strategy

| Scenario | Behavior |
|---|---|
| API down at session start | Offer **offline mini-session** from locally cached cards (client preload of ~30 generic-interest + last-topic cards) with a visible "offline mode" chip; lock is still applied locally |
| API fails mid-session | Local countdown continues from last sync; completion is queued and retried; lock applied from last known `lock_until` |
| Rediscover on relaunch | `GET /lock/status` refreshes; if unreachable, trust local cached `lock_until` |
| LLM provider down | Fallback chain → template-based generation → retrieval-only sessions (never block the core loop) |

---

## 9. Deployment (MVP)

```text
docker-compose.prod.yml
├─ api        (FastAPI, 2 replicas behind Caddy/Nginx, TLS)
├─ worker     (ARQ ingestion + housekeeper jobs)
├─ postgres   (pgvector/pg16, volume, daily pg_dump)
├─ redis      (AOF persistence for lock keys)
└─ caddy      (reverse proxy + auto-TLS)
```

Environments: `dev` (compose with hot reload) · `staging` (prod-like, seeded content) · `prod`. Config via env vars only (`07` §8). CI: lint → typecheck → unit → integration (testcontainers) → client web build; Capacitor Android/iOS builds on tag once wrappers land (`15`).

**Explicitly deferred:** Kubernetes, multi-region, managed vector DB, Elasticsearch, system-wide blockers, mobile. (Idea doc §42 — "What NOT to build first".)

---

## 10. Scalability Notes (Phase 3+ path)

| Bottleneck to expect | Trigger | Upgrade |
|---|---|---|
| pgvector latency | content > ~2M rows or p95 search > 120 ms | HNSW index tuning → dedicated Qdrant/pgvector partition |
| External API quotas | on-demand fetch share > 30% | Aggressive prefetch of top-N topics, provider pooling |
| LLM cost/latency at session creation | cost/session > budget | Cache task-object digests → reuse ranked pools; distill generation templates |
| Redis job backlog | ingest lag > 1 h | Horizontal worker scale-out (jobs are idempotent) |
| Analytics volume | events > 5M/day | Move `analytics_events` to columnar store (ClickHouse) — schema already append-only |

No premature work on any of these until telemetry says so (golden rule: behavior first, infra second — idea doc §29).
