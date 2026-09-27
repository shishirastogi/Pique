# 15 — Testing & QA Strategy

> Goal: prove the behavior loop works and the invariants (finite sessions, lock, provenance, safety) can never silently break.

---

## 1. Test Pyramid & Tooling

| Layer | Backend | Frontend | Share target |
|---|---|---|---|
| Unit | pytest (+ pytest-asyncio), factories for TaskObject/Profile | vitest + testing-library | ~60% |
| Contract | pydantic schema tests ↔ `packages/shared-types` codegen diff in CI | ts types are codegen — drift fails build | — |
| Integration | testcontainers (pg16+pgvector, redis), httpx ASGI client | msw-mocked API component tests | ~30% |
| E2E | — | Playwright against staging compose stack | ~10% |
| LLM evals | custom harness (§4) | — | gates on AI changes |

CI pipeline (per PR): lint (ruff, eslint) → typecheck (mypy strict-ish, tsc) → unit+contract → integration → build Tauri per-OS (on tags). Secret scan + dependency audit block merges (`14` §5).

## 2. Invariant Tests (the product rules as unit tests)

These map 1:1 to the idea doc's anti-goals — if any fails, release stops:

1. **Finiteness:** for every duration, `len(plan.items)` equals template size; plan has terminal `first_work_action` at N−1 (`10` §4).
2. **Lock invariant:** `POST /sessions` during active lock → 409 `LOCKED`; completing session always sets `lock_until`; emergency unlock requires exact confirm string and logs event (`07` §4.11).
3. **No rabbit holes:** response of items endpoint contains **no** related-content/"more-like-this" fields (snapshot the serializer).
4. **Provenance:** invariant test walking 100 random active content rows — all have `content_sources` with license non-null (`08` §3).
5. **Type adjacency/interaction pacing/media-streak** rules hold for 1,000 fuzzed ranked pools into the planner (property-based via `hypothesis`).
6. **Countdown integrity:** heartbeat with client_ts skewed ±600 s still completes at server `ends_at`; events with drift > 60 s rejected (`07` §4.6).
7. **Safety floor:** items with safety_confidence < 0.6 can never appear in a plan even when pool is starved (`09` §9 — pool falls back to generation path instead).

## 3. Session-Flow E2E Scenarios (Playwright)

1. Happy path: type prompt → 10-min session → cards → complete → "I'm starting now" → locked screen shows countdown.
2. Clarify path: vague prompt → modal → pick level → session.
3. End early → confirm → lock still applied (04 §6).
4. Report a card → replaced by reserve; report recorded.
5. Kill app mid-session → relaunch → still locked at right value (Tauri lock file + `/lock/status`).
6. Offline: airplane mode → offline mini-session badge → lock applies; events flush on reconnect.
7. Emergency unlock flow (typed phrase gating the button's disabled state).
8. History: retro initiation report updates badge.

## 4. LLM Evaluation Harness (`services/api/tests/evals/`)

Golden datasets are versioned JSONL in-repo; evals run on demand + nightly against cheap tier, and block release when regressing > 5 pp:

| Suite | n (start) | Checks |
|---|---|---|
| `task_parse` | 100 prompts (incl. Hinglish, vague, non-study, injection attempts) | field accuracy ≥ 85%; clarification fired iff level/topic missing; injection → safe default parse |
| `generation_quality` | 60 tasks × types | schema validity 100%; factuality spot-check sample (human-reviewed monthly); toxicity 0% |
| `scoring_stability` | 40 contents × 3 runs | score σ ≤ 0.05 at temp 0.2 |
| `analogy_bridge` | 30 topic×interest pairs | human rubric sample: "actually bridges" ≥ 80% |

Cost guardrail: eval suite budget cap per nightly run; results stored to track drift across model/prompt versions (matches `11` §6 drift gate).

## 5. Load & Performance Tests (k6)

| Scenario | Target |
|---|---|
| `POST /sessions` cold (cache miss, incl. generation) | p95 < 8 s at 20 rps |
| …warm (rank cache hit) | p95 < 1.5 s |
| `GET /sessions/{id}/items` | p95 < 300 ms |
| heartbeat events | 200 rps sustained, no loss |
| pgvector candidate query @ 100k rows | p95 < 120 ms (`02` §10 trigger) |
| Redis lock path | status p99 < 20 ms |

## 6. Staging Environment & Seed Data

`docker-compose` staging with: seeded ~2,000 content items across 30 starter topics (`08` §8), fixtures for 3 test profiles (student/designer/dev mirroring idea doc §19), fake LLM provider (deterministic responses) for CI, real providers in staging with quota caps.

## 7. Release QA Checklist (per milestone)

- [ ] All invariant tests green (§2)
- [ ] E2E 8 scenarios green on Windows + macOS builds
- [ ] Eval suites within budget (§4)
- [ ] p95 session-create within target (§5)
- [ ] License/attribution spot audit (20 cards) (`14` §7)
- [ ] Locked screen verified from cold launch
- [ ] Analytics events validated against taxonomy (no new unlisted event)
- [ ] No "engagement growth" metrics shipped to primary dashboard (`13` §1)

## 8. Bug Taxonomy & Priority

| Class | Example | Priority |
|---|---|---|
| Broken invariant (lock, finiteness, provenance) | session served during lock | P0 — hotfix |
| Safety/moderation miss | NSFW card served | P0 |
| Data/privacy | raw task text leaked to analytics payload | P0 |
| Core-loop failure | generation down with no fallback | P1 |
| UX/card rendering | broken diagram scaling | P2 |
| Cosmetic/copy | typo | P3 |
