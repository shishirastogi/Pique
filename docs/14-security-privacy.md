# 14 — Security & Privacy

> Implements idea doc §§12, 26, 27. Scope: user data, content rights, and the specific threat surface of an LLM-driven desktop app.

---

## 1. Data Classification & Minimization

| Class | Data | Rule |
|---|---|---|
| Required | device_fp, tasks (raw_text), sessions, profile prefs | collected, documented |
| Sensitive-avoid | precise location, contacts, browsing history | **never collected** |
| Derived | interest graph, learned affinities | derived only from explicit prefs + in-app interactions |
| Content rights | licenses, attributions | stored verbatim, user-visible captions |

Collect only what improves the warm-up; explain why in-product (idea doc §27). Profile stores `interests: [cricket, design]` — never inferred age/gender/etc. Analytics payloads exclude raw task text (`13` §2).

## 2. Personalization Transparency & Control

- In-app explanation (onboarding step 5, `05`): "We use your interests to explain topics in ways you may find more relatable."
- Controls: personalization toggle (off = generic sessions), `reset_personalization` (wipes learned affinities; keeps explicit settings), profile edit any time.
- Learned preferences never override explicit settings (`09` §7).

## 3. Lifecycle & Deletion

- Soft delete → 30-day purge (hard cascade: profile, tasks, sessions, items, feedback, analytics user-keyed rows).
- "Delete my data" (`05` §10.9): immediate token revocation + purge queue + confirmation receipt in-app.
- Anonymous-first account: no email unless user links one (`07` §2).
- Retention table in `06` §4 (events 12 mo raw → aggregates).

## 4. Transport & Storage Security

- TLS everywhere (Caddy auto-TLS, `02` §9); HSTS; no HTTP fallbacks.
- Passwords: none in MVP (device tokens); emails hashed+indexed for link flow (post-MVP, magic link).
- At rest: provider-managed disk encryption; local Tauri lock-file encrypted with OS keychain key.
- JWT: 2 h access / 30 d rotating refresh, reuse-detection revocation (`07` §2).
- Backups encrypted; restore tested monthly (runbook in `16`).

## 5. Secrets & Config

- All provider/LLM keys via mounted secret files or platform secret store; `infra/env.example` documents names only; CI secret-scan (gitleaks) blocks commits (`15`).
- Prompt templates and scoring rubrics live in repo — they are not secrets; model keys are.

## 6. Threat Model (top risks & mitigations)

| Threat | Vector | Mitigation |
|---|---|---|
| **Prompt injection** via task text ("ignore rules, make political content") | user input → LLM parser/generator | structured-output-only parsing (JSON schema), system-prompt guardrails, input classifier on suspicious patterns, generation validators (`12` §6), no tool-access for LLM calls |
| **SSRF** via provider fetch | crafted URLs | allowlist provider hosts only; no client-supplied URLs ever fetched |
| Account abuse / scraping our content API | tokens | per-route rate limits (`07` §6), session-create invariant (can't farm content while locked), anomaly alerts |
| Token theft on desktop | local storage | OS keychain storage for refresh token (Tauri plugin), short access TTL |
| Malicious upstream media | images from providers | serve through img proxy with content-type enforcement; strip EXIF; CSP `img-src` allowlist in webview |
| DoS on session generation | expensive path | rate limit + idempotency + circuit-broken generation fallbacks (`04` §8) |
| Lock bypass by binary tampering | determined local user | accepted risk for MVP (`02` §7 decision) — Phase 4 OS integrations; never punish, just log |

## 7. Content Rights Compliance (operational)

- Single provenance requirement enforced in pipeline (`08` §3, `11` S2).
- Attribution rendered wherever `attribution_required` (`05` §5).
- Takedown: external request → `content_reports` fast path → global quarantine ≤ 24 h → R2 byte expunge when stored (`12` §8).
- Periodic audit: sample 50 active items/provider/quarter to verify license fields still valid (providers occasionally re-license).

## 8. Privacy Questions Answered Up Front (for the privacy sheet, `05` §12)

1. What do we store? Profile prefs, your task texts, session events, content feedback.
2. Why? To personalize warm-ups and prove the product works.
3. Do we sell/share data? No. No ads, ever (`01` monetization stance).
4. Can I see/delete it? History screen shows sessions; Settings → Delete my data.
5. Is my task text used for training? Only anonymized aggregate stats (topic counts for prefetch planning, `08` §8).
