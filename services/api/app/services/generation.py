"""GenerationService — docs/03 A.5. Uses the configured LLM provider
(one batch call per session for latency) with strict validation and a
per-item fallback to the template generator, so sessions NEVER fail on
LLM errors (docs/04 §8)."""
import json
import logging

from app import ai
from app.ai.prompts import BATCH_GEN_SYSTEM, batch_gen_user
from app.schemas import TaskObject

log = logging.getLogger("pique.generation")

_INTERACTION_KIND = {"poll": "poll", "question": "question", "challenge": "challenge",
                     "joke": "reveal", "trivia": "reveal"}


def generate_session_payloads(slots: list[dict], task: TaskObject,
                              interests: list[str], humor: str | None) -> dict[int, dict] | None:
    """One LLM batch -> {position: payload}. Returns None when unconfigured or
    failed (caller then per-slot falls back to templates)."""
    if not slots:
        return None
    slots = [s for s in slots if s["type"] != "first_work_action"]  # template stays deterministic
    if not slots:
        return None
    analogy_pos = next((s["position"] for s in slots if s["type"] == "analogy"), None)
    try:
        raw = ai.complete(
            BATCH_GEN_SYSTEM,
            batch_gen_user(slots, task.topic, task.subtopics, task.level or "beginner",
                           interests, humor, task.language, analogy_pos),
            json_mode=True)
        if raw is None:
            return None
        data = json.loads(_strip_fences(raw))
        by_pos = {i.get("position"): i for i in data.get("items", [])}
        out: dict[int, dict] = {}
        for s in slots:
            payload = _adapt(by_pos.get(s["position"]), s["type"], task)
            if payload is not None:  # invalid/missing items: caller template-fallback per slot
                out[s["position"]] = payload
        return out
    except Exception as e:
        log.warning("llm batch generation failed, using templates: %s", e)
        return None


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    return raw


def _adapt(item: dict | None, ctype: str, task: TaskObject) -> dict | None:
    """LLM JSON -> generator payload shape (content_generator.generate_item)."""
    if not item:
        return None
    body = (item.get("body") or "").strip()
    if not body:
        return None
    interaction = None
    kind = _INTERACTION_KIND.get(ctype)
    if kind == "poll":
        options = [str(o) for o in (item.get("options") or [])][:4]
        if len(options) < 2:
            return None
        interaction = {"kind": "poll", "question": item.get("title") or "Quick pulse",
                       "options": options}
    elif kind == "question":
        interaction = {"kind": "question", "hint": item.get("hint") or "",
                       "answer": item.get("answer") or ""}
    elif kind == "reveal":
        interaction = {"kind": "reveal", "reveal": item.get("reveal") or ""}
    elif kind == "challenge":
        interaction = {"kind": "challenge"}
    return {
        "type": ctype, "topic": task.topic, "subtopics": task.subtopics,
        "tags": [task.topic.lower()], "language": task.language,
        "difficulty": task.level or "beginner", "tone": None,
        "humor_style": None if ctype not in ("meme", "joke") else "nerdy",
        "title": (item.get("title") or None), "body": body,
        "media": {"kind": "none"}, "interaction": interaction,
        "gen_source": "llm",  # provenance marker: which engine wrote this card
        "scores": {"relevance": 0.85, "personalization": 0.8, "curiosity": 0.8,
                   "quality": 0.75, "learning_value": 0.7},  # real scoring in 09
    }
