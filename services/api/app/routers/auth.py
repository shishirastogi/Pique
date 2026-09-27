from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.core.security import create_token
from app.db import get_db, User, UserProfile
from app.schemas import AuthSessionIn, AuthSessionOut

router = APIRouter()


@router.post("/auth/session", response_model=AuthSessionOut, status_code=201)
def create_session_token(body: AuthSessionIn, db: Session = Depends(get_db)):
    """Anonymous device account (docs/07 §4.1). Email linking post-MVP."""
    user = db.scalar(select(User).where(User.device_fp == body.device_fp))
    is_new = user is None
    if is_new:
        user = User(device_fp=body.device_fp)
        db.add(user)
        db.flush()
        db.add(UserProfile(user_id=user.id))
        db.commit()
        db.refresh(user)
    return AuthSessionOut(access_token=create_token(user.id), user_id=user.id, is_new_user=is_new)
