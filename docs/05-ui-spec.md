# 05 — UI Specification (Every Screen, Section & Button)

> Exhaustive UI contract for the desktop app. Component names match `02` §4 layout; handlers match `03` Part B; API calls match `07`. States: **[loading] [error] [empty] [disabled]** noted per screen.

---

## 0. App Shell (all screens)

**Sections:** native shell (**final product: Android + iOS via Capacitor** — user decision; plain web during the slice), screen root, toast viewport, modal root. Mobile rules: respect status-bar safe areas, ≥ 44 pt touch targets, swipe-back = previous read-only card.

| Element | Type | Behavior |
|---|---|---|
| App wordmark "FocusWarmup" | text | — |
| Countdown chip (visible only in session) | status | mirrors `useCountdown` |
| Lock chip (visible only when locked) | status | opens Locked screen |
| OS back / swipe | native nav | session → confirm "Leaving ends your warm-up (lock still applies)"; else default back |
| Background/kill app | OS | mid-session: heartbeat stops → server applies lock rules (`04` §6) |

Desktop-web dev extras (slice only): `→` next card · `←` previous · `Esc` close modal · `Ctrl/Cmd+Enter` primary action on Home.

Accessibility: full keyboard navigation, ARIA live region for countdown announcements (polite, every 60 s), reduced-motion setting respected, min contrast AA.

---

## 1. Onboarding (first run only, 5 steps, skippable after step 1)

### Step 1 — Welcome
- **Sections:** product promise copy, "how it works" 3-icon strip (Tell → Warm up → Work), CTA.
- **Buttons:** `Get started` → step 2 · `Skip setup` → Home with defaults (marks profile `onboarded=true`, defaults language=en, level=beginner).

### Step 2 — Language
- **Sections:** language cards (English / हिन्दी / Hinglish) radio cards.
- **Buttons:** card select (radio) · `Continue` [disabled until selected] · `Back`.

### Step 3 — Interests
- **Sections:** chip grid (cricket, gaming, anime, music, movies, cars, technology, design, football, cooking, space, finance… ~20, multi-select, min 1 max 8), custom interest input.
- **Buttons:** chips toggle · `Add` (custom) · `Continue` [disabled if 0] · `Back`.

### Step 4 — Humor style
- **Sections:** radio list (dry, absurd, sarcastic, wholesome, dark, nerdy, relatable, "no preference").
- **Buttons:** select · `Continue` · `Back`.

### Step 5 — Personalization consent + knowledge default
- **Sections:** explainer copy ("We use your interests to explain topics in ways you'll find relatable. Nothing else."), toggle `Personalization ON` (default on), radio "Your usual familiarity with new topics" (beginner/intermediate/advanced).
- **Buttons:** `Finish setup` → writes profile (`profileApi.patch`) → Home · `Back`.

[error] profile save fails → inline retry, still proceeds locally (queued sync).

---

## 2. Home / Task Input (default screen when IDLE/UNLOCKED)

**Layout (idea doc §38 direction — "pre-game tunnel"): calm, centered column.**

### Sections
1. **Header:** greeting + date; right side: `History` icon-button, `Settings` icon-button.
2. **Mission prompt card:** label `"What do you need to work on?"`, multiline textarea (placeholder cycles through 3 examples: study DBMS / design poster / learn closures), char count 0/500, helper "Be specific — subject + why, e.g. exam tomorrow".
3. **Example chips row:** 3 clickable prompts (insert into textarea).
4. **Duration selector:** segmented chips `5 · 10 · 15 · 20 min` (10 preselected) + lock-upcoming hint "App locks for 2 h after the session".
5. **Recent tasks:** last 5 `tasks` rows as chips (one-tap refill) — *not* a history feed, no infinite list.
6. **Offline banner** [conditional]: "Offline — you'll get a cached mini warm-up".

| Button / Control | Behavior | API |
|---|---|---|
| Textarea | validates non-empty; `Ctrl+Enter` submits | — |
| Example/Recent chips | fill textarea | — |
| `Start Warm-up` (primary CTA) | [disabled] if empty or locked → `submitTaskPrompt()` | `POST /tasks/parse` |
| Duration chips | `selectDuration(m)` | — |
| `History` | → screen 8 | — |
| `Settings` | → screen 9 | — |

**States:** [loading] CTA spinner during parse → [clarify modal if needed] → Generating screen. [error] parse failure → inline error under textarea + `Try again`. Locked → entire composer replaced by **Locked banner** (mini version of screen 7 + `Go to lock screen`).

---

## 3. Clarification Modal (≤1 question, only if parser asks)

- **Sections:** task summary line ("Thermodynamics · exam tomorrow"), question text ("How familiar are you with this?"), answer options as big radio cards (per parser payload, e.g. Beginner / Some basics / Advanced).
- **Buttons:** option cards · `Continue` → `answerClarification()` → Generating · `Skip` → proceed with defaults (beginner) · `Edit prompt` (text link) → back to Home.
- [loading] skeleton on Continue.

---

## 4. Generating Screen

- **Sections:** animated progress checklist (Understanding your task → Finding interesting material → Personalizing → Planning your 10 minutes → Final check), progress bar (indeterminate→stepwise), cancel affordance.
- **Buttons:** `Cancel` → abort flow, back to Home (idempotency key discarded).
- Copy rule: no fake content teasers here (avoid pre-consumption).
- [error] >12 s or failure → message + `Try again` / `Rephrase prompt` / `Back`.
- Target: p95 < 8 s (`02` §6).

---

## 5. Session Player (core screen)

```text
┌──────────────────────────────────────────────┐
│ Thermodynamics · exam prep        07:42  ⏱   │  ← task label + countdown
│ ●●●○○○○○○○                        6 / 10     │  ← progress dots + index
├──────────────────────────────────────────────┤
│                                              │
│              CONTENT CARD AREA               │
│         (one card, see §6 variants)          │
│                                              │
├──────────────────────────────────────────────┤
│  ⚑ Report      ⟲ Skip         Next →         │
│  End early                          (phase:  │
│                                     curiosity)│
└──────────────────────────────────────────────┘
```

### Sections
1. **Top bar:** task label (topic · goal), countdown `mm:ss` (amber < 2 min, red pulse < 30 s), phase tag.
2. **Progress:** dots (filled/shown/current) + "n / N". Dots are **not** clickable — Decision: free navigation invites cherry-picking entertainment; only `Back` (view) allowed via `←`.
3. **Card viewport:** single card, subtle enter animation; skeleton while media loads; image attribution caption when required (`attribution_text` from `content_sources`).
4. **Footer controls** (below).
5. **Offline chip** + **report confirmation toast** area.

| Button | Behavior | API/event |
|---|---|---|
| `Next →` | advance cursor; on final card label changes to `Finish warm-up ✓` → complete flow | item event `shown`/`dwell_ms` |
| `⟲ Skip` | advance + mark skipped; toast "Noted — we'll show fewer like this" | event `skipped=true` |
| `⚑ Report` | opens Report modal (§7) | `POST /content/report` |
| `End early` | confirm modal: *"Your warm-up will end and the 2 h lock still starts."* → abandon → Complete screen (abandoned variant) | `POST /sessions/{id}/complete` with `"abandoned": true` |
| Card interaction (poll option, question answer, flip) | per §6 | `engagement` in heartbeat |
| (implicit) `←` back | previous card read-only; interaction disabled | — |

**No pause button. Decision:** a pause defeats the hard timebox; the countdown keeps running (idea doc §7 hard limit). Copy explains this if user tries.

**States:** [loading] per-card skeleton; [error] media fails → auto-fallback to text-only rendering; heartbeat fail → retry banner after 2 failures, playback continues offline (`04` §9).

---

## 6. Card Variants (one renderer per `CONTENT_TYPES`)

All cards share: type badge (small), body, optional attribution, optional `phase` tint. Each registered in `components/cards/`.

**Global body rule (user decision 2026-09-26):** cards stay scannable — body text longer than ~240 chars renders clamped with a **Read more / Show less** toggle (sentence-boundary cut). Short cards are never touched. Player remounts via keyed card wrap, so expansion resets per card.

| # | Type | Card contents | Interactive elements |
|---|---|---|---|
| 1 | `meme` | image (or rendered text-meme), caption | none |
| 2 | `interesting_fact` | headline + 1–2 sentence fact + "why it matters" line | optional expand "Tell me why" (inline, no navigation) |
| 3 | `quote` | quote text, author, tiny context | none |
| 4 | `visual_explanation` | image/diagram + short caption + 3-bullet breakdown | zoom on click |
| 5 | `analogy` | "Think about **{interest}**…" bridge + mapping to topic | optional "another angle" (regenerates inline, max 1, counts against time) |
| 6 | `joke` | setup + punchline (punchline hidden until tap · "Reveal") | Reveal button |
| 7 | `poll` | question + 2–4 options + live session-local result bar after voting | option buttons (single vote, locks) |
| 8 | `question` | open/Socratic question about topic | "Show hint" (reveals pointer, then "Show answer") |
| 9 | `mini_story` | 3–5 sentence story (historical/anecdotal) | none |
| 10 | `trivia` | fact framed as trivia + "Did you know?" | flip-style reveal |
| 11 | `historical_context` | era tag + context paragraph + optional archival image | none |
| 12 | `diagram` | SVG/image diagram + labels | zoom; optional step-through if multi-part |
| 13 | `reaction_gif` | GIPHY gif + caption + provider attribution | none |
| 14 | `micro_lesson` | 3-line concept explanation + 1 example | optional "show example" toggle |
| 15 | `challenge` | tiny 2-minute challenge tied to task | `I'll try it` / `Not now` (recorded) |
| 16 | `first_work_action` (**always last**) | "You're ready. First step:" + concrete action + session end CTA | `Finish warm-up ✓` |

---

## 7. Report Content Modal

- **Sections:** offending card thumbnail, radio reasons: `Inappropriate` / `Wrong or misleading` / `Copyright concern` / `Off-topic` / `Other`, optional comment field, reassurance copy.
- **Buttons:** `Submit report` → API; card **immediately replaced** by reserve item (response carries it) → toast "Reported. This card won't appear again." · `Cancel`.
- Reports land in `moderation_queue` (`12` §4).

---

## 8. Session Complete Screen

### Variant A — completed
- **Sections:** `WARM-UP COMPLETE` headline · summary chips (topic, minutes, cards seen, skipped count) · North-Star prompt: **"Ready to start?"** · next-lock notice ("Locked for 2 h once you continue").
- **Buttons:**
  - `I'm starting now →` (primary; records initiation=true) → `complete` → Locked screen
  - `Not yet` (secondary, honest path; initiation=false) → same flow
  - `View summary` (expands per-card list w/ report links — read-only)

### Variant B — abandoned
- headline "Warm-up ended early", same buttons minus summary pride copy.

---

## 9. Locked Screen

```text
      🔒 LOCKED
   You're warmed up.
   Now go do the work.

      01:57:32        ← live countdown
   Unlocks at 4:12 PM

 [ Why am I locked? ]   [ Settings ]
 [ Emergency unlock ]
```

- **Sections:** lock countdown, unlock-at time, one-line rationale, motivational task echo ("Thermodynamics — you were curious about entropy"), quiet tips (optional 3 static tips, not content).
- **Buttons:**
  - `Why am I locked?` → info popover (product principle)
  - `Settings` → screen 10 (allowed while locked; profile edits take effect next session)
  - `Emergency unlock` → friction modal: type `I NEED TO STOP` → `lockApi.emergencyUnlock(confirm)` → logged `lock_break` → Home
  - **No** "one more session", **no** snooze, **no** content browsing. Hard wall by design.
- Relaunch/app-kill lands here again (`04` §5).

---

## 10. Settings & Profile

### Sections & every control
1. **Personalization** — toggle `Use my interests & humor for content` (off → generic non-personalized sessions + pause preference learning); link `What we store` (privacy sheet from `14` §4); `Reset personalization` button (confirm → `profileApi.resetPersonalization()`).
2. **Interests** — chip editor (same component as onboarding step 3) + custom add/remove.
3. **Humor style** — radio list (same set).
4. **Language** — radio cards (en / hi / hinglish).
5. **Content formats** — checkbox grid (memes, facts, visuals, stories, questions/polls, quotes, trivia, examples) min 2 enforced.
6. **Default session length** — radio 5/10/15/20.
7. **Lock duration** — select 60 / **120** / 180 / 240 min. Changes apply to *next* lock (never retroactive, to prevent mid-lock manipulation).
8. **Playback** — toggles: `Auto-advance cards` (default OFF, `04` §3) · `Reduced motion` · `Countdown sound at 1 min` (default off).
9. **Account** — email link field (`Add email to sync` magic link, post-MVP), `Copy device ID`, `Delete my data` (danger, double-confirm → full wipe per `14`).
10. **About** — version, content licenses info page ("Made possible by open content: list of providers"), report-a-bug mailto.

| Buttons | API |
|---|---|
| `Save changes` (per section, sticky) | `PATCH /profile` |
| `Reset personalization` | profile reset endpoint |
| `Delete my data` | account deletion endpoint |
| `Back` | — |

---

## 11. History

- **Sections:** session list (date, topic chip, duration, status badge: Completed/Abandoned, initiation badge: Started work ✓ / Not reported), each row expands to: cards seen, skip pattern, `Did you end up starting?` retro self-report (`Yes` / `No`) when initiation was never recorded → fires initiation event with `retroactive: true`.
- **Limit:** last 30 sessions paginated; **no stats-gamification**, no streak UI (anti-goal).
- **Buttons:** row expand · `Yes I started` / `Didn't start` · `Back`.
- [empty] "No warm-ups yet — start your first one."

---

## 12. Global Modals

| Modal | Sections | Buttons |
|---|---|---|
| Confirm end early | warning copy, lock reminder | `End warm-up` (danger) · `Keep going` |
| Emergency unlock | type-to-confirm input, consequence copy | `Unlock` [disabled till exact phrase] · `Cancel` |
| Delete data | irreversible warning, checkbox "I understand" | `Delete everything` · `Cancel` |
| Error (generic) | message, copyable error id | `Retry` · `Dismiss` |
| Privacy sheet | data list, why, delete instructions | `Close` |

---

## 13. Copy & Visual Direction

- Dark/light themes follow system; large media cards, strong type, minimal chrome (idea doc §38).
- Tone: calm coach, not hype. Session-end copy is the product moment: **"You're ready. Go work."**
- Countdown always visible during session — primary anti-distraction affordance.
