"""Semantic (embedding) candidate ordering — docs/09-lite b. Offline: embed()
is stubbed; vectors chosen so the cosine-closest row must win despite a lower
lexical score."""
from app.db import SessionLocal, Content, ContentSource
from app.schemas import TaskObject
from app.services import retrieval
from app.services.retrieval import _cosine


def _mk(title, scores, embedding, db):
    """Pool candidates need whitelisted provenance (anti-recycling rule)."""
    c = Content(type="interesting_fact", title=title, body="entropy", topic="entropy",
                tags=["entropy"], scores=scores, embedding=embedding)
    db.add(c)
    db.flush()
    db.add(ContentSource(content_id=c.id, provider="wikipedia",
                         source_url="https://en.wikipedia.org/wiki/X", license="CC BY-SA 4.0"))
    return c


def test_cosine():
    assert abs(_cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9
    assert _cosine([], [1.0]) == 0.0


def test_semantic_rank_beats_lexical(monkeypatch):
    db = SessionLocal()
    near = _mk("Entropy disorder note", {"relevance": 0.5, "quality": 0.5}, [1.0, 0.0, 0.0], db)
    far = _mk("Unrelated but shiny", {"relevance": 0.95, "quality": 0.95}, [0.0, 1.0, 0.0], db)
    _mk("No vector", {"relevance": 0.4, "quality": 0.4}, None, db)
    db.commit()

    monkeypatch.setattr("app.ai.embeddings.embed",
                        lambda texts, task="RETRIEVAL_DOCUMENT": [[1.0, 0.0, 0.0]])
    t = TaskObject(goal="learn", category="education", subject=None, topic="entropy",
                   subtopics=[], level="beginner", urgency=None, duration_minutes=None,
                   language="en", confidence=0.8)
    pool = retrieval._db_pool(db, t, limit=5)
    db.close()
    assert pool[0].title == "Entropy disorder note"   # cosine winner
    assert all(c is not None for c in pool)