# 03 — Functions & Module Inventory

> The complete function-level design. Signatures are canonical: backend in Python, client in TypeScript. Schemas referenced here are defined in `06-database.md` / `07-backend-api.md`.

---

## PART A — BACKEND (FastAPI, `services/api`)

### A.1 AI Provider Abstraction (`app/ai/`)

```python
class ChatProvider(Protocol):
    async def complete(self, messages: list[Message], *,
                       model_tier: Literal["fast", "smart"] = "fast",
                       response_format: type[BaseModel] | None = None,
                       temperature: float = 0.7,
                       max_tokens: int = 2000,
                       timeout_s: float = 20.0) -> Completion: ...

class ProviderRegistry:
    def get(self, tier: str) -> ChatProvider: ...        # primary with fallback chain
    async def complete_with_fallback(self, req: CompletionRequest) -> Completion: ...
```

| Function | Input → Output | Notes |
|---|---|---|
| `build_task_parse_prompt(raw_text, profile) -> list[Message]` | str + Profile → prompt | Injects anti-injection guardrails (`14` §6) |
| `build_generation_prompt(kind, task, profile, ctx) -> list[Message]` | → prompt for one content item | One builder per generatable type (§A.5) |
| `build_scoring_prompt(candidate, task, profile) -> list[Message]` | → heuristic scoring prompt | Used only when LLM-assisted scoring enabled |

### A.2 Task Understanding (`app/services/task_parser.py`)

```python
class TaskParserService:
    async def parse_task(self, raw_text: str, profile: Profile) -> TaskObject
    def validate(self, obj: TaskObject) -> list[str]                  # returns missing fields
    def needs_clarification(self, obj: TaskObject) -> ClarifyingQuestion | None
    def refine_with_answer(self, obj: TaskObject, answer: str) -> TaskObject
```

**Behavior:** LLM-first (configured provider, JSON-mode) extracts `{goal, category, subject, topic, subtopics[], level, urgency, duration_minutes?, language}` with a **heuristic fallback** so parsing works keyless/offline. `needs_clarification` fires **only** when `level` or `topic` is unrecoverably missing — max one question (idea doc §6 step 2). Robust to non-academic tasks ("design a poster") and code-switching (Hinglish). Implemented: `app/services/task_parser.py` + `app/ai/` (gemini/groq free tiers, `PIQUE_LLM_PROVIDER`).

```python
@dataclass
class TaskObject:
    goal: str                # exam_prep | design | learn | create | other
    category: str            # education | creative | work | personal
    subject: str | None
    topic: str
    subtopics: list[str]
    level: Literal["beginner","intermediate","advanced"] | None
    urgency: str | None      # free text, e.g. "tomorrow"
    duration_minutes: Literal[5,10,15,20] | None
    language: str            # en | hi | hinglish
    confidence: float        # parser self-assessment 0..1
```

### A.3 Session Orchestration (`app/services/session_service.py`)

```python
class SessionService:
    async def create_session(self, user_id: UUID, task_id: UUID,
                             duration: int) -> Session                  # runs §6 pipeline, 02
    async def get_session(self, session_id: UUID, user_id: UUID) -> SessionDetail
    async def list_items(self, session_id: UUID) -> list[SessionItem]   # ordered, full payload
    async def record_event(self, session_id: UUID, event: SessionEvent) -> None
    async def complete_session(self, session_id: UUID,
                               payload: CompletionReport) -> SessionResult
    async def abandon_session(self, session_id: UUID, reason: str | None) -> None
    def check_invariants(self, session: Session) -> None                # no active session while locked
```

**Key invariant:** `create_session` raises `LockedError` if `LockService.status(user_id).locked`. Server-side truth, never client trust.

### A.4 Retrieval (`app/services/retrieval.py`)

```python
class RetrievalService:
    async def fetch_candidates(self, task: TaskObject, profile: Profile,
                               k: int = 120) -> list[Candidate]
    async def semantic_search(self, query_vec: Vector, filters: Filters,
                              k: int) -> list[Candidate]                # pgvector
    async def text_search(self, query: str, filters: Filters, k: int) -> list[Candidate]
    async def on_demand_external(self, task: TaskObject, k: int) -> list[Candidate]
    def merge_dedup(self, *pools: list[Candidate]) -> list[Candidate]
```

See `09-recommendation-algorithms.md` §3 for query construction and filters.

### A.5 Generation (`app/services/generation.py`)

```python
class GenerationService:
    async def generate(self, kind: GenKind, task: TaskObject,
                       profile: Profile, seeds_to_avoid: list[str]) -> GeneratedContent
    async def generate_poll(self, task, profile) -> GeneratedContent
    async def generate_question(self, task, profile, difficulty) -> GeneratedContent
    async def generate_micro_lesson(self, task, profile, subtopic) -> GeneratedContent
    async def generate_joke(self, task, profile, humor_style) -> GeneratedContent
    async def generate_first_work_action(self, task, profile) -> GeneratedContent   # terminal card
    def render_card_image(self, content: GeneratedContent) -> AssetRef | None        # SVG/PNG cards (opt)
```

`GenKind = Literal["analogy","poll","question","micro_lesson","joke","trivia","first_work_action"]`. Generated content is persisted as `content` rows with `provenance.type='generated'` for reuse + quality tracking (`11` §8).

### A.6 Analogy Engine (`app/services/analogy.py`) — signature feature

```python
class AnalogyService:
    async def pick_bridge_interest(self, profile: Profile, task: TaskObject) -> str | None
    async def generate_analogy(self, topic: str, interest: str,
                               level: str, language: str) -> GeneratedContent
    async def cache_key(self, topic: str, interest: str) -> str         # reuse good analogies
```

Algorithm detail: `09-recommendation-algorithms.md` §7.

### A.7 Ranking (`app/services/ranking.py`)

```python
class RankingService:
    async def rank(self, candidates: list[Candidate], ctx: RankingContext) -> list[RankedItem]
    async def score_one(self, c: Candidate, ctx: RankingContext) -> ScoreVector
    def combine(self, s: ScoreVector, weights: WeightConfig) -> float
    def apply_guardrails(self, ranked: list[RankedItem],
                         caps: GuardrailConfig) -> list[RankedItem]      # per-type/source caps
```

Full math: `09` §§4–6.

### A.8 Sequence Planning / Data Sorting (`app/services/sequencing.py`)

```python
class SequencePlanner:
    def plan(self, ranked: list[RankedItem], duration: int,
             task: TaskObject, profile: Profile) -> SequencePlan
    def slot_template(self, duration: int) -> list[SlotSpec]            # phases + budgets
    def fill_slots(self, ranked: list[RankedItem],
                   slots: list[SlotSpec]) -> list[PlannedItem]
    def validate(self, plan: SequencePlan) -> list[Violation]           # + auto-repair
    def allocate_dwell(self, plan: SequencePlan) -> None                # seconds per item
```

Full algorithm + constraints: `10-data-sorting-sequencing.md`.

### A.9 Safety Gate (`app/services/safety.py`)

```python
class SafetyGate:
    async def check_plan(self, plan: SequencePlan) -> None        # raises on violation
    async def check_item(self, c: Candidate) -> SafetyVerdict
```

Thin orchestrator over `ModerationService` (`11`, `12`).

### A.10 Lock (`app/services/lock_service.py`)

```python
class LockService:
    async def start_lock(self, user_id: UUID, session_id: UUID,
                         minutes: int) -> LockState               # DB row + Redis TTL
    async def status(self, user_id: UUID) -> LockState
    async def unlock_expired(self) -> int                          # housekeeper job
    async def emergency_unlock(self, user_id: UUID, confirm: str) -> LockState  # friction-gated
```

Lock model + emergency-unlock policy: `04` §5, `05` §8.

### A.11 Profile (`app/services/profile_service.py`)

```python
class ProfileService:
    async def get(self, user_id: UUID) -> Profile
    async def update(self, user_id: UUID, patch: ProfilePatch) -> Profile
    async def reset_personalization(self, user_id: UUID) -> None   # clears learned prefs
    async def learned_preferences(self, user_id: UUID) -> LearnedPrefs  # Phase 2
```

### A.12 Feedback & Reports

```python
class FeedbackService:
    async def record(self, user_id: UUID, session_id: UUID,
                     item_fb: list[ItemFeedback]) -> None
class ReportService:
    async def create_report(self, user_id, content_id, reason, comment) -> Report  # → moderation queue
```

### A.13 Analytics (`app/services/analytics.py`)

```python
class AnalyticsService:
    async def track(self, user_id: UUID | None, event: AnalyticsEvent) -> None
    async def task_initiation_rate(self, window: Window, arm: str | None) -> float
    def build_daily_aggregates(self) -> None                       # housekeeper job
```

Event taxonomy: `13`.

### A.14 Ingestion & Pipeline (`app/workers/`)

```python
class IngestionService:
    async def run_source(self, provider: str, query_plan: QueryPlan) -> IngestRunReport
    async def process_asset(self, raw: RawAsset) -> ContentRecord | None   # stages per 11
class OcrService(Protocol):
    async def extract_text(self, image: bytes) -> OcrResult
class EmbeddingService(Protocol):
    async def embed(self, texts: list[str]) -> list[Vector]                # batch
class ModerationService:
    async def screen(self, content: ContentRecord) -> ModerationResult
    async def quality_score(self, content: ContentRecord) -> QualityScores
class DedupService:
    async def is_duplicate(self, c: ContentRecord) -> bool                 # phash + cosine
```

### A.15 Auth (`app/services/auth_service.py`)

```python
class AuthService:
    async def issue_device_token(self, device_fp: str) -> TokenPair       # anonymous MVP account
    async def refresh(self, refresh_token: str) -> TokenPair
    async def link_email(self, user_id: UUID, email: str) -> None         # magic link, post-MVP
    async def resolve_user(self, jwt: str) -> UUID
```

---

## PART B — CLIENT (Tauri + React, `apps/desktop/src`)

### B.1 API client (`lib/api/`)

TanStack Query hooks, one module per router. All functions throw typed `ApiError{code,message}`.

```ts
authApi.createSession(): Promise<TokenPair>
tasksApi.parse(rawText: string): Promise<ParseResponse>           // task + clarification?
tasksApi.answerClarification(taskId, answer): Promise<TaskObject>
sessionsApi.create(taskId, duration): Promise<SessionDetail>
sessionsApi.get(id): Promise<SessionDetail>
sessionsApi.items(id): Promise<SessionItem[]>
sessionsApi.event(id, event): Promise<void>                       // heartbeat + item events
sessionsApi.complete(id, report): Promise<SessionResult>
sessionsApi.feedback(id, items: ItemFeedback[]): Promise<void>
profileApi.get(): Promise<Profile>;  profileApi.patch(p): Promise<Profile>
profileApi.resetPersonalization(): Promise<void>
lockApi.status(): Promise<LockState>
lockApi.emergencyUnlock(confirm: string): Promise<LockState>
contentApi.report(contentId, reason, comment?): Promise<void>
```

### B.2 State stores (Zustand, `stores/`)

```ts
useSessionStore { state: SessionState, session?, items[], cursor, dwellLeft,
                  actions: hydrate(), next(), skip(), endEarly(), complete() }
useLockStore    { lockedUntil, poll(), emergencyUnlock() }
useProfileStore { profile, save(), reset() }
useUiStore      { screen, modal, toast() }
```

### B.3 Hooks (`hooks/`)

```ts
useCountdown(target: Date, onExpire): { mm, ss, pct }     // server-synced via heartbeats
useLockStatus(): { locked: boolean, remaining: number }
useSessionFlow(): controller used by screens (see 04 §2 for transitions)
useServerClock(): { now(): Date }                          // offset-corrected
usePrefetchItems(sessionId): void                          // preload all item assets
```

### B.4 Screen-level handlers (wired to buttons in `05`)

| Handler | Triggered by | Effect |
|---|---|---|
| `submitTaskPrompt(text)` | Home ▸ Start Warm-up | parse → clarify? → duration confirm → create session |
| `selectDuration(m)` | Duration chips | store choice, default 10 |
| `answerClarification(a)` / `skipClarification()` | Clarify modal | refine task object / proceed with defaults |
| `cancelGeneration()` | Generating screen | abort `POST /sessions` (idempotency key discarded) |
| `nextCard()` / `skipCard()` | Player footer | advance cursor; `skipped` flag on event log |
| `reportCurrentCard()` | Report button | open report modal → `contentApi.report` |
| `endSessionEarly()` | End Early | confirm modal → `abandon_session` → lock still applies (**Decision**, see 04 §6) |
| `confirmStartedWork()` | Complete screen ▸ "I'm starting now" | records initiation (North Star input) |
| `backToWork()` | Complete/Locked | minimize to tray + show lock state |
| `emergencyUnlockFlow()` | Locked ▸ Emergency | type-to-confirm → `lockApi.emergencyUnlock` |
| `saveProfile()` / `resetPersonalization()` | Settings | profile API |
| `checkTaskInitiated(sessionId)` | History ▸ "Did you start?" | self-report → initiation metric |

### B.5 Tauri (Rust) commands (`src-tauri/`)

```rust
#[tauri::command] fn set_lock_overlay(locked: bool)         // always-on-top overlay window
#[tauri::command] fn minimize_to_tray()
#[tauri::command] fn cache_lock_state(lock_until: String)   // encrypted local file
#[tauri::command] fn read_lock_state() -> Option<String>
```

---

## PART C — Shared Contracts

All crossing types (`TaskObject, Profile, Session, SessionItem, LockState, ContentCard, Feedback, AnalyticsEvent`) live in `packages/shared-types` as JSON Schema and codegen to both languages (see `02` §4). Adding a content type = add schema + card renderer (`05` §6) + generator slot (`10`) — nothing else should change.
