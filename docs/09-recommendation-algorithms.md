# 09 — Recommendation & Ranking Algorithms

> **Implementation status (2026-09):** 09-lite shipped in the slice —
> `services/selection.py` (the LLM curates pool→slot picks, one call/session,
> constraint-validated, heuristic fallback), hybrid scoring
> (`0.75·cosine + 0.25·lexical` when `PIQUE_EMBEDDINGS_ENABLED=true`, lexical-only
> otherwise — embeddings quota on the Gemini free key is the constraint), plus the
> ingestion-time relevance gate (`08`). Remaining 09-formal: pgvector column + MMR
> + weight learning (needs the Docker Postgres from 11 + embedding quota).


> Implements idea doc §16 (content ranking) + §9–10 (personalization). Output feeds the sequence planner (`10`). Key difference from typical recommenders: we rank a **small finite candidate set for one bounded session** — no feeds, no exploration loops, no rabbit holes.

---

## 1. Inputs / Outputs

```python
rank(candidates: list[Candidate], ctx: RankingContext) -> list[RankedItem]   # 03 A.7

RankingContext = {
  task: TaskObject,            # topic, subtopics, level, goal, language
  profile: Profile,            # interests, humor, content prefs, level default
  history: HistorySlice,       # last N sessions' content ids + feedback (exclude repeats)
  config: WeightConfig,        # weights live in DB config table (06 §4)
  session_intent: {duration_minutes, phase_needs}   # from slot template (10 §3)
}
```

Candidate sources: DB semantic/FTS pool · on-demand external pool · generated pool (`03` A.4–A.5).

## 2. Stage Overview

```text
candidates (≈80–150)
  │ 1. FILTER: language · status=active · provenance ok · not shown in last 10 sessions
  ▼
  │ 2. RETRIEVAL SCORES: semantic sim, FTS rank (already computed in fetch)
  ▼
  │ 3. DIMENSION SCORING: 6 sub-scores per item (§4)
  ▼
  │ 4. COMBINE: weighted sum → base_score (§5)
  ▼
  │ 5. MMR diversity pass over embeddings (§6)
  ▼
  │ 6. GUARDRAILS: per-type/per-source caps, safety floor (§9)
  ▼
ranked list → SequencePlanner (10)
```

## 3. Candidate Retrieval (detail for `RetrievalService`)

**Query construction**
```python
q_text = f"{task.topic} {' '.join(task.subtopics)} {type_hint} {level_hint}"
q_vec  = EmbeddingService.embed([q_text])[0]
```

**Hybrid SQL sketch (pgvector + FTS, single roundtrip):**
```sql
WITH s AS (SELECT id, 1 - (embedding <=> :qvec) AS sim FROM content
           WHERE status='active' AND language IN (:langs)
           ORDER BY embedding <=> :qvec LIMIT 60),
     t AS (SELECT id, ts_rank(fts, plainto_tsquery('english', :qtext)) AS tsv
           FROM content WHERE status='active' AND language IN (:langs)
           ORDER BY tsv DESC LIMIT 40)
SELECT c.*, coalesce(s.sim,0)*0.7 + coalesce(t.tsv,0)*0.3 AS retrieval_score
FROM content c LEFT JOIN s USING(id) LEFT JOIN t USING(id)
WHERE c.id IN (SELECT id FROM s UNION SELECT id FROM t);
```
RRF (reciprocal rank fusion) is an acceptable alternative; keep behind one function (`03` A.4) so it can be swapped after A/B.

**Filters applied here:** language, `level ± 1` of task level, hard-exclude `content_id` seen in last 10 sessions, exclude reported-by-this-user content.

## 4. Score Dimensions (each 0…1)

| Dimension | Meaning | How computed (MVP) |
|---|---|---|
| `relevance` | on-topic-ness for *this* task | 0.6·semantic_sim + 0.4·subtopic overlap; LLM-rerank top-30 optional flag |
| `personalization` | fit to user's interests/formats/humor/level | profile-match rules (§7) + format preference boost |
| `curiosity` | "wait, really?" pull | ingestion-time LLM heuristic score stored in `content.scores` |
| `quality` | production/factual quality | ingestion-time score (11 §stage-7) + feedback-adjusted (§8) |
| `variety` | contribution to session diversity | computed in MMR pass (§6), not stored |
| `learning_value` | genuine understanding value | ingestion-time heuristic, weighted by `difficulty` match |

## 5. Combine

```python
base = ( 0.30*relevance + 0.20*personalization + 0.15*curiosity
       + 0.15*quality    + 0.10*variety         + 0.10*learning_value )
# weights from config table `ranking.weights.v1` — hot-tunable for experiments
final = base * safety_confidence            # < 0.6 floors item to 0 (hard gate in §9)
```

**Phase-aware weighting (Decision):** weights shift slightly per slot phase — `entertainment` slots bump `curiosity/humor ×1.25`, `activation` slots bump `learning_value/relevance ×1.25`. Implemented as per-phase weight profiles in `SequencePlanner` call to ranker (details `10` §5). Keeps ranking and sequencing decoupled.

## 6. Variety via MMR

Maximal Marginal Relevance over the base-scored list:
```python
selected = []
while len(selected) < pool_target:          # pool_target = 3× slots; planner trims
    best = argmax_c [ λ*base(c) - (1-λ)*max_sim(c, s for s in selected) ]
    # λ = 0.7 (config); max_sim = cosine on embeddings
```
This both orders the pool and supplies the `variety` sub-score surface the planner needs. Hard type-cap inside selection loop: no more than 2 of same `type` in pool_target.

## 7. Personalization Signals & the Analogy Bridge

**Rule-based personalization vector (MVP, interpretable):**
```text
personalization(c) = 0.40·format_pref_match      (c.type ∈ profile.content_preferences)
                   + 0.25·humor_match            (c.humor_style == profile.humor)
                   + 0.20·interest_tag_overlap   (c.tags ∩ profile.interests)
                   + 0.15·level_match            (|c.difficulty - task.level| penalty)
```

**Cross-interest analogy (signature feature, idea doc §10):** analogies are *generated*, not retrieved. `AnalogyService` (`03` A.6):
```python
bridge = pick_bridge_interest(profile, task)
#   choose interest with zero overlap to topic domain, prefer user's top-2;
#   e.g. task=economics, profile.interests=[cricket, music] → cricket
analogy = generate(topic, bridge, level, language)   # cached by (topic, bridge)
```
The ranker always reserves ≥1 analogy slot in the mid-session `understanding` zone (planner constraint, `10` §4); the analogy card gets `personalization := max(...)` style boost via `interest_tag_overlap=1` by construction.

**Learning (Phase 2+, gated):** update per-user `format_affinity` from dwell/skip/feedback: `affinity[type] ← EMA(engagement[type])`, blended 50/50 with explicit settings (explicit settings always win ties). Never infer sensitive traits (`14` §2).

## 8. Feedback-Adjusted Quality

`quality_adjusted = quality * (1 + 0.1 * mean(feedback_rating for content))` with a minimum-sample guard (n≥5) and per-user negative overrides (user reported/downvoted → hard-exclude for that user). Skip-with-early-dwell contributes −0.5 implicit rating (config).

## 9. Guardrails

- **Safety floor:** `SafetyGate.check_item` verdict `block` OR `safety_confidence < 0.6` ⇒ removed from pool (never merely downweighted).
- **Caps per session pool:** ≤ 40% from any single provider; ≤ 2 items per type; ≥ 1 item each from `retrieved` and `generated` origins where possible.
- **High-stakes topics (medical/legal/financial):** only `quality ≥ 0.8` + `generated_by` reviewed templates + mandatory source references (`12` §5).
- **No rabbit holes by construction:** ranked pool is consumed once, planner trims to the finite sequence; nothing recommends beyond it.

## 10. Cold Start & Performance

- **New user:** default priors from config (safe high-curiosity general science/design/dev items) + explicit onboarding prefs. Offline-seeded cards cover zero-network case (`04` §9).
- **New topic (thin pool):** generation-heavy session (`04` §8); queue ingestion for the topic so next session is richer (`08` §5).
- **Latency budget:** retrieval ≤ 250 ms · scoring ≤ 150 ms (vectorized numpy) · optional LLM rerank ≤ 1.5 s (flag-gated) · MMR ≤ 50 ms. Rank cache (`07` §6) absorbs repeat traffic.
- **Caching generated analogies** via `analogy:{topic}:{interest}` cuts the most expensive generation call.

## 11. Weight Learning & Experimentation (roadmap hooks)

1. **Config-driven weights** ship in MVP (change without deploy, guardrailed bounds).
2. **Phase 2:** per-segment weight search (offline grid search against logged sessions using completion+initiation as reward, `13`).
3. **Phase 7 (adaptive intelligence):** contextual bandit over {weight profile × phase template} per user segment. Explicitly post-MVP; the event schema already logs `experiment_arm` + `config_version` so historical data stays usable.

**Offline sanity metrics** (for CI of ranker changes, `15`): pool coverage per phase ≥ 2×, mean base_score of plan ≥ threshold, zero stuffed-same-type adjacency, no reported/repeat leakage.

## 12. Pseudocode (rank, end-to-end)

```python
async def rank(candidates, ctx):
    pool   = hard_filters(candidates, ctx)                    # §3
    scored = [ScoreVector(c, compute_dims(c, ctx)) for c in pool]
    for s in scored: s.base = combine(s.dims, ctx.config.weights)  # §5
    pool   = mmr_select(scored, lam=0.7, cap_per_type=2)      # §6
    pool   = apply_guardrails(pool, caps=ctx.config.guardrails)     # §9
    return sorted(pool, key=lambda s: s.base, reverse=True)   # → planner
```
