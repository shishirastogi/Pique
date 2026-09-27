"""LockService (docs/03 A.10 · docs/04 §5). Slice: DB-only (Redis TTL later)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import err
from app.core.time import now_utc
from app.db import LockState

EMERGENCY_CONFIRM_PHRASE = "I NEED TO STOP"  # friction gate (docs/05 §9)


def active_lock(db: Session, user_id: str) -> LockState | None:
    lock = db.scalar(select(LockState).where(LockState.user_id == user_id))
    if lock is not None and lock.lock_until > now_utc():
        return lock
    return None


def start_lock(db: Session, user_id: str, session_id: str, minutes: int) -> LockState:
    from datetime import timedelta

    lock = db.scalar(select(LockState).where(LockState.user_id == user_id))
    if lock is None:
        lock = LockState(user_id=user_id)
    lock.lock_until = now_utc() + timedelta(minutes=minutes)
    lock.session_id = session_id
    lock.broken_at = None
    db.add(lock)
    return lock


def emergency_unlock(db: Session, user_id: str, confirm: str) -> LockState:
    if confirm != EMERGENCY_CONFIRM_PHRASE:
        raise err(422, "VALIDATION", f'Type "{EMERGENCY_CONFIRM_PHRASE}" exactly to unlock early.')
    lock = db.scalar(select(LockState).where(LockState.user_id == user_id))
    if lock is None:
        raise err(404, "NOT_FOUND", "No lock to clear")
    lock.broken_at = now_utc()      # logged for the lock_break metric (docs/13 §2)
    lock.lock_until = now_utc()
    db.add(lock)
    db.commit()
    return lock
