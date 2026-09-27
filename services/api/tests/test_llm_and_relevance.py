"""LLM layer (fallback contract) + ingestion relevance gate — all offline."""
import json

import pytest

from app.db import SessionLocal
from app.providers.base import RawAsset
from app.services import generation, ingestion, task_parser

PARSE_OK = json.dumps({
    "goal": "exam_prep", "category": "education", "subject": "physics",
    "topic": "Quantum Mechanics", "subtopics": ["Superposition"],
    "level": "beginner", "urgency": "tomorrow", "duration_minutes": None,
    "language": "en"})

GEN_OK = json.dumps({"items": [
    {"position": 0, "type": "meme", "title": "Quantum students",
     "body": "Nobody:\nMy brain: but the cat is BOTH"},
    {"position": 4, "type": "poll", "title": "Pick your confusion",
     "body": "Which of these?", "options": ["Superposition", "Entanglement", "All of it"]},
]})


class FakeProvider:
    name = "fake"

    def __init__(self, text):
        self._text = text

    def complete(self, system, user, *, json_mode=False, timeout_s=None):
        return self._text


def test_llm_parse_success(monkeypatch):
    monkeypatch.setattr(task_parser.ai, "complete", lambda *a, **k: PARSE_OK)
    t = task_parser.parse_task("study quantum mechanics for my exam tomorrow")
    assert t.topic == "Quantum Mechanics" and t.level == "beginner" and t.goal == "exam_prep"


def test_llm_parse_falls_back_on_garbage(monkeypatch):
    monkeypatch.setattr(task_parser.ai, "complete", lambda *a, **k: "not json")
    t = task_parser.parse_task("I need to study thermodynamics, I'm weak at it")
    assert "Thermodynamics" in t.topic and t.level == "beginner"   # heuristic path


def test_llm_disabled_by_default():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.core.config.settings.llm_provider", "none")
    assert task_parser.ai.get_provider() is None
    assert task_parser.ai.complete("s", "u") is None
    monkeypatch.undo()


def test_llm_batch_generation(monkeypatch):
    monkeypatch.setattr(generation.ai, "complete", lambda *a, **k: GEN_OK)
    t = task_parser._parse_heuristic("study quantum mechanics, I'm new to it")
    slots = [{"position": 0, "type": "meme"}, {"position": 4, "type": "poll"}]
    payloads = generation.generate_session_payloads(slots, t, ["cricket"], None)
    assert payloads is not None
    assert payloads[0]["body"].startswith("Nobody:")
    poll = payloads[4]
    assert poll["interaction"]["kind"] == "poll" and len(poll["interaction"]["options"]) == 3


def test_llm_batch_invalid_item_falls_back_per_slot(monkeypatch):
    """Poll without options is dropped -> that slot template-generates instead."""
    bad = json.dumps({"items": [{"position": 4, "type": "poll", "body": "…"}]})
    monkeypatch.setattr(generation.ai, "complete", lambda *a, **k: bad)
    t = task_parser._parse_heuristic("study quantum mechanics")
    out = generation.generate_session_payloads([{"position": 4, "type": "poll"}], t, [], None)
    assert out == {}  # empty mapping -> caller treats as per-slot template fallback


class IrrelevantProvider:
    name = "stubjunk"

    def search(self, query, limit):
        return [RawAsset(provider=self.name, source_id="junk-1",
                         source_url="https://x/1", media_url="https://cdn.x/1.jpg",
                         title="Two-dimensional schematic of quartz silica",  # no topic words
                         license="CC BY 4.0", suggested_type="diagram")]


def test_relevance_gate_drops_offtopic(monkeypatch):
    monkeypatch.setattr(ingestion, "enabled_providers", lambda: [IrrelevantProvider()])
    db = SessionLocal()
    try:
        report = ingestion.ingest_topic(db, "thermodynamics", per_provider=3)
        assert report["stubjunk"]["stored"] == 0
        assert report["stubjunk"]["skipped_irrelevant"] == 1
    finally:
        db.close()
