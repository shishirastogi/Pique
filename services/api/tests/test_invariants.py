"""Invariant tests from docs/15-testing-qa.md §2 — product rules as tests.

Covered: finiteness + terminal card + dwell budget (1), lock invariant (2),
no rabbit-hole fields (3), type adjacency + interaction pacing (5),
auth error envelope.
"""
import pytest

SIZE = {5: 10, 10: 20, 15: 28, 20: 36}
HUMOR_MIN = {5: 2, 10: 3, 15: 4, 20: 4}
HUMOR_TYPES = {"meme", "joke", "reaction_gif"}
INTERACTIVE = {"poll", "question", "challenge"}
PHASE_ORDER = ["entertainment", "curiosity", "understanding", "activation"]


def _mk_task(client, auth, text="I need to study thermodynamics for my exam, I'm weak at it"):
    r = client.post("/api/v1/tasks/parse", headers=auth, json={"raw_text": text})
    assert r.status_code == 200, r.text
    return r.json()["task_id"]


def test_seq_finiteness_and_terminal_card(client, auth):
    for duration, expected in SIZE.items():
        task_id = _mk_task(client, auth)
        r = client.post("/api/v1/sessions", headers=auth,
                        json={"task_id": task_id, "duration_minutes": duration})
        assert r.status_code == 201, r.text
        sid = r.json()["session_id"]
        assert r.json()["planned_items"] == expected

        items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
        assert len(items) == expected                      # finite
        assert items[-1]["type"] == "first_work_action"    # terminal card (10 §4.1)
        assert items[-1]["phase"] == "activation"
        assert sum(i["planned_seconds"] for i in items) == duration * 60  # time budget
        client.post(f"/api/v1/sessions/{sid}/complete", headers=auth,
                    json={"started_work_confirmed": True})
        client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_humor_quota(client, auth):
    """User-set rule: meme hooks position 0; humor cards scale 2-4 by duration."""
    for duration, min_humor in HUMOR_MIN.items():
        sid = client.post("/api/v1/sessions", headers=auth, json={
            "task_id": _mk_task(client, auth), "duration_minutes": duration}).json()["session_id"]
        items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
        types = [i["type"] for i in items]
        assert types[0] == "meme"
        assert sum(1 for t in types if t in HUMOR_TYPES) >= min_humor
        client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
        client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_seq_structure_rules(client, auth):
    task_id = _mk_task(client, auth)
    sid = client.post("/api/v1/sessions", headers=auth,
                      json={"task_id": task_id, "duration_minutes": 20}).json()["session_id"]
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
    types = [i["type"] for i in items]
    n = len(items)

    # no adjacent same type (10 §4.2)
    assert all(types[i] != types[i + 1] for i in range(n - 1))
    # interaction pacing (10 §4.4): none at 0-1, none at N-2; at least one overall
    assert not (set(types[:2]) & INTERACTIVE)
    assert types[n - 2] not in INTERACTIVE
    assert set(types) & INTERACTIVE
    # phases non-decreasing in the arc order (10 §3)
    idx = [PHASE_ORDER.index(i["phase"]) for i in items]
    assert idx == sorted(idx)
    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_lock_invariant(client, auth):
    task_id = _mk_task(client, auth)
    sid = client.post("/api/v1/sessions", headers=auth,
                      json={"task_id": task_id, "duration_minutes": 5}).json()["session_id"]
    r = client.post(f"/api/v1/sessions/{sid}/complete", headers=auth,
                    json={"started_work_confirmed": True})
    lock_until = r.json()["lock"]["lock_until"]
    assert r.json()["status"] == "LOCKED" and lock_until

    st = client.get("/api/v1/lock/status", headers=auth).json()
    assert st["locked"] and st["remaining_seconds"] > 7000  # ~2h

    # new sessions refused while locked → 409 LOCKED (docs/04 §2.1)
    r2 = client.post("/api/v1/sessions", headers=auth,
                     json={"task_id": _mk_task(client, auth), "duration_minutes": 5})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "LOCKED"

    # complete is idempotent (07 §4.8)
    again = client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    assert again.json()["lock"]["lock_until"] == lock_until

    # emergency unlock requires the exact phrase (05 §9)
    bad = client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "let me out"})
    assert bad.status_code == 422
    good = client.post("/api/v1/lock/emergency-unlock", headers=auth,
                       json={"confirm": "I NEED TO STOP"})
    assert good.json()["locked"] is False

    # and sessions work again after unlock
    r3 = client.post("/api/v1/sessions", headers=auth,
                     json={"task_id": _mk_task(client, auth), "duration_minutes": 5})
    assert r3.status_code == 201
    client.post(f"/api/v1/sessions/{r3.json()['session_id']}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_no_rabbit_hole_fields(client, auth):
    """Items payload must not offer related-content hooks (docs/15 §2.3)."""
    task_id = _mk_task(client, auth)
    sid = client.post("/api/v1/sessions", headers=auth,
                      json={"task_id": task_id, "duration_minutes": 10}).json()["session_id"]
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
    forbidden = {"related", "more_like_this", "recommended", "up_next", "next_items"}
    for i in items:
        assert forbidden.isdisjoint(i.keys())
    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_events_and_auth_envelope(client, auth):
    task_id = _mk_task(client, auth)
    sid = client.post("/api/v1/sessions", headers=auth,
                      json={"task_id": task_id, "duration_minutes": 10}).json()["session_id"]
    r = client.post(f"/api/v1/sessions/{sid}/events", headers=auth, json={"events": [
        {"type": "item_shown", "position": 0},
        {"type": "item_done", "position": 0, "dwell_ms": 12000, "skipped": False},
        {"type": "heartbeat"},
    ]})
    assert r.status_code == 200 and r.json()["force_complete"] is False

    # unauthenticated + envelope shape (07 §3)
    r2 = client.get("/api/v1/lock/status")
    assert r2.status_code == 401
    body = r2.json()
    assert set(body["error"].keys()) >= {"code", "message"}

    # report flow stores a report and continues (05 §7)
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
    rr = client.post("/api/v1/content/report", headers=auth,
                     json={"content_id": items[0]["content_id"], "reason": "other"})
    assert rr.status_code == 201

    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_custom_lock_timing_and_minimum_one_hour(client, auth):
    task_id = _mk_task(client, auth)

    # Less than 60 minutes is rejected by validation (minimum 1 hour)
    bad = client.post("/api/v1/sessions", headers=auth,
                      json={"task_id": task_id, "duration_minutes": 5, "lock_minutes": 30})
    assert bad.status_code == 422

    # Custom lock duration of 90 minutes (1.5 hours) is accepted
    r = client.post("/api/v1/sessions", headers=auth,
                    json={"task_id": task_id, "duration_minutes": 5, "lock_minutes": 90})
    assert r.status_code == 201
    sid = r.json()["session_id"]

    comp = client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    assert comp.status_code == 200
    assert comp.json()["lock"]["minutes"] == 90

    st = client.get("/api/v1/lock/status", headers=auth).json()
    assert st["locked"] is True
    assert st["minutes"] == 90
    assert 5000 < st["remaining_seconds"] <= 5400  # 90 mins = 5400s

    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})

