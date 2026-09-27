# 11 — Content Ingestion Pipeline

> **Implementation status (2026-09):** pipeline-lite live — S2 provenance precheck,
> S3 dedup (`provider+source_id`), S5-lite classify (provider heuristics), S7-lite
> moderation, S9 embeddings (flag-gated, `app/ai/embeddings.py`), persist+store in
> `services/ingestion.py`; on-demand fill in `services/retrieval.py`; batch-embed at
> ingest. `infra/docker-compose.yml` ships Postgres 16+pgvector and Redis (start with
> `docker compose -f infra/docker-compose.yml up -d`). Remaining 11-formal: point
> `PIQUE_DATABASE_URL` at Postgres, Alembic migrations, ARQ workers + queues, OCR, drift
> dashboards.


> Implements idea doc §15. Turns external/generated material into ranked-ready `content` rows with provenance, moderation, scores and embeddings. Runs on ARQ workers (`07` §5); providers from `08`.

---

## 1. Pipeline Stages

```text
  EXTERNAL PROVIDER / GENERATOR                        (08)
            │  RawAsset {provider payload}
            ▼
  S1 FETCH/CREATE            provider client or GenerationService
            ▼
  S2 PROVENANCE PRECHECK     license fields present? known provider terms?
            │  fail → drop + log (never quarantine-on-uncertain for MVP; only known-good admitted)
            ▼
  S3 DEDUP                   sha256(url) → perceptual hash (images) → embedding cosine ≥0.94
            │  dup → discard (link metrics)
            ▼
  S4 OCR / TEXT EXTRACTION   Tesseract/PaddleOCR for text-bearing images  (08 §9)
            ▼
  S5 CLASSIFICATION          LLM (fast tier): type, topic, subtopics, tags,
                             difficulty, language, humor_style, tone
            ▼
  S6 STORAGE DECISION        fetchable? → bytes → R2 : hotlink url only   (08 §4, §6)
            ▼
  S7 MODERATION + SAFETY     NSFW/hate/violence/spam/dup + factuality risk  (12)
            │  fail → status=quarantined + moderation_queue row
            ▼
  S8 QUALITY & CURIOSITY SCORING   LLM heuristics → scores jsonb (09 §4)
            ▼
  S9 EMBEDDING               EmbeddingService.embed(title+body+ocr)
            ▼
  S10 PERSIST                content(status=active) + content_sources rows
```

Every stage emits `pipeline_stage_total{stage, result}` metrics + structured logs with `job_id` (traceability from a bad card back to its provider payload).

## 2. Job Model (ARQ)

| Job | Payload | Concurrency | Idempotency key |
|---|---|---|---|
| `ingest_source{provider, queries, limit}` | run spec | 1 worker foreach provider | `provider+date+queries-hash` |
| `process_asset{provider, source_id}` | raw payload inline (≤ 32 KB) or R2 pointer | 20 | `provider+source_id` |
| `embed_batch{content_ids[]}` | up to 64 items | 4 | ids sorted+joined |
| `score_batch{content_ids[]}` | up to 32 items | 4 | ids+model version |

Dedup of queue entries via Redis `SETNX ingest-lock:{key} ex=3600`.

## 3. Stage Contracts

**S2 Provenance precheck — fields required per provider (subset of `06.content_sources`):**
provider, source_id, source_url, license (or explicit provider-terms mapping), plus creator when supplied. Missing ⇒ item dropped and counted; providers returning sparse licenses (portion of LoC) rely on collection-level rights filters in the query itself (`08` §1 matrix).

**S3 Dedup:**
```python
if sha256(asset_url) in seen_urls: drop
if images and min_hamming(phash, neighbors) <= 6: drop
if max(cosine(embed, existing same-topic embeddings)) >= 0.94: drop
```
Fast path uses a Redis bloom of url hashes; similarity path needs S9 embedding — handled by a cheap title-embedding first pass, full check post-S9 with late-merge discard.

**S5 Classification output (validated by pydantic, retry once on parse fail):**
```json
{"type":"interesting_fact","topic":"thermodynamics","subtopics":["entropy"],
 "tags":["physics","entropy","energy"],"difficulty":"beginner","language":"en",
 "tone":"surprising","humor_style":null,"curiosity":0.88,"quality":0.9,"learning_value":0.75}
```

**S8 Scoring rubric (fast-tier LLM, temperature 0.2, cached by content hash):**
- curiosity: hooks attention for a stranger to the topic
- quality: clarity, correctness-likelihood, production value (for images: resolution/relevance of depiction)
- learning_value: durable understanding per second
Scores land in `content.scores`; the ranker reads them directly (`09` §4) — no session-time LLM cost for these dims.

## 4. Generated Content Path

Generated items (analogy, poll, question, micro_lesson, joke, trivia, first_work_action) skip S2/S3-hash/S4/S6 and enter at S5 (they classify trivially) → S7 (strict, incl. factuality + tone) → S8 → S9 → persist with `provenance.type='generated'`, `generated_by='{provider}:{model}:{prompt_version}'`. Reuse: generators first check cache (`analogy:{topic}:{interest}` etc., `03` A.5–A.6) so popular pairs (entropy×gaming) are generated once, scored once.

**Factuality for generated educational cards (micro_lesson, interesting rewrites):** model must return `{claims:[...], confidence}`; `confidence < 0.8` → quarantine for sample human review (12 §5). High-stakes topics use curated templates only (`09` §9).

## 5. Card Rendering (generated visuals)

`text card spec → renderer (Satori/SVG or Pillow) → PNG/WebP + thumbnail → R2 → media.url`. Used for text-memes, quote cards, poll/question visuals, comparison cards (idea doc §15 third diagram). Fonts + templates versioned in repo (`apps/assets/cards/`).

## 6. Quality Gates & SLOs

| Gate | Threshold | Action |
|---|---|---|
| Provenance completeness | 100% | no exceptions |
| Active-rate of a provider run | ≥ 85% pass → review provider config if lower |
| Scoring model drift | score distribution shift (KS test) weekly | alert |
| Embedding backlog | < 500 items | scale `embed_batch` |
| OCR failure rate | < 15% per provider | demote OCR-centric types for that provider |
| End-to-end freshness | new hot-topic coverage < 24 h | prefetch planner (08 §8) |

## 7. Reprocessing

- Model upgrades → `POST /admin/content/re-score` / `reindex` re-runs S8/S9 in place (new `generated_by`/embedding version stamped; rank cache version bump invalidates `rankcache`).
- License policy change → bulk quarantine by `provider`+`license` query (`14` §7 takedown path).
- Failed-stage replay: `process_asset` reads stage checkpoints stored in job meta; replays only downstream stages.

## 8. Data Quality as an Asset

The scored, embedded, provenance-cleaned content graph is the long-term moat (idea doc §34 area 2+5). Phase 3 adds: semantic topic graph edges (`content_relations`), duplicate-cluster views, coverage dashboard per topic×type, and sequence-outcome labels joined from `13` events — all consuming exactly this pipeline's outputs.
