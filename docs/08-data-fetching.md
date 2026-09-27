# 08 — Data Fetching (External Content Sources)

> Implements idea doc §§11–12, 15. Rules: **provenance always**, **respect provider terms**, **never scrape** public-but-copyrighted sources. Feeds the pipeline in `11`.

---

## 1. Provider Registry

Every provider implements one interface (`app/services/providers/`):

```python
class ProviderClient(Protocol):
    name: str
    async def search(self, query: ProviderQuery, limit: int) -> list[RawAsset]
    async def fetch_asset(self, source_id: str) -> RawAsset
    def normalize(self, raw: RawAsset) -> ContentRecord          # → 06 shape + content_sources row
    def license_policy(self) -> LicensePolicy                    # cacheable? attribution?
```

| Provider | Base | Auth | MVP? | Fetch for | Notes / terms we honor |
|---|---|---|---|---|---|
| **Wikipedia** | `lang.wikipedia.org` (REST summary + opensearch) | none | ✅ | real fact cards (`interesting_fact`), thumbnails | content is CC BY-SA 4.0 → attribution required; prefetch-only (multi-call) |
| **Openverse** | `api.openverse.org/v1` | API token (anonymous OK at low limits) | ✅ | images, illustrations (CC/PD) | returns license fields — store verbatim |
| **Wikimedia Commons** | `commons.wikimedia.org/w/api.php` | none — **UA must include contact info** (robot policy; learned the hard way) | ✅ | diagrams, science, maps, historical | `extmetadata` gives license + attribution; hotlink via thumbnail URL |
| **Project Gutenberg** | `gutendex.com` mirror API | none | ✅ (flag-off default) | excerpts (public domain) | verify PD status per record; prefetch-only |
| **Smithsonian OA** | `api.si.edu/openaccess/api/v1.0` | api.data.gov key (free) | next | science/culture objects (CC0) | CC0 filter on |
| **Library of Congress** | `loc.gov/…?fo=json&c=…` | none | next | historical photos, posters, maps | filter rights="no known restrictions" |
| **NASA Image Library** | `images-api.nasa.gov` | none | next | space/science images | mostly PD/NASA guidelines |
| **Open Trivia DB** | `opentdb.com/api.php` | none | next | real trivia → question/poll cards | CC BY-SA; category-mapped |
| **Unsplash** | `api.unsplash.com` | key (free) | optional | high-quality photos | **hotlink only** (`urls.raw`), trigger download endpoint, author attribution; no byte storage |
| **GIPHY** | `api.giphy.com/v1/gifs` | key (free) | optional | reaction GIFs | require "Powered by GIPHY" attribution; serve via their CDN URLs |
| **Imgflip** | `api.imgflip.com` | key (free) | optional | meme templates we caption in-house | owned captions + template per terms |

**Where providers plug in (code):** `services/api/app/providers/<name>.py` — implement
`search(query, limit) -> list[RawAsset]`, then register in `enabled_providers()` in
`base.py`. Ingestion's `_precheck` (license/safety) + `_relevant` (topic-word overlap
gate, until embeddings land in 09) apply automatically to every provider.

**Generation-time enrichers (different kind):** real meme/gif media for *generated* humor
cards lives in `app/services/media_enrichment.py` (Imgflip template captioning → `meme`
cards; GIPHY search → `reaction_gif` cards), invoked from `session_service` during
session creation. Without keys, `card_renderer.ensure_visual()` guarantees every humor
card renders as an owned SVG visual (zero deps, offline-safe). Add new enrichers there.

Out of scope forever without licenses: Google Images, Pinterest, Instagram, Reddit bulk scrape, random websites (idea doc §12.3).

---

## 2. Query Construction

From `TaskObject` + planner needs:

```python
def build_queries(task: TaskObject, need: ContentNeed) -> list[ProviderQuery]
# need: {"type":"visual_explanation","count":6,"phase":"understanding"}  (from 10 slot template)
# e.g. task("thermodynamics", beginner, en) →
#   ["thermodynamics engine", "heat engine diagram", "entropy", "Carnot"]
# provider-specific expansion: Wikimedia gets "category:Diagrams of thermodynamics"
```

- Query expansion via LLM synonym/topic map (cached in Redis `analogy`-style).
- Subtopics (`06.tasks.subtopics`) issue targeted secondary queries.
- Language filter applied post-fetch (most providers are English-heavy) — non-English text content is mostly *generated* (Decision: safer for quality/licensing than scraping regional meme sites).

## 3. Normalization & Provenance

`normalize()` maps every external hit to:

```python
ContentRecord(
  type=…, title=…, body= OCR|caption|summary, language=…, topic=…, tags=…,
  media={kind, url, storage: "hotlink"|"r2"},
  source=ContentSource(provider, source_id, source_url, creator, license,
                       license_url, attribution_required, attribution_text,
                       fetchable=license_policy.may_store_bytes) )
```

Hard rule: **no `content_sources` row ⇒ asset never becomes `active`.** Attribution text is generated at normalize time when `attribution_required` (UI shows caption, `05` §5).

## 4. License Policy Matrix

| License / terms | May store bytes? | How served in app |
|---|---|---|
| CC0 / PDM / "no known restrictions" | ✅ (store copy in R2 for perf) | mention creator when given |
| CC-BY / CC-BY-SA | ✅ with attribution stored | attribution caption under card |
| Unsplash terms | ❌ | hotlink `urls.raw` + author name/photo credit + ping their download endpoint |
| GIPHY terms | ❌ | hotlink + "Powered by GIPHY" |
| Generated in-house | owned | rendered cards stored in R2 |

`fetchable` flag in DB enforces this automatically in the storage step (`11` §stage-6).

## 5. Fetch Execution Modes

1. **Prefetch (primary):** nightly + 6 h refresh jobs hydrate pools for top topics (trending topics derived from recent `tasks` aggregates, privacy-safe counts only). Target: ≥ 200 active items per hot topic.
2. **On-demand (fallback):** `RetrievalService.on_demand_external` fires during session creation only when merged pool < `k_min(=2× sequence length)`. Adds ≤ 2 s latency cap; circuit-broken providers are skipped (`Redis cbr:{provider}`).
3. **Ad-hoc admin runs:** `POST /admin/ingestion/run`.

## 6. Storage Rules

- Only `fetchable=true` bytes go to object storage (R2 key `content/{provider}/{source_id}.{ext}`), with CDN URL saved in `media.url`.
- Hotlink-only providers: store URL + metadata only; periodic liveness check job marks dead links `status=removed`.

## 7. HTTP Resilience Standards (all providers)

- Timeouts: connect 3 s, read 10 s; total budget 12 s.
- Retries: 3 × exponential backoff (0.5/1/2 s) + jitter; only on 429/5xx/network.
- Circuit breaker: open after 5 consecutive failures → 5 min cool-down (`cbr:{provider}`), half-open probe.
- Concurrency: per-provider semaphore (Openverse 20, Wikimedia 10, others 10); global 60.
- Quotas: daily budget per provider in config; approaching 80% → switch affected queries to cached pool, alert.
- Headers: descriptive User-Agent w/ contact URL (provider policy compliance).

## 8. Scheduling & Coverage (prefetch planner)

```text
topics = top_recent_topics(7d) ∪ curated_seed_topics(~100) ∪ exam-season topics
for topic: enqueue ingest_source(provider, queries(topic), limit=25)
```
Cold-start seed: curated starter packs for ~30 common student/dev/creative topics (manual + generated), so week-1 users never hit empty pools (`04` §8).

## 9. OCR & Text Extraction

- Images queued to `OcrService` (Tesseract default) **only when** the card type needs text (memes, screenshots, posters) or classification needs it.
- Output feeds: classification (topic/subtopic/tags), moderation text checks, embedding input.
- Failures are non-fatal: asset proceeds with caption-only metadata but can't serve as `meme` type (a meme without readable text is misclassified risk).

## 10. Failure Matrix

| Failure | Effect | Handling |
|---|---|---|
| Provider 5xx | degraded pool | fallback chain → cached pool; alert at > 5% of runs |
| Rate limit 429 | queue slow-down | backoff, shift to other providers |
| License fields missing/ambiguous | item unusable | quarantine (`status=pending`) for human check (12) |
| Dead hotlink detected | broken media risk | liveness sweeper; remove |
| OCR garbage (non-target language etc.) | mislabel risk | langdetect gate → skip text, caption-only |

## 11. What We Never Do (guardrails)

- No scraping beyond documented APIs. No storing hotlink-only bytes. No stripping attribution. No serving `pending`/`quarantined` content. Violations = P0 bug class in CI review checklist (`15`).
