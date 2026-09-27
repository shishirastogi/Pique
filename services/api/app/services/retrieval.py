"""RetrievalService — slice (docs/03 A.4 · docs/09 §3).

DB pool match via sqlite LIKE (semantic pgvector search lands in the ranking
phase), topped up by on-demand provider fetch when the pool is thin
(docs/08 §5). Generated content fills the rest in the planner.
"""
import math
import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai import embeddings
from app.core.config import settings
from app.db import Content, ContentSource
from app.schemas import TaskObject
from app.services import ingestion


def _cosine(a: list, b: list) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    return dot / (na * nb) if na and nb else 0.0


# Pool whitelist: only genuinely sourced external content joins the candidate
# pool. Generated per-session cards (mock/llm/imgflip/giphy) stay session-scoped —
# recycling them across sessions re-serves stale text and bakes in old parser
# topics (the "Botany Tommorow" bug class the user hit).
_POOLABLE_PROVIDERS = {"wikimedia", "openverse", "wikipedia", "gutenberg", "smithsonian", "loc"}


def fetch_candidates(db: Session, task: TaskObject, needed: int) -> list[Content]:
    pool = _db_pool(db, task, limit=max(needed * 4, 40))
    if len(pool) < needed * 2 and (settings.openverse_enabled or settings.wikimedia_enabled
                                   or settings.gutenberg_enabled):
        _on_demand_fetch(db, task)          # best effort, failure-tolerant
        pool = _db_pool(db, task, limit=max(needed * 4, 40))
    return pool


def _db_pool(db: Session, task: TaskObject, limit: int) -> list[Content]:
    words = [w.lower() for w in re.split(r"\W+", task.topic) if len(w) > 2]
    words += [s.lower() for s in (task.subtopics or [])]
    if not words:
        words = [task.topic.lower()]
    clauses = [c for w in set(words) for c in (
        Content.topic.ilike(f"%{w}%"),
        Content.title.ilike(f"%{w}%"),
        Content.body.ilike(f"%{w}%"),
    )]
    rows = db.scalars(select(Content).where(
        Content.status == "active", or_(*clauses)).limit(limit * 3)).all()
    if not rows:
        return []
    prov = {s.content_id: s.provider for s in db.scalars(
        select(ContentSource).where(ContentSource.content_id.in_([r.id for r in rows]))).all()}
    # whitelist + same-image / same-title dedupe (docs/11 S3 surface-level)
    seen: set[tuple] = set()
    filtered: list[Content] = []
    for c in rows:
        if prov.get(c.id) not in _POOLABLE_PROVIDERS:
            continue
        key = (re.sub(r"\W+", "", (c.title or "")[:60].lower()),
               re.sub(r"\W+", "", (c.body or "")[:80].lower()))  # same plate/caption, any URL
        if key in seen:
            continue
        seen.add(key)
        filtered.append(c)
        if len(filtered) >= limit:
            break
    rows = filtered

    # semantic ordering when embeddings are available; else lexical-lite
    qv = embeddings.embed([f"{task.topic} {' '.join(task.subtopics)}"],
                          task="RETRIEVAL_QUERY")
    qv = qv[0] if qv else None

    def score(c: Content) -> float:
        lex = (c.scores or {}).get("relevance", 0.5) + (c.scores or {}).get("quality", 0.5)
        if task.topic.lower() in (c.topic or "").lower():
            lex += 0.5
        if qv is not None:  # semantic blend; rows lacking vectors score cosine 0
            return 0.75 * _cosine(qv, c.embedding or []) + 0.25 * lex  # docs/09 §3 hybrid
        return lex
    return sorted(rows, key=score, reverse=True)


def _on_demand_fetch(db: Session, task: TaskObject) -> None:
    from app.providers import enabled_providers
    from app.providers.base import tight
    # tighten fast providers' budgets: on-demand must stay snappy
    # (docs/02 §6 p95 session-create < 8s); full timeouts are for prefetch
    fast = [tight(p, connect=2.0, read=8.0)
            for p in enabled_providers() if getattr(p, "on_demand_ok", True)]
    try:
        ingestion.ingest_topic(db, task.topic, per_provider=settings.on_demand_per_provider,
                               providers=fast)
    except Exception:
        pass  # never let a provider break session creation (04 §8)
