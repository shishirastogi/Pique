"""SequencePlanner — slice implementation of docs/10-data-sorting-sequencing.md.

Implements the durable rules (used with mock content now, real ranking later):
- duration -> card count (§2), phase templates (§3)
- hard constraints (§4): terminal first_work_action, no adjacent same type,
  interaction pacing (no interactive at 0-1 / N-2), >=1 interactive card,
  exactly one analogy in understanding when the profile has interests
- dwell-time allocation (§6) scaled to the session budget
"""
import random
from dataclasses import dataclass, field

from app.services.content_generator import generate_item
from app.schemas import TaskObject

# ~2 cards/minute so the countdown (not the deck) is what ends a session
SIZE = {5: 10, 10: 20, 15: 28, 20: 36}
# guaranteed humor cards (meme/joke/reaction_gif) per duration (user-set product rule)
HUMOR_MIN = {5: 2, 10: 3, 15: 4, 20: 4}
PHASES = ("entertainment", "curiosity", "understanding", "activation")
ENTERTAINMENT = ["meme", "reaction_gif", "trivia", "interesting_fact"]
CURIOSITY = ["question", "poll", "interesting_fact", "historical_context", "mini_story",
             "trivia", "book_excerpt", "visual_explanation", "diagram"]
UNDERSTANDING = ["visual_explanation", "analogy", "micro_lesson", "diagram",
                 "interesting_fact", "challenge", "book_excerpt"]
INTERACTIVE = {"poll", "question", "challenge"}
# types the slot filler can ever place from the real pool or generate
TYPES_IN_SLOTS = set(ENTERTAINMENT + CURIOSITY + UNDERSTANDING + ["first_work_action"])
# types the mock generator can produce; real-content-only types (e.g. book_excerpt)
# are pool-only and must never fall through to generation
GENERATABLE = {"meme", "reaction_gif", "joke", "trivia", "interesting_fact", "quote",
               "question", "poll", "analogy", "historical_context", "mini_story",
               "visual_explanation", "diagram", "micro_lesson", "challenge",
               "first_work_action"}
DWELL_NOMINAL = {
    "meme": 30, "reaction_gif": 30, "joke": 30, "quote": 40, "trivia": 40,
    "interesting_fact": 40, "question": 50, "poll": 50, "visual_explanation": 60,
    "analogy": 60, "mini_story": 60, "historical_context": 60, "diagram": 75,
    "micro_lesson": 75, "challenge": 75, "first_work_action": 30,
}


@dataclass
class SlotSpec:
    position: int
    phase: str
    allowed_types: list[str] = field(default_factory=list)
    force_type: str | None = None


def slot_template(duration: int, need_analogy_interest: str | None) -> list[SlotSpec]:
    """doc 10 §3: entertainment 20% · curiosity 30% · understanding rest · activation last."""
    n = SIZE[duration]
    e = max(1, round(0.2 * (n - 1)))
    c = max(1, round(0.3 * (n - 1)))
    slots: list[SlotSpec] = []
    for pos in range(n):
        if pos == n - 1:
            slots.append(SlotSpec(pos, "activation", ["first_work_action"], "first_work_action"))
        elif pos < e:
            slots.append(SlotSpec(pos, "entertainment", list(ENTERTAINMENT)))
        elif pos < e + c:
            slots.append(SlotSpec(pos, "curiosity", list(CURIOSITY)))
        else:
            slots.append(SlotSpec(pos, "understanding", list(UNDERSTANDING)))
    # humor guarantee (user rule): meme hooks position 0; jokes retired; the
    # alternating meme/gif cycle puts the extra meme in joke's old slot
    humor_cycle = ["meme", "reaction_gif"]
    for i, slot in enumerate(s for s in slots if s.phase == "entertainment"):
        if i < HUMOR_MIN[duration]:
            t = humor_cycle[i % len(humor_cycle)]
            slot.allowed_types = [t]
            slot.force_type = t
    # reserve exactly one analogy slot in the understanding zone (docs/09 §7)
    if need_analogy_interest:
        for pos in range(e + c, n - 1):
            if "analogy" in slots[pos].allowed_types:
                slots[pos].allowed_types = ["analogy"]
                slots[pos].force_type = "analogy"
                break
    # guarantee >=1 interactive card, placed mid-session only (docs/10 §4.4:
    # interactive is forbidden at positions 0-1 and N-2, so force one capable slot)
    capable = [s for s in slots
               if 2 <= s.position < n - 2 and not s.force_type
               and set(s.allowed_types) & INTERACTIVE]
    if capable:
        capable[0].allowed_types = [t for t in capable[0].allowed_types if t in INTERACTIVE]
    else:
        for s in slots:
            if 2 <= s.position < n - 2 and not s.force_type:
                s.allowed_types = ["poll"]
                break
    return slots


def plan(duration: int, task: TaskObject, interests: list[str], seed: str,
         real_pool: list[dict] | None = None,
         pregen_payloads: dict[int, dict] | None = None,
         llm_picks: dict[int, str] | None = None) -> list[dict]:
    """Greedy constraint fill (doc 10 §7). Order of choice per slot:
    LLM-picked candidate (09 selection) > heuristic best-fit pool item > generated
    (LLM batch `pregen_payloads`, else templates). Returns planned items:
    [{position, phase, type, planned_seconds, existing_content_id|payload}]"""
    slots = slot_template(duration, interests[0] if interests else None)
    pool = list(real_pool or [])
    pregen = pregen_payloads or {}
    picks = llm_picks or {}
    picked: list[str] = []  # types chosen so far
    items: list[dict] = []

    def ok(ctype: str, pos: int) -> bool:
        if ctype in INTERACTIVE and (pos <= 1 or pos >= len(slots) - 2):
            # interaction pacing (10 §4.4): none at 0-1, none at N-2
            return False
        if picked and picked[-1] == ctype:  # no adjacent same type (10 §4.2)
            return False
        return True

    for slot in slots:
        # position-scoped RNG: decisions per slot are reproducible across the
        # dry-run (needed_generation_types) and the real run, regardless of
        # whether payloads came from the LLM batch or the mock generator
        rng = random.Random(f"{seed}#{slot.position}")
        used: dict | None = None
        if pool and not slot.force_type:
            llm_pick = picks.get(slot.position)
            if llm_pick:  # selection service already validated type/phase
                used = next((c for c in pool if c["content_id"] == llm_pick), None)
            if used is None:
                fitting = [c for c in pool if c["type"] in slot.allowed_types
                           and ok(c["type"], slot.position)]
                if fitting:  # visuals first, then best stored score (tie-break seeded)
                    fitting.sort(key=lambda c: (bool((c.get("media") or {}).get("url")),
                                                (c.get("scores") or {}).get("relevance", 0)
                                                + rng.random() * 0.1), reverse=True)
                    used = fitting[0]
            if used is not None:
                pool.remove(used)

        if used is not None:
            items.append({"position": slot.position, "phase": slot.phase,
                          "type": used["type"], "existing_content_id": used["content_id"]})
            picked.append(used["type"])
            continue

        cands = [t for t in slot.allowed_types if t in GENERATABLE and ok(t, slot.position)]
        fell_back = False
        if not cands:  # repair: relax only the adjacency rule (10 §7)
            cands = [t for t in slot.allowed_types if t in GENERATABLE
                     and not (t in INTERACTIVE and (slot.position <= 1 or slot.position >= len(slots) - 2))]
            fell_back = True
        ctype = slot.force_type if slot.force_type in cands else rng.choice(cands or slot.allowed_types)
        payload = pregen.get(slot.position) or generate_item(ctype, task, interests, rng,
                                                             variant=rng.randint(0, 999))
        items.append({"position": slot.position, "phase": slot.phase, "type": ctype,
                      "fell_back": fell_back, "payload": payload})
        picked.append(ctype)

    _allocate_dwell(items, duration)
    return items


def needed_generation_types(duration: int, task: TaskObject, interests: list[str],
                            seed: str, real_pool: list[dict] | None = None,
                            llm_picks: dict[int, str] | None = None) -> list[dict]:
    """Dry-run of plan() returning only the slots that WILL need generation
    (position + type), so the LLM batch can pre-generate their payloads in one
    call (session-create latency, docs/02 §6). Must receive the same
    `llm_picks` as the real plan() call or positions would shift."""
    items = plan(duration, task, interests, seed, real_pool=real_pool,
                 pregen_payloads=None, llm_picks=llm_picks)
    return [{"position": i["position"], "type": i["type"]}
            for i in items if "payload" in i]


def _allocate_dwell(items: list[dict], duration: int) -> None:
    budget = duration * 60
    nominal = [DWELL_NOMINAL[i["type"]] for i in items]
    total = sum(nominal)
    remaining = budget
    for it, nom in zip(items, nominal):
        seconds = max(15, round(budget * nom / total))
        if it is items[-1]:
            seconds = remaining  # absorb rounding at the terminal card
        seconds = min(seconds, remaining)
        it["planned_seconds"] = seconds
        remaining -= seconds
    # if budget wasn't fully consumed (clamping), top up the mid-sequence understanding card
    if remaining > 0 and len(items) > 2:
        items[-2]["planned_seconds"] += remaining
