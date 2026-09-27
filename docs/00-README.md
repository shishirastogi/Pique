# FocusWarmup — Implementation Plan (Docs Index)

> **Product name:** FocusWarmup (working title) · **Repo:** `pique-project`
>
> **One-liner:** A personalized 5–20 minute curiosity warm-up that makes your next task interesting before you start it — then locks and sends you back to work.

This folder is the **implementation plan** derived from [`../pique-idea.md`](../pique-idea.md). It is written so a developer can build the MVP without having to invent product decisions. Where a decision had to be made beyond the original idea doc, it is marked **Decision** with rationale.

---

## Document Map

| # | File | Contents | Build it from this when… |
|---|------|----------|--------------------------|
| 00 | [`00-README.md`](00-README.md) | This index + shared conventions | Onboarding |
| 01 | [`01-concept.md`](01-concept.md) | Product concept, problem, thesis, users, principles, glossary | Aligning on *what/why* |
| 02 | [`02-architecture.md`](02-architecture.md) | System architecture, tech stack, repo layout, deployment | Setting up the codebase |
| 03 | [`03-functions.md`](03-functions.md) | Every module + function signature (client & backend) | Writing code skeletons |
| 04 | [`04-working.md`](04-working.md) | End-to-end working, session state machine, lifecycle, edge cases | Wiring the session loop |
| 05 | [`05-ui-spec.md`](05-ui-spec.md) | Every screen, every section, every button + behavior | Building the frontend |
| 06 | [`06-database.md`](06-database.md) | Schema, ERD, indexes, Redis keys, migrations | Building the data layer |
| 07 | [`07-backend-api.md`](07-backend-api.md) | FastAPI structure + full endpoint specs with payloads | Building the API |
| 08 | [`08-data-fetching.md`](08-data-fetching.md) | External providers (Openverse, Wikimedia, …), caching, OCR | Building ingestion clients |
| 09 | [`09-recommendation-algorithms.md`](09-recommendation-algorithms.md) | Retrieval, scoring, ranking, personalization, analogies | Building the ranker |
| 10 | [`10-data-sorting-sequencing.md`](10-data-sorting-sequencing.md) | Sequence planning: slots, phases, ordering constraints | Building the session generator |
| 11 | [`11-content-pipeline.md`](11-content-pipeline.md) | Ingestion → OCR → moderation → embeddings pipeline | Building workers |
| 12 | [`12-moderation-safety.md`](12-moderation-safety.md) | Safety checks, human review, reports, high-stakes topics | Trust & safety |
| 13 | [`13-analytics-experiments.md`](13-analytics-experiments.md) | Events, metrics, North Star, A/B experiment framework | Instrumenting the app |
| 14 | [`14-security-privacy.md`](14-security-privacy.md) | Data minimization, auth, threat model, licensing compliance | Hardening |
| 15 | [`15-testing-qa.md`](15-testing-qa.md) | Test strategy, LLM eval harness, QA checklists | QA |
| 16 | [`16-roadmap.md`](16-roadmap.md) | Phases, weekly build order, milestones, risks | Planning sprints |

**Suggested reading order for a new developer:** `00 → 01 → 02 → 04 → 05 → 06 → 07 → 03 → (09, 10 as needed)`.

---

## Shared Conventions (used consistently across all docs)

### Product constants

| Constant | Value | Defined in |
|---|---|---|
| `DURATION_OPTIONS` | `5, 10, 15, 20` minutes | 05, 07 |
| `DEFAULT_DURATION` | `10` minutes | 05 |
| `DEFAULT_LOCK_MINUTES` | `120` (2 h) | 04, 06 |
| `CONTENT_TYPES` (MVP, live roster) | `meme, interesting_fact, quote, visual_explanation, analogy, poll, question, mini_story, trivia, historical_context, diagram, reaction_gif, micro_lesson, challenge, first_work_action, book_excerpt` — **`joke` retired by user decision (2026-09); type exists in registry but never planned** | 06, 09, 10 |
| `SESSION_SIZES` | `5→10, 10→20, 15→28, 20→36` cards (~2/min) | 10 |
| `HUMOR_MIN` | `5→2, 10→3, 15→4, 20→4` (meme at position 0 always) | 10 |
| `SESSION_STATES` | `IDLE → TASK_INPUT → TASK_PARSED → SESSION_GENERATING → SESSION_ACTIVE → SESSION_ENDING → LOCKED → UNLOCKED` | 04 |
| `KNOWLEDGE_LEVELS` | `beginner, intermediate, advanced` | 06 |
| `LANGUAGES` (MVP) | `en, hi, hinglish` | 06 |

### Ranking weights (MVP defaults, must be config-driven)

`relevance 0.30 · personalization 0.20 · curiosity 0.15 · quality 0.15 · variety 0.10 · learning_value 0.10`

### API conventions

- Base path: `/api/v1`
- JSON in/out; errors shaped as `{ "error": { "code", "message", "details?" } }`
- All timestamps UTC ISO-8601; the **server is authoritative for time** (countdown, lock).
- Endpoint names used across docs are exactly those in [`07-backend-api.md`](07-backend-api.md).

### Naming

- DB tables: `snake_case` plural (`session_items`, `content_sources`).
- Code: Python `snake_case` functions / `PascalCase` services; TypeScript `camelCase` functions / `PascalCase` components.
- Docs cross-reference each other by relative link. If you rename a file, update this index.

---

## Golden Rules (never violate while implementing)

1. **No infinite feed.** Sessions are finite, pre-generated sequences. (01, 10)
2. **No engagement loops.** No likes feed, no followers, no streak pressure, no autoplay-next-forever. (01)
3. **Visible countdown + hard stop + lock.** Always. (04, 05)
4. **Provenance for every external asset.** No asset without license metadata enters the pool. (06, 08, 11)
5. **Optimize for task initiation, not time-in-app.** Every metric and ranking decision follows this. (09, 13)
