# 10 — Data Sorting & Sequence Planning

> How the ranked pool becomes **the ordered, time-budgeted session**. Implements idea doc §17 (sequence generation) and the curiosity arc of §6 (Step 5). Owner module: `SequencePlanner` (`03` A.8).

---

## 1. Inputs / Outputs

```python
plan(ranked: list[RankedItem], duration: int, task, profile) -> SequencePlan

SequencePlan = {
  slots:  list[SlotSpec],        # from template (§3)
  items:  list[PlannedItem],     # content_id, position, phase, planned_seconds
  reserve: list[content_id],     # 2 spares for report-replacement / media failure (07 §4.13)
  meta:   {duration, config_version, generation_mix}
}
```

Sequence planning is a **constrained ordering problem**, not a top-N sort: the best item set ≠ the best sequence; position matters (idea doc §17).

---

## 2. Duration → Size

| Duration | Cards incl. terminal | Reserve |
|---|---|---|
| 5 min | 10 | 2 |
| 10 min | 20 | 2 |
| 15 min | 28 | 3 |
| 20 min | 36 | 3 |

Sizing targets **~2 cards/minute** (≈ 30 s mean dwell) so the countdown — never an
empty deck — ends the session. Per-type dwell budgets (§6) rescale to fit.

**Humor guarantee (user-set product rule):** position 0 is always a meme; the
entertainment zone follows a `meme → joke → reaction_gif` cycle until the
minimum humor count is met: 5 min → 2, 10 min → 3, 15/20 min → 4.

## 3. Phase Templates (the curiosity arc)

Phases: `entertainment → curiosity → understanding → activation` (idea doc §6.5). Fractions are anchor ratios (of card count, terminal card excluded):

| Phase | Share | Allowed types | Role |
|---|---|---|---|
| Entertainment | first 20% | meme, reaction_gif, joke, trivia, surprising image (interesting_fact w/ media) | kill resistance — pure hook |
| Curiosity | next 30% | interesting_fact, question, poll, historical_context, mini_story | open a loop in the brain ("why?") |
| Understanding | next 35% | visual_explanation, analogy, micro_lesson, diagram | actually teach the core idea |
| Activation | last card + bridge card | **first_work_action (always final)**, challenge (penultimate optional) | convert interest → first physical step |

Example 10-card template (position: type constraint):
```text
0 meme|reaction_gif        5 analogy!            ← reserved analogy slot (09 §7)
1 interesting_fact(media)  6 joke|meme           (humor dip re-energizes)
2 question|poll            7 poll|question
3 historical_context       8 micro_lesson|diagram
4 visual_explanation       9 first_work_action   (hard-fixed terminal)
```

Templates stored in DB config `sequence.templates.v1` (`06` §4) — tunable per experiment without deploys.

## 4. Hard Constraints (never violated; validator enforces)

1. **Terminal lock:** position N-1 must be `first_work_action`.
2. **No immediate type repeat:** `type(i) ≠ type(i+1)` (format fatigue guard).
3. **Media streak cap:** ≤ 2 consecutive image-only cards (meme/gif/image-fact) before a text/interactive card.
4. **Interaction pacing:** ≥ 1 interactive card (poll/question/challenge) per session; none in the first 2 positions (earn attention before asking input) and none at position N-2 (don't bury the ending).
5. **Phase membership:** card type must be allowed in its slot's phase (§3).
6. **Difficulty ramp:** `difficulty(i) ≤ difficulty(i+1) + none` — non-decreasing level from mid-sequence onward; nothing above task level in `entertainment`.
7. **Analogy presence:** exactly 1 analogy in the `understanding` zone when `bridge_interest` exists (`09` §7).
8. **Uniqueness:** no two cards from same `source_id`; no near-duplicate pairs (cosine > 0.92).

## 5. Soft Objectives (optimize subject to §4)

- `relevance` should be **monotonic-ish increasing**: penalize `rel(i) > rel(i+1) + 0.1`.
- Personal-fit peak lands mid-session (positions 40–70%) — the "this is for me" moment.
- Humor density: high early, tailing off (`humor_total(pos)` decreasing).
- Slot-phase weight profiles from `09` §5 applied when ranking per-slot.
- Maximize total `learning_value` in the back half without breaking the ramp.

## 6. Dwell-Time Allocation

Seconds per card = duration budget distributed by type cost, then clamped so sum = duration·60:

| Type | nominal s |
|---|---|
| meme / reaction_gif / joke | 30 |
| interesting_fact / trivia / quote | 40 |
| poll / question | 50 |
| visual_explanation / analogy / mini_story / historical_context | 60 |
| micro_lesson / diagram / challenge | 75 |
| first_work_action | 30 |

Sum-scaled to fit exactly; `planned_seconds` stored per item (`06.session_items`) and shown as the card's soft pacing hint (`05` §5). Auto-advance is OFF by default — dwell is guidance, not enforcement (`04` §3).

## 7. The Fill Algorithm (MVP: greedy + lookahead + repair)

```python
def fill_slots(ranked, slots, ctx):
    remaining = ranked.copy()               # base-score ordered (09)
    plan, violations = [], 0
    for slot in slots:                       # slots in position order
        cands = [c for c in remaining
                 if c.type in slot.allowed_types
                 and satisfies_hard(plan, c, slot)]          # §4 checks incl. lookahead:
        # lookahead = ensure filling now cannot make NEXT slot unfillable (check type supply)
        if not cands: violations += 1; relax(slot) ; cands = fallback_pool(slot, ctx)
        pick = argmax(cands, key=phase_weighted_score)        # §5 weights
        plan.append(to_planned(pick, slot)); remaining.remove(pick)
    reserve = remaining[:2_or_3]
    return validate(plan, slots, reserve)                     # + repair pass below
```

**Repair pass:** if validator still flags violations (e.g. type repeat after fallback), swap offenders with the best constraint-satisfying later item; if template unfillable at both ends (tiny pool), allow one same-type adjacency but never break constraints 1, 6, 7, 8.

**Upgrade path (Phase 7):** beam search (width 8) over slot assignments maximizing `Σ phase_weighted_score − soft penalties`; the greedy version is deliberately simple until telemetry justifies more (idea doc §42).

## 8. Variety Between Sessions (same task re-run)

Rank cache reuses the pool (`07` §6) but planning re-runs with a per-session seed: shuffle within equal-score bands (±0.02) before slot fill → same-quality but visibly different sequences; history filter already excludes last-10-session items (`09` §3).

## 9. Validation & Safety Gate

`validate()` emits violations → repair → if any **critical** violation remains (terminal card missing, empty plan, safety-flagged item), fail session creation → client graceful error (`04` §8, `07` §4.3). Then `SafetyGate.check_plan(plan)` runs a final whole-sequence screen (e.g., accidental topic drift, joke-context collisions) before persisting `session_items` (`02` §6).

## 10. Worked Example (10-minute student session)

Ranked pool of 34 → template of §3 → selected plan:

| Pos | Phase | Type | Why it landed here |
|---|---|---|---|
| 0 | entertainment | meme | top humor + relevance |
| 1 | entertainment | interesting_fact (entropy image) | high curiosity, has media |
| 2 | curiosity | question ("why can't engines be 100%?") | interaction pacing satisfied later instead — moved from 2→7 by pacing rule? No: rule 4 only forbids interaction at 0–1 and N−2 → kept |
| 3 | curiosity | historical_context (Carnot) | story arc bridges eras |
| 4 | understanding | visual_explanation (heat engine) | rising relevance |
| 5 | understanding | **analogy (cricket ↔ energy transfer)** | reserved slot rule 7 |
| 6 | understanding | joke (dip) | re-energize before lessons |
| 7 | understanding | poll | interactive mid-late |
| 8 | understanding→activation | micro_lesson (3-line 2nd law) | max learning_value in back half |
| 9 | activation | first_work_action ("Open notes: second law") | hard-fixed terminal |

Reserve: `[trivia(Maxwell demon), diagram(engine cycle)]` → used instantly if any card is reported (`05` §7).

## 11. What Sorting Must Never Do

- Never extend the session. Never reorder to serve "engagement". Never surface adjacent-session suggestions ("more like this" — anti-rabbit-hole, `01` §6). The sorter's only customer is **task initiation**.
