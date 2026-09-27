"""SelectionService (docs/09-lite): the LLM decides which pool candidates go
into the session's slots — semantic relevance + intrigue, per slot role.

Falls back to heuristic scoring when no LLM is configured/quota-free.
One call per session; id -> position mapping validated defensively.
"""
import json
import logging

from app import ai
from app.schemas import TaskObject

log = logging.getLogger("pique.selection")

_SYSTEM = """You are the curator for a FocusWarmup session — a short warm-up that must make
the user genuinely curious so they go start the real task. You choose WHICH existing
content cards go into which slots.

Rules:
- Prefer cards that are clearly about the topic; kill anything off-topic even if well-made.
- Visual cards (has_media) are valuable in visual slots; text-only is fine elsewhere.
- Match the slot's allowed types exactly; fit the phase vibe (curiosity = questions/history,
  understanding = explanations/diagrams).
- Maximize "huh, interesting" per card; prefer beginner-friendly when level is beginner.
- Return ONLY JSON: {"picks": {"<position>": "<candidate_id>" or null}}.
  null = "no good candidate; generate one instead"."""

_MAX_CANDIDATES = 40


def select_for_slots(slots: list[dict], candidates: list[dict],
                     task: TaskObject, interests: list[str]) -> dict[int, str] | None:
    """->{position: content_id}. slots: [{position, phase, allowed_types}],
    candidates: [{content_id, type, title, has_media}]. None => heuristic path."""
    # only slots that may take pool content (force-typed slots skip: memes etc.)
    open_slots = [s for s in slots if not s.get("force_type")]
    if not open_slots or not candidates:
        return None
    cand_lines = [
        f'- {c["content_id"]} | type={c["type"]} | media={bool(c.get("has_media"))} | {str(c.get("title") or c.get("body", ""))[:70]}'
        for c in candidates[:_MAX_CANDIDATES]
    ]
    slot_lines = [f'- pos {s["position"]}: phase={s["phase"]}, types={"|".join(s["allowed_types"])}'
                  for s in open_slots]
    user = f"""Topic: {task.topic} (subtopics: {', '.join(task.subtopics) or 'general'}, level: {task.level or 'beginner'})
User interests: {', '.join(interests) if interests else 'general'}

SLOTS:
{chr(10).join(slot_lines)}

CANDIDATES:
{chr(10).join(cand_lines)}

Pick the best candidate id per slot (or null)."""
    try:
        raw = ai.complete(_SYSTEM, user, json_mode=True, timeout_s=12.0)
        if not raw:
            return None
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        picks_raw = data.get("picks") or {}
        valid_ids = {c["content_id"] for c in candidates}
        used: set[str] = set()
        out: dict[int, str] = {}
        type_by_id = {c["content_id"]: c["type"] for c in candidates[:_MAX_CANDIDATES]}
        slot_types = {s["position"]: set(s["allowed_types"]) for s in open_slots}
        for pos_s, cid in picks_raw.items():
            try:
                pos = int(pos_s)
            except (TypeError, ValueError):
                continue
            if (not cid) or cid not in valid_ids or cid in used or pos not in slot_types:
                continue
            if type_by_id.get(cid) not in slot_types[pos]:
                continue  # never trust the LLM over slot constraints (docs/10 §4)
            used.add(cid)
            out[pos] = cid
        log.info("llm selection: %d/%d slots filled from pool", len(out), len(open_slots))
        return out or None
    except Exception as e:
        log.warning("llm selection failed, heuristic fallback: %s", e)
        return None
