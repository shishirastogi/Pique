# 13 — Analytics & Experimentation

> Implements idea doc §§28–29, 43. Analytics exists to answer one question: **does the warm-up make people start the work?** — not to maximize consumption.

---

## 1. North Star & Guardrail Metrics

| Metric | Definition | Target direction |
|---|---|---|
| **Task initiation rate (North Star)** | % completed warm-ups with `started_work_confirmed=true` (or retro report) within measurement window | ↑ vs control |
| Task-start latency | `initiation_reported_at − completed_at` (minutes) | ↓ |
| Warm-up completion rate | completed / started sessions | ↑ (guardrail — should not collapse) |
| Lock compliance | 1 − `lock_break` events / locks started | ↑ |
| Session abandonment | abandons / starts + last-position distribution | ↓, but weigh vs initiation trade-off honestly |
| Content satisfaction | mean per-item rating; skip-adjusted dwell | ↑ (secondary) |
| Repeat usage | users with ≥ 2 sessions / 14 days | ↑ (retention sanity, not a growth loop) |

**Explicit non-goals:** time-in-app, cards/session depth, "engagement" growth. Dashboards put North Star first, consumption metrics in a separate clearly-labeled guardrail panel.

## 2. Event Taxonomy (`analytics_events.payload`)

Client → `POST /sessions/{id}/events` (session loop) and a generic `POST /events` (non-session) — batched, retried offline (`04` §9).

| event_type | payload keys | emitted when |
|---|---|---|
| `app_open` / `app_close` | — | lifecycle |
| `task_parsed` | `{duration_ms, confidence, clarified}` | parse response |
| `session_created` | `{duration, pool_size, generation_ms, config_version, experiment_arm}` | 201 from POST /sessions |
| `item_shown` / `item_done` | `{position, content_id, dwell_ms, skipped, engagement}` | player (`07` §4.6) |
| `session_completed` | `{skipped_count, overrun_s}` | complete |
| `session_abandoned` | `{position, reason}` | end-early / timeout |
| `initiation_reported` | `{retroactive: bool, latency_s}` | complete screen or History |
| `lock_break` | `{confirm: true}` | emergency unlock |
| `content_reported` | `{reason}` | report modal |
| `generation_failed` | `{stage}` | pipeline fallback paths |

Every event carries `user_id`, `session_id?`, `client_ts`, `server_ts`; sensitive fields (raw task text) are **never** in analytics payloads — only parsed metadata (`14` §2).

## 3. Funnel

```text
app_open → task_parsed → session_created → session_completed
         → initiation_reported (North Star conversion)
         → lock obeyed (no lock_break before lock_until)
```
Dropped-into segments: duration (5/10/15/20), level, category, experiment arm, language, day-part.

## 4. Experiment Framework (idea doc §29)

**E0 — The core hypothesis (runs from first MVP):**
- Arms: `control` (plain "Time to work" prompt — minimal flow, still records initiation) vs `treatment` (full warm-up).
- Assignment: per-user sticky random 50/50 at first session → `experiment_assignments`; logged on every session (`config_version` too).
- Read-outs: initiation rate (primary), latency, abandonment, subjective readiness (1-question post-lock survey: "How ready did you feel? 1–5").
- Guardrails: completion rate, report rate, latency p95.
- Power note: with baseline initiation p≈0.35, detecting +10 pp at n≈350 sessions/arm (90% power) — Phase 0 cohort (20–50 users × ~8 sessions) gives directional signal; treat as hypothesis screen, not proof (idea doc Phase 0).

**Later experiments (guided by §"Weight learning" in `09` §11):** duration defaults, phase templates, analogy presence on/off, weight profile A/Bs. All through the same `experiment_assignments` + config-table machinery; no code forks.

## 5. Measurement Integrity Rules

1. Self-report is the primary initiation signal in MVP — add optional desktop-activity signal later and treat it as secondary ("do not overclaim from passive signals", idea doc §28).
2. Never compare arms on unequal follow-up windows; initiation window fixed at 2 h post-completion.
3. Novelty bias: read metrics by session-number cohort (1st, 2–5, 6+ sessions separately).
4. Surveys are optional and max 1 question, post-lock (not post-session — don't delay the work moment, `05` §8).

## 6. Dashboards

| Dashboard | Panels |
|---|---|
| **Behavioral (weekly review)** | North Star by arm · funnel · latency distribution · completion by duration · lock compliance |
| **Content** | satisfaction by type · skip heatmap by position · report rate · per-provider problem rates (feeds `11` §6, `12` §9) |
| **System** | session-create p50/p95 · stage latencies · provider error mix · LLM cost/session budget |
| **Experiment** | arm balance check · metric lift + CI · guardrail status |

Implementation: Postgres daily rollups (`daily_aggregates` job) → Metabase/Grafana. Raw events → ClickHouse only if volume demands (`02` §10).

## 7. Definition of Success (MVP exit)

Proceed from Phase 1 → 2 when: treatment initiation ≥ control + 10 pp (or strong qualitative signal in small-N), completion ≥ 60%, lock compliance ≥ 80%, and interviews say "I actually wanted to start after this" (Phase 0 success wording, idea doc §33). Otherwise iterate content/sequence — **not** add engagement features.
