# 01 — Product Concept

> Source: `pique-idea.md` §§1–9, 18, 30, 43–47. This file condenses the *what and why*; implementation details live in the other docs.

---

## 1. Definition

**FocusWarmup** is a **pre-focus application**. It solves the *activation barrier* — the moment where a person knows what to do but cannot start because the task feels boring, hard, or unrewarding.

**Core promise:**
> Tell us what you need to work on. We spend 5–20 minutes making you genuinely curious about it — then lock the app and send you back to work.

**Core loop:**
```
PROMPT → GET INTERESTED → LOCK → WORK
```

**Product thesis (hypothesis to be tested, not assumed):**
> A short, personalized, entertaining, relevant introduction to a subject decreases psychological resistance to beginning work on that subject.

The MVP exists to **test this thesis experimentally** (`13-analytics-experiments.md`).

---

## 2. Problem

People avoid starting even when they know what to do:

- "I need to study, but I don't feel like starting."
- "I need to design this poster, but I keep scrolling."
- "I know I should work on this, but I cannot switch on mentally."

Conventional tools (Pomodoro timers, blockers, task lists, streaks, stats) all assume the user is **already ready to work**. FocusWarmup addresses the missing stage:

> **avoidance → curiosity → task initiation**

---

## 3. Positioning

- **Weak:** "An app that shows you educational memes before you work."
- **Strong:** "A 5–20 minute curiosity warm-up for whatever you need to work on."
- **One-liner:** FocusWarmup makes your next task interesting before it asks you to do it.
- **Final pitch:** FocusWarmup turns procrastination into curiosity: tell it what you need to work on, spend 5–20 minutes getting genuinely interested, then get locked out and go do the work.

---

## 4. Target Users

| Segment | Example tasks |
|---|---|
| **Students** | exam prep, assignments, difficult subjects, revision, programming topics |
| **Creatives** | design posters, write, edit video, illustration briefs |
| **Knowledge workers** | developers, marketers, analysts, researchers, founders |
| **Self-learners** | languages, hobbies, technical skills, new topics |

MVP copy and onboarding examples should serve **students first** (clearest pain, easiest to recruit for Phase 0 validation).

---

## 5. Core User Experience (concept view)

1. **Tell:** user types a natural-language intention — "I need to study thermodynamics for my exam."
2. **Parse:** AI extracts goal/category/subject/topic/level/urgency; asks at most **one** clarifying question if essential data is missing.
3. **Choose length:** 5 / 10 / 15 / 20 minutes (intentionally short — the app is not a destination).
4. **Generate:** system builds a **time-bounded finite sequence** (never a feed) from profile + task + ranked content.
5. **Progress:** content moves through phases — **Entertainment → Curiosity → Understanding → Activation** (see `10-data-sorting-sequencing.md`).
6. **End:** "WARM-UP COMPLETE — you have enough context, now go do the work."
7. **Lock:** app stops serving content for a configurable period (default 2 hours).

The goal is to make the user **want to leave the app**.

---

## 6. Defining Product Principles

These are non-negotiable and shape every downstream doc:

| # | Principle | Enforced in |
|---|-----------|-------------|
| 1 | **No infinite scrolling** — finite sequence, clear beginning/middle/end | 04, 05, 10 |
| 2 | **No recommendation rabbit holes** — never "20 more like this" | 09 |
| 3 | **No social mechanics in MVP** — no likes/follows/comments/streaks/notifications for engagement | 05, 31-scope |
| 4 | **Visible countdown** — user always knows "3 minutes left", never "here's another meme" | 05 |
| 5 | **Hard stop** — at session end the content engine shuts down | 04, 07 |
| 6 | **Lock period** — no new warm-up content until unlock time | 04, 06 |
| 7 | **Minimal setup** — user reaches a session in seconds, ≤1 clarifying question | 05, 07 |
| 8 | **Curiosity first, learning second** — first cards entertain; last cards drive action | 10 |
| 9 | **Strong ending** — the end is a product moment: "You're ready. Go work." | 05 |
| 10 | **Privacy-minimal personalization** — context & preferences, not demographic profiling | 14 |

---

## 7. Personalization Concept

Personalize via **context and preferences**, not demographics:

- **High-value signals:** current task · knowledge level · content-format preferences · humor style (dry/absurd/sarcastic/wholesome/dark/nerdy/relatable) · language (en/hi/hinglish MVP) · interests (cricket, gaming, anime, music, cars, tech, design, movies) · study/work area.
- **Signature feature — cross-interest analogies:** explain the *topic* through the user's *interest*. E.g. economics → "Think about IPL auction demand…". The engine decides **how to explain the topic to this person**, not just which content to show. (Algorithm: `09-recommendation-algorithms.md` §7.)

---

## 8. Content Concept

Hybrid content strategy:

- **A. Open/licensed sources** — Openverse, Wikimedia Commons, Smithsonian Open Access, Library of Congress, Project Gutenberg; optional Unsplash/GIPHY under their API rules. (Fetching: `08-data-fetching.md`.)
- **B. Generated content** — jokes, analogies, trivia, polls, questions, micro-explanations, comparison cards, quizzes, challenge prompts. Many useful types need no external media.
- **C. User-generated (later phase only)** — submissions enter moderation before joining the pool.

Rights model: own / licensed-for-display / merely-public (**never build on scraping public-but-copyrighted content**). Every asset stores provenance + license (`06-database.md` → `content_sources`).

---

## 9. Anti-Goals

FocusWarmup must explicitly **not** become:

- TikTok for studying · Pinterest for procrastination · an infinite meme feed · a social network · a general AI chatbot · a learning platform replacement · a task manager with a meme tab.

It is a **temporary bridge into work**.

---

## 10. North Star & Success

**North Star Metric:** *Meaningful task initiation after a completed warm-up.*

- A success is **not** "user watched all 10 cards".
- A success **is** "user finished the warm-up and actually began the intended work."

**Key experiment** (MVP must instrument this): control arm gets a plain "Time to work" prompt; experimental arm gets the full warm-up. Compare task initiation, start latency, intended-task duration, abandonment, subjective readiness. Judged on initiation, **not** minutes consumed. (Full framework: `13-analytics-experiments.md`.)

**Product mantra:**
> Do not optimize for time inside FocusWarmup. Optimize for time outside it, doing the work.

---

## 11. Behavioral Model

```
AVOIDANCE → CURIOSITY → INTEREST → READINESS → LOCK → WORK
```

The media (memes, facts, polls, analogies…) is only the mechanism for this transition. The app succeeds **only when the user leaves it** — this is the central principle the architecture (02) is built around.

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **Warm-up** | One finite 5–20 min personalized content session |
| **Task object** | Structured parse of the user's natural-language intention (`07` → `POST /tasks/parse`) |
| **Sequence** | The ordered, time-budgeted list of content items for a session (`10`) |
| **Card** | One rendered content item in the player UI (`05`) |
| **Phase** | Session segment: `entertainment / curiosity / understanding / activation` |
| **`first_work_action`** | Terminal card pointing at the concrete first step of the real task |
| **Lock** | Post-session state where no new content is served (default 2 h) |
| **Candidate pool** | Retrieved + generated content before ranking (`09`) |
| **Provenance** | Source + license metadata attached to every external asset (`06`, `08`) |
| **Initiation** | User actually starting the intended task (North Star, `13`) |
