"""LLM slot-selection (docs/09-lite) + provider chain failover — offline."""
import json

from app import ai
from app.services import selection, task_parser


class FakeFail:
    name = "broken"

    def complete(self, *a, **k):
        raise RuntimeError("429 quota")


class FakeOk:
    name = "ok"

    def __init__(self, text):
        self._text = text

    def complete(self, *a, **k):
        return self._text


def test_chain_failover(monkeypatch):
    providers = {"broken": FakeFail(), "ok": FakeOk("hello")}
    monkeypatch.setattr(ai.base, "get_provider", lambda name=None: providers.get(name or "none"))
    monkeypatch.setattr("app.core.config.settings.llm_provider", "broken,ok")
    assert ai.complete("s", "u") == "hello"


def test_chain_all_fail_returns_none(monkeypatch):
    monkeypatch.setattr(ai.base, "get_provider", lambda name=None: FakeFail() if name else None)
    monkeypatch.setattr("app.core.config.settings.llm_provider", "broken,gone")
    assert ai.complete("s", "u") is None
    # callers must degrade silently
    monkeypatch.setattr(selection.ai, "complete", lambda *a, **k: None)
    assert selection.select_for_slots([{"position": 4, "phase": "curiosity",
                                        "allowed_types": ["diagram"]}],
                                      [{"content_id": "c1", "type": "diagram",
                                        "title": "x"}], task_parser._parse_heuristic("study x"), []) is None


def _setup(monkeypatch, payload):
    monkeypatch.setattr(selection.ai, "complete", lambda *a, **k: json.dumps(payload))


def test_selection_validates_and_respects_slots(monkeypatch):
    slots = [
        {"position": 4, "phase": "curiosity", "allowed_types": ["diagram", "interesting_fact"]},
        {"position": 7, "phase": "understanding", "allowed_types": ["diagram"]},
        {"position": 9, "phase": "understanding", "allowed_types": ["micro_lesson"],
         "force_type": "micro_lesson"},  # force-typed slots: never eligible
    ]
    cands = [
        {"content_id": "a", "type": "diagram", "title": "Engine cycle diagram"},
        {"content_id": "b", "type": "diagram", "title": "Another diagram"},
        {"content_id": "c", "type": "micro_lesson", "title": "Lesson"},
    ]
    # LLM tries: dup reuse (a twice), wrong-type (c into diagram slot) — both must be filtered
    _setup(monkeypatch, {"picks": {"4": "a", "7": "a", "9": "c"}})
    out = selection.select_for_slots(slots, [{**c, "has_media": True} for c in cands],
                                     task_parser._parse_heuristic("study engines"), [])
    assert out == {4: "a", 7: "b"} or out == {4: "a"}  # 7 dedup: 'a' reused -> rejected
    assert 9 not in out  # force_type slot excluded


def test_selection_none_when_no_llm():
    # conftest disables llm -> selection must quietly return None
    out = selection.select_for_slots(
        [{"position": 4, "phase": "curiosity", "allowed_types": ["diagram"]}],
        [{"content_id": "a", "type": "diagram", "title": "t"}],
        task_parser._parse_heuristic("study entropy"), [])
    assert out is None
