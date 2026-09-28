from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.time import iso_z, now_utc
from app.db import get_db, User
from app.schemas import EmergencyUnlockIn, LockStatusOut
from app.services import lock_service

router = APIRouter()


@router.get("/status", response_model=LockStatusOut)
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lock = lock_service.active_lock(db, user.id)
    if lock is None:
        return LockStatusOut(locked=False)
    remaining = int((lock.lock_until - now_utc()).total_seconds())
    mins = user.profile.lock_minutes if user.profile else 120
    return LockStatusOut(locked=True, lock_until=iso_z(lock.lock_until),
                         remaining_seconds=max(remaining, 0), session_id=lock.session_id,
                         minutes=mins)


@router.post("/emergency-unlock", response_model=LockStatusOut)
def emergency_unlock(body: EmergencyUnlockIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    lock_service.emergency_unlock(db, user.id, body.confirm)
    return LockStatusOut(locked=False)
