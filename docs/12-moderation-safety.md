# 12 — Moderation & Safety

> Implements idea doc §26. Pipeline integration: `11` S7. Serving-time gate: `09` §9 / `SafetyGate` (`03` A.9). User-facing flows: `05` §7 (report), §9.

---

## 1. Where Safety Applies

| Point | What runs | Blocking? |
|---|---|---|
| Ingestion (S7) | automated screens below | yes — fail → quarantine |
| Generation output | same screens + factuality + tone | yes |
| Sequence assembly | `SafetyGate.check_plan` whole-sequence checks | yes — fail plan |
| Runtime | user reports → immediate replacement + review | post-hoc |
| Periodic | drift audits, re-screening on model/policy updates | post-hoc |

## 2. Automated Screens (every candidate)

| Check | Method (MVP) | Fail threshold |
|---|---|---|
| NSFW / sexual | vision classifier (provider or open model) on images; text classifier on body/OCR | ≥ 0.5 |
| Hate / harassment | text classifier + denylist lexicon (multi-lang) | any strong hit |
| Extremist / violent / gore | vision + text classifiers | ≥ 0.5 |
| Misinformation risk | topic flag (health/politics/news) → routes to template-only policy | flag = stricter path |
| Copyright/provenance | S2 precheck (`11`) | missing fields = drop |
| Duplicates / spam | `DedupService` + URL reputation | dup = drop |
| PII in content | regex + NER on OCR/body | any → quarantine |

Verdicts: `pass | quarantine | block`. Quarantined items enqueue `moderation_queue` (`06`) with `source=auto_screen`.

## 3. Moderation Review (human)

- Queue UI (admin web, post-MVP simple FastAPI-admin page; decision MVP: SQL + lightweight admin route from `07` §4.14).
- Actions: `approve` (status→active) / `remove` (status→removed + tombstone reason) / `escalate` (second reviewer).
- SLA targets: user-report items ≤ 24 h; auto-quarantine backlog drained ≥ weekly.
- Every review decision is stored — becomes training data for thresholds (Phase 3).

## 4. User Reports Flow

`POST /content/report` (`07` §4.13):
1. Row → `content_reports`; user toast "This card won't appear again."
2. **Immediate:** per-user exclusion of the card; response carries a reserve item so playback continues (`05` §7, `10` §1 reserve).
3. Report count ≥ 2 (config) or `reason=copyright` ⇒ content auto-quarantined globally pending review.
4. Resolution mails nobody in MVP (no email) — outcome silently reflected; reporter trust comes from instant removal.

## 5. High-Stakes Topics Policy

Medical, legal, financial, mental-health and similar topics **never** get:
- jokes/memes presenting as advice, generated factual claims without references, or `curiosity`-style hooks that trivialize.

They get: template-generated framing cards ("here's how professionals think about X"), source-referenced `interesting_fact`s (Gutenberg/LoC-style archival or explicitly licensed), `micro_lesson`s from reviewed templates, and the activation card linking to the user's own materials/professional help. Config flag `topics.high_stakes` (list) drives routing in ranker guardrails (`09` §9) and generators (`11` §4).

## 6. Generated-Content Safety

- Prompt-level constraints (no medical/legal/financial advice, no real-person ridicule, no politics).
- Output validators: factuality confidence (`11` §4), tone check, denylist, length caps.
- Model/prompt versioning: every generated row stamped `provider:model:prompt_version` → bad pattern discovered = one query to bulk-wipe a prompt version.
- Adversarial user prompts (injection trying to force unsafe generation) handled in `14` §6.

## 7. Session-Level Safety Checks

`SafetyGate.check_plan` catches things item-screening can't:
- **Context collisions:** e.g. joke card adjacent to a tragedy-adjacent historical card on same topic.
- **Drift:** sequence semantic centroid must remain within radius of task embedding (guards against off-topic hallucinated curation).
- **Load balance sanity:** ≥ 70% of cards match task language (fallback acceptable for English media in hi/hinglish sessions, flagged in telemetry).

## 8. Compliance & Takedown Hooks

- License-based instant filter: `UPDATE content SET status='removed' WHERE source.provider=? AND license=?` used for provider term changes (`11` §7).
- External takedown requests: email alias → `content_reports(reason=copyright, comment=external ref)` fast path, expunge bytes from R2 where stored (`14` §7).
- Audit trail: every status transition logged (who/which job/when) in `moderation_queue` + ingest logs.

## 9. Metrics (dashboard in `13` §6)

`flagged_rate{check}`, auto-quarantine precision (sampled human review), report→takedown latency, false-positive appeals from quality dashboard, per-provider problem rates (provider demotion input, `11` §6).
