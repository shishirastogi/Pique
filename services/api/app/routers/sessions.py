from sqlalchemy import select
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import err
from app.core.security import get_current_user
from app.db import get_db, ContentSource, Task, User
from app.schemas import (SessionCompleteIn, SessionEventsIn, SessionItemsOut, SessionOut,
                         SessionCreateIn)
from app.services import session_service

router = APIRouter()


@router.post("", response_model=SessionOut, status_code=201)
def create(body: SessionCreateIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    session = session_service.create_session(db, user, body.task_id, body.duration_minutes)
    task = db.scalar(select(Task).where(Task.id == session.task_id))
    return session_service.session_out(session, task)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    session = session_service.get_owned_session(db, user, session_id)
    task = db.scalar(select(Task).where(Task.id == session.task_id))
    return session_service.session_out(session, task)


@router.get("/{session_id}/items", response_model=SessionItemsOut)
def items(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = session_service.get_owned_session(db, user, session_id)
    ids = [i.content_id for i in session.items]
    sources = {s.content_id: s for s in db.scalars(
        select(ContentSource).where(ContentSource.content_id.in_(ids))).all()} if ids else {}
    return SessionItemsOut(items=[session_service.card_for(i, sources.get(i.content_id))
                                  for i in session.items])


@router.post("/{session_id}/events")
def events(session_id: str, body: SessionEventsIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    session = session_service.get_owned_session(db, user, session_id)
    if session.status != "SESSION_ACTIVE":
        raise err(409, "CONFLICT", "Session is no longer active")
    return session_service.record_events(db, session, body.events)


@router.post("/{session_id}/complete")
def complete(session_id: str, body: SessionCompleteIn, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    session = session_service.get_owned_session(db, user, session_id)
    return session_service.complete_session(db, user, session, body)
