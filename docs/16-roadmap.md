# 16 — Roadmap & Build Plan

> Expands idea doc §§31, 33, 40–42. Two views: **phases** (product maturity) and the **MVP weekly order** (execution). Rule: no new major feature until the core loop shows promise (§40 week 7+).

---

## 1. MVP Scope (frozen)

**Must have** (idea doc §31): desktop app · natural-language task input · 5/10/15/20 choice · task parsing · interest profile · finite session sequence · mixed content types · AI personalization · countdown · lock state · content reporting · basic analytics · content provenance.

**MVP content sources:** Openverse + Wikimedia Commons + Project Gutenberg (+ Smithsonian/LoC selected) + generated. Optional: Unsplash, GIPHY.

**Explicitly NOT in MVP:** social anything, likes/comments/follows, gamification/streaks, mobile parity, mass scraping, Reddit, 50+ provider APIs, OS-wide blocking, custom model training (§42).

---

## 2. MVP Weekly Build Order (from idea doc §40, wired to these docs)

| Week | Deliverable | Tasks (docs to follow) |
|---|---|---|
| **1 — Product skeleton** | runnable client shell (Vite web first; **Capacitor Android/iOS wrap-ready** — final product is mobile, user-confirmed), all screens with mock data | Screens + components + button wiring (`05`), stores/hooks (`03`B), state machine client side (`04` §2), theme |
| **2 — Task understanding** | parse endpoint live | FastAPI boot + auth device token (`07` §1–2, §4.1–4.2), `TaskParserService` + clarify policy (`03`A.2), eval harness seed (`15` §4), DB users/profiles/tasks (`06`) |
| **3 — Content engine** | content pool exists | provider clients Openverse/Wikimedia/Gutenberg (`08` §1–5), pipeline S1–S10 (`11`), embeddings, quality scoring, admin run endpoint (`07` §4.14) |
| **4 — Session engine** | end-to-end sessions work | retrieval (`09` §3), ranking weights v1 (`09` §4–6), `SequencePlanner` + templates (`10`), `POST /sessions` + items + events (`07` §4.3–4.6), player wired to real data (`05` §5–6) |
| **5 — Personalization + lock hardening** | analogies land | profile endpoints (`07` §4.9–4.10), rule personalization (`09` §7), `AnalogyService` + cache (`03`A.6), lock service + overlay + emergency unlock (`04` §5, `05` §9), settings screen (`05` §10) |
| **6 — Analytics & experiment** | E0 measurable | event pipeline (`13` §2), initiation capture + History retro report (`05` §8/§11), experiment assignment (`13` §4), daily aggregates dashboard |
| **7 — Hardening** | release candidate | offline mode (`04` §9), moderation closure loop (`12` §4), invariant + E2E suites green (`15` §§2–3), perf targets (`15` §5), installers + auto-update |

Exit = MVP definition of success (`13` §7).

## 3. Phase Map (post-MVP horizons)

| Phase | Focus | Key adds | Exit signal |
|---|---|---|---|
| **0 — Validation** | is the hypothesis real? | manual-curation prototype, 20–50 users, 5–10 min sessions | users say "I wanted to start"; initiation vs baseline ↑ (§33) |
| **1 — Functional MVP** | end-to-end loop | everything in §2 (weekly plan) | E0 experiment instrumented; loop stable |
| **2 — Personalization** | adaptive fit | learned format affinities (`09` §7), weighted interest graph, humor/language adaptation, cross-interest analogy quality loop | initiation lift vs MVP personalization baseline |
| **3 — Content intelligence** | library as moat | full automation (`11`), dedup clusters, source confidence, coverage dashboard, sequence-outcome labels | active-rate ↑, coverage ≥ 95% of hot topics, cost/session ↓ |
| **4 — Focus enforcement** | stronger lock | OS-level blocks, browser extension, calendar/task integrations; emergency-unlock re-evaluated (`04` §5 decision) | lock compliance ↑ without support burden |
| **5 — Mobile ship** | Capacitor Android/iOS wrappers over the same codebase | store setup, OS focus APIs (App Timers / Screen Time), notifications only-if-useful | initiation metric parity on mobile |
| **6 — Community content** | UGC ecosystem | submissions → moderation → packs | moderated inflow sustains coverage |
| **7 — Adaptive intelligence** | behavioral sequences | bandit over weights/templates (`09` §11), per-user session-length adaptation | sustained initiation lift in holdout |

## 4. Monetization Snapshot (idea doc §35 — no build until Phase 2+)

Freemium: limited daily warm-ups free; paid unlimited + advanced personalization + integrations. **Never ads.** Success of app ≠ time in app; pricing must not invert the incentive.

## 5. Risk Register (owner-file mapping)

| Risk (idea doc §36) | Primary mitigation | Where implemented |
|---|---|---|
| App becomes the distraction | finiteness, countdown, lock, no loops | `01` §6 · `04` · `05` · `10` |
| Entertaining but not useful | activation phase, terminal action card | `10` §§3–4 |
| Creepy personalization | minimal data, transparency, reset | `14` §§1–2 |
| Copyright trouble | provenance gate, takedown path | `08` · `11` S2 · `12` §8 |
| AI wrong facts | retrieval-backing, factuality checks, high-stakes policy | `11` §4 · `12` §5 |
| Hypothesis false | E0 experiment before heavy infra | `13` §4 |

## 6. Operational Runbook Seeds (grow over time)

- Backup/restore: daily `pg_dump` → encrypted bucket; monthly restore drill (`14` §4).
- Incident basics: provider outage (circuit opens — expected; verify fallbacks), LLM outage (template/retrieval-only mode), moderation incident (quarantine query + comms), lock bug (P0, emergency unlock data audits).
- Capacity review monthly against `02` §10 triggers.

## 7. "Definition of Done" for MVP Features

A feature is done when: docs updated (relevant `0X` file), schema/typed contracts codegen'd, invariant/unit/E2E coverage added where applicable (`15`), events instrumented per taxonomy (`13` §2), and it respects the golden rules (`00` — no feeds, no loops, countdown+lock+provenance always, optimize initiation).
