"""Session + Lock services (docs/03 A.3, A.10 · docs/04 working rules).

Slice notes: generation is synchronous (mock content is instant); the
"resume active session" branch covers app restarts mid-warm-up.
"""
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import err
from app.core.time import iso_z, now_utc
from app.db import (Content, ContentSource, LockState, SessionModel, SessionItem,
                    Task, User, UserProfile,
                    SESSION_ACTIVE, COMPLETED, ABANDONED)
from app.schemas import (ContentCard, Interaction, MediaRef, SessionCompleteIn,
                         SessionOut, TaskObject)
from app.services import generation, media_enrichment, retrieval, selection, sequencing
from app.services.card_renderer import ensure_visual
from app.services.lock_service import active_lock, start_lock
from app.ai import base as ai_base
from app.ai import get_provider


def _enrich_generated_media(p: dict, task: TaskObject) -> dict:
    """Real media for humor cards when keys exist (imgflip meme / giphy gif),
    else the owned SVG renderer. Returns provenance overrides for the
    content_sources row (docs/11 S2)."""
    if p["type"] == "meme":
        meme = media_enrichment.caption_meme(p.get("title") or task.topic, p.get("body", ""))
        if meme:
            p["media"] = {"kind": "image", "url": meme["url"]}
            return {"provider": "imgflip", "source_url": meme["page_url"],
                    "license": "Imgflip API terms", "creator": meme["template"]}
    elif p["type"] == "reaction_gif":
        gif = media_enrichment.find_gif(f"{task.topic} study mood")
        if gif:
            p["media"] = {"kind": "image", "url": gif["url"]}
            return {"provider": "giphy", "source_url": gif["page_url"],
                    "license": "GIPHY terms", "creator": gif["title"],
                    "attribution_required": True, "attribution_text": "Powered by GIPHY"}
    ensure_visual(p)  # owned SVG cards as universal fallback
    return {"provider": "mock", "license": "owned"}


def _task_object(task: Task) -> TaskObject:
    return TaskObject(
        goal=task.goal or "learn", category=task.category or "education",
        subject=task.subject, topic=task.topic, subtopics=task.subtopics or [],
        level=task.level, urgency=task.urgency, duration_minutes=task.duration_minutes,
        language=task.language, confidence=task.confidence,
    )


def session_out(session: SessionModel, task: Task) -> SessionOut:
    return SessionOut(
        session_id=session.id, status=session.status, task=_task_object(task),
        duration_minutes=session.duration_minutes, planned_items=session.planned_items,
        started_at=iso_z(session.started_at), ends_at=iso_z(session.ends_at),
    )


def create_session(db: Session, user: User, task_id: str, duration: int) -> SessionModel:
    if duration not in settings.duration_options:
        raise err(422, "VALIDATION", f"duration must be one of {settings.duration_options}")

    lock = active_lock(db, user.id)
    if lock is not None:  # lock invariant: server refuses new sessions while locked (04 §2)
        raise err(409, "LOCKED", "Warm-up locked.", {"lock_until": iso_z(lock.lock_until)})

    active = db.scalar(select(SessionModel).where(
        SessionModel.user_id == user.id, SessionModel.status == SESSION_ACTIVE))
    if active is not None:
        return active  # resume (crash/multi-device semantics, 04 §8)

    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise err(404, "NOT_FOUND", "Task not found")

    profile = user.profile
    interests = (profile.interests if profile and profile.personalization_enabled else []) or []

    now = now_utc()
    session = SessionModel(
        user_id=user.id, task_id=task.id, duration_minutes=duration,
        started_at=now, ends_at=now + timedelta(minutes=duration),
    )
    db.add(session)
    db.flush()

    task_obj = _task_object(task)
    real_pool = retrieval.fetch_candidates(db, task_obj, needed=sequencing.SIZE[duration])
    pool_dicts = [
        {"content_id": c.id, "type": c.type, "scores": c.scores or {}, "media": c.media,
         "title": c.title, "body": (c.body or "")[:70],
         "has_media": bool((c.media or {}).get("url"))}
        for c in real_pool
        if c.type in sequencing.TYPES_IN_SLOTS
    ]
    seed = f"{session.id}:{uuid4()}"

    # 1) LLM curation of the real pool (docs/09-lite); None -> heuristic picks
    slots_for_pick = [s.__dict__ for s in sequencing.slot_template(
        duration, interests[0] if interests else None)]
    llm_picks = selection.select_for_slots(slots_for_pick, pool_dicts, task_obj, interests)

    # 2) one LLM batch for all to-be-generated slots (latency: docs/02 §6);
    #    None -> per-slot template fallback inside plan()
    slots_missing = sequencing.needed_generation_types(duration, task_obj, interests,
                                                       seed=seed, real_pool=pool_dicts,
                                                       llm_picks=llm_picks)
    pregen = generation.generate_session_payloads(
        slots_missing, task_obj, interests,
        profile.humor_preference if profile and profile.personalization_enabled else None)
    plan = sequencing.plan(duration, task_obj, interests,
                           seed=seed, real_pool=pool_dicts, pregen_payloads=pregen,
                           llm_picks=llm_picks)
    session.planned_items = len(plan)
    for item in plan:
        if "existing_content_id" in item:   # real pool item already persisted w/ provenance
            content_id = item["existing_content_id"]
        else:
            p = item["payload"]
            gen_src = p.pop("gen_source", "mock")      # which engine wrote this card
            provenance = _enrich_generated_media(p, task_obj)   # imgflip/giphy/SVG/owned
            if gen_src == "llm":
                gen_by = f"llm-{getattr(ai_base, 'last_used', None) or 'unknown'}"
            else:
                gen_by = "mock-template"
            content = Content(
                type=item["type"], title=p["title"], body=p["body"], language=p["language"],
                topic=p["topic"], subtopics=p["subtopics"], tags=p["tags"],
                difficulty=p["difficulty"], tone=p["tone"], humor_style=p["humor_style"],
                media=p["media"], interaction=p["interaction"], scores=p["scores"],
                status="active", generated_by=gen_by,
            )
            db.add(content)
            db.flush()
            src = {"provider": "mock", "source_url": None, "license": "owned",
                   "attribution_required": False}
            src.update(provenance)
            db.add(ContentSource(content_id=content.id, **src))
            content_id = content.id
        db.add(SessionItem(session_id=session.id, content_id=content_id,
                           position=item["position"], phase=item["phase"],
                           planned_seconds=item["planned_seconds"]))
    db.commit()
    db.refresh(session)
    return session


def get_owned_session(db: Session, user: User, session_id: str) -> SessionModel:
    session = db.scalar(select(SessionModel).where(
        SessionModel.id == session_id, SessionModel.user_id == user.id))
    if session is None:
        raise err(404, "NOT_FOUND", "Session not found")
    return session


def card_for(item: SessionItem, source: ContentSource | None = None) -> ContentCard:
    c = item.content
    attribution = None
    if source and source.attribution_required and source.attribution_text:
        attribution = {"required": True, "text": source.attribution_text,
                       "source_url": source.source_url}
    return ContentCard(
        content_id=c.id, position=item.position, phase=item.phase,
        planned_seconds=item.planned_seconds, type=c.type, title=c.title, body=c.body,
        media=MediaRef(**c.media) if c.media else None,
        attribution=attribution,
        interaction=Interaction(**c.interaction) if c.interaction else Interaction(kind="none"),
    )


def record_events(db: Session, session: SessionModel, events) -> dict:
    for ev in events:
        if ev.type == "item_shown" and ev.position is not None:
            it = next((i for i in session.items if i.position == ev.position), None)
            if it and it.shown_at is None:
                it.shown_at = now_utc()
        elif ev.type == "item_done" and ev.position is not None:
            it = next((i for i in session.items if i.position == ev.position), None)
            if it:
                it.dwell_ms = ev.dwell_ms
                it.skipped = bool(ev.skipped)
                it.engagement = ev.engagement
        elif ev.type == "initiation_reported" and ev.started is not None:
            session.started_work_confirmed = ev.started  # retro report (05 §11)
            session.initiation_reported_at = now_utc()
    force = now_utc() > session.ends_at + timedelta(seconds=settings.session_grace_seconds)
    db.commit()
    return {"server_now": iso_z(now_utc()), "force_complete": force}


def complete_session(db: Session, user: User, session: SessionModel,
                     payload: SessionCompleteIn) -> dict:
    if session.status in (COMPLETED, ABANDONED):  # idempotent (07 §4.8)
        lock = active_lock(db, user.id)
        return {"status": session.status,
                "lock": {"lock_until": iso_z(lock.lock_until) if lock else iso_z(now_utc()),
                         "minutes": user.profile.lock_minutes if user.profile else settings.lock_default_minutes}}

    session.status = ABANDONED if payload.abandoned else COMPLETED
    session.completed_at = now_utc()
    session.abandon_reason = payload.abandon_reason
    if payload.started_work_confirmed is not None:
        session.started_work_confirmed = payload.started_work_confirmed
        session.initiation_reported_at = now_utc()
    minutes = user.profile.lock_minutes if user.profile else settings.lock_default_minutes
    lock = start_lock(db, user.id, session.id, minutes)  # end-early still locks (04 §6)
    db.commit()
    return {"status": "LOCKED", "lock": {"lock_until": iso_z(lock.lock_until), "minutes": minutes}}
