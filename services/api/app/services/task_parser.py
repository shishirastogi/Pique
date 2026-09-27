"""TaskParserService — docs/03 A.2. LLM-primary (configured provider),
heuristic fallback. The heuristic path keeps the app fully functional offline /
keyless; it intentionally returns a clarifying question when level can't be
inferred, to exercise the clarify flow (docs/05 §3)."""
import json
import logging
import re

from app import ai
from app.ai.prompts import TASK_PARSE_SYSTEM, task_parse_user
from app.schemas import ClarifyingQuestion, TaskObject

log = logging.getLogger("pique.task_parser")

_GOAL_MAP = [
    (("exam", "study", "studying", "revise", "revision", "test", "assignment", "homework"),
     ("exam_prep", "education")),
    (("design", "poster", "logo", "thumbnail", "illustration", "draw"),
     ("design", "creative")),
    (("write", "essay", "blog", "article", "script", "story"),
     ("create", "creative")),
    (("learn", "understand", "practice", "code", "build", "implement"),
     ("learn", "education")),
]
_LEVEL_HINTS = {
    "beginner": ("weak", "beginner", "new to", "basics", "never", "struggling", "start"),
    "intermediate": ("intermediate", "some", "basic knowledge", "familiar"),
    "advanced": ("advanced", "expert", "deep dive", "master"),
}
_URGENCY_WORDS = ("tonight", "tomorrow", "today", "asap", "this week", "next week", "soon")
_STOPWORDS = set(
    "i me my we our need needed to a an the for and or of in on at with about "
    "have has had do does did im ive really just please want must should this that "
    "is are was were be been being it its as by from up out so too very "
    "study studying learn learning understand design write create make build "
    "implement prepare exam exams test tests assignment homework tomorrow tonight "
    "tommorow tommorrow tomorow tonite 2moro today soon weak basics new totally "
    "completely kind sort pretty quite actually basically literally honestly stuff "
    "things thing something anything everything hard easy fast quickly slowly "
    "before after because dont cant wont"
    .split()
)
# artifact words are the DELIVERABLE, not the subject — "design a poster about X"
# should extract topic X, never make cards about "Poster"
_ARTIFACT_WORDS = {"poster", "logo", "thumbnail", "video", "presentation", "essay",
                   "blog", "article", "flyer", "banner", "slideshow", "slides",
                   "report", "cover", "illustration"}


def parse_task(raw_text: str, profile_language: str = "en") -> TaskObject:
    """LLM first (when configured), heuristic mock as the durable fallback."""
    obj = _parse_with_llm(raw_text, profile_language)
    if obj is not None:
        return obj
    return _parse_heuristic(raw_text, profile_language)


def _parse_with_llm(raw_text: str, profile_language: str) -> TaskObject | None:
    try:
        raw = ai.complete(TASK_PARSE_SYSTEM, task_parse_user(raw_text, profile_language),
                          json_mode=True, timeout_s=10.0)
        if raw is None:
            return None
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        data["language"] = data.get("language") or profile_language
        data["confidence"] = 0.9
        data.setdefault("subtopics", [])
        return TaskObject(**{k: v for k, v in data.items() if k in TaskObject.model_fields})
    except Exception as e:
        log.warning("llm parse failed, falling back to heuristics: %s", e)
        return None


def _parse_heuristic(raw_text: str, profile_language: str = "en") -> TaskObject:
    text = raw_text.strip()
    lower = text.lower()

    goal, category = "learn", "education"
    for words, gc in _GOAL_MAP:
        if any(w in lower for w in words):
            goal, category = gc
            break

    level = next((lv for lv, hints in _LEVEL_HINTS.items() if any(h in lower for h in hints)), None)
    urgency = next((u for u in _URGENCY_WORDS if u in lower), None)

    duration = None
    m = re.search(r"(\d+)\s*(?:min|mins|minutes)", lower)
    if m:
        n = int(m.group(1))
        duration = min((5, 10, 15, 20), key=lambda d: abs(d - n))

    topic = _extract_topic(text, lower)
    subtopics = _guess_subtopics(lower, topic)

    confidence = 0.5 + (0.2 if level else 0.0) + (0.1 if urgency else 0.0) + (0.2 if len(topic) > 2 else 0.0)
    return TaskObject(
        goal=goal, category=category, subject=None, topic=topic, subtopics=subtopics,
        level=level, urgency=urgency, duration_minutes=duration,
        language=profile_language, confidence=round(min(confidence, 0.95), 2),
    )


def needs_clarification(task: TaskObject) -> ClarifyingQuestion | None:
    """At most ONE question (docs/01 §5). Mock: only level."""
    if task.level is None:
        return ClarifyingQuestion(
            field="level",
            question=f"How familiar are you with {task.topic}?",
            options=["beginner", "intermediate", "advanced"],
        )
    return None


def refine_with_answer(task: TaskObject, answer: str) -> TaskObject:
    data = task.model_dump()
    a = answer.strip().lower()
    if a in ("beginner", "intermediate", "advanced"):
        data["level"] = a
        data["confidence"] = min(data["confidence"] + 0.2, 0.95)
    return TaskObject(**data)


def _extract_topic(text: str, lower: str) -> str:
    for pat in (r"(?:study|studying|learn|learning|understand|practice)\s+(.+?)(?:\s+for\b|$)",
                r"(?:design|write|create|make|build|implement|prepare for)\s+(?:a|an|the)?\s*(.+?)(?:\s+for\b|$)",
                r"(?:exam|test|assignment|homework)(?:\s+(?:on|about|in|tomorrow|today))?\s*(.+)?$"):
        m = re.search(pat, lower)
        if m and m.group(1):
            words = [w for w in re.findall(r"[a-z0-9#$+.]+", m.group(1))
                     if w not in _STOPWORDS and len(w) > 1]
            if words and words[0] in _ARTIFACT_WORDS and len(words) > 1:
                words = [w for w in words if w not in _ARTIFACT_WORDS] or words
            if words:
                return " ".join(words[:5]).title()
    words = [w for w in re.findall(r"[a-z0-9#$+.]+", lower) if w not in _STOPWORDS and len(w) > 2]
    return " ".join(words[:4]).title() if words else "Your Task"


def _guess_subtopics(lower: str, topic: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9#$+.]+", lower) if w not in _STOPWORDS and len(w) > 3]
    return [w.title() for w in words[:3]] or [topic]
