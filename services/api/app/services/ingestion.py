"""IngestionService — slice pipeline (docs/11): S2 provenance precheck ->
S3 dedup -> S5 heuristic classify -> S7 moderation-lite -> persist.

Full worker stages (OCR, LLM classification, embeddings, scoring) arrive in
the content-pipeline phase; the stage contract is already honored here.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import embeddings
from app.core.time import now_utc
from app.db import Content, ContentSource
from app.providers import RawAsset, enabled_providers

_DENY = re.compile(r"\b(nsfw|nude|nudity|gore|porn)\b", re.I)  # moderation-lite; §12 full screens later


def ingest_topic(db: Session, topic: str, per_provider: int = 10,
                 providers: list | None = None) -> dict:
    """Fetch+normalize+persist active content for a topic. Idempotent per
    (provider, source_id) — safe to re-run (docs/11 §2). `providers` override
    is used by on-demand fill to stick to fast providers (08 §5).
    Provider searches run in parallel threads (latency: docs/02 §6)."""
    from concurrent.futures import ThreadPoolExecutor

    clients = providers if providers is not None else enabled_providers()

    def fetch(client) -> tuple[str, list]:
        try:
            assets = client.search(topic, per_provider)
            # image providers also pull diagram-targeted results (docs/08 §2)
            if client.name in ("wikimedia", "openverse"):
                assets += client.search(f"{topic} diagram", max(2, per_provider // 3))
            return client.name, assets
        except Exception as e:  # provider down/limited -> circuit skip (08 §7)
            return client.name, e

    with ThreadPoolExecutor(max_workers=max(len(clients), 1)) as ex:
        fetched = list(ex.map(fetch, clients))

    report = {}
    for (name, assets), client in zip(fetched, clients):
        if isinstance(assets, Exception):
            report[name] = {"error": str(assets)[:200]}
            continue
        counts = {"fetched": len(assets), "stored": 0, "skipped_license": 0,
                  "skipped_dup": 0, "skipped_safety": 0, "skipped_irrelevant": 0}
        to_store = []
        for a in assets:
            verdict = _precheck(a)
            if verdict == "license":
                counts["skipped_license"] += 1
                continue
            if verdict == "safety":
                counts["skipped_safety"] += 1
                continue
            if not _relevant(a, topic):
                counts["skipped_irrelevant"] += 1
                continue
            if _is_dup(db, a):
                counts["skipped_dup"] += 1
                continue
            to_store.append(a)
        # batch-embed when embeddings enabled (docs/09-lite); None -> lexical path
        vectors = embeddings.embed([f"{a.title or ''} {a.body or ''}"[:500] for a in to_store],
                                   task="RETRIEVAL_DOCUMENT") if to_store else None
        for a, vec in zip(to_store, vectors or [None] * len(to_store)):
            _persist(db, a, topic, embedding=vec)
            counts["stored"] += 1
        report[name] = counts
    db.commit()
    return report


# summary pages whose description is a place/person/creative-work — the classic
# "Botany Bay" trap: word overlap says relevant, the page is a Sydney suburb.
_TRAP_DESC = ("suburb", "town", "city", "village", "district", "municipality",
              "county", "provence", "island", "bay", "river", "mountain",
              "film", "album", "song", "band", "novel", "series", "footballer",
              "cricketer", "surname", "given name", "actress", "actor", "singer",
              "electorate", "constituency", "parliamentary", "ship", "railway")


def _relevant(a: RawAsset, topic: str) -> bool:
    """Relevance gate: at least one topic word (>3 chars) must appear in the
    asset's own metadata, AND it's not a name-collision trap page (Wikipedia
    summaries of places/people/songs sharing the topic word).
    Full semantic matching replaces this with embeddings in 09 (docs/09)."""
    desc = (a.meta.get("wikipedia_description") or "").lower()
    if desc and any(t in desc for t in _TRAP_DESC) and topic.lower() not in desc:
        return False
    words = {w.lower() for w in re.split(r"\W+", topic) if len(w) > 3}
    if not words:
        return True
    haystack = f"{a.title or ''} {a.body or ''} {desc}".lower()
    return any(w in haystack for w in words)


def _precheck(a: RawAsset) -> str | None:
    """S2 provenance + S7 moderation-lite."""
    if not a.license:                       # no license metadata: never admitted
        return "license"
    if not a.source_url and not a.source_id:
        return "license"
    text = f"{a.title or ''} {a.body or ''}"
    if _DENY.search(text):
        return "safety"
    if a.media_url and not a.media_url.startswith("https://"):
        return "safety"
    return None


def _is_dup(db: Session, a: RawAsset) -> bool:
    if db.scalar(select(ContentSource).where(
            ContentSource.provider == a.provider, ContentSource.source_id == a.source_id)):
        return True
    # content-level: same plate/caption re-uploaded under another File page
    # (common on Commons; source-id dedup can't catch it)
    norm_title = re.sub(r"\W+", "", (a.title or "")[:60].lower())
    norm_body = re.sub(r"\W+", "", (a.body or "")[:80].lower())
    if not norm_title and not norm_body:
        return False
    rows = db.scalars(select(Content).where(Content.status == "active").limit(2000)).all()
    for c in rows:
        if (re.sub(r"\W+", "", (c.title or "")[:60].lower()) == norm_title and
                re.sub(r"\W+", "", (c.body or "")[:80].lower()) == norm_body):
            return True
    return False


def _persist(db: Session, a: RawAsset, topic: str, embedding: list | None = None) -> Content:
    title = a.title or (a.body[:80] if a.body else None)
    body = a.body or f"THIS is what part of {topic.lower()} actually looks like. Keep it in mind while you work."
    scores = {
        "relevance": 0.6,                      # real scoring arrives with the ranker (09)
        "curiosity": 0.7 if a.suggested_type == "diagram" else 0.6,
        "quality": 0.75 if title else 0.6,
        "learning_value": 0.8 if a.suggested_type in ("diagram", "book_excerpt") else 0.65,
        "humor": 0.1,
    }
    content = Content(
        type=a.suggested_type, title=title[:200] if title else None, body=body,
        topic=topic, subtopics=[], tags=[topic.lower()], language="en",
        media={"kind": "image", "url": a.media_url, **{k: v for k, v in a.meta.items() if v}}
              if a.media_url else {"kind": "none"},
        scores=scores, embedding=embedding, status="active",
        generated_by=None, created_at=now_utc(),
    )
    db.add(content)
    db.flush()
    db.add(ContentSource(
        content_id=content.id, provider=a.provider, source_id=a.source_id,
        source_url=a.source_url, creator=a.creator, license=a.license,
        license_url=a.license_url, attribution_required=a.attribution_required,
        attribution_text=a.attribution_text, fetchable=a.fetchable, fetched_at=now_utc(),
    ))
    return content
